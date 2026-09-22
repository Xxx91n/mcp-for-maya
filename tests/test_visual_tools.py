"""T-08 contract tests: visual tools (D-023..D-027).

VisualExecClient runs the code visual_tools generates against the
stub-bound _mcp_visual module using the REAL result-capture
transform, so these tests exercise the full chain: host gate ->
injection -> generated code -> Maya-side module -> mixed blocks.

Stub layer = contract layer (D-027): no pixel assertions, no golden
images, no exact call-sequence pinning. Terminal-state roundtrips
(success AND failure paths) and loose restore evidence instead.
"""

from __future__ import annotations

import base64
import glob
import json
import os
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import maya_stub
import pytest
from maya_stub.fakeqt import png_decode

from maya_mcp_server.maya_mcp_helper import prepare_code_for_result_capture
from maya_mcp_server.types import CommandResponse, OutputBuffer, ResultType
from maya_mcp_server.visual_tools import (
    _visual_injected,
    register_visual_tools,
)


class VisualExecClient:
    """Fake framed client: runs generated code on the stub module."""

    framed_channel = True
    key = "127.0.0.1:50999"

    def __init__(self, module):
        self.module = module
        self.calls = []
        self.injected = []

    async def execute_code(self, code, result_type=ResultType.NONE):
        self.calls.append(code)
        rt = getattr(result_type, "value", result_type)
        ctx = {"__builtins__": __builtins__}
        if rt == "NONE":
            exec(compile(code, "<mcp>", "exec"), ctx)
            return CommandResponse(result=None, error=None)
        modified, was = prepare_code_for_result_capture(code)
        if not was:
            raise RuntimeError(f"result not capturable: {code}")
        ctx["_mcp_result"] = None
        exec(compile(modified, "<mcp>", "exec"), ctx)
        return CommandResponse(result=ctx["_mcp_result"], error=None)

    async def write_module(self, name, code, overwrite=False):
        self.injected.append(name)
        return name

    async def get_buffered_output(self):
        return OutputBuffer()

    def append_output(self, stdout, stderr):
        pass


class NativeExecClient(VisualExecClient):
    """Headless/native-channel client: framed_channel is False."""

    framed_channel = False


class ErrorClient(VisualExecClient):
    """Transport-level failure: error must propagate as isError."""

    async def execute_code(self, code, result_type=ResultType.NONE):
        self.calls.append(code)
        return CommandResponse(
            result=None,
            error={
                "type": "builtins.RuntimeError",
                "message": "kaboom in maya",
                "traceback": "Traceback... RuntimeError: kaboom in maya",
            },
        )


@pytest.fixture
def vtools(maya_env, monkeypatch):
    maya_env.scene.setup_gui()
    module = maya_stub.load_visual_module()
    sys.modules["_mcp_visual"] = module
    _visual_injected.clear()
    client = VisualExecClient(module)
    manager = MagicMock()
    manager.get_client = AsyncMock(return_value=client)
    monkeypatch.setattr("maya_mcp_server.server.get_session_manager", lambda: manager)
    mock_mcp = MagicMock()
    fns = {}

    def capture(fn=None, **_kwargs):
        if fn is None:
            return lambda f: capture(f)
        fns[fn.__name__] = fn
        return fn

    mock_mcp.tool = capture
    register_visual_tools(mock_mcp)
    yield SimpleNamespace(fns=fns, client=client, manager=manager, env=maya_env, module=module)
    _visual_injected.clear()
    sys.modules.pop("_mcp_visual", None)
    sys.modules.pop("maya_mcp_server.visual_module", None)


def _meta(out):
    """Parse the TextContent metadata block of a mixed result."""
    return json.loads(out[1].text)


# ------------------------------------------------------------
# Injection trajectory + double headless gate (D-024/D-025)
# ------------------------------------------------------------


