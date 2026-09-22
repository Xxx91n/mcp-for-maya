"""Teardown protocol regression tests (D-058 / upstream issue #4).

create_module(overwrite=True) must invoke the old module's _mcp_teardown
hook before evicting it from sys.modules; the injected helper ships an
idempotent _mcp_teardown that releases its Qt server and stream capture.
"""

from __future__ import annotations

import json
import sys

import pytest

import maya_mcp_server.maya_mcp_helper as helper
from maya_mcp_server.bootstrap import get_bootstrap_code


_MOD = "_mcp_t16_probe"


@pytest.fixture
def create_module():
    """The real bootstrap create_module, exec'd into a private namespace.

    create_module writes into the ambient sys.modules (it is Maya-side
    code), so each test pops its probe module on teardown.
    """
    ns: dict = {}
    exec(get_bootstrap_code(), ns)
    yield ns["create_module"]
    sys.modules.pop(_MOD, None)


class TestCreateModuleTeardown:
    """The overwrite branch must run the old module's hook first."""

    def test_teardown_called_and_resources_closed(self, create_module) -> None:
        code_v1 = (
            "class _Res:\n"
            "    closed = False\n"
            "    def close(self):\n"
            "        self.closed = True\n"
            "resource = _Res()\n"
            "calls = []\n"
            "def _mcp_teardown():\n"
            "    calls.append(1)\n"
            "    resource.close()\n"
            "    return '{\"success\": true}'\n"
        )
        out = json.loads(create_module(_MOD, code_v1))
        assert out["success"] is True
        old = sys.modules[_MOD]

        out = json.loads(create_module(_MOD, "MARKER = 'v2'\n", overwrite=True))

        assert out["success"] is True
        assert "warning" not in out
        assert old.calls == [1]
        assert old.resource.closed is True
        assert sys.modules[_MOD] is not old
        assert sys.modules[_MOD].MARKER == "v2"

    def test_teardown_exception_does_not_block_replacement(self, create_module) -> None:
        create_module(_MOD, "def _mcp_teardown():\n    raise RuntimeError('boom')\n")
        old = sys.modules[_MOD]

        out = json.loads(create_module(_MOD, "MARKER = 'v2'\n", overwrite=True))

        assert out["success"] is True
        assert "boom" in out["warning"]
        assert sys.modules[_MOD] is not old
        assert sys.modules[_MOD].MARKER == "v2"

    def test_overwrite_module_without_hook(self, create_module) -> None:
        create_module(_MOD, "X = 1\n")
        old = sys.modules[_MOD]

        out = json.loads(create_module(_MOD, "X = 2\n", overwrite=True))

        assert out["success"] is True
        assert "warning" not in out
        assert sys.modules[_MOD] is not old
        assert sys.modules[_MOD].X == 2


class _FakeQtServer:
    def __init__(self) -> None:
        self.stop_calls = 0

    def stop(self) -> None:
        self.stop_calls += 1


class TestHelperTeardown:
    """maya_mcp_helper._mcp_teardown releases module-level resources."""

    def test_stops_qt_server_and_is_idempotent(self, monkeypatch) -> None:
        fake = _FakeQtServer()
        monkeypatch.setattr(helper, "_qt_server", fake)

        first = json.loads(helper._mcp_teardown())
        assert first["success"] is True
        assert fake.stop_calls == 1
        assert helper._qt_server is None

        second = json.loads(helper._mcp_teardown())
        assert second["success"] is True
        assert fake.stop_calls == 1  # second call is a no-op

    def test_teardown_error_isolated_per_resource(self, monkeypatch) -> None:
        class _Boom:
            def stop(self) -> None:
                raise RuntimeError("stop exploded")

        monkeypatch.setattr(helper, "_qt_server", _Boom())
        out = json.loads(helper._mcp_teardown())
        assert out["success"] is False
        assert any("stop exploded" in e for e in out["errors"])
        assert helper._qt_server is None  # released anyway

    def test_restores_stream_capture(self, monkeypatch) -> None:
        helper.install_stream_capture()
        assert helper._stdout_writer is not None
        monkeypatch.setattr(helper, "_qt_server", None)
        try:
            out = json.loads(helper._mcp_teardown())
            assert out["success"] is True
            assert helper._stdout_writer is None
            assert helper._stderr_writer is None
        finally:
            helper.uninstall_stream_capture()  # never leak wrapped streams


class _FakeSignal:
    def __init__(self) -> None:
        self.disconnected: list = []

    def disconnect(self, slot) -> None:
        self.disconnected.append(slot)


class _FakeTcpServer:
    def __init__(self) -> None:
        self.newConnection = _FakeSignal()
        self.closed = False
        self.deleted = False

    def close(self) -> None:
        self.closed = True

    def deleteLater(self) -> None:  # noqa: N802 - mirrors Qt API
        self.deleted = True


class _FakeSocket:
    def __init__(self) -> None:
        self.disconnected = False
        self.deleted = False

    def disconnectFromHost(self) -> None:  # noqa: N802 - mirrors Qt API
        self.disconnected = True

    def deleteLater(self) -> None:  # noqa: N802
        self.deleted = True


class TestQtTeardownSemantics:
    """stop() must unwire signals and deleteLater Qt objects (D-058)."""

    def test_stop_disconnects_new_connection_and_deletes(self) -> None:
        srv = helper.QtCommandServer.__new__(helper.QtCommandServer)
        srv._server = _FakeTcpServer()
        srv._channels = {}
        srv._running = True

        srv.stop()

        assert srv._server.newConnection.disconnected == [srv._on_new_connection]
        assert srv._server.closed is True
        assert srv._server.deleted is True

    def test_channel_close_deletes_socket(self) -> None:
        sock = _FakeSocket()
        ch = helper.ClientChannel(sock)
        ch.close()
        assert sock.disconnected is True
        assert sock.deleted is True


def test_build_marker_present() -> None:
    assert isinstance(helper.__build__, str) and helper.__build__
