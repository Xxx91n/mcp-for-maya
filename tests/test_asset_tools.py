"""T-19a tests: asset_search / asset_import tool layer.

ExecClient runs the generated code against the stub-bound _mcp_asset
module through the REAL result-capture transform - same harness pattern
as test_scene_tools_json.py. The host-side downloader is monkeypatched
to a canned descriptor; network tests live in test_polyhaven.py.
"""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import maya_stub
import pytest

from maya_mcp_server.asset_tools import (
    _asset_injected,
    _ensure_asset_injected,
    register_asset_tools,
)
from maya_mcp_server.maya_mcp_helper import prepare_code_for_result_capture
from maya_mcp_server.security import AuditLogger, InputValidationError
from maya_mcp_server.types import CommandResponse, OutputBuffer, ResultType


class ExecClient:
    """Fake client: executes generated code with _mcp_asset bound."""

    def __init__(self, module):
        self.module = module
        self.calls = []

    async def execute_code(self, code, result_type=ResultType.NONE):
        self.calls.append(code)
        rt = getattr(result_type, "value", result_type)
        ctx = {"__builtins__": __builtins__, "_mcp_asset": self.module}
        if rt == "NONE":
            exec(compile(code, "<mcp>", "exec"), ctx)
            return CommandResponse(result=None, error=None)
        modified, was = prepare_code_for_result_capture(code)
        if not was:
            raise RuntimeError(f"result not capturable: {code}")
        ctx["_mcp_result"] = None
        exec(compile(modified, "<mcp>", "exec"), ctx)
        return CommandResponse(result=ctx["_mcp_result"], error=None)

    async def get_buffered_output(self):
        return OutputBuffer()

    def append_output(self, stdout, stderr):
        pass

    async def write_module(self, name, code, overwrite=False):
        return name


@pytest.fixture
def tools(maya_env, monkeypatch, tmp_path):
    """Stub scene + bound _mcp_asset + captured tool fns."""
    module = maya_stub.load_asset_module()
    sys.modules["_mcp_asset"] = module
    _asset_injected.add("_default")

    # local asset files for the descriptor
    fbx = tmp_path / "Camera_01_1k.fbx"
    fbx.write_bytes(b"FBX!!")
    tex = tmp_path / "body_diff_1k.jpg"
    tex.write_bytes(b"DIFF")

    descriptor = {
        "asset_id": "Camera_01",
        "resolution": "1k",
        "fbx_path": str(fbx),
        "texture_parts": {"body": {"diff": str(tex)}},
        "license": "CC0-1.0",
        "source": "download",
        "size_bytes": 9,
        "cache_dir": str(tmp_path),
        "asset_page": "https://polyhaven.com/a/Camera_01",
        "files_hash": {
            "Camera_01_1k.fbx": {
                "url": "https://dl.polyhaven.org/x/Camera_01_1k.fbx",
                "size": 5,
                "md5": "m1",
                "sha256": "s1",
            }
        },
    }

    maya_env.scene.fbx_fixture = {
        "materials": [{"name": "body", "type": "phong"}],
        "meshes": [{"name": "Camera_01_body", "faces": 1200, "material": "body"}],
    }

    from maya_mcp_server import polyhaven

    monkeypatch.setattr(polyhaven, "download_asset", lambda *a, **kw: dict(descriptor))
    monkeypatch.setattr(
        polyhaven,
        "search_assets",
        lambda query="", asset_type="models", limit=20: {
            "results": [{"id": "Camera_01", "name": "Camera 01"}],
            "total_count": 1,
            "query": query,
            "asset_type": asset_type,
        },
    )

    client = ExecClient(module)
    manager = MagicMock()
    manager.get_client = AsyncMock(return_value=client)
    monkeypatch.setattr("maya_mcp_server.server.get_session_manager", lambda: manager)

    audit = AuditLogger(tmp_path / "audit.jsonl")
    mock_mcp = MagicMock()
    fns = {}

    def capture(fn=None, **_kwargs):
        if fn is None:
            return lambda f: capture(f)
        fns[fn.__name__] = fn
        return fn

    mock_mcp.tool = capture
    register_asset_tools(mock_mcp, audit=audit)
    yield SimpleNamespace(
        fns=fns,
        client=client,
        manager=manager,
        env=maya_env,
        module=module,
        audit=audit,
        audit_path=tmp_path / "audit.jsonl",
        descriptor=descriptor,
    )
    _asset_injected.discard("_default")
    sys.modules.pop("_mcp_asset", None)


