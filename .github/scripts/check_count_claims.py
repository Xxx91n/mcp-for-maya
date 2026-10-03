"""D-216 count-claims gate — retires bare count/enumeration claims in live docs.

Legislated by ``docs/decision-ledger.md`` row D-216 and ADR-0029. One unified
entry point, per-family derivers dispatched internally, a family table fixed
in this script, plus a denylist layer (D-216②) for historical drifted strings.

Discriminator (D-216①): a count claim in a versioned doc is a normative claim
and MUST be machine-checked when a reader relies on it being true *now*, or
when a code change can invalidate it. A claim that only describes the state at
some past time is a point-in-time record and is exempt — but only where it
carries a point-in-time marker.

Exemptions actually implemented (and the ones deliberately NOT needed):

- CHANGELOG.md (D-216④) — TOPMOST ``## [x.y.z]`` section only; the section
  label is itself the point-in-time marker. ``## [Unreleased]`` is skipped
  (same precedent as check_tool_count_claims.py). The 0.1.0 section's "11
  audit checks" is a real 0.1.0 artifact claim and is not asserted.
- Transcription (D-216⑤) — needs no table: the surface glob asserts a source
  doc and its transcribers in the same pass (README / README.zh-CN / AGENTS /
  llms.txt / skills/** all restate the same three families), so no claim is
  exempt merely for being a copy of another doc's claim.
- ``docs/decision-ledger.md`` and ``docs/adr/**`` stay IN the surface. Their
  Chinese "11 维" / "9/11维" phrases are quotes of past audit findings, not
  claims about the present, and the claim shapes below do not read them as
  claims (pinned by ``test_past_records_quoting_counts_are_not_claims``).

The three migrated families (D-216③), each derived from a live AST literal:

===========================  ============================================  =====
family                       derived from                                 n
===========================  ============================================  =====
scene_review checks          ``maya_scene_module.py::scene_review``        11
                             ``checks = [...]``
aesthetic dimensions         ``maya_scene_module.py``                      5
                             ``::_compute_full_aesthetic_score``
                             ``weights = {...}``
shot types                   ``maya_scene_module.py::SHOT_TYPES``          8
===========================  ============================================  =====

Values are read statically via ``ast`` — the lint job runs without project
dependencies installed, so importing ``maya_mcp_server`` is not available.
The shot-type source was verified to be a live dict literal in source
(D-216③ precondition), not a docstring.

Claim shapes are the ones the live docs actually use, not a general noun-phrase
grammar: a false positive that blocks the lint job gets the shape deleted, a
missed shape gets a new pattern. Known residual false-positive risk: the zh
"N 项检查" shape cannot distinguish a scene_review count from an unrelated
"N 项检查" (e.g. a pre-commit run); no live doc uses that shape today.
"""

from __future__ import annotations

import ast
import re
import sys
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple


REPO = Path(__file__).resolve().parent.parent.parent
MODULE = Path("src/maya_mcp_server/maya_scene_module.py")
CHANGELOG = Path("CHANGELOG.md")

# Assertion surface. Whole file for normative docs (D-216①: a reader decides on
# them now). CHANGELOG is handled separately — topmost release section only.
SURFACE_FILES = ("README.md", "README.zh-CN.md", "AGENTS.md", "llms.txt", "CONTEXT.md")
SURFACE_DIRS = ("docs", "skills")

# D-216② denylist layer: literal strings this repo's docs are known to have
# drifted to. Reactive complement to the derived layer above it — it catches a
# drifted number whose shape still parses cleanly (clockify keeps both layers).
# Every entry is reproducible with `git log -S"<needle>"`.
_DENYLIST: tuple[tuple[str, str], ...] = (
    (
        "9 universal audit dimensions",
        "scene_review check count drifted to 9 and was labelled a dimension count "
        "(git log -S, baa0d29); the check count is derived from scene_review",
    ),
    (
        "9维度审核",
        "zh mirror of the 9-vs-11 review-check drift (git log -S, baa0d29)",
    ),
    (
        "9 维度审核",
        "zh mirror of the 9-vs-11 review-check drift (git log -S, baa0d29)",
    ),
    (
        "11 维度审核",
        "the review CHECK count labelled as a dimension count (git log -S, baa0d29)",
    ),
    (
        "11 dimensions",
        "the scene_review CHECK count labelled as a dimension count (git log -S, "
        "baa0d29); the dimension count is derived from _compute_full_aesthetic_score",
    ),
)


class Family(NamedTuple):
    """One count-claim family: what it counts, where truth lives, its shapes."""

    name: str
    source: str
    derive: Callable[[Path], int]
    claims: tuple[re.Pattern[str], ...]


def _count_literal(root: Path, func: str | None, name: str) -> int:
    """Element count of the first ``name = <list|dict literal>`` (AST-only).

    ``func`` scopes the search to one function body; ``None`` searches the
    whole module. Raises ValueError when the literal is absent — a renamed or
    refactored source must fail the gate (exit 2), never silently count 0.
    """
    tree = ast.parse((root / MODULE).read_text(encoding="utf-8"))
    scope: ast.AST = tree
    if func is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == func:
                scope = node
                break
        else:
            raise ValueError(f"{func} not found in {MODULE}")
    for node in ast.walk(scope):
        if isinstance(node, ast.Assign):
            targets: list[ast.expr] = list(node.targets)
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            continue
        if not any(isinstance(t, ast.Name) and t.id == name for t in targets):
            continue
        if isinstance(node.value, ast.List):
            return len(node.value.elts)
        if isinstance(node.value, ast.Dict):
            return len(node.value.keys)
    raise ValueError(f"{name} list/dict literal not found in {MODULE} (function={func})")


