"""Maya-side visual capture module - injected as _mcp_visual (D-023/D-024).

GUI-only capture paths. The host never injects this module into a
headless session (framed_channel gate), but every public function
still re-checks GUI capability and returns the two-layer error
contract's domain shape {error:{code,message,suggestion}} (D-019)
for extreme headless-ish GUI environments (missing omui/PySide,
batch mode, no modelPanel).

Public API:
    viewport_snapshot(max_size, format, quality) -> dict
    render_preview(camera, width, height, max_size, format, quality) -> dict

Both return {"data_b64", "camera", "panel", "width", "height",
"format", "bytes"} on success (preview adds "source": "playblast"),
or {"error": {...}} on a domain failure. Exceptions raised here are
transport errors, not domain results.
"""

from __future__ import annotations

import base64
import glob
import importlib
import logging
import os
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import maya.cmds as cmds


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Optional GUI dependencies - defensive import (D-024)
# ---------------------------------------------------------------------------

_omui: Any = None
_QtGui: Any = None
_QtCore: Any = None
_IMPORT_ERROR: Exception | None = None

try:
    _omui = importlib.import_module("maya.api.OpenMayaUI")
except Exception as exc:  # pragma: no cover - real-Maya only
    _IMPORT_ERROR = exc

# MImage lives in maya.api.OpenMaya on Maya <=2024 and moved to
# maya.api.OpenMayaUI on 2025+ — resolve once, tolerate both layouts.
# (Real-Maya find: the omui-only path crashed on Maya 2024 with
# "module 'maya.api.OpenMayaUI' has no attribute 'MImage'".)
_MImage: Any = None
if _omui is not None:
    _MImage = getattr(_omui, "MImage", None)
if _MImage is None:
    try:
        _MImage = getattr(importlib.import_module("maya.api.OpenMaya"), "MImage", None)
    except Exception:
        _MImage = None

try:
    _QtCore = importlib.import_module("PySide6.QtCore")
    _QtGui = importlib.import_module("PySide6.QtGui")
except Exception:
    try:
        _QtCore = importlib.import_module("PySide2.QtCore")
        _QtGui = importlib.import_module("PySide2.QtGui")
    except Exception as exc:
        if _IMPORT_ERROR is None:
            _IMPORT_ERROR = exc


_GUI_REQUIRED_SUGGESTION = (
    "connect to a Maya GUI session; headless (mayapy/batch) sessions "
    "have no viewport or playblast surface"
)


# ---------------------------------------------------------------------------
# Error helpers + capability gate
# ---------------------------------------------------------------------------


def _err(code: str, message: str, suggestion: str | None = None) -> dict[str, Any]:
    """D-019 domain error shape: {error:{code,message,suggestion?}}."""
    e = {"code": code, "message": str(message)}
    if suggestion:
        e["suggestion"] = suggestion
    return {"error": e}


def _gui_block() -> dict[str, Any] | None:
    """None when GUI capture is possible, else the structured error.

    Maya-side gate of the double headless check (D-024/D-025): batch
    mode OR no modelPanel -> gui_session_required. Import failure of
    omui/PySide in extreme headless-ish GUI envs maps to the same code.
    """
    if _omui is None or _QtGui is None or _QtCore is None:
        return _err(
            "gui_session_required",
            f"visual capture dependencies failed to import: {_IMPORT_ERROR}",
            _GUI_REQUIRED_SUGGESTION,
        )
    try:
        if cmds.about(batch=True):
            return _err(
                "gui_session_required",
                "Maya is running in batch mode",
                _GUI_REQUIRED_SUGGESTION,
            )
    except Exception:
        pass
    try:
        if not (cmds.getPanel(type="modelPanel") or []):
            return _err(
                "gui_session_required",
                "no modelPanel exists in this session",
                _GUI_REQUIRED_SUGGESTION,
            )
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Viewport state helpers (D-026 net-zero side effect machinery)
# ---------------------------------------------------------------------------


def _active_model_panel() -> str | None:
    """Two-level probe for the working model panel.

    1) getPanel(withFocus=True) verified as a modelEditor via objectTypeUI
    2) fallback: first lsUI(editors=True) editor whose activeView is set
    """
    try:
        panel = cmds.getPanel(withFocus=True)
        if panel and cmds.objectTypeUI(panel) == "modelEditor":
            return str(panel)
    except Exception:
        pass
    try:
        for ed in cmds.lsUI(editors=True) or []:
            try:
                if cmds.modelEditor(ed, query=True, activeView=True):
                    return str(ed)
            except Exception:
                continue
    except Exception:
        pass
    return None