class TestInjectionAndGates:
    async def test_first_call_injects_once(self, vtools):
        await vtools.fns["scene_viewport_snapshot"]()
        assert vtools.client.injected == ["_mcp_visual"]
        assert "import _mcp_visual" in vtools.client.calls[0]
        await vtools.fns["scene_viewport_snapshot"]()
        assert vtools.client.injected == ["_mcp_visual"], "no re-inject"

    async def test_headless_channel_short_circuits(self, vtools):
        """framed_channel=False -> coded error, ZERO round trips (D-024)."""
        native = NativeExecClient(vtools.module)
        vtools.manager.get_client = AsyncMock(return_value=native)
        from maya_mcp_server.security import GuiSessionRequiredError

        with pytest.raises(GuiSessionRequiredError):
            await vtools.fns["scene_viewport_snapshot"]()
        assert native.calls == [], "must not round-trip Maya"
        assert native.injected == [], "headless never injects _mcp_visual"

    async def test_maya_side_gate_batch(self, vtools):
        vtools.env.scene.batch = True
        out = await vtools.fns["scene_viewport_snapshot"]()
        res = json.loads(out)
        assert res["error"]["code"] == "gui_session_required"
        assert "suggestion" in res["error"]

    async def test_maya_side_gate_no_panels(self, vtools):
        vtools.env.scene.panels.clear()
        vtools.env.scene.focus_panel = None
        out = await vtools.fns["scene_render_preview"]()
        res = json.loads(out)
        assert res["error"]["code"] == "gui_session_required"

    async def test_gui_deps_missing_maps_gui_error(self, vtools, monkeypatch):
        """Extreme headless-ish GUI env: omui/PySide absent -> same code."""
        monkeypatch.setattr(vtools.module, "_omui", None)
        monkeypatch.setattr(vtools.module, "_IMPORT_ERROR", ImportError("no omui"))
        out = await vtools.fns["scene_viewport_snapshot"]()
        res = json.loads(out)
        assert res["error"]["code"] == "gui_session_required"


class TestMImageModuleLayout:
    """MImage moved modules across Maya versions: maya.api.OpenMaya on
    <=2024, maya.api.OpenMayaUI on 2025+. Real-Maya find (D-046 round):
    the omui-only path crashed on Maya 2024 with
    "module 'maya.api.OpenMayaUI' has no attribute 'MImage'"."""

    def test_mimage_prefers_openmayaui(self, maya_env):
        """2025+ layout: _MImage resolves to the OpenMayaUI class."""
        maya_env.scene.setup_gui()
        module = maya_stub.load_visual_module()
        assert module._MImage is sys.modules["maya.api.OpenMayaUI"].MImage

    def test_mimage_falls_back_to_openmaya_2024(self, maya_env, monkeypatch):
        """2024 layout: OpenMayaUI lacks MImage -> resolves via
        maya.api.OpenMaya and capture still works. (convertPixelFormat
        is C++-only — absent from Python API 2.0 on every documented
        version, so the stub no longer models it: D-056⑤.)"""
        maya_env.scene.setup_gui()
        omui = sys.modules["maya.api.OpenMayaUI"]
        monkeypatch.delattr(omui, "MImage")
        module = maya_stub.load_visual_module()
        assert module._MImage is sys.modules["maya.api.OpenMaya"].MImage
        result = module.viewport_snapshot(max_size=64, format="png")
        assert "error" not in result

    def test_mimage_absent_maps_domain_error(self, maya_env, monkeypatch):
        """No MImage anywhere -> structured capture_unsupported error,
        not an AttributeError traceback."""
        maya_env.scene.setup_gui()
        omui = sys.modules["maya.api.OpenMayaUI"]
        om = sys.modules["maya.api.OpenMaya"]
        monkeypatch.delattr(omui, "MImage")
        monkeypatch.delattr(om, "MImage")
        module = maya_stub.load_visual_module()
        assert module._MImage is None
        result = module.viewport_snapshot()
        assert result["error"]["code"] == "capture_unsupported"

    async def test_both_tools_registered(self, vtools):
        assert set(vtools.fns) == {
            "scene_viewport_snapshot",
            "scene_render_preview",
        }


# ------------------------------------------------------------
# Annotations (D-018 matrix rows)
# ------------------------------------------------------------


class TestAnnotations:
    def test_visual_tools_readonly_idempotent(self):
        from maya_mcp_server.pipeline import TOOL_ANNOTATIONS

        for name in ("scene_viewport_snapshot", "scene_render_preview"):
            ann = TOOL_ANNOTATIONS[name]
            assert ann.readOnlyHint is True, name
            assert ann.idempotentHint is True, name
            assert ann.destructiveHint is False, name
            assert ann.openWorldHint is False, name


# ------------------------------------------------------------
# Snapshot contract (D-023/D-025)
# ------------------------------------------------------------


