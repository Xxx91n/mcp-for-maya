"""Regression tests for .github/scripts/check_tool_count_claims.py.

D-121: live ``N tools total``-style claims must equal the count
derived from pipeline.TOOL_ANNOTATIONS; historical CHANGELOG sections
are exempt.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "check_tool_count_claims.py"
REPO = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("check_tool_count_claims", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _tree(tmp_path: Path, n_tools: int = 2) -> None:
    """Minimal repo tree: pipeline with N annotation keys + doc surface."""
    (tmp_path / "src/maya_mcp_server").mkdir(parents=True)
    (tmp_path / "docs").mkdir()
    entries = "\n".join(f'    "tool_{i}": X,' for i in range(n_tools))
    (tmp_path / "src/maya_mcp_server/pipeline.py").write_text(
        f"TOOL_ANNOTATIONS = {{\n{entries}\n}}\n", encoding="utf-8"
    )
    for name in ("README.md", "README.zh-CN.md", "AGENTS.md"):
        (tmp_path / name).write_text(f"all {n_tools} tools pass the gate.\n", encoding="utf-8")
    (tmp_path / "docs/threat-model.md").write_text(
        f"annotations on all {n_tools} tools\n", encoding="utf-8"
    )
    (tmp_path / "CHANGELOG.md").write_text(
        "## [Unreleased]\n\n- wip\n\n"
        f"## [1.0.0] - 2026-01-01\n\n- now {n_tools} tools total.\n\n"
        "## [0.1.0] - 2025-01-01\n\n- back then, 20 tools total.\n",
        encoding="utf-8",
    )


def test_tool_count_reads_dict_keys(tmp_path):
    mod = _load()
    _tree(tmp_path, n_tools=3)
    assert mod.tool_count(tmp_path / "src/maya_mcp_server/pipeline.py") == 3


def test_matching_claims_pass(tmp_path):
    mod = _load()
    _tree(tmp_path, n_tools=2)
    n, violations = mod.check(tmp_path)
    assert n == 2
    assert violations == []


def test_stale_claim_fails_everywhere_it_lives(tmp_path):
    mod = _load()
    _tree(tmp_path, n_tools=2)
    (tmp_path / "README.md").write_text(
        "23 tools total today.\nall 2 tools audited.\n25 MCP tools in total.\n",
        encoding="utf-8",
    )
    n, violations = mod.check(tmp_path)
    assert n == 2
    files = {(f, line) for f, line, _ in violations}
    assert ("README.md", 1) in files  # 23 tools total
    assert ("README.md", 3) in files  # 25 MCP tools in total
    assert all("README.md" == f for f, _, _ in violations)
    assert len(violations) == 2  # "all 2 tools" matches truth


def test_historical_changelog_sections_exempt(tmp_path):
    mod = _load()
    _tree(tmp_path, n_tools=2)
    n, violations = mod.check(tmp_path)
    assert violations == []  # [0.1.0] "20 tools total" is not scanned


def test_zh_mirror_claims_asserted(tmp_path):
    mod = _load()
    _tree(tmp_path, n_tools=2)
    (tmp_path / "README.zh-CN.md").write_text(
        "共 2 个 MCP 工具。\n覆盖全部 2 个工具。\n", encoding="utf-8"
    )
    n, violations = mod.check(tmp_path)
    assert violations == []


def test_per_file_counts_are_not_total_claims(tmp_path):
    mod = _load()
    _tree(tmp_path, n_tools=2)
    (tmp_path / "AGENTS.md").write_text(
        "├── scene_tools.py    # 13 MCP scene tool definitions\n"
        "├── visual_tools.py   # 2 GUI-only visual tools\n",
        encoding="utf-8",
    )
    n, violations = mod.check(tmp_path)
    assert violations == []


def test_last_release_section_skips_unreleased():
    mod = _load()
    text = "## [Unreleased]\n\n- wip\n\n## [2.0.0] - d\n\n- a\n\n## [1.0.0] - d\n"
    start, label, section = mod.last_release_section(text)
    assert label == "2.0.0"
    assert "## [1.0.0]" not in section


def test_main_annotations_format(tmp_path, monkeypatch, capsys):
    mod = _load()
    _tree(tmp_path, n_tools=1)
    (tmp_path / "AGENTS.md").write_text("all 9 tools pass\n", encoding="utf-8")
    monkeypatch.setattr(mod, "REPO", tmp_path)
    assert mod.main() == 1
    out = capsys.readouterr().out
    assert "::error file=AGENTS.md,line=1::" in out


def test_repo_surface_currently_consistent():
    """The live repo itself must pass — this is the gate, in-suite."""
    mod = _load()
    n, violations = mod.check(REPO)
    assert violations == [] and n == 25
