"""D-072 pins for .github/scripts/check_readme_skeleton.py.

This gate shipped with ZERO pins. It was the one `bound_class: gate` entry the
new D-215 registry flagged on arrival, via the zero-pin guard: a CI gate whose
verdict nobody can reproduce is a claim about the mirror, not a check of it.

Every red below asserts a NON-EMPTY finding (D-213 2) and is paired with the
live-green control at the bottom, so a `check()` that returned a finding for
everything would be as visible as one that returned nothing.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_readme_skeleton.py"

EN_SELECTOR = "**English** | [简体中文](README.zh-CN.md)"
ZH_SELECTOR = "[English](README.md) | **简体中文**"
ANCHOR = "<!-- synced-with: README.md @ abc1234 -->"


def _load():
    spec = importlib.util.spec_from_file_location("check_readme_skeleton", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _mirror(tmp_path: Path, en: str, zh: str) -> Path:
    (tmp_path / "README.md").write_text(en, encoding="utf-8")
    (tmp_path / "README.zh-CN.md").write_text(zh, encoding="utf-8")
    return tmp_path


def _in_sync(
    en_headings: str = "## A\n### B\n", zh_headings: str = "## 甲\n### 乙\n"
) -> tuple[str, str]:
    return (
        f"# Title\n\n{EN_SELECTOR}\n\n{en_headings}",
        f"# 标题\n\n{ZH_SELECTOR}\n\n{ANCHOR}\n\n{zh_headings}",
    )


# --- reds -----------------------------------------------------------------


def test_missing_mirror_file_is_red(tmp_path):
    mod = _load()
    (tmp_path / "README.md").write_text("# t\n", encoding="utf-8")
    findings = mod.check(tmp_path)
    assert findings, "a missing mirror must be red"
    assert any("missing" in f for f in findings), findings


def test_dropped_heading_in_the_mirror_is_red(tmp_path):
    """The whole point of the skeleton check: a lagging mirror is detectable
    because the heading LEVEL SEQUENCE diverges, even though every title still
    reads plausibly in its own language."""
    mod = _load()
    en, zh = _in_sync("## A\n### B\n", "## A\n")
    findings = mod.check(_mirror(tmp_path, en, zh))
    assert findings, "a heading dropped from the mirror must be red"
    assert any("skeleton divergence" in f for f in findings), findings


def test_reordered_headings_are_red_even_at_the_same_levels(tmp_path):
    """Levels alone are not enough -- order is part of the contract, so two
    mirrors with the same multiset of levels in a different order must fail."""
    mod = _load()
    en, _ = _in_sync("## A\n### B\n", "")
    zh = f"# 标题\n\n{ZH_SELECTOR}\n\n{ANCHOR}\n\n### 乙\n## 甲\n"
    findings = mod.check(_mirror(tmp_path, en, zh))
    assert any("skeleton divergence" in f for f in findings), findings


def test_promoted_heading_level_in_the_mirror_is_red(tmp_path):
    mod = _load()
    en, _ = _in_sync("## A\n### B\n", "")
    zh = f"# 标题\n\n{ZH_SELECTOR}\n\n{ANCHOR}\n\n## 甲\n## 乙\n"
    findings = mod.check(_mirror(tmp_path, en, zh))
    assert any("skeleton divergence" in f for f in findings), findings


def test_missing_language_selector_in_the_source_is_red(tmp_path):
    mod = _load()
    en, zh = _in_sync()
    findings = mod.check(_mirror(tmp_path, en.replace(EN_SELECTOR, "EN | 中文"), zh))
    assert any("README.md missing top language selector" in f for f in findings), findings


def test_missing_language_selector_in_the_mirror_is_red(tmp_path):
    mod = _load()
    en, zh = _in_sync()
    findings = mod.check(_mirror(tmp_path, en, zh.replace(ZH_SELECTOR, "英文 | 简体中文")))
    assert any("README.zh-CN.md missing top language selector" in f for f in findings), findings


def test_missing_synced_with_anchor_is_red(tmp_path):
    """The anchor is what makes a lag attributable: without the sha there is no
    way to tell a deliberate lag from a mirror nobody updated."""
    mod = _load()
    en, zh = _in_sync()
    findings = mod.check(_mirror(tmp_path, en, zh.replace(ANCHOR, "<!-- synced long ago -->")))
    assert any("synced-with anchor" in f for f in findings), findings


def test_an_unparseable_anchor_sha_is_red(tmp_path):
    mod = _load()
    en, zh = _in_sync()
    findings = mod.check(
        _mirror(tmp_path, en, zh.replace(ANCHOR, "<!-- synced-with: README.md @ zzz -->"))
    )
    assert any("synced-with anchor" in f for f in findings), findings


def test_headings_inside_a_fenced_code_block_are_not_skeleton(tmp_path):
    """A negative control on the parser, not on the contract: a '# comment'
    line inside a fence would otherwise read as an H1 and make every mirror
    look divergent."""
    mod = _load()
    en = f"# Title\n\n{EN_SELECTOR}\n\n## A\n\n```python\n# not a heading\n```\n"
    zh = f"# 标题\n\n{ZH_SELECTOR}\n\n{ANCHOR}\n\n## 甲\n\n```python\n# 也不是标题\n```\n"
    assert mod.check(_mirror(tmp_path, en, zh)) == []


# --- live-green controls --------------------------------------------------


def test_a_matching_mirror_is_green(tmp_path):
    mod = _load()
    en, zh = _in_sync()
    assert mod.check(_mirror(tmp_path, en, zh)) == []


def test_the_real_repo_mirror_is_green():
    """The live-green control. Without it every red above could be explained by
    a `check()` that simply always fails."""
    mod = _load()
    assert mod.check(REPO) == []
