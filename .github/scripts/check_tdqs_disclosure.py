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
observation period a match occurring only inside a negation window is
reported as a warning, not an error. Mechanism form (window width / cue
list / positive exemptions) is execution-window owned: it had to pass
the live 25-docstring corpus with zero false rejections before landing,
and may be promoted from warn to hard only after the corpus stays clean.

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

# Execution-window-owned mechanism form (D-180, warn observation period):
# a match is negated when a negation cue appears inside the window before
# the match start. The cue list stays deliberately small \u2014 broad lists
# false-positive on correct negative-form disclosures like "cannot be
# undone" / "does not persist" (five negation-form tokens already live in
# the elements file's own patterns).
#
# Corpus evidence (2026-09-30, all 264 src docstrings x every element
# pattern): 339 pattern matches, 53 fall inside a naive window — nearly all
# legitimate negative-form disclosures ("no undo rollback checkpoint",
# "cannot modify", "not idempotent — each call adds"). That is exactly why
# the flag is opt-in per element (mutation-class positive assertions only)
# and why hardening needs a refined mechanism (clause-scope window,
# positive exemptions) — not this naive window — before it may error.
POLARITY_WINDOW = 80
NEGATION_CUES = re.compile(
    r"(?i)\b(?:no|not|never|without|cannot|can't|won't|don't|doesn't|didn't"
    r"|nor|neither)\b|\bnon[-\s]|instead of|rather than|free of"
)


def _negated(docstring: str, start: int) -> bool:
    """Match at start is negated if a cue sits in the window before it."""
    window = docstring[max(0, start - POLARITY_WINDOW) : start]
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
    elements whose only matches sit inside negation windows produce
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
            polarity = bool(elem.get("polarity_aware"))

            matched = False
            negated_only = False
            if "any" in elem:
                patterns = elem["any"]
                if polarity:
                    positive = negated = False
                    for pat in patterns:
                        for m in re.finditer(pat, docstring):
                            if _negated(docstring, m.start()):
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
                        elif all(_negated(docstring, m.start()) for m in occ):
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
