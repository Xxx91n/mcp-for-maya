"""GUI manual tier (D-049a): machine-checkable items against a
live Maya GUI session.

These carry the ``gui`` marker and skip cleanly when no session is
reachable (conftest ``gui_client`` probes MAYA_MCP_GUI_ADDR or
:7001). They are the HIL layer of the SIL/PIL/HIL split: real asserts
on real wire — never pixel assertions, which stay with human_verify.
"""

from __future__ import annotations

import base64
import json

import pytest

from maya_mcp_server.client import MayaQtClient, raise_for_error
from maya_mcp_server.types import ResultType
from maya_mcp_server.visual_tools import _MODULE_SOURCE

pytestmark = pytest.mark.gui

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


async def _vcall(client, fn: str, **kwargs):
    """Call a _mcp_visual function over the live channel (same JSON-args
    pattern as visual_tools._visual_call)."""
    payload = json.dumps({"args": [], "kwargs": kwargs})
    code = (
        f"import json, _mcp_visual; _a = json.loads({json.dumps(payload)}); "
        f"_mcp_visual.{fn}(*_a['args'], **_a['kwargs'])"
    )
    resp = await client.execute_code(code, ResultType.JSON)
    raise_for_error(resp)
    data = resp.result
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return data
    return data


async def _cmds(client, code: str):
    """Run a maya.cmds snippet, returning the decoded JSON result."""
    resp = await client.execute_code(code, ResultType.JSON)
    raise_for_error(resp)
    return resp.result


@pytest.fixture
async def visual_module(gui_client):
    """Inject the worktree _mcp_visual into the live session (idempotent
    overwrite — tests the CURRENT source, not whatever the backend
    injected earlier)."""
    src = _MODULE_SOURCE.read_text(encoding="utf-8")
    await gui_client.write_module("_mcp_visual", src, overwrite=True)
    resp = await gui_client.execute_code("import _mcp_visual", ResultType.NONE)
    assert resp.error is None
    return gui_client


async def test_bootstrap_uses_framed_qt_channel(gui_client):
    """issue #7 PySide2 item: bootstrap on a real GUI session must yield
    the framed Qt working channel."""
    assert isinstance(gui_client, MayaQtClient)
    assert gui_client.framed_channel is True


async def test_execute_code_str_result_type_live(gui_client):
    """D-046 against the real wire: bare str result_type through the
    framed channel returns decoded data, not AttributeError."""
    resp = await gui_client.execute_code(
        "import maya.cmds as cmds; cmds.ls(type='camera')", result_type="JSON"
    )
    assert resp.error is None
    assert isinstance(resp.result, list)
    assert "perspShape" in resp.result


async def test_viewport_snapshot_returns_image(visual_module):
    """viewport_snapshot contract on a real viewport: non-empty PNG
    payload with plausible metadata."""
    result = await _vcall(visual_module, "viewport_snapshot", max_size=200, format="png")
    assert "error" not in result
    raw = base64.b64decode(result["data_b64"])
    assert raw.startswith(PNG_MAGIC)
    assert result["bytes"] == len(raw)
    assert result["width"] > 0 and result["height"] > 0
    assert result["panel"]


async def test_render_preview_net_zero_side_effects(visual_module):
    """D-026 on real Maya: panel camera + currentTime are restored after
    playblast, and the artifact is a real non-empty image."""
    client = visual_module
    # cmds.camera(name=X) may return a renamed node (X1) — the returned
    # transform name is authoritative, not the request.
    cam_name = await _cmds(
        client,
        "import maya.cmds as cmds; cmds.camera(name='CAM_gui_test')[0]",
    )
    assert isinstance(cam_name, str) and cam_name
    try:
        panel = await _vcall(client, "_active_model_panel")
        assert panel, "no active model panel in a live GUI session"
        cam0 = await _cmds(
            client,
            f"import maya.cmds as cmds; cmds.modelEditor('{panel}', q=True, camera=True)",
        )
        t0 = await _cmds(client, "import maya.cmds as cmds; cmds.currentTime(q=True)")

        result = await _vcall(
            client,
            "render_preview",
            camera=cam_name,
            width=320,
            height=180,
            format="png",
        )
        assert "error" not in result
        assert result["camera"] == cam_name
        assert result["source"] == "playblast"
        raw = base64.b64decode(result["data_b64"])
        assert raw.startswith(PNG_MAGIC)

        cam1 = await _cmds(
            client,
            f"import maya.cmds as cmds; cmds.modelEditor('{panel}', q=True, camera=True)",
        )
        t1 = await _cmds(client, "import maya.cmds as cmds; cmds.currentTime(q=True)")
        assert cam1 == cam0, f"panel camera not restored: {cam0!r} -> {cam1!r}"
        assert t1 == t0, f"currentTime not restored: {t0!r} -> {t1!r}"
    finally:
        await _cmds(
            client,
            f"import maya.cmds as cmds; cmds.delete('{cam_name}') "
            f"if cmds.objExists('{cam_name}') else None",
        )


async def test_render_preview_missing_camera_domain_error(visual_module):
    """objExists pre-check on a real session returns the structured
    camera_not_found error, not a traceback."""
    result = await _vcall(visual_module, "render_preview", camera="no_such_cam_xyz_2024")
    assert "error" in result
    assert result["error"]["code"] == "camera_not_found"
