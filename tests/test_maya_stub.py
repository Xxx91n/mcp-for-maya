"""Self-tests for tests/maya_stub — the harness must be right
before product tests can be trusted (D-004/ADR-0002 stub tier)."""

from __future__ import annotations

import math

import maya_stub
import pytest
from maya_stub.math3d import MBoundingBox, MPoint, euler_from_matrix, trs_matrix


@pytest.fixture
def scene():
    sc = maya_stub.install()
    yield sc
    maya_stub.uninstall()


class TestMatrixMath:
    def test_translation(self):
        m = trs_matrix(t=(5, 2, -3))
        p = MPoint(1, 1, 1) * m
        assert (p.x, p.y, p.z) == (6, 3, -2)

    def test_rotate_y_90(self):
        # row-vector: +90 deg about Y maps +X -> -Z
        m = trs_matrix(r=(0, 90, 0))
        p = MPoint(1, 0, 0) * m
        assert p.x == pytest.approx(0, abs=1e-9)
        assert p.z == pytest.approx(-1, abs=1e-9)

    def test_scale_then_translate(self):
        m = trs_matrix(t=(10, 0, 0), s=(2, 2, 2))
        p = MPoint(1, 0, 0) * m
        assert p.x == pytest.approx(12)

    def test_euler_roundtrip_compound(self):
        m = trs_matrix(r=(30, -45, 60))
        rx, ry, rz = euler_from_matrix(m)
        assert rx == pytest.approx(30, abs=1e-6)
        assert ry == pytest.approx(-45, abs=1e-6)
        assert rz == pytest.approx(60, abs=1e-6)

    def test_matrix_mul_is_composable(self):
        a = trs_matrix(t=(1, 0, 0))
        b = trs_matrix(t=(0, 5, 0))
        p = MPoint(0, 0, 0) * (a * b)
        assert (p.x, p.y, p.z) == (1, 5, 0)


class TestSceneGraph:
    def test_hierarchy_world_position(self, scene):
        g = scene.add_transform("GRP_a", t=(10, 0, 0))
        m = scene.add_mesh("GEO_box", t=(0, 0, 5), parent=g)
        assert scene.world_position(m) == (10, 0, 5)

    def test_long_name_and_resolve(self, scene):
        g = scene.add_transform("GRP_a")
        m = scene.add_mesh("GEO_box", parent=g)
        assert scene.long_name(m) == "|GRP_a|GEO_box"
        assert scene.resolve("|GRP_a|GEO_box") is m
        assert scene.resolve("GEO_box") is m

    def test_resolve_missing_raises(self, scene):
        with pytest.raises(RuntimeError):
            scene.resolve("nope")

    def test_duplicate_names_auto_uniquified(self, scene):
        # Maya-style: creating a second node with the same name gets numbered
        scene.add_mesh("GEO_same")
        scene.add_mesh("GEO_same")
        assert scene.resolve("GEO_same1") is not None

    def test_ambiguous_short_name_raises(self, scene):
        # Same short name under different parents is legal in Maya
        g1 = scene.add_transform("GRP_a")
        g2 = scene.add_transform("GRP_b")
        scene.add_node("dup", "transform", parent=g1, exists_ok=True)
        scene.add_node("dup", "transform", parent=g2, exists_ok=True)
        with pytest.raises(RuntimeError):
            scene.resolve("dup")
        # long names disambiguate
        assert scene.resolve("|GRP_a|dup").parent is g1

    def test_world_bbox_rotated_8_corners(self, scene):
        # 2x1x1 box rotated 45 deg about Y: world XZ extent = 3*sqrt(2)/2
        box = scene.add_mesh(
            "GEO_rot", bbox_min=(-1, -0.5, -0.5), bbox_max=(1, 0.5, 0.5), r=(0, 45, 0)
        )
        wb = scene.object_bbox(box)  # local space bbox
        wm = scene.inclusive_matrix(box)
        out = MBoundingBox()
        for c in wb.corners():
            out.expand(c * wm)
        ext = 3 * math.sqrt(2) / 2  # (|x|+|z|) extents of a 2x1 box at 45deg
        assert (out.max.x - out.min.x) == pytest.approx(ext, abs=1e-9)
        assert (out.max.z - out.min.z) == pytest.approx(ext, abs=1e-9)
        assert (out.max.y - out.min.y) == pytest.approx(1.0)

    def test_naive_minmax_transform_is_wrong(self, scene):
        # Corner-at-origin box rotated 45 deg: min*M/max*M shortcut gives a
        # DIFFERENT (wrong) world AABB than the 8-corner transform.
        box = scene.add_mesh("GEO_off", bbox_min=(0, 0, 0), bbox_max=(2, 1, 1), r=(0, 45, 0))
        wb = scene.object_bbox(box)
        wm = scene.inclusive_matrix(box)
        out = MBoundingBox()
        for c in wb.corners():
            out.expand(c * wm)
        naive_min = wb.min * wm
        naive_max = wb.max * wm
        # 8-corner truth: x in [0, 3*sqrt(2)/2], z in [-sqrt(2), sqrt(2)/2]
        assert out.min.x == pytest.approx(0.0, abs=1e-9)
        assert out.max.x == pytest.approx(3 * math.sqrt(2) / 2, abs=1e-9)
        assert out.min.z == pytest.approx(-math.sqrt(2), abs=1e-9)
        assert out.max.z == pytest.approx(math.sqrt(2) / 2, abs=1e-9)
        # naive min*M/max*M reports z=[0, -0.707] — both bounds wrong
        assert not math.isclose(naive_min.z, out.min.z, abs_tol=1e-6)
        assert not math.isclose(naive_max.z, out.max.z, abs_tol=1e-6)


