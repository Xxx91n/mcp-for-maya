"""D-049b signature/presence audit — ratchet against stub drift.

The maya stub may only model API that EXISTS in the real-Maya baseline
(tests/maya_stub/signature-baseline.json) or is explicitly allowlisted
with a reason (signature-allowlist.json). A stub symbol missing from
both means the stub models something real Maya doesn't have — the exact
class of drift that let 0.1.1 ship str-result_type, omui.MImage-on-2024
and cmds.file(rename+prompt) bugs while CI stayed green.

Baseline collected on Maya 2024 over the live session via
inspect.signature + dir() (mayapy is broken on that box — see
baseline_meta). cmds builtins carry no inspectable signature, so the
auditable contract is presence + method-name lists. Re-collect on any
Maya version bump.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest


BASELINE_PATH = Path(__file__).parent / "maya_stub" / "signature-baseline.json"
ALLOWLIST_PATH = Path(__file__).parent / "maya_stub" / "signature-allowlist.json"


@pytest.fixture
def surface(maya_env):
    """The installed stub modules — the surface tests actually bind to."""
    import sys

    return {
        "cmds": sys.modules["maya.cmds"],
        "om": sys.modules["maya.api.OpenMaya"],
        "omui": sys.modules["maya.api.OpenMayaUI"],
    }


def _baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["symbols"]


def _allowlist() -> dict:
    return json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))


def test_stub_cmds_functions_exist_in_real_maya(surface):
    """Every public stub cmds function must exist in real maya.cmds
    (or carry an allowlist reason)."""
    baseline, allow = _baseline(), _allowlist()
    missing, allowed = [], []
    for name, fn in inspect.getmembers(surface["cmds"], inspect.isfunction):
        if name.startswith("_"):
            continue
        sym = baseline.get(f"cmds.{name}")
        if sym is None or not sym.get("exists"):
            (allowed if f"cmds.{name}" in allow else missing).append(name)
    assert not missing, (
        f"stub cmds functions absent from real-Maya baseline and not allowlisted: {missing}"
    )


def test_stub_om_classes_exist_in_real_maya(surface):
    baseline, allow = _baseline(), _allowlist()
    missing = []
    for mod_key in ("om", "omui"):
        for name, cls in inspect.getmembers(surface[mod_key], inspect.isclass):
            if name.startswith("_") or not cls.__module__.startswith("maya_stub"):
                continue
            sym = baseline.get(f"{mod_key}.{name}")
            if (sym is None or not sym.get("exists")) and f"{mod_key}.{name}" not in allow:
                missing.append(f"{mod_key}.{name}")
    assert not missing, f"stub classes absent from real-Maya baseline: {missing}"


def test_stub_methods_exist_in_real_maya(surface):
    """Every public method on a stub class must exist on the real class
    (allowlist covers version-conditional API like 2025+ MImage)."""
    baseline, allow = _baseline(), _allowlist()
    missing = []
    for mod_key in ("om", "omui"):
        for name, cls in inspect.getmembers(surface[mod_key], inspect.isclass):
            if name.startswith("_"):
                continue
            if f"{mod_key}.{name}" in allow:
                continue  # allowlisted class exempts its methods
            sym = baseline.get(f"{mod_key}.{name}") or {}
            real_methods = set((sym.get("methods") or {}).keys())
            for m, _f in inspect.getmembers(cls, inspect.isfunction):
                if m.startswith("_"):
                    continue
                key = f"{mod_key}.{name}.{m}"
                if m not in real_methods and key not in allow:
                    missing.append(key)
    assert not missing, f"stub methods absent from real-Maya baseline: {missing}"


def test_baseline_is_version_stamped():
    """The baseline must record which Maya version it was collected on —
    drift risk scales with version skew."""
    meta = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))["baseline_meta"]
    assert "Maya 2024" in meta["collected_on"]
    assert "collector" in meta


def test_allowlist_entries_have_reasons():
    allow = _allowlist()
    for key, reason in allow.items():
        if key == "_comment":
            continue
        assert isinstance(reason, str) and len(reason) > 20, (
            f"allowlist entry {key} needs a real reason"
        )
