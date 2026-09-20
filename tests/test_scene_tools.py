"""Tests for scene_tools.py.

Note: These tests mock the Maya client since we cannot run Maya in test env.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from maya_mcp_server.cos_formatter import format_measure_cos, format_scene_cos
from maya_mcp_server.scene_tools import (
    TokenBudget,
    _caches,
    _get_cache,
    _injected_sessions,
    mark_dirty,
    register_scene_tools,
)


class TestTokenBudget:
    """Test token budget auto-selection."""

    def test_small_scene(self):
        assert TokenBudget.auto_select_level(30) == "small"

    def test_medium_scene(self):
        assert TokenBudget.auto_select_level(100) == "medium"

    def test_large_scene(self):
        assert TokenBudget.auto_select_level(300) == "large"

    def test_huge_scene(self):
        assert TokenBudget.auto_select_level(800) == "huge"

    def test_estimate_tokens(self):
        """Token estimate is roughly len/4."""
        assert TokenBudget.estimate_tokens("hello world test") == 4  # 16 chars / 4

    def test_budgets_have_required_keys(self):
        """All budgets have required fields."""
        for level, budget in TokenBudget.BUDGETS.items():
            assert "max_tokens" in budget
            assert "detail" in budget
            assert "max_objects" in budget


class TestCacheIntegration:
    """Test cache and dirty marking."""

    def setup_method(self):
        """Clear global caches before each test."""
        _caches.clear()
        _injected_sessions.clear()

    def test_get_cache_creates_new(self):
        """First access creates a new cache."""
        cache = _get_cache("test_session")
        assert cache is not None
        assert cache.is_dirty is True

    def test_get_cache_returns_same(self):
        """Second access returns the same cache."""
        cache1 = _get_cache("test_session")
        cache2 = _get_cache("test_session")
        assert cache1 is cache2

    def test_mark_dirty_existing(self):
        """mark_dirty on existing cache sets dirty flag."""
        cache = _get_cache("test_session")
        cache._dirty = False
        mark_dirty("test_session")
        assert cache.is_dirty is True

    def test_mark_dirty_nonexistent(self):
        """mark_dirty on nonexistent session is a no-op."""
        mark_dirty("nonexistent")  # Should not raise

    def test_mark_dirty_default_session(self):
        """mark_dirty works with None session key."""
        cache = _get_cache(None)
        cache._dirty = False
        mark_dirty(None)
        assert cache.is_dirty is True


class TestSceneToolsRegistration:
    """Test that scene tools can be registered."""

    def test_register_scene_tools_callable(self):
        """register_scene_tools is callable."""
        assert callable(register_scene_tools)

    def test_register_adds_tools(self):
        """register_scene_tools adds 4 tools to MCP."""
        mock_mcp = MagicMock()
        registered = {}

        def capture_tool(fn=None, **_kwargs):
            if fn is None:
                return lambda f: capture_tool(f)
            registered[fn.__name__] = fn
            return fn

        mock_mcp.tool = capture_tool

        register_scene_tools(mock_mcp)

        assert "scene_snapshot" in registered
        assert "scene_inspect" in registered
        assert "scene_measure" in registered
        assert "scene_assert" in registered
        assert len(registered) == 13


class TestMayaSceneModule:
    """Test maya_scene_module.py can be imported (syntax check)."""

    def test_module_source_exists(self):
        """Module source file exists."""
        from maya_mcp_server.scene_tools import _MODULE_SOURCE

        assert _MODULE_SOURCE.exists()

    def test_module_source_is_valid_python(self):
        """Module source is valid Python (syntax check)."""
        from maya_mcp_server.scene_tools import _MODULE_SOURCE

        source = _MODULE_SOURCE.read_text(encoding="utf-8-sig")  # Handle BOM
        compile(source, str(_MODULE_SOURCE), "exec")

    def test_module_has_required_functions(self):
        """Module defines all required functions."""
        from maya_mcp_server.scene_tools import _MODULE_SOURCE

        source = _MODULE_SOURCE.read_text(encoding="utf-8-sig")
        required = [
            "def get_scene_graph(",
            "def get_zone_map(",
            "def get_spatial_index(",
            "def measure(",
            "def get_material_map(",
            "def get_unit_info(",
            "def assert_scene_state(",
        ]
        for func_sig in required:
            assert func_sig in source, f"Missing function: {func_sig}"


class TestCosFormatterIntegration:
    """Integration test: CoS formatter works with scene data shapes."""

    def test_format_scene_cos_roundtrip(self):
        """CoS formatter handles realistic scene data."""
        scene = {
            "objects": [
                {
                    "n": "store_shell",
                    "t": "mesh",
                    "p": [0, 0, 300],
                    "b": [-500, -10, 0, 500, 10, 600],
                },
                {
                    "n": "entrance_door",
                    "t": "mesh",
                    "p": [0, 0, 500],
                    "b": [-100, -5, 490, 100, 5, 510],
                },
                {
                    "n": "kitty_figure",
                    "t": "mesh",
                    "p": [0, 0, 300],
                    "b": [-30, 0, 270, 30, 60, 330],
                },
            ],
            "stats": {"total": 3, "by_type": {"mesh": 3}},
            "unit": "cm",
            "up_axis": "y",
        }
        zones = [
            {"name": "shell", "objects": ["store_shell"], "center": [0, 0, 300]},
            {"name": "entrance", "objects": ["entrance_door"], "center": [0, 0, 500]},
            {"name": "ip_core", "objects": ["kitty_figure"], "center": [0, 0, 300]},
        ]
        result = format_scene_cos(scene, zones=zones)
        assert "SCENE[3obj, 3zones]" in result
        assert "store_shell" in result
        assert "kitty_figure" in result

    def test_format_measure_cos_roundtrip(self):
        """Measure formatter handles realistic data."""
        result_data = {
            "obj_a": "store_shell",
            "obj_b": "entrance_door",
            "mode": "clearance",
            "distance": 45.5,
            "unit": "cm",
            "bbox_overlap": False,
        }
        result = format_measure_cos(result_data)
        assert "45.5" in result
        assert "clearance" in result