class TestCmdsFacade:
    def test_ls_type_long(self, scene):
        import sys

        cmds = sys.modules["maya.cmds"]
        scene.add_mesh("GEO_a")
        trs = cmds.ls(type="transform", long=True)
        assert "|GEO_a" in trs
        meshes = cmds.ls(type="mesh")
        assert "GEO_aShape" in meshes

    def test_ls_empty_returns_none(self, scene):
        cmds = __import__("maya.cmds", fromlist=["x"])
        assert cmds.ls(type="transform") is None

    def test_ls_glob_patterns(self, scene):
        """Real-Maya glob semantics (verified live on 2024): string
        patterns filter by name, and * never crosses the namespace ':'."""
        cmds = __import__("maya.cmds", fromlist=["x"])
        scene.add_mesh("GEO_box")
        scene.add_mesh("v7ref:GEO_ref_cube")
        scene.add_mesh("LGT_key")
        assert set(cmds.ls("GEO_*") or []) == {"GEO_box", "GEO_boxShape"}
        assert cmds.ls("*GEO_ref_cube*") is None  # * does not cross ':'
        assert set(cmds.ls("*:*GEO_ref_cube*") or []) == {
            "v7ref:GEO_ref_cube",
            "v7ref:GEO_ref_cubeShape",
        }
        assert set(cmds.ls("v7ref:*") or []) == {
            "v7ref:GEO_ref_cube",
            "v7ref:GEO_ref_cubeShape",
        }
        assert set(cmds.ls("GEO_*", "LGT_*") or []) == {
            "GEO_box",
            "GEO_boxShape",
            "LGT_key",
            "LGT_keyShape",
        }

    def test_getattr_tuple(self, scene):
        cmds = __import__("maya.cmds", fromlist=["x"])
        scene.add_light("LGT_key", ltype="spotLight")
        assert cmds.getAttr("LGT_keyShape.intensity") == 1.0
        assert cmds.getAttr("LGT_keyShape.color") == [(1.0, 1.0, 1.0)]
        assert cmds.objExists("LGT_keyShape.coneAngle")
        assert not cmds.objExists("LGT_keyShape.bogusAttr")

    def test_camera_and_aim(self, scene):
        cmds = __import__("maya.cmds", fromlist=["x"])
        target = scene.add_mesh("GEO_t", t=(100, 0, 0))
        cam_t, cam_s = cmds.camera(name="CAM_x")
        cmds.move(0, 0, 0, cam_t)
        cmds.aimConstraint(target.name, cam_t, aimVector=[0, 0, -1])
        node = scene.resolve(cam_t)
        # camera looks down -Z; aiming at +X target => ry = -90
        assert node.r[1] == pytest.approx(-90, abs=1e-6)
        assert scene.constraints[-1]["target"] == "GEO_t"

    def test_xform_world_space(self, scene):
        cmds = __import__("maya.cmds", fromlist=["x"])
        g = scene.add_transform("GRP_p", t=(5, 0, 0))
        scene.add_mesh("GEO_c", t=(0, 0, 7), parent=g)
        assert cmds.xform("GEO_c", q=True, ws=True, t=True) == [5, 0, 7]

    def test_rename_uniquifies(self, scene):
        cmds = __import__("maya.cmds", fromlist=["x"])
        scene.add_mesh("GEO_a")
        scene.add_mesh("GEO_b")
        out = cmds.rename("GEO_b", "GEO_a")
        assert out == "GEO_a1"