def review_checks(root: Path) -> int:
    return _count_literal(root, "scene_review", "checks")


def aesthetic_dimensions(root: Path) -> int:
    return _count_literal(root, "_compute_full_aesthetic_score", "weights")


def shot_types(root: Path) -> int:
    return _count_literal(root, None, "SHOT_TYPES")


# The (?<![\d./]) lookbehind keeps a version string ("[0.6.0]"), a fraction and a
# slash alternation ("9/11维") from donating digits to a claim's N.
FAMILIES: tuple[Family, ...] = (
    Family(
        name="scene_review checks",
        source="src/maya_mcp_server/maya_scene_module.py::scene_review.checks",
        derive=review_checks,
        claims=(
            re.compile(r"(?<![\d./])(\d+)(?:[ \t]+[A-Za-z][A-Za-z_-]*)*[ \t]+checks?\b", re.I),
            re.compile(
                r"(?<![\d./])(\d+)[ \t]*项(?:[ \t]*(?:确定性|通用))*[ \t]*(?:检查项|检查|审核|审查)"
            ),
        ),
    ),
    Family(
        name="aesthetic dimensions",
        source="src/maya_mcp_server/maya_scene_module.py::_compute_full_aesthetic_score.weights",
        derive=aesthetic_dimensions,
        claims=(
            re.compile(
                r"(?<![\d./])(\d+)(?:-[ \t]+dimensions?\b"
                r"|[ \t]+(?:[A-Za-z][A-Za-z_-]*[ \t]+)*dimensions?\b)",
                re.I,
            ),
            re.compile(
                r"(?<![\d./])(\d+)[ \t]*维(?:度|审美|分析|审核|美学|轴|空间构图)"
                r"(?![\u3400-\u9fff])"
            ),
        ),
    ),
    Family(
        name="shot types",
        source="src/maya_mcp_server/maya_scene_module.py::SHOT_TYPES",
        derive=shot_types,
        claims=(
            re.compile(
                r"(?<![\d./])(\d+)(?:[ \t]+[A-Za-z][A-Za-z_-]*)*[ \t]+shot[ \t]+types?\b", re.I
            ),
            re.compile(
                r"(?<![\d./])(\d+)[ \t]*种[ \t]*(?:行业标准[ \t]*)?"
                r"(?:镜头[ \t]*类型|镜头|景别|类型)"
            ),
        ),
    ),
)


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def last_release_section(text: str) -> tuple[int, str, str]:
    """(start_line, label, section_text) of the topmost numbered release.

    Identical precedent to check_tool_count_claims.py (D-121): sections are
    delimited by ``## [label]``, ``Unreleased`` is skipped because it is not a
    release artifact, and everything below the topmost one is a frozen
    snapshot (D-216④).
    """
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"^## \[(.+?)\]", text, re.M)]
    for i, (pos, label) in enumerate(heads):
        if label.strip().lower() == "unreleased":
            continue
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        return _line_of(text, pos), label, text[pos:end]
    return 0, "", ""


def surface_files(root: Path) -> list[Path]:
    """Repo-relative versioned docs asserted whole-file, sorted for stability."""
    found: list[Path] = [Path(name) for name in SURFACE_FILES if (root / name).is_file()]
    for name in SURFACE_DIRS:
        base = root / name
        if base.is_dir():
            found.extend(p.relative_to(root) for p in base.rglob("*.md"))
    return sorted(found)


def check(root: Path) -> tuple[dict[str, int], list[tuple[str, int, str]]]:
    """(derived counts per family, [(file, line, message)] violations)."""
    derived = {f.name: f.derive(root) for f in FAMILIES}
    hits = {f.name: 0 for f in FAMILIES}
    violations: list[tuple[str, int, str]] = []

    sections: list[tuple[Path, int, str]] = [
        (rel, 0, (root / rel).read_text(encoding="utf-8")) for rel in surface_files(root)
    ]
    changelog = root / CHANGELOG
    if changelog.is_file():
        start, _label, section = last_release_section(changelog.read_text(encoding="utf-8"))
        sections.append((CHANGELOG, start - 1, section))

    for rel, offset, text in sections:
        for fam in FAMILIES:
            expected = derived[fam.name]
            for rx in fam.claims:
                for m in rx.finditer(text):
                    hits[fam.name] += 1
                    claimed = int(m.group(1))
                    if claimed != expected:
                        violations.append(
                            (
                                str(rel),
                                offset + _line_of(text, m.start()),
                                f"[{fam.name}] claims {claimed} ({m.group(0)!r}); "
                                f"{fam.source} derives {expected}",
                            )
                        )
        for needle, why in _DENYLIST:
            for m in re.finditer(re.escape(needle), text, re.I):
                violations.append(
                    (
                        str(rel),
                        offset + _line_of(text, m.start()),
                        f"denylisted drifted string {needle!r} — {why}",
                    )
                )

    for name, count in hits.items():
        if count == 0:
            violations.append(
                (
                    "",
                    0,
                    f"[{name}] asserted on 0 live claims — the family is vacuous; "
                    f"restore a claim or record why the carrier went away",
                )
            )
    return derived, violations


def main() -> int:
    try:
        derived, violations = check(REPO)
    except (OSError, ValueError, SyntaxError) as e:
        print(f"::error::count-claims checker error — {e}")
        return 2
    for rel, line, msg in violations:
        where = f"file={rel},line={line}::" if rel else "::"
        print(f"::error {where}count-claim violation — {msg}")
    if violations:
        print(
            "Fix the doc claim or the source. Do not delete the claim shape unless "
            "it is a documented false positive (D-216 denylist/derived split)."
        )
        return 1
    summary = ", ".join(f"{name}={n}" for name, n in derived.items())
    print(f"count claims OK: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
