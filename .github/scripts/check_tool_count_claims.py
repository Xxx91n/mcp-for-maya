"""D-121 tool-count claim gate.

``N tools total``-style claims in live docs must equal the tool count
derived from ``pipeline.TOOL_ANNOTATIONS`` — the single source of
truth (D-018). The count is read statically via ``ast`` because the
lint job runs without project dependencies installed.

Assertion surface (live sections only):

- README.md, README.zh-CN.md, AGENTS.md, docs/threat-model.md —
  whole file
- CHANGELOG.md — the TOPMOST release section only. Historical release
  sections are true-at-their-time snapshots ([0.1.0] "20 tools" is the
  0.1.0 artifact's real count) and are exempt by construction.

Claim shapes asserted:

- ``<N> [qualifier words] tool[s] (in )?total`` — "25 tools total",
  "25 MCP tools in total"
- ``all <N> tools`` (case-insensitive) — "all 25 tools"
- zh-CN mirror equivalents — "共 25 个 MCP 工具", "全部 25 个工具"
  (extension of the D-121 shapes: without them the mirror surface
  would be unassertable)

Per-file counts like AGENTS.md's "13 scene / 2 visual tools" are NOT
total-context claims and are never asserted (D-121).
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent.parent
PIPELINE = Path("src/maya_mcp_server/pipeline.py")
SURFACE = [
    Path("README.md"),
    Path("README.zh-CN.md"),
    Path("AGENTS.md"),
    Path("docs/threat-model.md"),
]
CHANGELOG = Path("CHANGELOG.md")

_CLAIM_RES = [
    # <N> [qualifier words] tool[s] (in )?total — single-line shape; the
    # (?<![\d.]) lookbehind keeps version strings like [1.0.0] from
    # donating their last digits as the claim's N.
    re.compile(
        r"(?<![\d.])(\d+)[ \t]+(?:[A-Za-z_-]+[ \t]+)*?"
        r"tools?[ \t]+(?:in[ \t]+)?total\b",
        re.I,
    ),
    re.compile(r"\ball[ \t]+(\d+)[ \t]+tools?\b", re.I),
    re.compile(r"(?:共|全部)[ \t]*(\d+)[ \t]*个(?:[ \t]*[A-Za-z_-]+)*[ \t]*工具"),
]


def tool_count(pipeline_path: Path) -> int:
    """Number of keys in the TOOL_ANNOTATIONS dict literal (AST-only)."""
    tree = ast.parse(pipeline_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        targets = node.targets if isinstance(node, ast.Assign) else []
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        for t in targets:
            if (
                isinstance(t, ast.Name)
                and t.id == "TOOL_ANNOTATIONS"
                and isinstance(node.value, ast.Dict)
            ):
                return len(node.value.keys)
    raise ValueError(f"TOOL_ANNOTATIONS dict literal not found in {pipeline_path}")


def _line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def claims_in(text: str) -> list[tuple[int, int, str]]:
    """(line, claimed N, matched phrase) for every tool-total claim."""
    seen: set[tuple[int, int]] = set()
    out: list[tuple[int, int, str]] = []
    for rx in _CLAIM_RES:
        for m in rx.finditer(text):
            if (m.start(), m.end()) in seen:
                continue
            seen.add((m.start(), m.end()))
            out.append((_line_of(text, m.start()), int(m.group(1)), m.group(0)))
    out.sort()
    return out


def last_release_section(text: str) -> tuple[int, str, str]:
    """(start_line, label, section_text) of the topmost numbered release.

    Sections are delimited by ``## [label]`` headings; the section
    runs to the next such heading or EOF. ``Unreleased`` is skipped —
    it is not a release artifact and forward wording discipline
    (D-121) already bans absolute counts in new bullets.
    """
    heads = [(m.start(), m.group(1)) for m in re.finditer(r"^## \[(.+?)\]", text, re.M)]
    for i, (pos, label) in enumerate(heads):
        if label.strip().lower() == "unreleased":
            continue
        end = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        return _line_of(text, pos), label, text[pos:end]
    return 0, "", ""


def check(root: Path) -> tuple[int, list[tuple[str, int, str]]]:
    """(derived count, [(file, line, message)] violations)."""
    n = tool_count(root / PIPELINE)
    violations: list[tuple[str, int, str]] = []
    for rel in SURFACE:
        text = (root / rel).read_text(encoding="utf-8")
        for line, claimed, phrase in claims_in(text):
            if claimed != n:
                violations.append(
                    (
                        str(rel),
                        line,
                        f"claims {claimed} tools ({phrase!r}); pipeline.TOOL_ANNOTATIONS has {n}",
                    )
                )
    ch = (root / CHANGELOG).read_text(encoding="utf-8")
    start, label, section = last_release_section(ch)
    for line, claimed, phrase in claims_in(section):
        if claimed != n:
            violations.append(
                (
                    str(CHANGELOG),
                    start + line - 1,
                    f"[{label}] section claims {claimed} tools ({phrase!r}); "
                    f"pipeline.TOOL_ANNOTATIONS has {n}",
                )
            )
    return n, violations


def main() -> int:
    try:
        n, violations = check(REPO)
    except (OSError, ValueError, SyntaxError) as e:
        print(f"::error::{e}")
        return 2
    for rel, line, msg in violations:
        print(f"::error file={rel},line={line}::tool-count claim mismatch — {msg}")
    if violations:
        print(
            "Fix the claim or, if the tool surface changed, update every "
            "live claim in the same commit (D-121)."
        )
        return 1
    print(f"tool-count claims OK: all live claims == {n} (pipeline.TOOL_ANNOTATIONS)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
