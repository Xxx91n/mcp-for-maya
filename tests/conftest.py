"""Pytest fixtures for maya-mcp-server tests."""

from __future__ import annotations

import asyncio
import os
import socket
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


# tests/ dir is on sys.path under pytest prepend import mode; be explicit
# so maya_stub also resolves when tests are imported as a package.
sys.path.insert(0, str(Path(__file__).parent))

import maya_stub  # noqa: E402


@pytest.fixture
def mock_port() -> int:
    """Return a port for the mock server."""
    return 17002


def _probe_gui_addr() -> tuple[str, int] | None:
    """Detect a live Maya session for the gui manual tier (D-049a).

    Default probe is the :7001 bootstrap commandPort; override with
    MAYA_MCP_GUI_ADDR=host:port. Returns None when unreachable.
    """
    addr = os.environ.get("MAYA_MCP_GUI_ADDR", "127.0.0.1:7001")
    host, _, port_s = addr.partition(":")
    try:
        port = int(port_s)
    except ValueError:
        return None
    try:
        with socket.create_connection((host, port), timeout=2.0):
            return host, port
    except OSError:
        return None


@pytest.fixture
async def gui_client():
    """Bootstrap a real client against a live Maya GUI session.

    Skips cleanly when no session is reachable, or when the session
    cannot serve the Qt framed channel (headless/native-only) — the
    visual surface is structurally absent there (D-024).
    """
    from maya_mcp_server.client import MayaClient

    addr = _probe_gui_addr()
    if addr is None:
        pytest.skip("no live Maya session — set MAYA_MCP_GUI_ADDR=host:port")
    host, port = addr
    bootstrap_client = MayaClient(host=host, port=port, timeout=30.0)
    try:
        await bootstrap_client.connect()
        working = await bootstrap_client.bootstrap(client_type="qt")
    except Exception as e:
        pytest.skip(f"Maya session probe failed: {e}")
    finally:
        await bootstrap_client.disconnect()
    if not getattr(working, "framed_channel", False):
        await working.disconnect()
        pytest.skip("session has no Qt framed channel (headless or native-only)")
    yield working
    await working.disconnect()


@pytest.fixture
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def maya_env():
    """Install the maya stub and import maya_scene_module bound to it.

    Yields a namespace: .scene (stub Scene builder), .module (the
    maya_scene_module under test), .cmds (stub maya.cmds).
    """
    scene = maya_stub.install()
    module = maya_stub.load_scene_module()
    env = SimpleNamespace(
        scene=scene,
        module=module,
        cmds=sys.modules["maya.cmds"],
        om2=sys.modules["maya.api.OpenMaya"],
    )
    yield env
    maya_stub.uninstall()
    sys.modules.pop("maya_mcp_server.maya_scene_module", None)