class TestGuiSurface:
    """D-039: stub GUI surface fidelity - modelPanel camera API and a
    type-disambiguated lookThru with warn/strict anomaly policy."""

    def test_model_panel_camera_roundtrip(self, scene):
        cmds = __import__("maya.cmds", fromlist=["x"])
        scene.setup_gui()
        assert cmds.modelPanel("modelPanel1", q=True, camera=True) == "persp"
        cmds.modelPanel("modelPanel1", e=True, camera="top")
        assert cmds.modelPanel("modelPanel1", q=True, camera=True) == "top"
        assert ("modelPanel1", "top") in scene.model_panel_calls

    def test_model_panel_exists_and_bad_panel(self, scene):
        cmds = __import__("maya.cmds", fromlist=["x"])
        scene.setup_gui()
        assert cmds.modelPanel("modelPanel1", ex=True) is True
        assert cmds.modelPanel("nope", ex=True) is False
        with pytest.raises(RuntimeError):
            cmds.modelPanel("nope", q=True, camera=True)

    def test_model_editor_camera_edit_resolves(self, scene):
        cmds = __import__("maya.cmds", fromlist=["x"])
        scene.setup_gui()
        cmds.modelEditor("modelPanel1", e=True, camera="top")
        assert scene.panels["modelPanel1"]["camera"] == "top"
        with pytest.raises(RuntimeError):
            cmds.modelEditor("modelPanel1", e=True, camera="not_a_node")

    def test_look_thru_type_disambiguation_both_orders(self, scene):
        """Both positional orders work - classified by arg type, like
        the real command (official examples show both)."""
        cmds = __import__("maya.cmds", fromlist=["x"])
        scene.setup_gui()
        cmds.lookThru("top", "modelPanel1")  # object-first
        assert scene.panels["modelPanel1"]["camera"] == "top"
        cmds.lookThru("modelPanel2", "front")  # editor-first
        assert scene.panels["modelPanel2"]["camera"] == "front"
        assert scene.look_thru_calls[-2:] == [
            ("modelPanel1", "top"),
            ("modelPanel2", "front"),
        ]

    def test_look_thru_unclassifiable_warns_in_default_mode(self, scene):
        cmds = __import__("maya.cmds", fromlist=["x"])
        scene.setup_gui()
        cmds.lookThru("modelPanel1", "not_a_camera")
        assert scene.stub_notes, "anomaly must be recorded"
        assert scene.panels["modelPanel1"]["camera"] == "persp"  # unchanged

    def test_look_thru_unclassifiable_raises_in_strict_mode(self, scene):
        cmds = __import__("maya.cmds", fromlist=["x"])
        scene.setup_gui()
        scene.stub_strict = True
        with pytest.raises(RuntimeError):
            cmds.lookThru("modelPanel1", "not_a_camera")
