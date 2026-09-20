"""Tests for cos_formatter.py."""

from __future__ import annotations

import pytest

from maya_mcp_server.cos_formatter import (
    format_assert_cos,
    format_inspect_cos,
    format_measure_cos,
    format_scene_cos,
    format_zone_map_cos,
)


class TestFormatSceneCos:
    """Test scene CoS formatting."""

    def test_basic_format(self):
        """Basic scene formatting produces correct header."""
        scene = {
            "objects": [
                {"n": "wall_n", "t": "mesh", "p": [0, 0, 500], "b": [-100, -5, 490, 100, 5, 510]},
            ],
            "stats": {"total": 1},
            "unit": "cm",
            "up_axis": "y",
        }
        result = format_scene_cos(scene)
        assert "SCENE[1obj, 0zones]" in result
        assert "UNIT=cm UP=y" in result
        assert "wall_n[mesh]" in result

    def test_with_zones(self):
        """Objects grouped by zones."""
        scene = {
            "objects": [
                {"n": "wall_1", "t": "mesh", "p": [0, 0, 0], "b": [0, 0, 0, 100, 100, 100]},
                {"n": "shelf_1", "t": "mesh", "p": [200, 0, 0], "b": [200, 0, 0, 300, 50, 50]},
            ],
            "stats": {"total": 2},
            "unit": "cm",
            "up_axis": "y",
        }
        zones = [
            {"name": "shell", "objects": ["wall_1"], "center": [50, 50, 50], "object_count": 1},
            {"name": "display", "objects": ["shelf_1"], "center": [250, 25, 25], "object_count": 1},
        ]
        result = format_scene_cos(scene, zones=zones)
        assert "SHELL" in result
        assert "DISPLAY" in result

    def test_max_objects_truncation(self):
        """Objects truncated to max_objects."""
        objects = [
            {"n": f"obj_{i}", "t": "mesh", "p": [0, 0, i * 100], "b": [0, 0, 0, 10, 10, 10]}
            for i in range(100)
        ]
        scene = {"objects": objects, "stats": {"total": 100}, "unit": "cm", "up_axis": "y"}
        result = format_scene_cos(scene, max_objects=10)
        assert "90 more objects" in result

    def test_bbox_dimensions(self):
        """BBox dimensions correctly calculated."""
        scene = {
            "objects": [
                {"n": "box", "t": "mesh", "p": [0, 0, 0], "b": [0, 0, 0, 200, 300, 100]},
            ],
            "stats": {"total": 1},
            "unit": "cm",
            "up_axis": "y",
        }
        result = format_scene_cos(scene)
        assert "200x300x100" in result

    def test_child_count(self):
        """Child count shown in brackets."""
        scene = {
            "objects": [
                {"n": "group1", "t": "group", "p": [0, 0, 0], "b": [0, 0, 0, 0, 0, 0], "c": 5},
            ],
            "stats": {"total": 1},
            "unit": "cm",
            "up_axis": "y",
        }
        result = format_scene_cos(scene)
        assert "[5ch]" in result


class TestFormatInspectCos:
    """Test inspect CoS formatting."""

    def test_basic_inspect(self):
        """Basic object inspection."""
        obj = {
            "name": "wall_n",
            "type": "mesh",
            "position": [100, 0, 500],
            "bbox": {"min": [0, 0, 490], "max": [200, 30, 510]},
            "material": "mat_dark",
            "vertex_count": 24,
            "face_count": 6,
        }
        result = format_inspect_cos(obj)
        assert "INSPECT: wall_n[mesh]@(100,0,500)" in result
        assert "MAT: mat_dark" in result
        assert "24v 6f" in result

    def test_with_neighbors(self):
        """Neighbors shown with distances."""
        obj = {"name": "obj_a", "type": "mesh", "position": [0, 0, 0]}
        neighbors = [
            {"name": "obj_b", "distance": 150.5},
            {"name": "obj_c", "distance": 300.0},
        ]
        result = format_inspect_cos(obj, neighbors=neighbors)
        assert "NEIGHBORS[2]" in result
        assert "obj_b @ 150.5" in result

    def test_with_children(self):
        """Children listed."""
        obj = {
            "name": "group1",
            "type": "group",
            "position": [0, 0, 0],
            "children": ["child_a", "child_b", "child_c"],
        }
        result = format_inspect_cos(obj)
        assert "CHILDREN[3]" in result
        assert "child_a" in result


class TestFormatMeasureCos:
    """Test measure CoS formatting."""

    def test_center_distance(self):
        """Center distance formatted correctly."""
        result_data = {"obj_a": "wall", "obj_b": "shelf", "mode": "center", "distance": 500.123}
        result = format_measure_cos(result_data)
        assert "MEASURE[center]: wall ↔ shelf = 500.123" in result

    def test_overlap_flag(self):
        """Overlap shown when bbox_overlap is True."""
        result_data = {
            "obj_a": "a",
            "obj_b": "b",
            "mode": "bbox",
            "distance": 0,
            "bbox_overlap": True,
        }
        result = format_measure_cos(result_data)
        assert "[OVERLAP]" in result

    def test_clearance_mode(self):
        """Clearance mode shown."""
        result_data = {"obj_a": "wall", "obj_b": "counter", "mode": "clearance", "distance": 45.0}
        result = format_measure_cos(result_data)
        assert "MEASURE[clearance]" in result


class TestFormatAssertCos:
    """Test assert CoS formatting."""

    def test_pass(self):
        """Passing assertion."""
        result_data = {"passed": True, "checked_count": 4, "mismatches": []}
        result = format_assert_cos(result_data)
        assert "ASSERT[PASS]: 4 checks" in result

    def test_fail_with_mismatches(self):
        """Failing assertion shows mismatches."""
        result_data = {
            "passed": False,
            "checked_count": 2,
            "mismatches": [
                {
                    "object": "wall",
                    "property": "position",
                    "expected": [0, 0, 0],
                    "actual": [10, 0, 0],
                },
            ],
        }
        result = format_assert_cos(result_data)
        assert "ASSERT[FAIL]" in result
        assert "MISMATCH: wall.position" in result

    def test_many_mismatches_truncated(self):
        """Only first 5 mismatches shown."""
        mismatches = [
            {"object": f"obj_{i}", "property": "pos", "expected": 0, "actual": i} for i in range(10)
        ]
        result_data = {"passed": False, "checked_count": 10, "mismatches": mismatches}
        result = format_assert_cos(result_data)
        assert "+5 more mismatches" in result


class TestFormatZoneMapCos:
    """Test zone map CoS formatting."""

    def test_basic_zones(self):
        """Zone map formatted correctly."""
        zones = [
            {
                "name": "entrance",
                "object_count": 5,
                "center": [0, 0, 100],
                "pattern_matched": "entrance",
                "objects": ["door", "gate"],
            },
            {
                "name": "display",
                "object_count": 10,
                "center": [200, 0, 300],
                "pattern_matched": "display",
                "objects": ["shelf_1", "shelf_2"],
            },
        ]
        result = format_zone_map_cos(zones)
        assert "ZONES[2]" in result
        assert "entrance: 5obj" in result
        assert "display: 10obj" in result
