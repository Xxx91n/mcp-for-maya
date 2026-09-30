"""Regression tests for the evidence-anchor discipline checker (D-183).

The checker runs inside the lint job; all findings are ::warning:: during
the observation period and the exit code is always 0.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parent.parent / ".github" / "scripts" / "check_evidence_anchors.py"
)


def _load():
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("check_evidence_anchors", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_real_whitelist_is_single_source_of_forms():
    """The checker consumes .github/evidence-anchor-forms.yaml verbatim \u2014
    tests must never fork detection patterns (D-183 single source)."""
    mod = _load()
    data = json.loads(mod.FORMS_PATH.read_text(encoding="utf-8"))
    priorities = {f["form"]: f["priority"] for f in data["anchor_forms"]}
    assert priorities == {
        "pytest_node_id": 1,
        "path_symbol": 2,
        "sha_path_line": 3,
        "bare_path_line": 4,
    }
    assert all("detect_regex" in f for f in data["anchor_forms"])
    assert set(mod.load_forms()) == set(priorities)


def _root(tmp_path: Path, changelog: str) -> Path:
    (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    return tmp_path


def test_bare_path_line_warns_not_fails(tmp_path):
    mod = _load()
    root = _root(
        tmp_path,
        "## [0.2.1]\n### Fixed\n- Fix (src/maya_mcp_server/scene_tools.py:71)\n",
    )
    warnings = mod.check(root)
    assert any("bare path:line" in w for w in warnings)
    assert "scene_tools.py" in warnings[0]


def test_sha_path_line_with_existing_path_is_silent(tmp_path):
    mod = _load()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.py").write_text("def f():\n    pass\n", encoding="utf-8")
    root = _root(
        tmp_path,
        "## [0.2.1]\n### Fixed\n- Fix (abc1234:src/foo.py:12)\n",
    )
    warnings = mod.check(root)
    assert warnings == []


def test_sha_path_line_missing_path_warns(tmp_path):
    mod = _load()
    root = _root(
        tmp_path,
        "## [0.2.1]\n### Fixed\n- Fix (abc1234:src/missing.py:12)\n",
    )
    warnings = mod.check(root)
    assert any("does not exist at HEAD" in w for w in warnings)


def test_path_symbol_resolves_via_ast(tmp_path):
    mod = _load()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.py").write_text(
        "def alpha():\n    pass\n\nclass Beta:\n    def gamma(self):\n        pass\n",
        encoding="utf-8",
    )
    root = _root(
        tmp_path,
        "## [0.2.1]\n### Fixed\n- Fix (src/foo.py::alpha) and (src/foo.py::Beta::gamma)\n",
    )
    warnings = mod.check(root)
    assert warnings == []


def test_path_symbol_missing_symbol_warns(tmp_path):
    mod = _load()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "foo.py").write_text("def alpha():\n    pass\n", encoding="utf-8")
    root = _root(
        tmp_path,
        "## [0.2.1]\n### Fixed\n- Fix (src/foo.py::beta)\n",
    )
    warnings = mod.check(root)
    assert any("beta" in w and "not found" in w for w in warnings)


def test_pytest_node_id_resolves_test_function(tmp_path):
    mod = _load()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_thing():\n    pass\n", encoding="utf-8")
    root = _root(
        tmp_path,
        "## [0.2.1]\n### Added\n- Feature (tests/test_x.py::test_thing)\n",
    )
    warnings = mod.check(root)
    assert warnings == []


def test_pytest_node_id_missing_test_warns(tmp_path):
    mod = _load()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_x.py").write_text("def test_thing():\n    pass\n", encoding="utf-8")
    root = _root(
        tmp_path,
        "## [0.2.1]\n### Added\n- Feature (tests/test_x.py::test_gone)\n",
    )
    warnings = mod.check(root)
    assert any("pytest_node_id" in w for w in warnings)


def test_changelog_scans_only_latest_release_section(tmp_path):
    mod = _load()
    root = _root(
        tmp_path,
        "## [0.2.1]\n### Fixed\n- Clean fix.\n"
        "## [0.1.0]\n### Added\n- Old pointer (src/old.py:9)\n",
    )
    warnings = mod.check(root)
    assert warnings == []


def test_scan_decision_ledger_and_adr(tmp_path):
    mod = _load()
    root = _root(tmp_path, "## [0.2.1]\n### Fixed\n- Clean.\n")
    (tmp_path / "docs" / "adr").mkdir(parents=True)
    (tmp_path / "docs" / "decision-ledger.md").write_text(
        "| D-1 | q | a | n | refs src/ledger.py:4 | current |\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "adr" / "0001-x.md").write_text("see src/adr.py:8\n", encoding="utf-8")
    warnings = mod.check(root)
    assert len(warnings) == 2
    assert any("decision-ledger" in w for w in warnings)
    assert any("0001-x" in w for w in warnings)


def test_missing_forms_file_reports_error_string(tmp_path):
    mod = _load()
    warnings = mod.check(tmp_path, tmp_path / "nope.yaml")
    assert warnings == [w for w in warnings if "cannot load anchor forms" in w]