class TestInjectionHygiene:
    """D-082a: same mkstemp/0600/finally-unlink contract as _mcp_scene."""

    async def test_native_channel_tmpfile_lifecycle(self):
        import os
        from pathlib import Path

        import platformdirs

        inject_dir = Path(platformdirs.user_cache_dir("mcp-for-maya")) / "inject"
        pre = set(inject_dir.glob("_mcp_asset_src_*.py")) if inject_dir.exists() else set()

        client = SimpleNamespace(framed_channel=False)
        seen = {}

        async def exec_code(code, result_type=ResultType.NONE):
            # The follow-up "import _mcp_asset" call runs post-unlink —
            # only record while the staged file actually exists.
            now = sorted(inject_dir.glob("_mcp_asset_src_*.py"))
            if now:
                seen["files"] = [p.name for p in now]
                if os.name != "nt":
                    seen["mode"] = oct(now[0].stat().st_mode & 0o777)
            return CommandResponse(result=None, error=None)

        client.execute_code = exec_code
        _asset_injected.discard("hygiene")
        try:
            await _ensure_asset_injected(client, "hygiene")
        finally:
            _asset_injected.discard("hygiene")

        assert seen.get("files"), "native path must stage a temp file"
        assert seen["files"][0] != "_mcp_asset_src.py", "unique mkstemp name"
        if os.name != "nt":
            assert seen["mode"] == "0o600"
        post = set(inject_dir.glob("_mcp_asset_src_*.py")) if inject_dir.exists() else set()
        assert post == pre, "temp file must be unlinked after injection"


class TestAssetSearch:
    async def test_search_returns_results(self, tools):
        out = await tools.fns["asset_search"](query="camera")
        res = json.loads(out)
        assert res["total_count"] == 1
        assert res["results"][0]["id"] == "Camera_01"

    async def test_search_domain_error_not_raised(self, tools, monkeypatch):
        from maya_mcp_server import polyhaven

        def boom(**kw):
            raise polyhaven.AssetError("network_unavailable", "offline")

        monkeypatch.setattr(polyhaven, "search_assets", boom)
        out = await tools.fns["asset_search"](query="x")
        res = json.loads(out)
        assert res["error"]["code"] == "network_unavailable"

    async def test_search_bad_asset_type_raises(self, tools):
        with pytest.raises(InputValidationError):
            await tools.fns["asset_search"](asset_type="models;rm -rf")


class TestAssetImport:
    async def test_import_happy_path(self, tools):
        out = await tools.fns["asset_import"](asset_id="Camera_01")
        res = json.loads(out)
        assert "error" not in res, res
        assert res["group"].startswith("GRP_asset_Camera_01")
        assert res["polycount"] == 1200
        assert res["download"]["source"] == "download"
        assert res["license"] == "CC0-1.0"
        # the tool drove the real generated-code path
        assert any("_mcp_asset" in c for c in tools.client.calls)

    async def test_import_dedup_second_call(self, tools):
        await tools.fns["asset_import"](asset_id="Camera_01")
        out = await tools.fns["asset_import"](asset_id="Camera_01")
        res = json.loads(out)
        assert res.get("deduped") is True

    async def test_import_validation_errors(self, tools):
        with pytest.raises(InputValidationError):
            await tools.fns["asset_import"](asset_id="../bad id")
        with pytest.raises(InputValidationError):
            await tools.fns["asset_import"](asset_id="ok", resolution="3k")

    async def test_import_download_error_is_domain_json(self, tools, monkeypatch):
        from maya_mcp_server import polyhaven

        def boom(*a, **kw):
            raise polyhaven.AssetError("network_unavailable", "cannot reach dl.polyhaven.org")

        monkeypatch.setattr(polyhaven, "download_asset", boom)
        out = await tools.fns["asset_import"](asset_id="Camera_01")
        res = json.loads(out)
        assert res["error"]["code"] == "network_unavailable"

    async def test_polycount_gate_via_tool(self, tools):
        tools.env.scene.fbx_fixture["meshes"][0]["faces"] = 200000
        out = await tools.fns["asset_import"](asset_id="Camera_01")
        res = json.loads(out)
        assert res["error"]["code"] == "polycount_exceeded"
        # override keeps it
        out2 = await tools.fns["asset_import"](asset_id="Camera_01", allow_high_polycount=True)
        res2 = json.loads(out2)
        assert "error" not in res2, res2

    async def test_audit_records_download_details(self, tools):
        await tools.fns["asset_import"](asset_id="Camera_01")
        lines = [
            json.loads(line) for line in tools.audit_path.read_text().splitlines() if line.strip()
        ]
        rows = [line for line in lines if line.get("asset_download")]
        assert rows, "supplementary asset_download audit row missing"
        row = rows[0]["asset_download"]
        assert row["source"] == "download"
        assert row["size_bytes"] == 9
        assert "Camera_01_1k.fbx" in row["files_hash"]
        assert row["files_hash"]["Camera_01_1k.fbx"]["md5"] == "m1"
        # emitted after the Maya import, carrying its outcome
        assert rows[0]["outcome"] == "success"
        assert row["import_group"] == "GRP_asset_Camera_01"
        assert row["import_error"] is None

    async def test_audit_duration_ms_is_measured(self, tools, monkeypatch):
        """D-082f: duration_ms is a real wall-clock measurement, not the
        old 0.0 placeholder lying in every supplementary audit row."""
        # first monotonic() call is the t0 start mark; every later call
        # returns the end mark -> measured span is exactly 250 ms even
        # if the call sites gain extra monotonic probes.
        seq = iter([1000.0] + [1000.25] * 50)
        monkeypatch.setattr("maya_mcp_server.asset_tools.time.monotonic", lambda: next(seq))
        await tools.fns["asset_import"](asset_id="Camera_01")
        lines = [
            json.loads(line) for line in tools.audit_path.read_text().splitlines() if line.strip()
        ]
        rows = [line for line in lines if line.get("asset_download")]
        assert rows[0]["duration_ms"] == 250.0
