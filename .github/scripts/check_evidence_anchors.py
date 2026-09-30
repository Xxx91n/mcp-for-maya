"""D-183 evidence-anchor discipline \u2014 warn-level lint (observation period).

Scans versioned docs for evidence pointers and classifies each against
the anchor-form whitelist single source .github/evidence-anchor-forms.yaml:

  pytest node ID   tests/test_x.py::test_y (optionally ::TestClass::test_y)
  path::symbol     src/foo.py::symbol \u2014 verified via ast.parse (the symbol
                   must exist as a module-level def/class or Class::method)
  sha:path:line    <7+ hex>:<path>:<line> \u2014 commit-pinned, structural check
  bare path:line   src/foo.py:12 \u2014 warn-level upgrade hint in versioned
                   docs (legitimate transient form only inside .scratch/)

Machine-check boundary (D-183): pointer reachability + structural element
existence only. Content truth, semantic direction, fabricated commands
and actual reproducibility stay a human-review responsibility.

All findings are ::warning:: and the exit code is always 0 during the
observation period. Expiry anchor (D-183): the first release-preflight
review measures the false-positive rate \u2014 zero/low FP promotes missing
path::symbol classes to hard failure; the bare path:line hint stays warn
permanently; FP >30% returns the mechanism to manual audit sampling.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent.parent
FORMS_PATH = REPO / ".github" / "evidence-anchor-forms.yaml"


# ---------------------------------------------------------------------------
# anchor forms: single source of truth = .github/evidence-anchor-forms.yaml
# (detect_regex fields below are loaded from it \u2014 do not fork patterns here)
# ---------------------------------------------------------------------------
def load_forms(forms_path: Path = FORMS_PATH) -> dict[str, re.Pattern[str]]:
    data = json.loads(forms_path.read_text(encoding="utf-8"))
    return {f["form"]: re.compile(f["detect_regex"]) for f in data["anchor_forms"]}


def _release_section_lines(changelog: Path) -> list[tuple[int, str]]:
    """Lines of the most recent release section (topmost '## [' block)."""
    lines = changelog.read_text(encoding="utf-8").splitlines()
    heads = [i for i, ln in enumerate(lines) if ln.startswith("## ")]
    if not heads:
        return []
    start = heads[0]
    end = heads[1] if len(heads) > 1 else len(lines)
    return [(i + 1, lines[i]) for i in range(start, end)]


def _whole_file_lines(path: Path) -> list[tuple[int, str]]:
    try:
        return list(enumerate(path.read_text(encoding="utf-8").splitlines(), 1))
    except (OSError, UnicodeDecodeError):
        return []


def _scan_targets(root: Path) -> list[tuple[Path, list[tuple[int, str]]]]:
    targets: list[tuple[Path, list[tuple[int, str]]]] = []
    cl = root / "CHANGELOG.md"
    if cl.exists():
        targets.append((cl, _release_section_lines(cl)))
    for name in ["docs/decision-ledger.md"]:
        p = root / name
        if p.exists():
            targets.append((p, _whole_file_lines(p)))
    for p in sorted((root / "docs" / "adr").glob("*.md")):
        targets.append((p, _whole_file_lines(p)))
    ev = root / "docs" / "evidence"
    if ev.exists():
        for p in sorted(ev.rglob("*.md")):
            # provenance JSON payloads exempt (whitelist note)
            targets.append((p, _whole_file_lines(p)))
    return targets


def _symbol_exists(path: Path, symbol: str) -> tuple[bool, str]:
    """ast.resolve <path>::<symbol> or <path>::<Class>::<method>."""
    if not path.exists():
        return False, f"target file not found: {path}"
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as e:
        return False, f"cannot parse {path}: {e}"
    parts = symbol.split("::")
    top = {
        n.name
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    if len(parts) == 1:
        if parts[0] in top:
            return True, ""
        return False, f"symbol '{parts[0]}' not found in {path}"
    if len(parts) == 2:
        for n in tree.body:
            if isinstance(n, ast.ClassDef) and n.name == parts[0]:
                methods = {
                    m.name for m in n.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                if parts[1] in methods:
                    return True, ""
                return False, f"method '{parts[1]}' not found in {parts[0]} of {path}"
        return False, f"class '{parts[0]}' not found in {path}"
    return False, f"anchor '{symbol}' deeper than Class::method"


def check(root: Path, forms_path: Path = FORMS_PATH) -> list[str]:
    """Return warn-level findings (never fails — observation period)."""
    warnings: list[str] = []
    try:
        forms = load_forms(forms_path)
    except (OSError, ValueError, KeyError, re.error) as e:
        return [f"cannot load anchor forms {forms_path}: {e}"]
    seen: set[tuple[str, str]] = set()

    def add(path: Path, line_no: int, kind: str, msg: str) -> None:
        key = (str(path.relative_to(root)), kind + msg)
        if key in seen:
            return
        seen.add(key)
        warnings.append(f"file={path.relative_to(root)},line={line_no}::{kind}: {msg}")

    for path, lines in _scan_targets(root):
        for line_no, text in lines:
            for m in forms["sha_path_line"].finditer(text):
                sha, rel, lineno = m.groups()
                if not (root / rel).exists():
                    add(
                        path,
                        line_no,
                        "anchor",
                        f"sha-pinned path '{rel}' does not exist at HEAD "
                        f"(sha={sha}, line={lineno}) \u2014 verify the pin",
                    )
            for form_name in ("pytest_node_id", "path_symbol"):
                for m in forms[form_name].finditer(text):
                    rel, symbol = m.group(1), m.group(2)
                    if form_name == "path_symbol" and rel.startswith(("tests/", "tests\\")):
                        continue  # already covered by pytest_node_id pass
                    target = root / rel
                    ok, reason = _symbol_exists(target, symbol)
                    if not ok:
                        add(
                            path,
                            line_no,
                            "anchor",
                            f"unresolvable {form_name} '{rel}::{symbol}': {reason}",
                        )
            for m in forms["bare_path_line"].finditer(text):
                rel, lineno = m.groups()
                add(
                    path,
                    line_no,
                    "anchor",
                    f"bare path:line '{rel}:{lineno}' without sha prefix \u2014 "
                    "upgrade to pytest node ID, path::symbol, or sha:path:line "
                    "(whitelist priority 1-3; bare form drifts on every edit)",
                )
    return warnings


def main() -> int:
    warnings = check(REPO)
    for w in warnings:
        print(f"::warning::{w}")
    print(
        f"evidence anchors check: {len(warnings)} warning(s) \u2014 warn-level "
        "observation period (D-183); forms whitelist: .github/evidence-anchor-forms.yaml"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
