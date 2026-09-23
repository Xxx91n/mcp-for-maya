"""Maya stub package — fake maya.cmds + maya.api.OpenMaya.

Purpose (D-004 / ADR-0002): run maya_scene_module.py logic in pytest
WITHOUT a real Maya install. The stub implements a real DAG scene graph,
row-major matrix math, and 8-corner world-bbox transforms — semantically
correct, so tests catch real math bugs (e.g. min*M/max*M shortcuts).

Usage in tests:

    def test_x(maya_env):
        maya_env.scene.add_mesh("GEO_box", t=(10, 0, 0))
        result = maya_env.module.measure("GEO_box", "GEO_other", "bbox")

The fixture installs stub modules into sys.modules, imports
maya_scene_module bound to the stub, and cleans up afterwards.

NOT a Maya replacement: it models just enough cmds/OpenMaya surface used
by the scene module. Real-Maya verification stays on the mayapy tier
(docs/testing.md — manual, local-only, never in CI).
"""

from __future__ import annotations

import sys
import types

from . import cmds as _cmds
from . import fakeqt as _fakeqt
from . import openmaya as _om2
from . import openmayaui as _omui
from . import runtime
from .scene import Scene


_MODULES = (
    "maya.mel",
    "maya.api.OpenMayaUI",
    "maya.api.OpenMaya",
    "maya.api",
    "maya.cmds",
    "maya",
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6",
)


def install(scene=None):
    """Install fake maya.* modules into sys.modules. Returns the Scene."""
    sc = scene or Scene()
    runtime.scene = sc

    maya = types.ModuleType("maya")
    maya_cmds = types.ModuleType("maya.cmds")
    for name in dir(_cmds):
        if not name.startswith("_") or name in ("_s",):
            setattr(maya_cmds, name, getattr(_cmds, name))
    # private helpers that module code might use anyway
    maya_cmds.__dict__.update({k: getattr(_cmds, k) for k in dir(_cmds) if not k.startswith("__")})

    maya_api = types.ModuleType("maya.api")
    om = types.ModuleType("maya.api.OpenMaya")
    om.__dict__.update({k: getattr(_om2, k) for k in dir(_om2) if not k.startswith("__")})
    # MImage lives in OpenMaya on Maya <=2024 (moved to OpenMayaUI in
    # 2025+). The stub carries it in BOTH places so module code can be
    # tested against either layout — a test deletes omui.MImage to
    # simulate the 2024 surface.
    om.MImage = _omui.MImage

    omui = types.ModuleType("maya.api.OpenMayaUI")
    omui.__dict__.update({k: getattr(_omui, k) for k in dir(_omui) if not k.startswith("__")})

    maya.cmds = maya_cmds
    maya.api = maya_api
    maya_api.OpenMaya = om
    maya_api.OpenMayaUI = omui

    maya_mel = types.ModuleType("maya.mel")

    def _mel_eval(command):
        sc.mel_calls.append(command)
        return None

    maya_mel.eval = _mel_eval
    maya.mel = maya_mel

    sys.modules["maya"] = maya
    sys.modules["maya.mel"] = maya_mel
    sys.modules["maya.cmds"] = maya_cmds
    sys.modules["maya.api"] = maya_api
    sys.modules["maya.api.OpenMaya"] = om
    sys.modules["maya.api.OpenMayaUI"] = omui
    pyside = _fakeqt.make_pyside6()
    sys.modules["PySide6"] = pyside
    sys.modules["PySide6.QtCore"] = pyside.QtCore
    sys.modules["PySide6.QtGui"] = pyside.QtGui
    return sc


def uninstall():
    for m in _MODULES:
        sys.modules.pop(m, None)
    runtime.scene = None


def load_scene_module():
    """Import maya_scene_module fresh, bound to the installed stub."""
    sys.modules.pop("maya_mcp_server.maya_scene_module", None)
    import maya_mcp_server.maya_scene_module as msm

    return msm


def load_visual_module():
    """Import visual_module fresh, bound to the installed stub."""
    sys.modules.pop("maya_mcp_server.visual_module", None)
    import maya_mcp_server.visual_module as vm

    return vm


def load_asset_module():
    """Import asset_module fresh, bound to the installed stub."""
    sys.modules.pop("maya_mcp_server.asset_module", None)
    import maya_mcp_server.asset_module as am

    return am


__all__ = [
    "Scene",
    "install",
    "uninstall",
    "load_scene_module",
    "load_visual_module",
    "load_asset_module",
    "runtime",
]
