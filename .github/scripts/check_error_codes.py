#!/usr/bin/env python3
"""Error-code doc gate (D-207 4): the documented code set == the code set in code.

Why this exists: a hand-maintained error-code table rots the moment someone
adds an exception class and forgets the doc. That direction is the dangerous
one - the doc then promises a code that does not exist, or hides one that does,
and an agent matching on `[code]` prefixes has nothing trustworthy to match.

So the page is DERIVED (D-183: no third source of truth) and this checker is
the gate. It reads the code set with `ast` - no import, so it works on a tree
that has no dependencies installed and cannot be fooled by import side effects.

Two directions, both errors:
  * a `PipelineError` subclass whose `code` is absent from the page
  * a code documented on the page that no `PipelineError` subclass declares

Usage:
    python .github/scripts/check_error_codes.py            # check repo state
    python .github/scripts/check_error_codes.py --print    # dump the code set

Exit codes: 0 = sets match; 1 = drift (message names both directions).
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
SECURITY_PY = REPO / "src" / "maya_mcp_server" / "security.py"
DOC = REPO / "docs" / "guide" / "error-codes.md"

# Doc rows carry the code in a leading inline-code span: | `invalid_input` | ...
_DOC_ROW = re.compile(r"^\|\s*`([a-z0-9_]+)`\s*\|", re.MULTILINE)

# The page carries the same codes twice: once in the body table (code -> class,
# meaning, what to do) and once in the "Test anchors" table (code -> pytest node
# ID). Scanning the whole file therefore let the anchor table satisfy a code
# whose body row had been deleted - the gate printed "doc set == code set" while
# the page documented nothing about that code. Exactly the empty-claim state
# D-207 4 forbids. So the two tables are read as two separate sets and each must
# be complete on its own.
_ANCHORS_HEADING = "## Test anchors"


def code_set() -> dict[str, str]:
    """{code: class name} for every PipelineError subclass, via AST.

    Walks the class tree rather than importing: a subclass of a subclass is
    still a code the agent can see in an isError body, so it counts.
    """
    tree = ast.parse(SECURITY_PY.read_text(encoding="utf-8"), filename=str(SECURITY_PY))
    found: dict[str, str] = {}

    def own_code(node: ast.ClassDef) -> str | None:
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign):
                continue
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id == "code":
                    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                        return stmt.value.value
        return None

    def bases(node: ast.ClassDef) -> set[str]:
        out: set[str] = set()
        for base in node.bases:
            if isinstance(base, ast.Name):
                out.add(base.id)
            elif isinstance(base, ast.Attribute):
                out.add(base.attr)
        return out

    is_error = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if "PipelineError" in bases(node) or "Exception" in bases(node):
                is_error.add(node.name)
    # second pass: inheritance (code-less subclasses inherit the parent code,
    # which is the real runtime behaviour, so record it under the subclass)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name in is_error:
            direct = own_code(node)
            if direct is not None:
                found[direct] = node.name

    # resolve inherited codes
    by_name = {n.name: own_code(n) for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    bmap = {n.name: bases(n) for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    for name in is_error:
        if name in found.values():
            continue
        seen: set[str] = set()
        stack = list(bmap.get(name, set()))
        while stack:
            b = stack.pop()
            if b in seen:
                continue
            seen.add(b)
            c = by_name.get(b)
            if c is not None:
                found[c] = name
                break
            stack.extend(bmap.get(b, set()))
    return found


def _rel(path: Path) -> str:
    """Repo-relative when possible; a tmp path in a test must not crash the gate."""
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return path.name


def _split_doc(text: str) -> tuple[str, str]:
    """(body, anchors). The heading is the boundary; a missing heading yields an
    empty anchors section rather than silently folding anchor rows into the body
    set, which is the hole this scoping exists to close."""
    i = text.find(_ANCHORS_HEADING)
    if i < 0:
        return text, ""
    return text[:i], text[i:]


def doc_set() -> set[str]:
    """Codes the page actually documents in its body table."""
    if not DOC.exists():
        return set()
    body, _anchors = _split_doc(DOC.read_text(encoding="utf-8"))
    return set(_DOC_ROW.findall(body))


def anchor_set() -> set[str]:
    """Codes the page pins to a test node ID."""
    if not DOC.exists():
        return set()
    _body, anchors = _split_doc(DOC.read_text(encoding="utf-8"))
    return set(_DOC_ROW.findall(anchors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print",
        dest="dump",
        action="store_true",
        help="print the code set found in security.py, then exit",
    )
    args = parser.parse_args(argv)

    codes = code_set()
    if args.dump:
        for code, cls in sorted(codes.items()):
            print(f"{code}\t{cls}")
        return 0

    if not DOC.exists():
        print(
            f"::error file={_rel(DOC)}::missing - the error "
            f"contract has {len(codes)} codes in security.py and no page to hold them"
        )
        return 1

    documented = doc_set()
    implemented = set(codes)
    missing = sorted(implemented - documented)
    extra = sorted(documented - implemented)
    anchored = anchor_set()
    unpinned = sorted(implemented - anchored)
    overpinned = sorted(anchored - implemented)

    for code in missing:
        print(
            f"::error file={_rel(DOC)}::code '{code}' "
            f"(security.py::{codes[code]}) is implemented but undocumented - add the "
            f"row with its pytest node ID (D-207 4)"
        )
    for code in extra:
        print(
            f"::error file={_rel(DOC)}::code '{code}' is "
            f"documented but no PipelineError subclass declares it - remove the row "
            f"(D-207 4)"
        )
    for code in unpinned:
        print(
            f"::error file={_rel(DOC)}::code '{code}' has no row in the "
            f"'{_ANCHORS_HEADING}' table - the page claims every code is pinned to a "
            f"test, so an unpinned code is an unbacked claim (D-207 4)"
        )
    for code in overpinned:
        print(
            f"::error file={_rel(DOC)}::'{_ANCHORS_HEADING}' pins '{code}' but no "
            f"PipelineError subclass declares it - remove the row (D-207 4)"
        )
    if missing or extra or unpinned or overpinned:
        return 1

    print(
        f"Error-code check OK: {len(codes)} codes; body set == code set and "
        f"anchor set == code set (D-207 4)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