class TestSnapshotContract:
    async def test_returns_image_and_text_blocks(self, vtools):
        out = await vtools.fns["scene_viewport_snapshot"]()
        assert len(out) == 2
        img, txt = out
        assert img.type == "image"
        assert img.mimeType == "image/jpeg"
        assert list(img.annotations.audience) == ["assistant", "user"]
        raw = base64.b64decode(img.data)
        assert raw.startswith(b"\xff\xd8"), "jpeg magic"
        meta = _meta(out)
        assert meta["session"] == vtools.client.key
        assert meta["camera"] == "persp"
        assert meta["panel"] == "modelPanel1"
        assert meta["format"] == "jpeg"
        assert meta["bytes"] == len(raw)

    async def test_png_format_magic(self, vtools):
        out = await vtools.fns["scene_viewport_snapshot"](format="png")
        img = out[0]
        assert img.mimeType == "image/png"
        assert base64.b64decode(img.data).startswith(b"\x89PNG")
        assert _meta(out)["format"] == "png"

    async def test_max_size_downsample_math(self, vtools):
        """1280x720 viewport, max_size=800 -> 800x450 (aspect kept)."""
        out = await vtools.fns["scene_viewport_snapshot"](max_size=800)
        meta = _meta(out)
        assert (meta["width"], meta["height"]) == (800, 450)

    async def test_no_downsample_when_fits(self, vtools):
        out = await vtools.fns["scene_viewport_snapshot"](max_size=2000)
        meta = _meta(out)
        assert (meta["width"], meta["height"]) == (1280, 720)

    async def test_refresh_forced_before_capture(self, vtools):
        await vtools.fns["scene_viewport_snapshot"]()
        assert vtools.env.scene.refresh_calls >= 1

    async def test_invalid_format(self, vtools):
        from maya_mcp_server.security import InputValidationError

        with pytest.raises(InputValidationError):
            await vtools.fns["scene_viewport_snapshot"](format="gif")

    async def test_invalid_quality(self, vtools):
        from maya_mcp_server.security import InputValidationError

        with pytest.raises(InputValidationError):
            await vtools.fns["scene_viewport_snapshot"](quality=0)

    async def test_tiny_max_size_rejected(self, vtools):
        from maya_mcp_server.security import InputValidationError

        with pytest.raises(InputValidationError):
            await vtools.fns["scene_viewport_snapshot"](max_size=8)


# ------------------------------------------------------------
# VP2 readback truth (D-056⑤) — asymmetric pure-color pin
# ------------------------------------------------------------


def _top_left_red(x, y, w, h):
    """Asymmetric pattern: pure red block top-left quarter, black rest.

    Asymmetry is the point — only a layout like this can lock whether
    the readback was flipped and whether channels were swapped (a
    fullscreen solid cannot)."""
    if x < w // 4 and y < h // 4:
        return (1.0, 0.0, 0.0, 1.0)
    return (0.0, 0.0, 0.0, 1.0)


def _cell_mean(rows, w, h, x0, y0, x1, y1):
    """Mean (r,g,b) over a cell of decoded PNG rows (top-down coords)."""
    rs = gs = bs = n = 0
    for y in range(y0, y1):
        row = rows[y]
        for x in range(x0, x1):
            i = x * 3
            rs += row[i]
            gs += row[i + 1]
            bs += row[i + 2]
            n += 1
    return rs / n, gs / n, bs / n


