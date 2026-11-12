"""Issue #176 Maya-side tests: zone geometry from the assembled _mcp_scene unit.

These run on the Maya fake. They check the data the later recommendation pass
will read: zone boxes, object sizes, empty/unusable zones, and the unchanged
default scene_plan answer.
"""

from __future__ import annotations

import json
import math

import pytest


class TestZoneGeometry:
    def test_empty_scene(self, maya_env):
        res = maya_env.module.get_zone_geometry()

        assert res == {
            "unit": "cm",
            "up_axis": "y",
            "zones": [],
            "unassigned_count": 0,
            "total_objects": 0,
        }
        json.dumps(res, allow_nan=False)

    def test_multiple_zones_match_the_existing_zone_map(self, maya_env):
        maya_env.scene.add_mesh("GEO_wall_a", bbox_min=(0, 0, 0), bbox_max=(10, 20, 2), t=(0, 0, 0))
        maya_env.scene.add_mesh("GEO_shelf_a", bbox_min=(0, 0, 0), bbox_max=(4, 2, 1), t=(30, 0, 0))
        maya_env.scene.add_mesh(
            "GEO_door_a", bbox_min=(-1, 0, 0), bbox_max=(1, 3, 0.5), t=(0, 0, 10)
        )
        maya_env.scene.add_mesh("GEO_random", t=(100, 0, 0))

        res = maya_env.module.get_zone_geometry()
        zone_map = maya_env.module.get_zone_map()
        zones = {z["name"]: z for z in res["zones"]}

        assert set(zones) == {z["name"] for z in zone_map["zones"]}
        assert res["total_objects"] == 4
        assert res["unassigned_count"] == 1
        for old in zone_map["zones"]:
            new = zones[old["name"]]
            assert new["bbox_min"] == old["bbox_min"]
            assert new["bbox_max"] == old["bbox_max"]
            assert new["size"] == [
                round(hi - lo, 3) for lo, hi in zip(old["bbox_min"], old["bbox_max"])
            ]
            assert new["object_count"] == old["object_count"]
            assert new["unmeasured_count"] == 0

        shelf = zones["display"]
        assert shelf["bbox_min"] == [30, 0, 0]
        assert shelf["bbox_max"] == [34, 2, 1]
        assert shelf["size"] == [4, 2, 1]
        assert shelf["objects"] == [{"name": "|GEO_shelf_a", "size": [4, 2, 1]}]
        json.dumps(res, allow_nan=False)

    def test_zone_with_no_usable_bbox_reports_null_not_zero(self, maya_env):
        maya_env.scene.add_group("GRP_shelf_empty")

        res = maya_env.module.get_zone_geometry()
        zone = res["zones"][0]

        assert zone["name"] == "display"
        assert zone["bbox_min"] is None
        assert zone["bbox_max"] is None
        assert zone["size"] is None
        assert zone["object_count"] == 1
        assert zone["unmeasured_count"] == 1
        assert zone["objects"] == [{"name": "|GRP_shelf_empty", "size": None}]
        json.dumps(res, allow_nan=False)

    def test_one_unreadable_object_does_not_hide_the_rest(self, maya_env, monkeypatch):
        maya_env.scene.add_mesh(
            "GEO_shelf_good", bbox_min=(0, 0, 0), bbox_max=(4, 2, 1), t=(0, 0, 0)
        )
        maya_env.scene.add_mesh("GEO_shelf_bad", t=(10, 0, 0))
        real_world_bbox = maya_env.module._world_bbox

        def picky_bbox(dag):
            if maya_env.om2.MFnDagNode(dag).name() == "GEO_shelf_bad":
                raise RuntimeError("bbox unreadable")
            return real_world_bbox(dag)

        monkeypatch.setattr(maya_env.module, "_world_bbox", picky_bbox)
        zone = maya_env.module.get_zone_geometry()["zones"][0]

        assert zone["name"] == "display"
        assert zone["bbox_min"] == [0, 0, 0]
        assert zone["bbox_max"] == [4, 2, 1]
        assert zone["object_count"] == 2
        assert zone["unmeasured_count"] == 1
        by_name = {obj["name"]: obj["size"] for obj in zone["objects"]}
        assert by_name["|GEO_shelf_good"] == [4, 2, 1]
        assert by_name["|GEO_shelf_bad"] is None

    def test_non_finite_bbox_is_not_serialized(self, maya_env, monkeypatch):
        maya_env.scene.add_mesh("GEO_shelf_a")

        def nan_bbox(dag):
            return maya_env.om2.MBoundingBox((float("nan"), 0, 0), (float("nan"), 1, 1))

        monkeypatch.setattr(maya_env.module, "_world_bbox", nan_bbox)
        res = maya_env.module.get_zone_geometry()
        zone = res["zones"][0]

        assert zone["bbox_min"] is None
        assert zone["bbox_max"] is None
        assert zone["size"] is None
        assert zone["objects"][0]["size"] is None
        json.dumps(res, allow_nan=False)

    def test_world_size_follows_parent_rotation(self, maya_env):
        parent = maya_env.scene.add_transform("GRP_root", t=(10, 0, 0))
        parent.r = [0, 45, 0]
        maya_env.scene.add_mesh(
            "GEO_shelf_rot",
            bbox_min=(0, 0, 0),
            bbox_max=(2, 1, 1),
            parent=parent,
        )

        zone = maya_env.module.get_zone_geometry()["zones"][0]
        side = math.sqrt(2) + math.sqrt(2) / 2

        assert zone["name"] == "display"
        assert zone["size"] == pytest.approx([side, 1, side], abs=1e-3)
        assert zone["objects"][0]["name"] == "|GRP_root|GEO_shelf_rot"
        assert zone["objects"][0]["size"] == pytest.approx([side, 1, side], abs=1e-3)

    def test_duplicate_short_names_keep_their_own_full_paths(self, maya_env):
        left = maya_env.scene.add_group("GRP_left")
        right = maya_env.scene.add_transform("GRP_right", t=(50, 0, 0))
        # Maya allows the same leaf name under two parents; the fake's convenience
        # builder would auto-rename it, so create the duplicate transforms directly.
        left_shelf = maya_env.scene.add_node("GEO_shelf", "transform", parent=left, exists_ok=True)
        right_shelf = maya_env.scene.add_node(
            "GEO_shelf", "transform", parent=right, exists_ok=True
        )
        maya_env.scene.add_shape(
            "GEO_shelfShape_left", "mesh", left_shelf, bbox=((0, 0, 0), (2, 1, 1))
        )
        maya_env.scene.add_shape(
            "GEO_shelfShape_right", "mesh", right_shelf, bbox=((0, 0, 0), (6, 1, 1))
        )

        zone = maya_env.module.get_zone_geometry()["zones"][0]
        by_name = {obj["name"]: obj["size"] for obj in zone["objects"]}

        assert zone["object_count"] == 2
        assert by_name == {
            "|GRP_left|GEO_shelf": [2, 1, 1],
            "|GRP_right|GEO_shelf": [6, 1, 1],
        }

    def test_unit_and_up_axis_come_from_the_scene(self, maya_env):
        maya_env.scene.linear_unit = "m"
        maya_env.scene.up_axis = "z"

        res = maya_env.module.get_zone_geometry()

        assert res["unit"] == "m"
        assert res["up_axis"] == "z"

    def test_query_failure_uses_the_domain_error_shape(self, maya_env, monkeypatch):
        def boom(*args, **kwargs):
            raise RuntimeError("scene list failed")

        monkeypatch.setattr(maya_env.cmds, "ls", boom)
        res = maya_env.module.get_zone_geometry()

        assert res["error"]["code"] == "query_failed"
        assert "scene list failed" in res["error"]["message"]

    def test_reading_geometry_does_not_change_default_scene_plan_bytes(self, maya_env):
        maya_env.scene.add_mesh("GEO_shelf_a", t=(10, 0, 0))
        maya_env.scene.add_mesh("GEO_door_a", t=(0, 0, 10))
        before = json.dumps(maya_env.module.scene_plan(), indent=2).encode("utf-8")

        maya_env.module.get_zone_geometry()
        after = json.dumps(maya_env.module.scene_plan(), indent=2).encode("utf-8")

        assert after == before
        assert "zone_geometry" not in json.loads(after)