@contextmanager
def _camera_switch_restored(panel: str, camera: str | None) -> Iterator[None]:
    """Point *panel* at *camera*, restoring the prior camera afterwards.

    Switching a modelPanel's camera is instantaneous, visible, and NOT
    undoable - so the restore is what makes this net-zero. The finally
    block guards on panel survival; a failed restore is logged, never
    raised over the business result (D-026). Camera switching uses the
    unambiguous modelPanel named-argument API (D-039).
    """
    prev_camera = None
    if camera:
        try:
            prev_camera = cmds.modelPanel(panel, query=True, camera=True)
        except Exception:
            prev_camera = None
        cmds.modelPanel(panel, edit=True, camera=camera)
    try:
        yield
    finally:
        if camera:
            try:
                if cmds.modelPanel(panel, exists=True):
                    if prev_camera:
                        cmds.modelPanel(panel, edit=True, camera=prev_camera)
                    else:
                        logger.warning(
                            "camera restore skipped for %s: prior camera unreadable",
                            panel,
                        )
            except Exception:
                logger.warning("camera restore failed for panel %s", panel)


# ---------------------------------------------------------------------------
# Encode pipeline: MImage/file -> QImage -> downsample -> bytes
# ---------------------------------------------------------------------------


def _downscale(qimg: Any, max_size: int) -> Any:
    """Fit qimg inside a max_size box, preserving aspect ratio."""
    if max(qimg.width(), qimg.height()) > int(max_size):
        qimg = qimg.scaled(
            int(max_size),
            int(max_size),
            _QtCore.Qt.KeepAspectRatio,
            _QtCore.Qt.SmoothTransformation,
        )
    return qimg


def _encode_qimage(qimg: Any, out_format: str, quality: int) -> tuple[bytes, int, int]:
    """QImage -> encoded bytes via QBuffer. Returns (data, w, h)."""
    buf = _QtCore.QBuffer()
    # PySide6 exposes OpenModeFlag; PySide2 has the flag on QIODevice itself.
    iodev = getattr(_QtCore.QIODevice, "OpenModeFlag", _QtCore.QIODevice)
    buf.open(iodev.WriteOnly)
    if out_format == "png":
        qimg.save(buf, "PNG")
    else:
        qimg.save(buf, "JPEG", int(quality))
    data = bytes(buf.data())
    buf.close()
    return data, qimg.width(), qimg.height()


def _encode_file(path: str, max_size: int, out_format: str, quality: int) -> tuple[bytes, int, int]:
    """Load an image file, downsample, encode. Returns (data, w, h)."""
    qimg = _QtGui.QImage(path)
    if qimg.isNull():
        raise RuntimeError("QImage failed to decode capture output")
    qimg = _downscale(qimg, max_size)
    return _encode_qimage(qimg, out_format, quality)


# ---------------------------------------------------------------------------
# Public: viewport snapshot (D-023 readColorBuffer path)
# ---------------------------------------------------------------------------


def viewport_snapshot(
    max_size: int = 800, format: str = "jpeg", quality: int = 80
) -> dict[str, Any]:
    """Capture the active viewport (WYSIWYG: HUD/selection included).

    VP2 path per the official Autodesk patch: the image must be a
    float buffer or readColorBuffer returns an all-black image.
    """
    blocked = _gui_block()
    if blocked:
        return blocked
    if _MImage is None:
        return _err(
            "capture_unsupported",
            "MImage not found in maya.api.OpenMayaUI or maya.api.OpenMaya",
            "report the Maya version — MImage moved modules in Maya 2025",
        )
    try:
        cmds.refresh(force=True)
    except Exception:
        pass
    try:
        view = _omui.M3dView.active3dView()
        panel = _active_model_panel()
        img = _MImage()
        if view.getRendererName() == view.kViewport2Renderer:
            # VP2 needs a float target buffer or the read comes back
            # all-black (official patch path). convertPixelFormat only
            # exists on 2025+ — on <=2024 readColorBuffer already lands
            # in a writeToFile-able format (verified live: identical
            # PNG output with and without the conversion).
            img.create(
                view.portWidth(),
                view.portHeight(),
                4,
                _MImage.kFloat,
            )
            view.readColorBuffer(img)
            if hasattr(img, "convertPixelFormat"):
                img.convertPixelFormat(_MImage.kByte)
        else:
            view.readColorBuffer(img)
        # GL buffers arrive bottom-up; flip for a correctly-oriented PNG.
        img.verticalFlip()

        fd, tmp = tempfile.mkstemp(prefix="_mcp_visual_", suffix=".png")
        os.close(fd)
        try:
            img.writeToFile(tmp, "png")
            data, w, h = _encode_file(tmp, max_size, format, quality)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

        camera = None
        if panel:
            try:
                camera = cmds.modelEditor(panel, query=True, camera=True)
            except Exception:
                camera = None
        return {
            "data_b64": base64.b64encode(data).decode("ascii"),
            "camera": camera,
            "panel": panel,
            "width": w,
            "height": h,
            "format": format,
            "bytes": len(data),
        }
    except Exception as e:
        return _err("capture_failed", f"viewport snapshot failed: {e}")


