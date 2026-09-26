"""T-24b host-tool tests: scene_describe / scene_nodes (D-094/D-095).

ExecClient runs generated code against the stub-bound _mcp_scene
assembly (monolith + introspect_module fragment) via the REAL
result-capture transform - same chain as test_scene_tools_json.py and
test_export_tools.py. Covers injection lifecycle, dual channels,
domain-error passthrough, input validation, and annotations.
"""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from maya_mcp_server.introspect_tools import register_introspect_tools
from maya_mcp_server.maya_mcp_helper import prepare_code_for_result_capture
from maya_mcp_server.scene_tools import _injected_sessions
from maya_mcp_server.types import CommandResponse, OutputBuffer, ResultType


class ExecClient:
    """Fake framed-channel client: runs generated code on the stub module."""

    framed_channel = True

    def __init__(self, module):
        self.module = module
        self.calls = []
        self.written = []

    async def execute_code(self, code, result_type=ResultType.NONE):
        self.calls.append(code)
        rt = getattr(result_type, "value", result_type)
        ctx = {"__builtins__": __builtins__, "_mcp_scene": self.module}
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
        self.written.append((name, code))
        # mirror real write_module: register the module like Maya does
        import types as _t

        m = _t.ModuleType(name)
        exec(compile(code, name + ".py", "exec"), m.__dict__)
        sys.modules[name] = m
        return name

    async def get_buffered_output(self):
        return OutputBuffer()

    def append_output(self, stdout, stderr):
        pass


class NativeClient(ExecClient):
    """Headless/native channel: ensure_module_injected takes the mkstemp
    staging path for large modules (>15000 chars). The exec'd module
    lands in sys.modules under _mcp_scene - calls still resolve."""

    framed_channel = False


@pytest.fixture
def tools(maya_env, monkeypatch):
    sys.modules["_mcp_scene"] = maya_env.module
    _injected_sessions.add("_default")
    client = ExecClient(maya_env.module)
    manager = MagicMock()
    manager.get_client = AsyncMock(return_value=client)
    monkeypatch.setattr("maya_mcp_server.server.get_session_manager", lambda: manager)
    mock_mcp = MagicMock()
    fns = {}

    def capture(fn=None, **_kw):
        if fn is None:
            return lambda f: capture(f)
        fns[fn.__name__] = fn
        return fn

    mock_mcp.tool = capture
    register_introspect_tools(mock_mcp)
    yield SimpleNamespace(fns=fns, client=client, manager=manager, env=maya_env)
    _injected_sessions.discard("_default")
    sys.modules.pop("_mcp_scene", None)


# ------------------------------------------------------------
# Registration + contract
# ------------------------------------------------------------


def test_registers_exactly_two_tools(tools):
    assert set(tools.fns) == {"scene_describe", "scene_nodes"}


async def test_describe_returns_json_contract(tools):
    tools.env.scene.add_mesh("GEO_a", t=(1, 0, 0))
    out = json.loads(await tools.fns["scene_describe"]("GEO_a"))
    assert out["type"] == "transform"
    assert isinstance(out["attrs"], list) and out["attrs"]
    assert "connections" in out


async def test_describe_domain_error_passthrough(tools):
    out = json.loads(await tools.fns["scene_describe"]("ghost_node"))
    assert out["error"]["code"] == "node_not_found"


async def test_describe_attrs_subset_and_values(tools):
    tools.env.scene.add_mesh("GEO_a", t=(9, 9, 9))
    out = json.loads(
        await tools.fns["scene_describe"]("GEO_a", attrs=["translate"], include_values=True)
    )
    assert len(out["attrs"]) == 1
    assert out["attrs"][0]["value"] == [[9, 9, 9]]


async def test_nodes_enumeration_json(tools):
    tools.env.scene.add_mesh("GEO_a")
    tools.env.scene.add_material("MAT_a")
    out = json.loads(await tools.fns["scene_nodes"](dag_only=True))
    assert "MAT_a" not in out["nodes"]
    assert "|GEO_a" in out["nodes"]
    assert out["has_more"] is False


async def test_nodes_invalid_cursor_passthrough(tools):
    tools.env.scene.add_transform("T0")
    out = json.loads(await tools.fns["scene_nodes"](cursor="bogus"))
    assert out["error"]["code"] == "invalid_cursor"


