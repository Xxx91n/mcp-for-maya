"""D-175 TDQS disclosure elements static ratchet.

Asserts that required disclosure elements (legislated by ADR-0028 and
cataloged in docs/adr/0028-elements.yaml) are present in the live
tool docstrings across the codebase.

Elements are defined with either:
  - any: list of regex patterns (at least one must match)
  - all: list of literal strings (every string must be present)

D-180: mutation-class existence assertions MUST be polarity-aware \u2014
a statement like "without auto_fix mutations" must not satisfy an
assertion that a mutation exists (S-03 lesion: the old autofix_mutation
assertion was satisfied by the negated sentence and CI went fake-green).
Elements opt in via 'polarity_aware: true'; during the legislated
observation period a match occurring only inside a negation scope is
reported as a warning, not an error.

D-190 hardened the mechanism form (execution-window product, deliberately
not legislated here): the negation scope is the enclosing CLAUSE instead of
a fixed 80-char window, and an element may list the legitimate
negation-form phrases that forgive a cue in 'positive_exemptions'.
Direction limit (D-190 3): polarity_aware belongs only on mutation-class
existence assertions whose pattern set is purely positive \u2014 negation-form
pattern elements stay unguarded and rely on the exemption list instead.
The hardened form passed the live corpus with zero false rejections
(asserted in tests/test_check_tdqs_disclosure.py); warn may be promoted to
hard only after that corpus stays clean, reviewed at the 0.6.0 preflight
(D-189/D-190 4).

Hard-gated in the CI lint job alongside other check scripts.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent.parent
DEFAULT_ELEMENTS = REPO / "docs" / "adr" / "0028-elements.yaml"

# Execution-window-owned mechanism form (D-190, warn observation period):
# a match is negated when a negation cue appears in the same CLAUSE before
# the match start. Clause scope, not a fixed window — the retired 80-char
# form flagged legitimate disclosures whose cue sat in an earlier clause
# ("Not idempotent \u2014 each call adds another camera").
#
# Corpus evidence — both tracks, reproduced by
# .github/scripts/polarity_corpus_probe.py (stdlib, manual: run it, do not
# wire it into CI; it measures, it does not gate). PRIMARY surface, the
# denominator the D-190(4) zero-false-rejection judgement uses: each tool
# against its own docstring and its own elements = 36 elements, 1 guarded,
# 0 negated-only, asserted live by
# tests/test_check_tdqs_disclosure.py::test_live_corpus_has_no_polarity_warnings
# STRESS surface, diagnostic only: 287 docstring-bearing functions x every
# element pattern = 357 matches, 53 inside the retired naive 80-char window,
# 4 inside clause scope (49 false rejections forgiven). All 4 survivors are
# correct negative-form disclosures on NEGATION-form elements (irreversible /
# read_only_disclosure / no_mutation_no_undo /
# overwrite_or_persistence_semantics), which carry no polarity_aware guard by
# the direction limit below, so they are never judged.
#
# Caliber note (D-191 1c): the stress denominator is 287 docstring-bearing
# functions. The 264 figure in the pre-hardening evidence was a probe artifact
# -- that probe keyed docstrings by bare function name into one dict, silently
# collapsing 23 same-named functions. Do not compare the two numbers as if
# they were the same corpus.
#
# The narrowed scope trades that FP class for cross-clause false negatives —
# the legislated direction (D-190 1: on a fake-green-prone gate an FN hurts
# less than FP noise).
#
# The boundary set is clause TERMINATORS only. A line wrap is deliberately
# not a boundary: the D-180 lesion sentence wraps in real docstrings, and
# forgiving it would reopen the fake-green hole. A terminator counts only
# when followed by whitespace, so decimals ("0.5.0") and abbreviations
# ("e.g.") do not split a clause.
CLAUSE_BOUNDARIES = re.compile(r"[.!?;:\u2014\u2013](?=\s|$)")
# The cue list stays deliberately small \u2014 broad lists
# false-positive on correct negative-form disclosures like "cannot be
# undone" / "does not persist" (five negation-form tokens already live in
# the elements file's own patterns).
NEGATION_CUES = re.compile(
    r"(?i)\b(?:no|not|never|without|cannot|can't|won't|don't|doesn't|didn't"
    r"|nor|neither)\b|\bnon[-\s]|instead of|rather than|free of"
)


def _clause_start(docstring: str, start: int) -> int:
    """Index at which the clause containing start begins (D-190 1)."""
    boundaries = list(CLAUSE_BOUNDARIES.finditer(docstring, 0, start))
    return boundaries[-1].end() if boundaries else 0


def _negated(docstring: str, start: int, exemptions: tuple[str, ...]) -> bool:
    """Match at start is negated if a cue sits in its clause before it.

    ``exemptions`` is the element's positive_exemptions list (D-190 2): a
    cue that BELONGS to one of those legitimate negation-form phrases is
    forgiven, because the phrase documents the negated property itself
    rather than negating this match. Scoped to the cue, not to the clause --
    each listed phrase is blanked out before the cue search, so one listed
    phrase cannot forgive an unrelated real negation in the same clause.
    """
    window = docstring[_clause_start(docstring, start) : start].lower()
    for phrase in exemptions:
        if phrase:
            window = window.replace(phrase.lower(), " ")
    return bool(NEGATION_CUES.search(window))


def find_tool_docstring(filepath: Path, tool_name: str) -> str | None:
    """Extract docstring of a named function or async function via AST."""
    try:
        tree = ast.parse(filepath.read_text(encoding="utf-8"), filename=str(filepath))
    except (OSError, SyntaxError):
        return None
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == tool_name:
                return ast.get_docstring(node)
    return None


def check(root: Path, elements_path: Path) -> tuple[bool, list[str], list[str], int]:
    """Validate disclosure elements against tool docstrings.

    Returns (ok, errors, warnings, checked_count). Polarity-aware
    elements whose only matches sit inside a negation scope produce
    warnings during the observation period, never errors.
    """
    try:
        data = json.loads(elements_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return False, [f"::error::cannot read elements file {elements_path}: {e}"], [], 0

    tools = data.get("tools", {})
    if not isinstance(tools, dict) or not tools:
        return False, ["::error::elements file must define a non-empty 'tools' map"], [], 0

    errors: list[str] = []
    warnings: list[str] = []
    checked_elements = 0

    for tool_name, tool_cfg in sorted(tools.items()):
        file_rel = tool_cfg.get("file")
        if not file_rel:
            errors.append(f"::error::tool '{tool_name}' missing 'file' attribute")
            continue

        file_path = root / file_rel
        if not file_path.exists():
            errors.append(f"::error file={file_rel}::file not found: {file_rel}")
            continue

        docstring = find_tool_docstring(file_path, tool_name)
        if docstring is None:
            errors.append(
                f"::error file={file_rel}::tool function '{tool_name}' or docstring not found"
            )
            continue

        req_elements = tool_cfg.get("required_elements", [])
        for elem in req_elements:
            checked_elements += 1
            eid = elem.get("id", "<unnamed>")
            why = elem.get("why", "")
            # Direction limit (D-190 3): only purely-positive pattern sets
            # carry the guard; negation-form elements stay unguarded.
            polarity = bool(elem.get("polarity_aware"))
            exempt = tuple(elem.get("positive_exemptions", ()))

            matched = False
            negated_only = False
            if "any" in elem:
                patterns = elem["any"]
                if polarity:
                    positive = negated = False
                    for pat in patterns:
                        for m in re.finditer(pat, docstring):
                            if _negated(docstring, m.start(), exempt):
                                negated = True
                            else:
                                positive = True
                    matched = positive
                    negated_only = negated and not positive
                else:
                    matched = any(re.search(pat, docstring) for pat in patterns)
            elif "all" in elem:
                literals = elem["all"]
                if polarity:
                    # all-literals are polarity-aware too: each literal must
                    # occur positively at least once; a literal surviving only
                    # inside negation windows cannot satisfy the assertion.
                    matched = True
                    lit_negated = False
                    for lit in literals:
                        occ = list(re.finditer(re.escape(lit), docstring))
                        if not occ:
                            matched = False
                        elif all(_negated(docstring, m.start(), exempt) for m in occ):
                            matched = False
                            lit_negated = True
                    negated_only = lit_negated
                else:
                    matched = all(lit in docstring for lit in literals)
            else:
                errors.append(
                    f"::error file={file_rel}::element '{eid}' for tool '{tool_name}' "
                    "defines neither 'any' nor 'all'"
                )
                continue

            if not matched:
                if negated_only:
                    warnings.append(
                        f"file={file_rel}::{tool_name} element '{eid}' matched only "
                        "inside negated statements \u2014 a negated claim must not satisfy "
                        "a mutation-class existence assertion (D-180 polarity-aware, "
                        "observation period)"
                    )
                else:
                    errors.append(
                        f"::error file={file_rel}::{tool_name} missing required disclosure "
                        f"element '{eid}' (why: {why})"
                    )

    return not errors, errors, warnings, checked_elements


def main() -> int:
    elements_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ELEMENTS
    ok, errors, warnings, total_checked = check(REPO, elements_path)
    for w in warnings:
        print(f"::warning::{w}")
    for err in errors:
        print(err)
    if not ok:
        print(
            "\nTDQS disclosure check failed. Tool definitions must satisfy the required "
            "disclosure elements legislated by ADR-0028."
        )
        print("See docs/adr/0028-elements.yaml for required element specifications and reasons.")
        return 1

    suffix = f" ({len(warnings)} polarity warnings)" if warnings else ""
    print(
        f"TDQS disclosure check OK: {total_checked} elements verified across "
        f"{len(tools_map(elements_path))} tools{suffix}."
    )
    return 0


def tools_map(elements_path: Path) -> dict:
    try:
        return json.loads(elements_path.read_text(encoding="utf-8")).get("tools", {})
    except Exception:
        return {}


if __name__ == "__main__":
    sys.exit(main())
