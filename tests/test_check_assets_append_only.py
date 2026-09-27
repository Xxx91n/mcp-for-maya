"""Tests for .github/scripts/check_assets_append_only.py (D-113).

The guard must let pure additions under .github/assets/ pass and fail
on delete/modify/rename. Tests exercise the real script logic against
throwaway git repos — the mechanism IS git-diff semantics, so stubbing
it out would test nothing.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "check_assets_append_only.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_assets_append_only", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout


def _commit(repo: Path) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "x")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-b", "main")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    _git(tmp_path, "config", "commit.gpgsign", "false")
    d = tmp_path / ".github" / "assets"
    d.mkdir(parents=True)
    (d / "keep.png").write_bytes(b"png0")
    _commit(tmp_path)
    return tmp_path


def _head(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").strip()


def _run(mod, repo: Path, monkeypatch, before: str) -> int:
    monkeypatch.setenv("GITHUB_EVENT_NAME", "push")
    monkeypatch.setenv("GUARD_BEFORE", before)
    monkeypatch.setenv("GITHUB_SHA", "HEAD")
    monkeypatch.chdir(repo)
    return mod.main()


def test_pure_addition_passes(repo, monkeypatch):
    mod = _load()
    before = _head(repo)
    (repo / ".github" / "assets" / "new.png").write_bytes(b"png1")
    _commit(repo)
    assert _run(mod, repo, monkeypatch, before) == 0


def test_delete_fails(repo, monkeypatch):
    mod = _load()
    before = _head(repo)
    (repo / ".github" / "assets" / "keep.png").unlink()
    _commit(repo)
    assert _run(mod, repo, monkeypatch, before) == 1


def test_modify_fails(repo, monkeypatch):
    mod = _load()
    before = _head(repo)
    (repo / ".github" / "assets" / "keep.png").write_bytes(b"changed")
    _commit(repo)
    assert _run(mod, repo, monkeypatch, before) == 1


def test_rename_fails_via_expanded_delete(repo, monkeypatch):
    """--no-renames expands rename to D+A; the D side must catch it."""
    mod = _load()
    before = _head(repo)
    d = repo / ".github" / "assets"
    (d / "keep.png").rename(d / "renamed.png")
    _commit(repo)
    assert _run(mod, repo, monkeypatch, before) == 1


def test_outside_guard_prefix_passes(repo, monkeypatch):
    mod = _load()
    before = _head(repo)
    p = repo / "src" / "x.py"
    p.parent.mkdir(exist_ok=True)
    p.write_text("x=1\n")
    _commit(repo)
    _git(repo, "rm", "-q", "src/x.py")
    _git(repo, "commit", "-m", "del")
    assert _run(mod, repo, monkeypatch, before) == 0


def test_all_zero_before_skips(repo, monkeypatch):
    mod = _load()
    assert _run(mod, repo, monkeypatch, "0" * 40) == 0