# ------------------------------------------------------------
# Host-side validation
# ------------------------------------------------------------


async def test_describe_rejects_empty_node(tools):
    from maya_mcp_server.security import InputValidationError

    with pytest.raises(InputValidationError):
        await tools.fns["scene_describe"]("   ")
    with pytest.raises(InputValidationError):
        await tools.fns["scene_describe"]("GEO_a", attrs="translate")


async def test_nodes_rejects_bad_limit(tools):
    from maya_mcp_server.security import InputValidationError

    for bad in (0, -3, "fifty", True):
        with pytest.raises(InputValidationError):
            await tools.fns["scene_nodes"](limit=bad)


# ------------------------------------------------------------
# Injection lifecycle (D-095): same _mcp_scene unit, assembled payload
# ------------------------------------------------------------


async def _fresh_tools(maya_env, monkeypatch, client_cls):
    _injected_sessions.discard("_default")
    sys.modules.pop("_mcp_scene", None)
    client = client_cls(maya_env.module)
    manager = MagicMock()
    manager.get_client = AsyncMock(return_value=client)
    monkeypatch.setattr("maya_mcp_server.server.get_session_manager", lambda: manager)
    mock_mcp = MagicMock()
    fns = {}

    def capture(fn=None, **_kw):
        if fn is None:
            return lambda f: capture(f)
        fns[fn.__name__] = fn
        return fn

    mock_mcp.tool = capture
    register_introspect_tools(mock_mcp)
    return fns, client


async def test_injection_carries_fragment_in_one_unit(maya_env, monkeypatch):
    """First call writes ONE module named _mcp_scene whose source
    concatenates the monolith AND the introspection fragment (D-095)."""
    fns, client = await _fresh_tools(maya_env, monkeypatch, ExecClient)
    maya_env.scene.add_mesh("GEO_a")
    await fns["scene_describe"]("GEO_a")
    assert len(client.written) == 1
    name, source = client.written[0]
    assert name == "_mcp_scene"
    assert "def get_scene_graph" in source  # monolith half
    assert "def describe_node" in source  # fragment half
    assert "_mcp_introspect" not in source


async def test_injection_once_per_session(maya_env, monkeypatch):
    fns, client = await _fresh_tools(maya_env, monkeypatch, ExecClient)
    maya_env.scene.add_mesh("GEO_a")
    await fns["scene_describe"]("GEO_a")
    await fns["scene_nodes"]()
    assert len(client.written) == 1


async def test_native_channel_staged_injection(maya_env, monkeypatch):
    """Native (headless) channel: source staged via mkstemp + exec
    into sys.modules; the fragment still lands in _mcp_scene."""
    fns, client = await _fresh_tools(maya_env, monkeypatch, NativeClient)
    maya_env.scene.add_mesh("GEO_a")
    out = json.loads(await fns["scene_describe"]("GEO_a"))
    assert out["type"] == "transform"
    assert client.written == []  # no framed write_module
    staged = [c for c in client.calls if "mkstemp" not in c and "ModuleType" in c]
    assert staged, "native channel must stage via types.ModuleType exec"
    import sys as _s

    assert hasattr(_s.modules["_mcp_scene"], "describe_node")
    assert "_mcp_introspect" not in _s.modules
    # cleanup: the staged module replaced the fixture binding
    _s.modules["_mcp_scene"] = maya_env.module


async def test_no_cache_no_dirty(maya_env, monkeypatch, tools):
    """Read-only introspection touches neither scene cache nor dirty
    marking."""
    from maya_mcp_server.scene_tools import _caches

    tools.env.scene.add_mesh("GEO_a")
    await tools.fns["scene_describe"]("GEO_a")
    await tools.fns["scene_nodes"]()
    assert len(_caches) == 0
    assert tools.env.scene.refresh_calls == 0


# ------------------------------------------------------------
# Annotations
# ------------------------------------------------------------


def test_annotations_readonly():
    from maya_mcp_server.pipeline import TOOL_ANNOTATIONS

    for name in ("scene_describe", "scene_nodes"):
        ann = TOOL_ANNOTATIONS[name]
        assert ann.readOnlyHint is True
        assert ann.destructiveHint is False
        assert ann.idempotentHint is True
        assert ann.openWorldHint is False