# ---------------------------------------------------------------------------
# Public: render preview (D-023 playblast path + D-026 side-effect discipline)
# ---------------------------------------------------------------------------


def _find_playblast_output(tmp_base: str, expected: str) -> str | None:
    """Resolve the file playblast actually wrote.

    completeFilename is honored verbatim for a single-frame still, but
    Maya may still suffix a frame number on some paths - glob the stem.
    """
    if os.path.exists(expected):
        return expected
    hits = sorted(glob.glob(tmp_base + "*.png"))
    return hits[0] if hits else None


def render_preview(
    camera: str | None = None,
    width: int = 640,
    height: int = 360,
    max_size: int = 800,
    format: str = "jpeg",
    quality: int = 80,
) -> dict[str, Any]:
    """Single-frame playblast from *camera* (or the panel's current camera).

    Net-zero side effect (D-026): the panel camera and the timeline are
    restored on every path - success or failure - unless the process is
    killed mid-call. width/height arrive already rounded up to /4 by
    the host (playblast Windows constraint).
    """
    blocked = _gui_block()
    if blocked:
        return blocked
    if camera is not None and not cmds.objExists(camera):
        return _err(
            "camera_not_found",
            f"camera {camera!r} does not exist",
            "pass a camera name from scene_snapshot, or omit camera to capture the current view",
        )
    panel = _active_model_panel()
    if not panel:
        return _err(
            "gui_session_required",
            "no active model panel to playblast",
            _GUI_REQUIRED_SUGGESTION,
        )

    prev_time = cmds.currentTime(query=True)
    tmp_base = os.path.join(tempfile.gettempdir(), f"_mcp_visual_{uuid.uuid4().hex}")
    png_path = tmp_base + ".png"
    try:
        with _camera_switch_restored(panel, camera):
            cmds.playblast(
                frame=int(cmds.currentTime(query=True)),
                format="image",
                compression="png",
                offScreen=True,
                viewer=False,
                showOrnaments=False,
                widthHeight=(int(width), int(height)),
                percent=100,
                forceOverwrite=True,
                editorPanelName=panel,
                completeFilename=png_path,
            )
            produced = _find_playblast_output(tmp_base, png_path)
            # Headless playblast silently writes zero-byte files -
            # never let that masquerade as success (D-025).
            if produced is None or os.path.getsize(produced) == 0:
                return _err(
                    "capture_empty",
                    "playblast produced no image data",
                    "retry on a GUI session; batch-mode playblast silently writes empty files",
                )
            data, w, h = _encode_file(produced, max_size, format, quality)

        used_cam = camera
        if used_cam is None:
            try:
                used_cam = cmds.modelEditor(panel, query=True, camera=True)
            except Exception:
                pass
        return {
            "data_b64": base64.b64encode(data).decode("ascii"),
            "camera": used_cam,
            "panel": panel,
            "width": w,
            "height": h,
            "format": format,
            "bytes": len(data),
            "source": "playblast",
        }
    except Exception as e:
        return _err("capture_failed", f"render preview failed: {e}")
    finally:
        # playblast slams the timeline to the start (undo bug #21) -
        # restore regardless of outcome.
        try:
            cmds.currentTime(prev_time, edit=True)
        except Exception:
            pass
        for p in glob.glob(tmp_base + "*"):
            try:
                os.remove(p)
            except OSError:
                pass