class TestVp2ReadbackTruth:
    """The stub models the documented VP2 defect shape: readColorBuffer
    fills BGRA + top-down by default; the module asks for RGBA at the
    source (readRGBA=True) and lets writeToFile do float->byte — the
    floatPixels pointer path is gone (MScriptUtil removed in 2024). A
    red block painted top-left must land top-left and RED — a missed
    flip puts it bottom-left, a channel-order lie makes it blue."""

    async def test_rgb_readback_lands_red_top_left(self, vtools):
        """readColorBuffer(img, readRGBA=True) -> writeToFile — the only
        pointer-free path; the assertion arbitrates orientation."""
        vtools.env.scene.viewport_pattern = _top_left_red
        out = await vtools.fns["scene_viewport_snapshot"](format="png", max_size=2000)
        raw = base64.b64decode(out[0].data)
        w, h, rows = png_decode(raw)
        # tolerance bands, not exact equality (OCIO may drift pure colors)
        tr, tg, tb = _cell_mean(rows, w, h, w // 16, h // 16, w // 8, h // 8)
        br, bg, bb = _cell_mean(rows, w, h, w // 16, h * 13 // 16, w // 8, h * 7 // 8)
        assert tr > 180 and tb < 80, f"top-left must be RED, got {(tr, tg, tb)}"
        assert br < 60 and bb < 60, f"bottom-left must stay black, got {(br, bg, bb)}"

    async def test_missing_setrgba_marker_swaps_channels(self, vtools, monkeypatch):
        """Regression proof the pin has teeth: if the marker lie slips
        back in (RGBA bytes stored while BGRA flagged), the block goes
        BLUE — the assertion must see it."""
        vtools.env.scene.viewport_pattern = _top_left_red
        # simulate the defect directly: writeToFile with marker unset
        omui = sys.modules["maya.api.OpenMayaUI"]
        img = omui.MImage()
        img.create(64, 64, 4, omui.MImage.kFloat)
        omui.M3dView.active3dView().readColorBuffer(img)
        floats = img.floatPixels()
        px = bytearray(64 * 64 * 4)
        for i in range(0, len(px), 4):
            px[i] = int(floats[i + 2] * 255)  # R
            px[i + 1] = int(floats[i + 1] * 255)  # G
            px[i + 2] = int(floats[i + 0] * 255)  # B
            px[i + 3] = 255
        out_img = omui.MImage()
        out_img.create(64, 64, 4, omui.MImage.kByte)
        out_img.setPixels(bytes(px), 64, 64)
        # NB: deliberately NOT calling setRGBA(True) — marker stays BGRA
        import tempfile

        fd, tmp = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            out_img.writeToFile(tmp, "png")
            with open(tmp, "rb") as fh:
                w, h, rows = png_decode(fh.read())
        finally:
            os.remove(tmp)
        # unflipped buffer lands the block at top-LEFT (real readback is
        # top-down - T-18a re-pin), and the BGRA marker lie turns it BLUE
        tr, tg, tb = _cell_mean(rows, w, h, 2, h // 16, 8, h // 8)
        assert tb > tr + 60, f"marker lie must swap to BLUE, got {(tr, tg, tb)}"


# ------------------------------------------------------------
# Preview contract (D-023/D-025/D-026)
# ------------------------------------------------------------


class TestPreviewContract:
    async def test_returns_blocks_with_source(self, vtools):
        out = await vtools.fns["scene_render_preview"]()
        assert len(out) == 2
        meta = _meta(out)
        assert meta["source"] == "playblast"
        assert meta["panel"] == "modelPanel1"
        assert meta["camera"] == "persp"
        assert (meta["width"], meta["height"]) == (640, 360)

    async def test_width_height_rounded_up_to_4(self, vtools):
        """Server-side /4 round-up before reaching playblast (D-025)."""
        await vtools.fns["scene_render_preview"](width=641, height=361)
        wh = vtools.env.scene.playblast_calls[-1]["widthHeight"]
        assert tuple(wh) == (644, 364)

    async def test_playblast_call_flags(self, vtools):
        await vtools.fns["scene_render_preview"]()
        kw = vtools.env.scene.playblast_calls[-1]
        assert kw["format"] == "image"
        assert kw["compression"] == "png"
        assert kw["offScreen"] is True
        assert kw["viewer"] is False
        assert kw["showOrnaments"] is False
        assert kw["percent"] == 100
        assert kw["forceOverwrite"] is True
        assert kw["editorPanelName"] == "modelPanel1"

    async def test_camera_switch_terminal_state(self, vtools):
        """Net-zero: panel camera after == before; restore evidenced
        loosely (a second modelPanel camera edit back to the prior
        camera, D-039)."""
        vtools.env.scene.add_camera("CAM_x")
        before = vtools.env.scene.panels["modelPanel1"]["camera"]
        out = await vtools.fns["scene_render_preview"](camera="CAM_x")
        meta = _meta(out)
        assert meta["camera"] == "CAM_x"
        panel = vtools.env.scene.panels["modelPanel1"]
        assert panel["camera"] == before, "terminal state == entry state"
        calls = vtools.env.scene.model_panel_calls
        assert ("modelPanel1", "CAM_x") in calls
        assert len(calls) >= 2, "a restore camera edit must have happened"

    async def test_current_time_restored(self, vtools):
        """Stub playblast slams the timeline (undo bug #21) - the module
        must restore it."""
        vtools.env.scene.current_time = 42
        await vtools.fns["scene_render_preview"]()
        assert vtools.env.scene.current_time == 42

    async def test_terminal_state_on_failure(self, vtools, monkeypatch):
        """Restore still runs when playblast explodes."""
        vtools.env.scene.add_camera("CAM_x")
        vtools.env.scene.current_time = 7

        def boom(**kw):
            raise RuntimeError("playblast exploded")

        monkeypatch.setattr(vtools.module.cmds, "playblast", boom)

        out = await vtools.fns["scene_render_preview"](camera="CAM_x")
        res = json.loads(out)
        assert res["error"]["code"] == "capture_failed"
        assert vtools.env.scene.panels["modelPanel1"]["camera"] == "persp"
        assert vtools.env.scene.current_time == 7

    async def test_empty_artifact_domain_error(self, vtools):
        """Headless-quirk zero-byte playblast -> capture_empty, not
        success (D-025)."""
        vtools.env.scene.playblast_empty = True
        out = await vtools.fns["scene_render_preview"]()
        res = json.loads(out)
        assert res["error"]["code"] == "capture_empty"
        assert "suggestion" in res["error"]

    async def test_host_nonempty_gate(self, vtools, monkeypatch):
        """Even if a domain function slips through, the host never
        reports an empty artifact as success."""
        monkeypatch.setattr(
            vtools.module,
            "viewport_snapshot",
            lambda **kw: {
                "data_b64": "",
                "camera": None,
                "panel": "x",
                "width": 0,
                "height": 0,
                "format": "jpeg",
                "bytes": 0,
            },
        )
        from maya_mcp_server.security import CaptureEmptyError

        with pytest.raises(CaptureEmptyError):
            await vtools.fns["scene_viewport_snapshot"]()

    async def test_bad_base64_raises_capture_invalid(self, vtools, monkeypatch):
        """Undecodable payload -> capture_invalid (D-025 host validation)."""
        monkeypatch.setattr(
            vtools.module,
            "viewport_snapshot",
            lambda **kw: {
                "data_b64": "!!!not-base64!!!",
                "camera": "persp",
                "panel": "modelPanel1",
                "width": 4,
                "height": 4,
                "format": "jpeg",
                "bytes": 16,
            },
        )
        from maya_mcp_server.security import InvalidCaptureError

        with pytest.raises(InvalidCaptureError):
            await vtools.fns["scene_viewport_snapshot"]()

    async def test_magic_mismatch_raises_capture_invalid(self, vtools, monkeypatch):
        """Decodable but non-JPEG/PNG bytes -> capture_invalid."""
        monkeypatch.setattr(
            vtools.module,
            "viewport_snapshot",
            lambda **kw: {
                "data_b64": base64.b64encode(b"GIF89a-not-an-image").decode("ascii"),
                "camera": "persp",
                "panel": "modelPanel1",
                "width": 4,
                "height": 4,
                "format": "jpeg",
                "bytes": 16,
            },
        )
        from maya_mcp_server.security import InvalidCaptureError

        with pytest.raises(InvalidCaptureError):
            await vtools.fns["scene_viewport_snapshot"]()

    async def test_camera_not_found(self, vtools):
        out = await vtools.fns["scene_render_preview"](camera="nope_cam")
        res = json.loads(out)
        assert res["error"]["code"] == "camera_not_found"

    async def test_temp_files_cleaned(self, vtools):
        tmp = tempfile.gettempdir()
        before = set(glob.glob(os.path.join(tmp, "_mcp_visual_*")))
        await vtools.fns["scene_render_preview"]()
        await vtools.fns["scene_viewport_snapshot"]()
        after = set(glob.glob(os.path.join(tmp, "_mcp_visual_*")))
        assert after - before == set(), "no temp artifacts left"

    async def test_transport_error_raises(self, vtools):
        err_client = ErrorClient(vtools.module)
        vtools.manager.get_client = AsyncMock(return_value=err_client)
        from maya_mcp_server.client import MayaExecutionError

        with pytest.raises(MayaExecutionError, match="kaboom"):
            await vtools.fns["scene_viewport_snapshot"]()


# ------------------------------------------------------------
# Active-panel two-level probe (D-026)
# ------------------------------------------------------------


class TestActivePanelProbe:
    async def test_fallback_when_focus_panel_gone(self, vtools):
        """withFocus returns a dead/non-modelPanel name -> lsUI
        activeView fallback picks the right editor."""
        sc = vtools.env.scene
        sc.focus_panel = "bogus_panel"
        sc.panels["modelPanel2"]["activeView"] = True
        sc.panels["modelPanel1"]["activeView"] = False
        out = await vtools.fns["scene_render_preview"]()
        meta = _meta(out)
        assert meta["panel"] == "modelPanel2"
