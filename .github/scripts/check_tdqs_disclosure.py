"""D-175 TDQS disclosure elements static ratchet.

Asserts that required disclosure elements (legislated by ADR-0028 and
cataloged in docs/adr/0028-elements.yaml) are present in the live
tool docstrings across the codebase.

Elements are defined with either:
  - any: list of regex patterns (at least one must match)
  - all: list of literal strings (every string must be present)

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


def check(root: Path, elements_path: Path) -> tuple[bool, list[str], int]:
    """Validate disclosure elements against tool docstrings.

    Returns (ok, errors, checked_count).
    """
    try:
        data = json.loads(elements_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        return False, [f"::error::cannot read elements file {elements_path}: {e}"], 0

    tools = data.get("tools", {})
    if not isinstance(tools, dict) or not tools:
        return False, ["::error::elements file must define a non-empty 'tools' map"], 0

    errors: list[str] = []
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

            matched = False
            if "any" in elem:
                patterns = elem["any"]
                matched = any(re.search(pat, docstring) for pat in patterns)
            elif "all" in elem:
                literals = elem["all"]
                matched = all(lit in docstring for lit in literals)
            else:
                errors.append(
                    f"::error file={file_rel}::element '{eid}' for tool '{tool_name}' "
                    "defines neither 'any' nor 'all'"
                )
                continue

            if not matched:
                errors.append(
                    f"::error file={file_rel}::{tool_name} missing required disclosure "
                    f"element '{eid}' (why: {why})"
                )

    return not errors, errors, checked_elements


def main() -> int:
    elements_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_ELEMENTS
    ok, errors, total_checked = check(REPO, elements_path)
    for err in errors:
        print(err)
    if not ok:
        print(
            "\nTDQS disclosure check failed. Tool definitions must satisfy the required "
            "disclosure elements legislated by ADR-0028."
        )
        print("See docs/adr/0028-elements.yaml for required element specifications and reasons.")
        return 1

    print(
        f"TDQS disclosure check OK: {total_checked} elements verified across "
        f"{len(tools_map(elements_path))} tools."
    )
    return 0


def tools_map(elements_path: Path) -> dict:
    try:
        return json.loads(elements_path.read_text(encoding="utf-8")).get("tools", {})
    except Exception:
        return {}


if __name__ == "__main__":
    sys.exit(main())
