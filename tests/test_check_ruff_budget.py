"""Regression tests for .github/scripts/check_ruff_budget.py.

Per-rule budget that only goes down (D-044/T-10b): a rule may never exceed
its cap even when the segment total stays flat — rules cannot subsidise
each other.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "check_ruff_budget.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_ruff_budget", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _run(mod, tmp_path, monkeypatch, diags, budget):
    report = tmp_path / "report.json"
    report.write_text(json.dumps(diags), encoding="utf-8")
    base = tmp_path / "budget.json"
    base.write_text(json.dumps(budget), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["check_ruff_budget.py", str(report), str(base)])
    return mod.main()


def _diag(filename: str, code: str) -> dict:
    return {"filename": filename, "code": code}


def test_counts_per_segment_and_rule(tmp_path, monkeypatch):
    mod = _load()
    diags = [_diag("src/a.py", "E501"), _diag("src/a.py", "E501"), _diag("tests/t.py", "F401")]
    assert _run(mod, tmp_path, monkeypatch, diags, {"src": {"E501": 2}, "tests": {"F401": 1}}) == 0


def test_rule_cannot_subsidise_another_rule(tmp_path, monkeypatch):
    """5 new F401 must fail even though total (10) is under the 10-error cap."""
    mod = _load()
    diags = [_diag("src/a.py", "E501")] * 5 + [_diag("src/b.py", "F401")] * 5
    assert _run(mod, tmp_path, monkeypatch, diags, {"src": {"E501": 10}}) == 1


def test_new_rule_in_new_segment_fails(tmp_path, monkeypatch):
    mod = _load()
    diags = [_diag("tools/x.py", "W605")]
    assert _run(mod, tmp_path, monkeypatch, diags, {"src": {"E501": 3}}) == 1


def test_below_budget_passes_ratchet_hint(tmp_path, monkeypatch, capsys):
    mod = _load()
    diags = [_diag("src/a.py", "E501")]
    assert _run(mod, tmp_path, monkeypatch, diags, {"src": {"E501": 4}}) == 0
    assert "below budget" in capsys.readouterr().out


def test_legacy_flat_baseline_is_rejected_with_hint(tmp_path, monkeypatch, capsys):
    mod = _load()
    rc = _run(mod, tmp_path, monkeypatch, [], {"src": 174})
    assert rc == 2
    assert "per-rule" in capsys.readouterr().out


def test_null_code_buckets_as_unknown(tmp_path, monkeypatch):
    mod = _load()
    diags = [{"filename": "src/a.py", "code": None}]
    assert _run(mod, tmp_path, monkeypatch, diags, {"src": {"unknown": 1}}) == 0
