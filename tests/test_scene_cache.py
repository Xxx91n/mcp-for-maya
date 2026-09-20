"""Tests for scene_cache.py."""

from __future__ import annotations

import asyncio
import time

import pytest

from maya_mcp_server.scene_cache import SceneCache


class TestSceneCache:
    """Test SceneCache TTL and dirty detection."""

    def test_initial_dirty(self):
        """Cache starts dirty on creation."""
        cache = SceneCache()
        assert cache.is_dirty is True

    def test_hit_rate_empty(self):
        """Hit rate is 0 when no calls made."""
        cache = SceneCache()
        assert cache.hit_rate == 0.0

    def test_mark_dirty(self):
        """mark_dirty sets dirty flag."""
        cache = SceneCache()
        cache._dirty = False
        cache.mark_dirty()
        assert cache.is_dirty is True

    def test_invalidate_all(self):
        """invalidate() clears all entries."""
        cache = SceneCache()
        cache._cache["test"] = ("data", time.monotonic())
        cache._dirty = False
        cache.invalidate()
        assert len(cache._cache) == 0
        assert cache.is_dirty is True

    def test_invalidate_specific_key(self):
        """invalidate(key) removes only that key."""
        cache = SceneCache()
        cache._cache["a"] = ("data_a", time.monotonic())
        cache._cache["b"] = ("data_b", time.monotonic())
        cache._dirty = False
        cache.invalidate("a")
        assert "a" not in cache._cache
        assert "b" in cache._cache

    @pytest.mark.asyncio
    async def test_get_or_fetch_miss(self):
        """First call always fetches (dirty)."""
        cache = SceneCache()

        async def fetch():
            return "fresh_data"

        result = await cache.get_or_fetch("key", fetch)
        assert result == "fresh_data"
        assert cache._miss_count == 1

    @pytest.mark.asyncio
    async def test_get_or_fetch_hit(self):
        """Second call within TTL returns cached data."""
        cache = SceneCache(ttl_seconds=10.0)

        async def fetch():
            return "data"

        result1 = await cache.get_or_fetch("key", fetch)
        result2 = await cache.get_or_fetch("key", fetch)
        assert result1 == "data"
        assert result2 == "data"
        assert cache._hit_count == 1
        assert cache._miss_count == 1

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Cache expires after TTL."""
        cache = SceneCache(ttl_seconds=0.01)  # 10ms TTL
        call_count = 0

        async def fetch():
            nonlocal call_count
            call_count += 1
            return f"data_{call_count}"

        await cache.get_or_fetch("key", fetch)
        time.sleep(0.02)  # Wait for TTL
        result = await cache.get_or_fetch("key", fetch)
        assert result == "data_2"
        assert cache._miss_count == 2

    @pytest.mark.asyncio
    async def test_dirty_forces_refetch(self):
        """mark_dirty forces refetch on next get_or_fetch."""
        cache = SceneCache(ttl_seconds=10.0)
        call_count = 0

        async def fetch():
            nonlocal call_count
            call_count += 1
            return f"data_{call_count}"

        await cache.get_or_fetch("key", fetch)
        cache.mark_dirty()
        result = await cache.get_or_fetch("key", fetch)
        assert result == "data_2"
        assert cache._miss_count == 2

    def test_get_stats(self):
        """get_stats returns correct statistics."""
        cache = SceneCache()
        stats = cache.get_stats()
        assert stats["entries"] == 0
        assert stats["hit_count"] == 0
        assert stats["miss_count"] == 0
        assert stats["is_dirty"] is True
        assert stats["ttl_seconds"] == 5.0

    @pytest.mark.asyncio
    async def test_hit_rate_tracking(self):
        """Hit rate correctly tracks hits and misses."""
        cache = SceneCache(ttl_seconds=10.0)

        async def fetch():
            return "data"

        # 1 miss
        await cache.get_or_fetch("k1", fetch)
        # 1 hit
        await cache.get_or_fetch("k1", fetch)
        # 1 miss
        await cache.get_or_fetch("k2", fetch)

        assert cache._hit_count == 1
        assert cache._miss_count == 2
        assert abs(cache.hit_rate - 1 / 3) < 0.01
