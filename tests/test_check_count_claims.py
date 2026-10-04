"""Regression tests for .github/scripts/check_count_claims.py.

D-216: the three migrated count families (scene_review checks / aesthetic
dimensions / shot types) must equal their AST-derived sources on every live
doc claim; frozen historical claims stay exempt and historically drifted
strings stay on the denylist.

Per D-213② every counterfactual pin asserts a NON-EMPTY red result and is
paired with a live-green positive control (the ``_tree`` fixture as written is
the control for every pin that then corrupts it).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "check_count_claims.py"
REPO = Path(__file__).resolve().parents[1]

CHECKS, DIMS, SHOTS = 3, 2, 4

MODULE_SRC = """SHOT_TYPES = {
    "extreme_wide": {},
    "wide": {},
    "medium": {},
    "close": {},
}


def scene_review(checks=None):
    if checks is None:
        checks = ["spatial", "overlaps", "zones"]


def _compute_full_aesthetic_score(materials):
    weights = {"color_theory": 0.25, "lighting_quality": 0.15}
    return weights
"""

README = (
    "# Fixture\n\n"
    f"| **Audit** | `scene_review` | {CHECKS} deterministic checks (0-100 score) |\n"
    f"| **Aesthetic** | `scene_aesthetics` | {DIMS} dimensions: color theory |\n"
    f"| **Camera** | `camera_create` | {SHOTS} industry-standard shot types |\n"
)

README_ZH = (
    "# 夹具\n\n"
    f"| **工程审核** | `scene_review` | {CHECKS} 项确定性检查（0-100 分） |\n"
    f"| **审美分析** | `scene_aesthetics` | {DIMS} 维分析：色彩理论 |\n"
    f"| **镜头规划** | `camera_create` | {SHOTS} 种行业标准镜头 |\n"
)

CHANGELOG = (
    "## [Unreleased]\n\n- wip\n\n"
    f"## [2.0.0] - 2026-01-01\n\n- now {CHECKS} deterministic checks\n\n"
    "## [1.0.0] - 2025-01-01\n\n- back then 9 deterministic checks\n"
)


def _load():
    spec = importlib.util.spec_from_file_location("check_count_claims", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _tree(tmp_path: Path) -> Path:
    """Minimal repo tree whose docs already agree with the derived sources."""
    (tmp_path / "src/maya_mcp_server").mkdir(parents=True)
    (tmp_path / "docs/adr").mkdir(parents=True)
    (tmp_path / "src/maya_mcp_server/maya_scene_module.py").write_text(MODULE_SRC, encoding="utf-8")
    (tmp_path / "README.md").write_text(README, encoding="utf-8")
    (tmp_path / "README.zh-CN.md").write_text(README_ZH, encoding="utf-8")
    (tmp_path / "CHANGELOG.md").write_text(CHANGELOG, encoding="utf-8")
    return tmp_path


def _derived(mod, root):
    return {
        "scene_review checks": CHECKS,
        "aesthetic dimensions": DIMS,
        "shot types": SHOTS,
    }


# --- derivers (positive control) ------------------------------------------------


def test_derivers_read_live_source_literals(tmp_path):
    mod = _load()
    _tree(tmp_path)
    assert mod.review_checks(tmp_path) == CHECKS
    assert mod.aesthetic_dimensions(tmp_path) == DIMS
    assert mod.shot_types(tmp_path) == SHOTS


def test_deriver_raises_when_the_source_literal_is_gone(tmp_path):
    """A renamed source must fail the gate, never silently derive 0."""
    mod = _load()
    _tree(tmp_path)
    path = tmp_path / "src/maya_mcp_server/maya_scene_module.py"
    path.write_text(MODULE_SRC.replace("SHOT_TYPES", "RENAMED"), encoding="utf-8")
    try:
        mod.shot_types(tmp_path)
    except ValueError as exc:
        assert "SHOT_TYPES" in str(exc)
    else:
        raise AssertionError("expected ValueError for the missing source literal")


# --- live-green positive control ------------------------------------------------


def test_matching_claims_pass_everywhere(tmp_path):
    mod = _load()
    _tree(tmp_path)
    derived, violations = mod.check(tmp_path)
    assert derived == _derived(mod, tmp_path)
    assert violations == []


# --- counterfactual pins ---------------------------------------------------------


def test_stale_claim_fails_the_gate(tmp_path):
    mod = _load()
    _tree(tmp_path)
    (tmp_path / "README.md").write_text(
        README.replace(f"{CHECKS} deterministic checks", "9 deterministic checks"),
        encoding="utf-8",
    )
    derived, violations = mod.check(tmp_path)
    assert derived["scene_review checks"] == CHECKS
    assert len(violations) == 1
    rel, line, msg = violations[0]
    assert (rel, line) == ("README.md", 3)
    assert "claims 9" in msg and "derives 3" in msg


def test_zh_mirror_claim_fails_the_gate(tmp_path):
    mod = _load()
    _tree(tmp_path)
    (tmp_path / "README.zh-CN.md").write_text(
        README_ZH.replace(f"{CHECKS} 项确定性检查", "7 项确定性检查"), encoding="utf-8"
    )
    _, violations = mod.check(tmp_path)
    assert len(violations) == 1
    rel, line, msg = violations[0]
    assert (rel, line) == ("README.zh-CN.md", 3)
    assert "claims 7" in msg and "derives 3" in msg


def test_shot_type_and_dimension_drift_fail_the_gate(tmp_path):
    mod = _load()
    _tree(tmp_path)
    (tmp_path / "README.md").write_text(
        README.replace(f"{DIMS} dimensions", "3 dimensions").replace(
            f"{SHOTS} industry-standard shot types", "5 industry-standard shot types"
        ),
        encoding="utf-8",
    )
    _, violations = mod.check(tmp_path)
    messages = [msg for _, _, msg in violations]
    assert len(violations) == 2
    assert any("aesthetic dimensions" in m and "claims 3" in m for m in messages)
    assert any("shot types" in m and "claims 5" in m for m in messages)


def test_denylisted_drifted_string_fails_the_gate(tmp_path):
    """Reactive layer: a drifted string whose shape still parses must go red."""
    mod = _load()
    _tree(tmp_path)
    (tmp_path / "README.md").write_text(
        README.replace(f"{CHECKS} deterministic checks", "9 universal audit dimensions"),
        encoding="utf-8",
    )
    _, violations = mod.check(tmp_path)
    assert any(
        "denylisted drifted string '9 universal audit dimensions'" in msg
        for _, _, msg in violations
    )


def test_zh_denylisted_drifted_string_fails_the_gate(tmp_path):
    mod = _load()
    _tree(tmp_path)
    (tmp_path / "README.zh-CN.md").write_text(
        README_ZH.replace(f"{CHECKS} 项确定性检查", "9 维度审核"), encoding="utf-8"
    )
    _, violations = mod.check(tmp_path)
    assert any("denylisted drifted string '9 维度审核'" in msg for _, _, msg in violations)


def test_frozen_changelog_section_is_exempt(tmp_path):
    """[1.0.0] "9 deterministic checks" is a real 0.1.0 artifact claim."""
    mod = _load()
    _tree(tmp_path)
    text = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## [1.0.0]" in text and "back then 9 deterministic checks" in text
    _, violations = mod.check(tmp_path)
    assert violations == []


def test_drift_in_the_topmost_changelog_section_fails_the_gate(tmp_path):
    mod = _load()
    _tree(tmp_path)
    (tmp_path / "CHANGELOG.md").write_text(
        CHANGELOG.replace(f"- now {CHECKS} deterministic checks", "- now 9 deterministic checks"),
        encoding="utf-8",
    )
    _, violations = mod.check(tmp_path)
    drift = [(f, line, m) for f, line, m in violations if f == "CHANGELOG.md"]
    assert len(drift) == 1
    _rel, line, msg = drift[0]
    lines = (tmp_path / "CHANGELOG.md").read_text(encoding="utf-8").split("\n")
    assert "now 9 deterministic checks" in lines[line - 1]
    assert "claims 9" in msg


def test_family_with_no_live_claim_is_vacuous(tmp_path):
    """A deleted sentence must not turn the gate silently green (D-215①)."""
    mod = _load()
    _tree(tmp_path)
    (tmp_path / "README.md").write_text(
        "\n".join(ln for ln in README.split("\n") if "dimensions" not in ln),
        encoding="utf-8",
    )
    (tmp_path / "README.zh-CN.md").write_text(
        "\n".join(ln for ln in README_ZH.split("\n") if "维分析" not in ln),
        encoding="utf-8",
    )
    _, violations = mod.check(tmp_path)
    assert any(
        "[aesthetic dimensions] asserted on 0 live claims" in msg for _, _, msg in violations
    )


def test_past_records_quoting_counts_are_not_claims(tmp_path):
    """Ledger/ADR quotes of past drift stay in-surface without an exemption."""
    mod = _load()
    _tree(tmp_path)
    (tmp_path / "docs/decision-ledger.md").write_text(
        "| D-027 | Q5 | ... | 其余既有错数（9/11维/65%）落 PR 描述清单留 T-09 |\n",
        encoding="utf-8",
    )
    (tmp_path / "docs/adr/0008-validator-registry.md").write_text(
        "# ADR-0008\n\n日期：2026-01-01\n\n- 固定 11 维只整理边界：否决——工作室规范差异是刚需。\n",
        encoding="utf-8",
    )
    _, violations = mod.check(tmp_path)
    assert violations == []


# --- CLI contract ----------------------------------------------------------------


def test_main_is_zero_on_a_matching_tree(tmp_path, monkeypatch, capsys):
    mod = _load()
    _tree(tmp_path)
    monkeypatch.setattr(mod, "REPO", tmp_path)
    assert mod.main() == 0
    assert "count claims OK" in capsys.readouterr().out


def test_main_annotates_and_returns_one_when_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    _tree(tmp_path)
    (tmp_path / "README.md").write_text(
        README.replace(f"{CHECKS} deterministic checks", "9 deterministic checks"),
        encoding="utf-8",
    )
    monkeypatch.setattr(mod, "REPO", tmp_path)
    assert mod.main() == 1
    assert "::error file=README.md,line=3::" in capsys.readouterr().out


def test_main_returns_two_when_the_source_is_unreadable(tmp_path, monkeypatch, capsys):
    mod = _load()
    (tmp_path / "docs").mkdir()
    monkeypatch.setattr(mod, "REPO", tmp_path)
    assert mod.main() == 2
    assert "checker error" in capsys.readouterr().out


# --- the live repo ---------------------------------------------------------------


def test_repo_surface_currently_consistent():
    """The live repo itself must pass — this is the gate, in-suite."""
    mod = _load()
    derived, violations = mod.check(REPO)
    assert derived == {
        "scene_review checks": 11,
        "aesthetic dimensions": 5,
        "shot types": 8,
    }
    assert violations == []