class TestFragmentAssembly:
    async def test_shipped_payload_matches_the_stub_assembly(self, maya_env):
        from unittest.mock import AsyncMock, MagicMock

        from maya_mcp_server import scene_tools

        client = MagicMock()
        client.framed_channel = True
        client.write_module = AsyncMock()
        client.execute_code = AsyncMock()
        key = "zone-geometry-parity"
        scene_tools._injected_sessions.discard(key)
        try:
            await scene_tools._ensure_module_injected(client, key)
        finally:
            scene_tools._injected_sessions.discard(key)

        client.write_module.assert_awaited_once()
        name, shipped = client.write_module.await_args.args
        assert name == "_mcp_scene"
        assert shipped == maya_env.module.__mcp_payload__
        expected = "\n\n".join(
            path.read_text(encoding="utf-8")
            for path in (
                scene_tools._MODULE_SOURCE,
                scene_tools._INTROSPECT_FRAGMENT,
                scene_tools._VALIDATOR_FRAGMENT,
                scene_tools._ZONE_GEOMETRY_FRAGMENT,
            )
        )
        assert shipped == expected
        assert shipped.index("def get_scene_graph") < shipped.index("def describe_node")
        assert shipped.index("def describe_node") < shipped.index("def register_validator")
        assert shipped.index("def register_validator") < shipped.index("def get_zone_geometry")
