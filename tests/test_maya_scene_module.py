"""Regression tests for maya_scene_module running on the Maya fake.

Most tests pin a P0/P1 fix from the grill handoff (rui.txt); the scene-review
standards test (#255) pins the branches that the production thresholds drive.
The fake's matrix/bbox math is verified independently in test_maya_stub.py, so
failures here mean the production module is wrong — not the harness.
"""

from __future__ import annotations

import json
import math

import pytest


# ------------------------------------------------------------
# P0-4: world bbox must use all 8 corners (measure + conflicts)
# ------------------------------------------------------------


class TestWorldBbox:
    def test_measure_bbox_mode_rotated_object(self, maya_env):
        # Corner-at-origin 2x1x1 box rotated 45 deg about Y.
        # True world extents: x in [0, 2.121], z in [-1.414, 0.707].
        maya_env.scene.add_mesh("GEO_rot", bbox_min=(0, 0, 0), bbox_max=(2, 1, 1), r=(0, 45, 0))
        # Wall slab separated on +Z: z in [0.8, 1.0], x overlaps, y overlaps
        maya_env.scene.add_mesh(
            "GEO_wall",
            bbox_min=(0, 0, 0),
            bbox_max=(2, 1, 0.2),
            t=(0, 0, 0.8),
        )
        m = maya_env.module.measure("GEO_rot", "GEO_wall", "bbox")
        gaps = m["details"]["gaps_xyz"]
        # True z gap = 0.8 - 0.707 = ~0.093; naive min*M gives gap 0.8
        assert gaps[2] == pytest.approx(0.8 - math.sqrt(2) / 2, abs=1e-2)
        assert m["bbox_overlap"] is False

    def test_measure_clearance_zero_does_not_mean_merely_touching(self, maya_env):
        """A 0 clearance is NOT proof the boxes only touch.

        Per-axis gap is +separated / 0=touching / -penetrating. Here X and Z
        penetrate by 0.5 while Y is exactly touching, so the implementation
        takes the "at least one axis >= 0" branch and computes the euclidean
        distance over the POSITIVE parts only -- which is zero. Reading 0 as
        "the boxes just touch" would miss a real 0.5cm interpenetration.

        This is the counterexample that pinned the scene_measure docstring
        rewrite: the old wording claimed "0 means the boxes touch on every
        axis", which this configuration contradicts.
        """
        maya_env.scene.add_mesh("GEO_a", bbox_min=(-10, -10, -10), bbox_max=(-9, -9, -9))
        maya_env.scene.add_mesh("GEO_b", bbox_min=(-9.5, -9, -9.5), bbox_max=(-8.5, -8, -8.5))
        m = maya_env.module.measure("GEO_a", "GEO_b", "clearance")

        gaps = m["details"]["clearances_xyz"]
        assert gaps[0] == pytest.approx(-0.5, abs=1e-6), "X must read as penetrating"
        assert gaps[1] == pytest.approx(0.0, abs=1e-6), "Y must read as exactly touching"
        assert gaps[2] == pytest.approx(-0.5, abs=1e-6), "Z must read as penetrating"

        assert m["distance"] == pytest.approx(0.0, abs=1e-6), (
            "distance collapses to 0 even though two axes interpenetrate"
        )
        assert m["bbox_overlap"] is False, (
            "bbox_overlap is all-three-penetrating only, so 2-of-3 reads false"
        )

    def test_measure_clearance_negative_is_shallowest_penetration(self, maya_env):
        """All three axes penetrate -> distance is the shallowest one, i.e.
        the minimum translation that separates the boxes."""
        maya_env.scene.add_mesh("GEO_a", bbox_min=(-10, -10, -10), bbox_max=(-9, -9, -9))
        # X and Y shift by 0.5 (gap -0.5 each); Z is coincident (gap -1.0).
        maya_env.scene.add_mesh("GEO_b", bbox_min=(-9.5, -9.5, -10.0), bbox_max=(-8.5, -8.5, -9.0))
        m = maya_env.module.measure("GEO_a", "GEO_b", "clearance")
        assert m["details"]["clearances_xyz"] == pytest.approx([-0.5, -0.5, -1.0], abs=1e-6)
        assert m["distance"] == pytest.approx(-0.5, abs=1e-6), (
            "the SHALLOWEST penetration (-0.5) is reported, not the deepest (-1.0)"
        )
        assert m["bbox_overlap"] is True

    def test_measure_clearance_positive_ignores_penetrating_axes(self, maya_env):
        """A separated axis dominates: Y is clear by 2.5 while X and Z
        penetrate, so the distance is 3.0 and the penetration is invisible."""
        maya_env.scene.add_mesh("GEO_a", bbox_min=(-10, -10, -10), bbox_max=(-9, -9, -9))
        maya_env.scene.add_mesh("GEO_b", bbox_min=(-9.5, -6.5, -9.5), bbox_max=(-8.5, -5.5, -8.5))
        m = maya_env.module.measure("GEO_a", "GEO_b", "clearance")
        # Y separation = B.y_min - A.y_max = -6.5 - (-9) = 2.5
        assert m["distance"] == pytest.approx(2.5, abs=1e-6), (
            "only the separated axis contributes; X and Z penetration is invisible"
        )
        assert m["details"]["clearances_xyz"][0] == pytest.approx(-0.5, abs=1e-6)

    # ------------------------------------------------------------------
    # The scene_measure docstring states four rules about clearance. Those
    # rules used to be prose nobody checked, which is how a false one shipped
    # (F1: "0 means the boxes touch on every axis"). They are now asserted
    # against the real implementation across the whole enumerated domain, so a
    # future edit to either side fails loudly instead of drifting.
    #
    # Domain is stated explicitly and is deliberately NOT a claim about the
    # implementation: it is the enumeration set. Any count quoted without the
    # domain is meaningless, which is exactly how the original error read.
    # ------------------------------------------------------------------

    CLEARANCE_DOMAIN = (-2, -1, 0, 1, 1.5)  # penetrating / touching / separated

    @staticmethod
    def _clearance_for(maya_env, gaps, size=4.0, tag=""):
        """Drive measure() to a chosen per-axis gap triple.

        Two axis-aligned cubes of side `size`; shifting B by t on an axis
        yields gap = |t| - size, so t = gap + size realises any gap >= -size.
        Node names must be unique per call -- the fake keys transforms by name,
        so reusing them inside one scene silently keeps the first geometry.
        """
        a, b = f"GEO_a{tag}", f"GEO_b{tag}"
        maya_env.scene.add_mesh(a, bbox_min=(0, 0, 0), bbox_max=(size, size, size))
        off = tuple(g + size for g in gaps)
        maya_env.scene.add_mesh(b, bbox_min=off, bbox_max=tuple(v + size for v in off))
        return maya_env.module.measure(a, b, "clearance")

    def test_clearance_rules_hold_across_the_whole_domain(self, maya_env):
        """The docstring's three distance branches, asserted exhaustively."""
        import itertools

        dom = self.CLEARANCE_DOMAIN
        seen_zero = seen_pos = seen_neg = 0
        for n, gaps in enumerate(itertools.product(dom, repeat=3)):
            m = self._clearance_for(maya_env, gaps, tag=str(n))
            d = m["distance"]
            ov = m["bbox_overlap"]
            read = m["details"]["clearances_xyz"]

            # the per-axis read-back must equal what we asked for
            for want, got in zip(gaps, read):
                assert got == pytest.approx(want, abs=1e-6), (gaps, read)

            any_sep = any(g > 0 for g in gaps)
            any_touch = any(g == 0 for g in gaps)
            all_pen = all(g < 0 for g in gaps)

            # branch 1: >0 exactly when some axis is strictly separated
            if any_sep:
                seen_pos += 1
                assert d > 0, f"{gaps}: separated axis must give a positive distance"
                # only the separating axes contribute. measure() rounds the
                # result with _round3, so the tolerance must admit that
                # rounding rather than pretend the value is unrounded.
                want = math.sqrt(sum(g * g for g in gaps if g > 0))
                assert d == pytest.approx(want, abs=1e-3), gaps
            else:
                # branch 2: 0 exactly when touching and not separated
                if any_touch:
                    seen_zero += 1
                    assert d == pytest.approx(0.0, abs=1e-6), (
                        f"{gaps}: touching-but-not-separated must read 0, got {d}"
                    )
                else:
                    # branch 3: negative exactly when all three penetrate
                    seen_neg += 1
                    assert d < 0, f"{gaps}: all-penetrating must give a negative distance"
                    assert d == pytest.approx(max(gaps), abs=1e-3), (
                        f"{gaps}: must report the SHALLOWEST penetration"
                    )

            # bbox_overlap rule: true iff all three strictly penetrate
            assert ov is all_pen, f"{gaps}: bbox_overlap must be {all_pen}, got {ov}"

        # the enumeration must actually reach every branch, or it proves little
        assert seen_pos and seen_zero and seen_neg, (seen_pos, seen_zero, seen_neg)

    def test_bbox_overlap_is_false_for_a_single_penetrating_axis(self, maya_env):
        """The specific trap the old docstring understated: ONE penetrating
        axis already reads bbox_overlap False."""
        m = self._clearance_for(maya_env, (-1, 0, 2))
        assert m["bbox_overlap"] is False
        assert m["details"]["clearances_xyz"][0] == pytest.approx(-1, abs=1e-6)

    def test_clearance_docstring_does_not_assert_the_retired_false_claim(self):
        """Targeted guard against the exact hallucination that shipped (F1)."""
        import ast
        import inspect
        import textwrap

        from maya_mcp_server import scene_tools

        doc = ast.get_docstring(
            next(
                node
                for node in ast.walk(ast.parse(inspect.getsource(scene_tools)))
                if isinstance(node, ast.AsyncFunctionDef) and node.name == "scene_measure"
            )
        )
        assert doc is not None
        flat = " ".join(doc.split())
        assert "touch on every axis" not in flat, (
            "the retired false claim is back: distance 0 does not mean every "
            "axis is exactly touching"
        )
        # the corrected rule must be stated, in both branches
        assert "if and only if all three axes" in flat
        assert "does NOT mean the boxes just touch" in flat
        assert textwrap  # keep the import honest

    def test_measure_center_mode(self, maya_env):
        maya_env.scene.add_mesh("GEO_a", t=(10, 0, 0))
        maya_env.scene.add_mesh("GEO_b", t=(0, 0, 30))
        m = maya_env.module.measure("GEO_a", "GEO_b", "center")
        assert m["distance"] == pytest.approx(math.sqrt(100 + 900), abs=1e-3)

    def test_conflicts_uses_world_bbox(self, maya_env):
        # Rotated box: true world z range [-1.414, 0.707].
        maya_env.scene.add_mesh("GEO_rot", bbox_min=(0, 0, 0), bbox_max=(2, 1, 1), r=(0, 45, 0))
        # Wall whose CENTER (z=-1.25) is inside the rotated box's true bbox
        # but OUTSIDE the naive translate-only bbox (z in [0, 1]).
        maya_env.scene.add_mesh(
            "GEO_wall",
            bbox_min=(-1, -0.5, -0.1),
            bbox_max=(1, 0.5, 0.1),
            t=(1, 0.5, -1.25),
        )
        res = maya_env.module.scene_review(["conflicts"])
        conflicts = res["checks"]["conflicts"]
        assert conflicts["count"] >= 1, "rotated-object penetration must be detected via world bbox"


# ------------------------------------------------------------
# #255: scene_review branches that read _MAYA_STANDARDS
# ------------------------------------------------------------


class TestSceneReviewStandards:
    """The shipped thresholds drive real branches, not only comparisons.

    #255 gave _MAYA_STANDARDS a declared shape, which is a type-only change.
    This test pins the branches those values feed: a reworded message, or a
    value change that flips one of them, shows up here as well as in the mypy
    run. The >2000 "Excessive objects" branch has no test in this batch.
    """

    def test_thresholds_drive_the_review_branches(self, maya_env):
        scene = maya_env.scene
        # Deeper than max_nesting_depth (4) plus its +2 tolerance.
        group = scene.add_group("GRP_root")
        for level in range(6):
            group = scene.add_group(f"GRP_level_{level}", parent=group)
        scene.add_mesh("GEO_deep", parent=group)
        # Default-prefixed names: the forbidden_prefixes list.
        for i in range(12):
            scene.add_mesh(f"pCube{i + 1}", t=(i * 50, 0, 0))
        # Past max_cameras_keep (10).
        for i in range(12):
            scene.add_camera(f"CAM_shot_{i}", t=(0, 0, i * 10))
        # Below min_lights (3).
        scene.add_light("LGT_key", t=(0, 100, 0))
        scene.add_light("LGT_fill", t=(100, 100, 0))
        # Past max_objects_soft (500) but under max_objects_hard (2000).
        for i in range(500):
            scene.add_mesh(f"GEO_fill_{i}", t=(i * 3, 0, 40))

        messages = {issue["msg"] for issue in maya_env.module.scene_review()["issues"]}

        transforms = maya_env.cmds.ls(type="transform", long=True) or []
        assert len(transforms) > 500, "the soft object-count branch needs a scene past it"
        assert f"High object count ({len(transforms)}). Consider instancing." in messages
        assert "Excess cameras (12). Clean test shots." in messages
        assert "Only 2 lights. Need 3+." in messages
        assert "12 objects with default names." in messages
        assert "Nesting depth 8 exceeds 4." in messages
        assert "Scene hierarchy too deep (8 levels). Flatten to 4 max." in messages


# ------------------------------------------------------------
# #276: the review lighting check reads the shared light payload
# ------------------------------------------------------------


class TestSceneReviewLightingPayload:
    """Pin the review path's lighting result on the shared 13-field payload.

    The review check had no score assertion before #276; only its "no lights"
    and "too few lights" branches were tested. These numbers were measured on
    this fixture after the builder moved. The total gets a small tolerance
    because its weighted sum sits on a rounding boundary; the sub-scores are
    exact.
    """

    def test_review_lighting_score_and_subscores(self, maya_env):
        maya_env.scene.add_light("LGT_key", t=(0, 100, 0))
        maya_env.scene.add_light("LGT_fill", t=(100, 100, 0))

        lighting = maya_env.module.scene_review(["lighting"])["checks"]["lighting"]

        assert lighting["score"] == pytest.approx(67.8, abs=0.1)
        assert lighting["sub_scores"] == {
            "layers": 75,
            "three_point": 70,
            "fill_ratio": 70,
            "shadow_quality": 70,
            "temperature": 90,
            "coverage": 65,
            "decay": 30.0,
            "intensity_dist": 65,
        }
        assert lighting["layer_breakdown"] == {
            "key": 1,
            "fill": 1,
            "rim": 0,
            "accent": 0,
            "other": 0,
        }
        assert lighting["mood"] == "cool_dramatic"
        assert lighting["fill_ratio"] == 1.0
        assert lighting["temp_consistency"] == "very_consistent"


# ------------------------------------------------------------
# #266: the eight-corner transform must match cmds.exactWorldBoundingBox
# ------------------------------------------------------------


def _dag_path(maya_env, name):
    sel = maya_env.om2.MSelectionList()
    sel.add(name)
    return sel.getDagPath(0)


class TestWorldBboxMatchesExactBox:
    """MFnDagNode.boundingBox is PARENT space on a transform (it already
    carries the node's own translate/rotate) and OBJECT space on a shape.
    Feeding the inclusive matrix to a transform path lands that transform
    twice. The hardcoded numbers are the real pin — comparing against
    cmds.exactWorldBoundingBox only catches the fake drifting away from the
    module, because both sides of that comparison are the fake. Since #273
    the module walks the shapes and transforms each object-space box once,
    so the cached transform box is only read for nodes with no shape.
    """

    def test_translate_is_applied_once(self, maya_env):
        maya_env.scene.add_mesh(
            "GEO_box", bbox_min=(-50, -50, -50), bbox_max=(50, 50, 50), t=(200, 50, 300)
        )

        box = maya_env.module._world_bbox(_dag_path(maya_env, "GEO_box"))
        exact = maya_env.cmds.exactWorldBoundingBox("GEO_box")

        # The issue's own numbers: a 100 cube at (200, 50, 300).
        assert [box.min[i] for i in range(3)] == pytest.approx([150, 0, 250], abs=1e-3)
        assert [box.max[i] for i in range(3)] == pytest.approx([250, 100, 350], abs=1e-3)
        assert [box.min[i] for i in range(3)] == pytest.approx(exact[:3], abs=1e-3)
        assert [box.max[i] for i in range(3)] == pytest.approx(exact[3:], abs=1e-3)

    def test_rotation_gives_the_same_extents_as_the_exact_box(self, maya_env):
        maya_env.scene.add_mesh(
            "GEO_rot", bbox_min=(-50, -50, -50), bbox_max=(50, 50, 50), r=(0, 45, 0)
        )

        box = maya_env.module._world_bbox(_dag_path(maya_env, "GEO_rot"))
        exact = maya_env.cmds.exactWorldBoundingBox("GEO_rot")
        size = [box.max[i] - box.min[i] for i in range(3)]

        assert size == pytest.approx(
            [exact[3] - exact[0], exact[4] - exact[1], exact[5] - exact[2]], abs=1e-3
        )
        # A 100 cube at 45 deg is 141.421 wide, not 200.
        assert size[0] == pytest.approx(100 * math.sqrt(2), abs=1e-3)
        assert size[1] == pytest.approx(100, abs=1e-3)

    def test_child_rotation_cancelling_the_parent_reports_the_true_width(self, maya_env):
        """#273: the cached box is already widened by the child's own -30 deg
        before the parent's +30 deg reaches it, so the old read could not
        un-rotate it and reported 18.66 for a true 10 cube. Walking the
        shapes transforms each object-space box exactly once."""
        parent = maya_env.scene.add_transform("GRP_p")
        parent.r = [0, 30, 0]
        maya_env.scene.add_mesh(
            "GEO_c", bbox_min=(-5, -5, -5), bbox_max=(5, 5, 5), r=(0, -30, 0), parent=parent
        )

        box = maya_env.module._world_bbox(_dag_path(maya_env, "GEO_c"))
        exact = maya_env.cmds.exactWorldBoundingBox("GEO_c")
        size = [box.max[i] - box.min[i] for i in range(3)]

        # The two rotations cancel in world space, so this is the 10 cube.
        assert size == pytest.approx([10, 10, 10], abs=1e-3)
        assert [box.min[i] for i in range(3)] == pytest.approx([-5, -5, -5], abs=1e-3)
        assert [box.max[i] for i in range(3)] == pytest.approx([5, 5, 5], abs=1e-3)
        assert [box.min[i] for i in range(3)] == pytest.approx(exact[:3], abs=1e-3)
        assert [box.max[i] for i in range(3)] == pytest.approx(exact[3:], abs=1e-3)

    def test_nested_child_under_a_moved_parent(self, maya_env):
        parent = maya_env.scene.add_transform("GRP_root", t=(500, 0, 0))
        maya_env.scene.add_mesh(
            "GEO_child", bbox_min=(0, 0, 0), bbox_max=(10, 10, 10), t=(10, 0, 0), parent=parent
        )
        path = "|GRP_root|GEO_child"

        box = maya_env.module._world_bbox(_dag_path(maya_env, path))
        exact = maya_env.cmds.exactWorldBoundingBox(path)

        assert box.min.x == pytest.approx(510.0, abs=1e-3)
        assert box.max.x == pytest.approx(520.0, abs=1e-3)
        assert [box.min[i] for i in range(3)] == pytest.approx(exact[:3], abs=1e-3)
        assert [box.max[i] for i in range(3)] == pytest.approx(exact[3:], abs=1e-3)

    def test_shape_path_still_matches_the_exact_box(self, maya_env):
        maya_env.scene.add_mesh(
            "GEO_owner", bbox_min=(0, 0, 0), bbox_max=(4, 2, 1), t=(20, 0, 0), r=(0, 30, 0)
        )
        path = "|GEO_owner|GEO_ownerShape"

        box = maya_env.module._world_bbox(_dag_path(maya_env, path))
        exact = maya_env.cmds.exactWorldBoundingBox(path)

        # 4x2x1 box at (20,0,0) turned 30 deg about Y, computed by hand:
        # x = 20 .. 20 + 4cos30 + 1sin30, z = -4sin30 .. cos30, y = 0 .. 2.
        assert [box.min[i] for i in range(3)] == pytest.approx([20, 0, -2], abs=1e-3)
        assert [box.max[i] for i in range(3)] == pytest.approx(
            [20 + 4 * math.cos(math.radians(30)) + 0.5, 2, math.cos(math.radians(30))],
            abs=1e-3,
        )
        assert [box.min[i] for i in range(3)] == pytest.approx(exact[:3], abs=1e-3)
        assert [box.max[i] for i in range(3)] == pytest.approx(exact[3:], abs=1e-3)

    def test_a_group_without_shapes_keeps_the_cached_read(self, maya_env):
        """Nothing to walk: a shape-less group answers through the cached box.
        The stub represents an empty box as inf/-inf, so compare against the
        cached box itself rather than pinning the representation (real Maya
        reads 0..0 there; the GUI probe records it)."""
        group = maya_env.scene.add_transform("GRP_empty")
        cached = maya_env.scene.object_bbox(group)

        box = maya_env.module._world_bbox(_dag_path(maya_env, "GRP_empty"))

        assert [box.min[i] for i in range(3)] == [cached.min[i] for i in range(3)]
        assert [box.max[i] for i in range(3)] == [cached.max[i] for i in range(3)]

    def test_intermediate_shapes_are_left_out_of_the_walk(self, maya_env):
        """Intermediate objects are history, not geometry to measure; the
        cached aggregate ignored them too."""
        mesh = maya_env.scene.add_mesh("GEO_hist", bbox_min=(0, 0, 0), bbox_max=(1, 1, 1))
        mesh.children[0].intermediate = True

        assert maya_env.module._shape_dag_paths(_dag_path(maya_env, "GEO_hist")) == []

    def test_a_default_box_shape_is_skipped_but_a_real_point_is_kept(self, maya_env):
        """Maya 2024's MBoundingBox has no isEmpty(), and a shape with no
        geometry reads (0,0,0)..(0,0,0) in object space (GUI probe #273).
        Merging that would stretch a far-away union to the origin, so the
        default reading is skipped. A zero-extent box anywhere else is real
        geometry (a single vertex) and stays."""
        parent = maya_env.scene.add_transform("GRP_mix")
        maya_env.scene.add_mesh(
            "GEO_empty",
            bbox_min=(0, 0, 0),
            bbox_max=(0, 0, 0),
            num_vertices=0,
            parent=parent,
        )
        maya_env.scene.add_mesh("GEO_point", bbox_min=(5, 0, 0), bbox_max=(5, 0, 0), parent=parent)
        maya_env.scene.add_mesh(
            "GEO_far",
            bbox_min=(0, 0, 0),
            bbox_max=(10, 10, 10),
            t=(1000, 0, 0),
            parent=parent,
        )

        box = maya_env.module._world_bbox(_dag_path(maya_env, "GRP_mix"))

        assert box.min.x == pytest.approx(5.0, abs=1e-3)  # the point survived
        assert box.max.x == pytest.approx(1010.0, abs=1e-3)

    def test_an_empty_mesh_and_a_vertex_on_the_object_origin_are_told_apart(self, maya_env):
        """A single vertex on the object origin also reads a default box, so
        the vertex count decides: 0 is empty, 1 is a real point at the node's
        world position (moved to x=100 here; an empty mesh sits at x=200 and
        must not widen the union)."""
        parent = maya_env.scene.add_transform("GRP_points")
        maya_env.scene.add_mesh(
            "GEO_vertex",
            bbox_min=(0, 0, 0),
            bbox_max=(0, 0, 0),
            t=(100, 0, 0),
            num_vertices=1,
            parent=parent,
        )
        maya_env.scene.add_mesh(
            "GEO_no_verts",
            bbox_min=(0, 0, 0),
            bbox_max=(0, 0, 0),
            t=(200, 0, 0),
            num_vertices=0,
            parent=parent,
        )

        box = maya_env.module._world_bbox(_dag_path(maya_env, "GRP_points"))

        assert box.min.x == pytest.approx(100.0, abs=1e-3)
        assert box.max.x == pytest.approx(100.0, abs=1e-3)


class TestReportedBoxIsWorldSpace:
    """Anything reported next to a world `position` must be a world box."""

    def test_scene_graph_reports_the_world_box_of_a_nested_object(self, maya_env):
        parent = maya_env.scene.add_transform("GRP_root", t=(500, 0, 0))
        maya_env.scene.add_mesh(
            "GEO_child", bbox_min=(0, 0, 0), bbox_max=(10, 10, 10), t=(10, 0, 0), parent=parent
        )

        objects = {o["n"]: o for o in maya_env.module.get_scene_graph()["objects"]}

        assert objects["GEO_child"]["p"] == [510, 0, 0]
        assert objects["GEO_child"]["b"][0] == pytest.approx(510.0, abs=1e-3)
        assert objects["GEO_child"]["b"][3] == pytest.approx(520.0, abs=1e-3)

    def test_assert_scene_state_compares_the_world_box(self, maya_env):
        parent = maya_env.scene.add_transform("GRP_root", t=(500, 0, 0))
        maya_env.scene.add_mesh(
            "GEO_child", bbox_min=(0, 0, 0), bbox_max=(10, 10, 10), t=(10, 0, 0), parent=parent
        )

        res = maya_env.module.assert_scene_state(
            json.dumps({"GEO_child": {"bbox_min": [510, 0, 0]}})
        )

        assert res["passed"] is True, res


# ------------------------------------------------------------
# P1: scene_assert exists:false + bbox_min
# ------------------------------------------------------------


class TestSceneAssert:
    def test_exists_false_missing_object_passes(self, maya_env):
        res = maya_env.module.assert_scene_state(json.dumps({"ghost_obj": {"exists": False}}))
        assert res["passed"] is True
        assert res["passed_count"] == 1

    def test_exists_false_present_object_fails(self, maya_env):
        maya_env.scene.add_mesh("GEO_box")
        res = maya_env.module.assert_scene_state(json.dumps({"GEO_box": {"exists": False}}))
        assert res["passed"] is False
        assert any(mm["property"] == "existence" for mm in res["mismatches"])

    def test_exists_true_present_passes(self, maya_env):
        maya_env.scene.add_mesh("GEO_box")
        res = maya_env.module.assert_scene_state(json.dumps({"GEO_box": {"exists": True}}))
        assert res["passed"] is True

    def test_exists_true_missing_fails(self, maya_env):
        res = maya_env.module.assert_scene_state(json.dumps({"ghost": {"exists": True}}))
        assert res["passed"] is False

    def test_bbox_min_checked(self, maya_env):
        maya_env.scene.add_mesh("GEO_box", bbox_min=(-50, -50, -50), bbox_max=(50, 50, 50))
        res = maya_env.module.assert_scene_state(
            json.dumps({"GEO_box": {"bbox_min": [-50, -50, -50]}})
        )
        assert res["passed"] is True
        res2 = maya_env.module.assert_scene_state(json.dumps({"GEO_box": {"bbox_min": [0, 0, 0]}}))
        assert res2["passed"] is False
        assert any(mm["property"] == "bbox_min" for mm in res2["mismatches"])

    def test_position_check(self, maya_env):
        maya_env.scene.add_mesh("GEO_box", t=(10, 0, 5))
        res = maya_env.module.assert_scene_state(json.dumps({"GEO_box": {"position": [10, 0, 5]}}))
        assert res["passed"] is True


# ------------------------------------------------------------
# P0-5: check_constraints must catch penetration + disclose sampling
# ------------------------------------------------------------


class TestConstraints:
    def test_min_clearance_detects_penetration(self, maya_env):
        # Two overlapping boxes: clearance distance is NEGATIVE.
        maya_env.scene.add_mesh("GEO_a", bbox_min=(-50, -50, -50), bbox_max=(50, 50, 50))
        maya_env.scene.add_mesh(
            "GEO_b",
            bbox_min=(-50, -50, -50),
            bbox_max=(50, 50, 50),
            t=(20, 0, 0),
        )
        res = maya_env.module.check_constraints([{"type": "min_clearance", "value": 10}])
        assert res["passed"] is False, (
            "penetrating objects (negative clearance) must violate min_clearance"
        )
        assert any(v["type"] == "min_clearance" for v in res["violations"])

    def test_min_clearance_ok_when_separated(self, maya_env):
        maya_env.scene.add_mesh("GEO_a", t=(0, 0, 0))
        maya_env.scene.add_mesh("GEO_b", t=(1000, 0, 0))
        res = maya_env.module.check_constraints([{"type": "min_clearance", "value": 10}])
        assert res["passed"] is True

    def test_min_clearance_keeps_centimetre_thresholds_in_a_metre_scene(self, maya_env):
        maya_env.scene.linear_unit = "m"
        maya_env.scene.add_mesh("GEO_a", bbox_min=(0, 0, 0), bbox_max=(100, 100, 100))
        maya_env.scene.add_mesh(
            "GEO_b", bbox_min=(0, 0, 0), bbox_max=(100, 100, 100), t=(200, 0, 0)
        )

        tight = maya_env.module.check_constraints([{"type": "min_clearance", "value": 150}])
        loose = maya_env.module.check_constraints([{"type": "min_clearance", "value": 50}])

        violation = next(v for v in tight["violations"] if v["type"] == "min_clearance")
        assert violation["actual"] == pytest.approx(100.0)
        assert violation["required"] == 150
        assert loose["passed"] is True

    def test_min_clearance_keeps_precision_below_the_display_rounding(self, maya_env):
        """99.96 cm is below 100 cm; the displayed 0.9996 m rounds to 1.0 m,
        so comparing the display value would wrongly pass this rule."""
        maya_env.scene.linear_unit = "m"
        maya_env.scene.add_mesh("GEO_a", bbox_min=(0, 0, 0), bbox_max=(100, 100, 100))
        maya_env.scene.add_mesh(
            "GEO_b", bbox_min=(0, 0, 0), bbox_max=(100, 100, 100), t=(199.96, 0, 0)
        )

        res = maya_env.module.check_constraints([{"type": "min_clearance", "value": 100}])

        violation = next(v for v in res["violations"] if v["type"] == "min_clearance")
        assert violation["actual"] == pytest.approx(99.96)

    def test_sampling_disclosed(self, maya_env):
        # 30 transforms -> pair window (i+20) truncates some pairs
        for i in range(30):
            maya_env.scene.add_mesh(f"GEO_obj{i:02d}", t=(i * 500, 0, 0))
        res = maya_env.module.check_constraints([{"type": "no_overlap"}])
        assert "skipped" in res or "sampling" in res, (
            "truncated pair-scan must disclose how much was skipped"
        )

    def test_errored_measure_no_ghost_violation(self, maya_env):
        # Two same-named meshes under different parents -> short-name
        # resolution is ambiguous -> measure() returns an error dict whose
        # distance field is 0.0. That must NOT become a ghost violation.
        # Forge an ambiguous short-name state: two same-named nodes.
        # measure("dup", ...) then fails to resolve -> error dict -> must
        # be skipped, not turned into a ghost violation via distance 0.0.
        maya_env.scene.add_node("dup", "transform", exists_ok=True)
        maya_env.scene.add_node("dup", "transform", exists_ok=True)
        res = maya_env.module.check_constraints(
            [{"type": "min_clearance", "value": 10}, {"type": "no_overlap"}]
        )
        assert res["passed"] is True
        assert res["violations"] == []


# ------------------------------------------------------------
# Zone coverage (total_objects) + sampling disclosure in review
# ------------------------------------------------------------


class TestZoneCoverage:
    def test_coverage_not_negative(self, maya_env):
        # 3 zoned objects + 5 unassigned => coverage 3/8 = 0.375
        maya_env.scene.add_mesh("GEO_door_a")  # entrance pattern
        maya_env.scene.add_mesh("GEO_shelf_a")  # display pattern
        maya_env.scene.add_mesh("GEO_wall_a")  # shell pattern
        for i in range(5):
            maya_env.scene.add_mesh(f"random_{i}")
        res = maya_env.module.scene_plan()
        coverage = res["zone_analysis"]["coverage"]
        assert coverage == pytest.approx(0.375, abs=1e-3), (
            "coverage must be unassigned/total, not unassigned/1"
        )

    def test_get_zone_map_reports_total(self, maya_env):
        maya_env.scene.add_mesh("GEO_door_a")
        maya_env.scene.add_mesh("random_1")
        zd = maya_env.module.get_zone_map()
        assert zd["total_objects"] == 2
        assert zd["unassigned_count"] == 1


class TestSamplingDisclosure:
    def test_overlaps_checked_skipped(self, maya_env):
        for i in range(90):  # over the 80-object sample cap
            maya_env.scene.add_mesh(f"GEO_obj{i:02d}", t=(i * 1000, 0, 0))
        res = maya_env.module.scene_review(["overlaps"])
        check = res["checks"]["overlaps"]
        assert check["checked"] == 80
        assert check["skipped"] == 10

    def test_overlaps_no_skip_under_cap(self, maya_env):
        for i in range(3):
            maya_env.scene.add_mesh(f"GEO_obj{i}", t=(i * 1000, 0, 0))
        res = maya_env.module.scene_review(["overlaps"])
        assert res["checks"]["overlaps"]["skipped"] == 0

    def test_overlaps_substring_names_not_parent_child(self, maya_env):
        """D-037: basename-substring siblings are NOT parent-child -
        the old substring test wrongly excluded |GEO_wall vs
        |GEO_wall2 from the overlap check."""
        maya_env.scene.add_mesh("GEO_wall")
        maya_env.scene.add_mesh("GEO_wall2")  # same default bbox -> overlap
        res = maya_env.module.scene_review(["overlaps"])
        check = res["checks"]["overlaps"]
        assert check["pairs"] >= 1

    def test_overlaps_true_parent_child_excluded(self, maya_env):
        """A real parent-child pair stays excluded (DAG prefix)."""
        parent = maya_env.scene.add_mesh("GEO_p")
        maya_env.scene.add_mesh("GEO_c", parent=parent)
        res = maya_env.module.scene_review(["overlaps"])
        assert res["checks"]["overlaps"]["pairs"] == 0

    def test_conflicts_substring_names_not_parent_child(self, maya_env):
        """D-037: conflicts check must not exclude basename-substring
        siblings - |GEO_wall vs |GEO_wall2 are not parent-child."""
        maya_env.scene.add_mesh("GEO_wall")
        maya_env.scene.add_mesh("GEO_wall2")  # same default bbox -> penetration
        res = maya_env.module.scene_review(["conflicts"])
        assert res["checks"]["conflicts"]["count"] >= 1

    def test_conflicts_true_parent_child_excluded(self, maya_env):
        """A real parent-child pair stays excluded (DAG prefix)."""
        parent = maya_env.scene.add_mesh("GEO_p")
        maya_env.scene.add_mesh("GEO_c", parent=parent)
        res = maya_env.module.scene_review(["conflicts"])
        assert res["checks"]["conflicts"]["count"] == 0

    def test_predict_conflicts_substring_names_flagged(self, maya_env):
        """D-037: _predict_conflicts near-miss must not exclude
        basename-substring siblings either (audit T-11 F2)."""
        maya_env.scene.add_mesh("GEO_wall")
        maya_env.scene.add_mesh("GEO_wall2")  # same bbox -> zero gap
        res = maya_env.module.scene_plan()
        assert len(res["conflict_prevention"]) >= 1

    def test_predict_conflicts_true_parent_child_excluded(self, maya_env):
        """A real parent-child pair stays excluded (DAG prefix)."""
        parent = maya_env.scene.add_mesh("GEO_p")
        maya_env.scene.add_mesh("GEO_c", parent=parent)
        res = maya_env.module.scene_plan()
        assert len(res["conflict_prevention"]) == 0

    def test_conflicts_checked_skipped(self, maya_env):
        for i in range(70):  # over the 60-object cap
            maya_env.scene.add_mesh(f"GEO_obj{i:02d}", t=(i * 1000, 0, 0))
        res = maya_env.module.scene_review(["conflicts"])
        check = res["checks"]["conflicts"]
        assert check["checked"] == 60
        assert check["skipped"] == 10

    def test_aesthetics_sampling(self, maya_env):
        for i in range(210):  # over the 200-object cap
            maya_env.scene.add_mesh(f"GEO_obj{i:03d}", t=(i * 1000, 0, 0))
        res = maya_env.module.analyze_aesthetics()
        assert "sampling" in res
        assert res["sampling"]["skipped"] == 10


class TestAestheticsColorMath:
    """Pin the color_theory dimension, which is the widest path through the
    small color helpers (RGB->HSL, hue, color temperature in Kelvin, WCAG
    luminance). A change in that math then shows up as a changed score
    instead of a number nobody reads.

    The entry is analyze_aesthetics(), the module function the scene_aesthetics
    tool calls. Two things this test does NOT cover: the other call sites of
    those same helpers (_color_temp_k in _score_lighting_quality, _rgb_to_hsl
    in _analyze_style_consistency), and any band the fixture below does not
    land in.

    The fixture is picked so every expected value can be derived by hand:
    - object counts 6/3/1 of a 10-object total are exactly 60/30/10;
    - red (1,0,0) and green (0,1,0) estimate as 3000K and cyan (0,1,1) as
      10000K, so 7 objects land warm and 3 cool;
    - all three are fully saturated, so the saturation spread is zero;
    - red is hue 0 and cyan is hue 180, exactly complementary;
    - WCAG luminance is 0.2126 red, 0.7874 cyan, 0.7152 green, so the
      contrast ratio is (0.7874+0.05)/(0.2126+0.05) = 3.19.
    """

    def test_known_material_colors_score_as_expected(self, maya_env):
        reds = [f"GEO_red{i}" for i in range(6)]
        cyans = [f"GEO_cyan{i}" for i in range(3)]
        for i, name in enumerate(reds + cyans):
            maya_env.scene.add_mesh(name, t=(i * 200, 0, 0))
        maya_env.scene.add_mesh("GEO_green", t=(2000, 0, 0))

        maya_env.scene.add_material("MAT_red", color=(1.0, 0.0, 0.0), assign_to=reds)
        maya_env.scene.add_material("MAT_cyan", color=(0.0, 1.0, 1.0), assign_to=cyans)
        maya_env.scene.add_material("MAT_green", color=(0.0, 1.0, 0.0), assign_to=["GEO_green"])

        res = maya_env.module.analyze_aesthetics()

        color = res["detail"]["color_theory"]
        # Every value is pinned exactly because _score_color_theory rounds
        # them all to one decimal: 100 = no 60/30/10 deviation, 60 = 40 units
        # of warm/cool imbalance, 40 = spread 0 falls in the 40 band,
        # 90 = complementary hues, 65 = contrast ratio in 3-4.5.
        assert color["sub_scores"] == {
            "60_30_10": 100.0,
            "temperature": 60.0,
            "saturation": 40.0,
            "harmony": 90.0,
            "contrast": 65.0,
        }
        # 0.20*100 + 0.15*60 + 0.15*40 + 0.25*90 + 0.25*65 = 73.75, which the
        # function rounds to 73.8 — so exact equality is the honest assertion.
        assert color["score"] == 73.8


class TestAestheticsScoreContract:
    """Pin the whole 5-dimension result, not just the color dimension.

    The annotations added to this call chain must not move a single number.
    The expected values below were measured on the commit before that change
    and again after it, with this exact fixture; the two JSON dumps were
    byte-identical. The assertions pin the total, all five dimension scores,
    every dimension's sub_scores, the full output of three research helpers,
    and the silhouette average plus one sampled detail row. Deliberately not
    pinned: the remaining per-object silhouette rows and the top_colors and
    issues lists. No hand-derived expectation covers those, so a change there
    would pass this test.

    The total is the one value with a tolerance. Its weighted sum is exactly
    53.05, which sits on the round-half boundary, and CPython 3.12 changed
    float ``sum()`` to compensated summation: 3.9/3.10 land just above the
    boundary and round to 53.1, 3.13 lands just below and rounds to 53.0.
    Measured on 3.9.25, 3.10.20 and 3.13.13; every other value was identical.
    """

    def test_same_fixture_keeps_every_dimension_and_total(self, maya_env):
        reds = [f"GEO_red{i}" for i in range(6)]
        cyans = [f"GEO_cyan{i}" for i in range(3)]
        for i, name in enumerate(reds + cyans):
            maya_env.scene.add_mesh(name, t=(i * 200, 0, 0))
        maya_env.scene.add_mesh("GEO_green", t=(2000, 0, 0))
        maya_env.scene.add_material("MAT_red", color=(1.0, 0.0, 0.0), assign_to=reds)
        maya_env.scene.add_material("MAT_cyan", color=(0.0, 1.0, 1.0), assign_to=cyans)
        maya_env.scene.add_material("MAT_green", color=(0.0, 1.0, 0.0), assign_to=["GEO_green"])

        res = maya_env.module.analyze_aesthetics()

        assert res["overall_score"] == pytest.approx(53.05, abs=0.1)
        assert res["grade"] == "D"
        assert res["dimensions"] == {
            "color_theory": 73.8,
            "spatial_composition": 29.0,
            "proportion_scale": 85.0,
            "lighting_quality": 0,
            "visual_flow": 69.0,
        }
        detail = res["detail"]
        # color_theory's sub_scores are also pinned by TestAestheticsColorMath;
        # repeating them here keeps this contract readable on its own.
        assert detail["color_theory"]["sub_scores"] == {
            "60_30_10": 100.0,
            "temperature": 60.0,
            "saturation": 40.0,
            "harmony": 90.0,
            "contrast": 65.0,
        }
        assert detail["spatial_composition"]["sub_scores"] == {
            "golden_ratio": 50.0,
            "rule_of_thirds": 40.0,
            "visual_balance": 0,
        }
        assert detail["proportion_scale"]["sub_scores"] == {
            "human_scale": 100,
            "hierarchy": 70,
        }
        assert detail["lighting_quality"]["detail"] == "no_lights"
        assert detail["lighting_quality"]["sub_scores"] == {
            "layers": 0,
            "three_point": 0,
            "fill_ratio": 0,
            "shadow_quality": 0,
            "temperature": 0,
            "coverage": 0,
            "decay": 0,
            "intensity_dist": 0,
        }
        assert detail["visual_flow"]["sub_scores"] == {
            "sight_lines": 100.0,
            "circulation": 40,
            "rhythm": 60,
        }
        # The research-based analyses land in the dimension detail dicts. The
        # three small helper results are pinned whole; silhouette is pinned by
        # its average and one sampled row (its detail list is per object).
        assert detail["color_theory"]["style_consistency"] == {
            "score": 79.0,
            "form_consistency": 100.0,
            "size_hierarchy": 50,
            "material_consistency": 80,
        }
        assert detail["proportion_scale"]["curvature"] == {
            "score": 40,
            "size_cv": 0.0,
            "avg_size": 100.0,
            "interpretation": "monotonous",
        }
        assert detail["visual_flow"]["rhythm_enhanced"] == {
            "score": 50,
            "repeating_groups": 1,
            "patterns_found": 1,
        }
        silhouette = detail["proportion_scale"]["silhouette"]
        assert silhouette["avg_clarity"] == 58.0
        assert len(silhouette["details"]) == 5
        assert silhouette["details"][0] == {
            "name": "GEO_red0",
            "aspect_ratio": 1.0,
            "compactness": 0.55,
            "clarity_score": 58.0,
        }
        assert res["sampling"]["checked"] == 10


# ------------------------------------------------------------
# P0-6: camera_orbit must constrain to a center locator
# ------------------------------------------------------------


class TestOrbitCamera:
    def test_orbit_creates_center_locator_and_constraint(self, maya_env):
        res = maya_env.module.create_orbit_camera(
            [10, 5, 0], radius=100, frames=120, name="CAM_orbit"
        )
        assert "error" not in res
        assert res["warnings"] == []
        # A locator must exist near the requested center
        loc = maya_env.scene.resolve(res["center_locator"])
        assert loc.name.startswith(("LOC_", "CAM_orbit"))
        wx, wy, wz = maya_env.scene.world_position(loc)
        assert (wx, wy, wz) == pytest.approx((10, 5, 0))
        # An aim constraint targeting that locator must exist
        assert maya_env.scene.constraints, "aim constraint never created"
        assert maya_env.scene.constraints[-1]["target"] == loc.name

    def test_orbit_aim_failure_surfaces(self, maya_env, monkeypatch):
        def boom(*a, **k):
            raise RuntimeError("constraint engine down")

        monkeypatch.setattr(maya_env.cmds, "aimConstraint", boom)
        res = maya_env.module.create_orbit_camera([0, 0, 0], radius=50, frames=60, name="CAM_orb3")
        assert res["warnings"], "aimConstraint failure must surface in result"
        assert "constraint engine down" in res["warnings"][0]
        assert maya_env.scene.warnings, "cmds.warning must be called"

    def test_orbit_keyframes_set(self, maya_env):
        res = maya_env.module.create_orbit_camera([0, 0, 0], radius=50, frames=60, name="CAM_orb2")
        cam = maya_env.scene.resolve(res["camera"])
        assert res["warnings"] == []
        assert len(maya_env.scene.keyed) >= 3
        assert all(node == cam.name for node, _attr in maya_env.scene.keyed)
        assert len(maya_env.scene.keyed) >= 3


# ------------------------------------------------------------
# #272: camera framing must speak the scene's working unit
# ------------------------------------------------------------


class TestCameraShotUnits:
    """OpenMaya hands back centimetres; cmds.move reads working units.

    In a centimetre scene the two agree, which is why this stayed green.
    In a metre scene the raw centimetre numbers put the camera 100x too far.
    """

    # The same numbers in every unit system: 2.2 units tall, medium = 3x,
    # azimuth 30 / elevation 15.
    EXPECTED_POSITION = [3.1876, 1.7082, 5.5210]

    @staticmethod
    def _door(maya_env, unit):
        """One 1.3 x 2.2 x 0.12 door in the requested working unit."""
        maya_env.scene.linear_unit = unit
        name = "door_" + unit
        maya_env.cmds.polyCube(w=1.3, h=2.2, d=0.12, name=name)
        return name

    def test_metre_scene_frames_the_target(self, maya_env):
        scene = maya_env.scene
        name = self._door(maya_env, "m")

        res = maya_env.module.create_camera_shot(name, shot_type="medium")
        assert "error" not in res

        assert res["distance"] == pytest.approx(6.6, abs=1e-3)
        assert res["position"] == pytest.approx(self.EXPECTED_POSITION, abs=1e-3)

        cam = scene.resolve(res["camera"])
        world_cm = scene.world_position(cam)
        world_m = [v * scene.working_unit_scale() for v in world_cm]
        assert world_m == pytest.approx(self.EXPECTED_POSITION, abs=1e-3)
        # The camera must actually aim at the door, not just sit near it.
        assert scene.constraints[-1]["target"] == scene.resolve(name).name

    def test_metre_scene_adds_the_target_offset(self, maya_env):
        """The target's own position is converted too, not just its size."""
        scene = maya_env.scene
        name = self._door(maya_env, "m")
        maya_env.cmds.move(2, 1, 3, name)

        res = maya_env.module.create_camera_shot(name, shot_type="medium")

        expected = [v + off for v, off in zip(self.EXPECTED_POSITION, (2, 1, 3))]
        assert res["position"] == pytest.approx(expected, abs=1e-3)
        world_cm = scene.world_position(scene.resolve(res["camera"]))
        world_m = [v * scene.working_unit_scale() for v in world_cm]
        assert world_m == pytest.approx(expected, abs=1e-3)

    def test_centimetre_scene_output_is_unchanged(self, maya_env):
        scene = maya_env.scene
        name = self._door(maya_env, "cm")

        res = maya_env.module.create_camera_shot(name, shot_type="medium")

        # Default scene: the reported numbers must stay exactly as before.
        assert res["position"] == [3.2, 1.7, 5.5]
        assert res["distance"] == 6.6
        cam = scene.resolve(res["camera"])
        # Byte-identical landing: the factor is exactly 1.0, so the stored
        # centimetres are the same floats the old code produced.
        assert cam.t == [3.187555226753925, 1.708205697676637, 5.521007604669533]

    def test_inch_scene_is_no_coarser_than_cm(self, maya_env):
        """A non-cm scene reports no coarser than 0.1 cm."""
        name = self._door(maya_env, "in")

        res = maya_env.module.create_camera_shot(name, shot_type="medium")

        assert res["distance"] == pytest.approx(6.6, abs=1e-3)
        assert res["position"] == [round(v, 2) for v in self.EXPECTED_POSITION]

    @pytest.mark.parametrize("unit", ["cm", "m"])
    def test_aim_fallback_aims_in_both_units(self, maya_env, monkeypatch, unit):
        """A failed constraint must not change the manual aim between units."""
        scene = maya_env.scene
        name = self._door(maya_env, unit)

        def boom(*a, **k):
            raise RuntimeError("constraint engine down")

        monkeypatch.setattr(maya_env.cmds, "aimConstraint", boom)
        res = maya_env.module.create_camera_shot(name, shot_type="medium")
        assert "error" not in res

        cam = scene.resolve(res["camera"])
        assert cam.r == pytest.approx([-15.0, 30.0, 0.0], abs=1e-6)

        # The -Z axis of a Maya camera is its view direction; it must point
        # from the camera to the door at the origin.
        cam_pos = [v * scene.working_unit_scale() for v in scene.world_position(cam)]
        norm = math.sqrt(sum(v * v for v in cam_pos))
        to_target = [-v / norm for v in cam_pos]
        rx, ry = math.radians(cam.r[0]), math.radians(cam.r[1])
        forward = [
            -math.cos(rx) * math.sin(ry),
            math.sin(rx),
            -math.cos(rx) * math.cos(ry),
        ]
        assert forward == pytest.approx(to_target, abs=1e-6)


# ------------------------------------------------------------
# #271: query payloads declare the working unit, so their lengths
# must be converted out of OpenMaya's internal centimetres.
# ------------------------------------------------------------


class TestWorkingUnitLengths:
    """OpenMaya always hands back centimetres; `unit` names the working unit."""

    def test_scene_graph_reports_working_unit_lengths(self, maya_env):
        maya_env.scene.linear_unit = "m"
        maya_env.scene.add_mesh(
            "GEO_door", bbox_min=(-65, -110, -6), bbox_max=(65, 110, 6), t=(0, 0, 0)
        )

        graph = maya_env.module.get_scene_graph()
        door = next(obj for obj in graph["objects"] if obj["n"] == "GEO_door")

        assert graph["unit"] == "m"
        assert door["p"] == [0.0, 0.0, 0.0]
        assert door["b"] == pytest.approx([-0.65, -1.1, -0.06, 0.65, 1.1, 0.06])

    def test_scene_graph_keeps_centimetre_numbers(self, maya_env):
        maya_env.scene.add_mesh(
            "GEO_door", bbox_min=(-65, -110, -6), bbox_max=(65, 110, 6), t=(0, 0, 0)
        )

        graph = maya_env.module.get_scene_graph()
        door = next(obj for obj in graph["objects"] if obj["n"] == "GEO_door")

        assert graph["unit"] == "cm"
        assert door["p"] == [0.0, 0.0, 0.0]
        assert door["b"] == [-65.0, -110.0, -6.0, 65.0, 110.0, 6.0]

    def test_measure_reports_working_unit_lengths(self, maya_env):
        maya_env.scene.linear_unit = "m"
        maya_env.scene.add_mesh(
            "GEO_door", bbox_min=(-65, -110, -6), bbox_max=(65, 110, 6), t=(0, 0, 0)
        )

        result = maya_env.module.measure("GEO_door", "GEO_door", mode="bbox")

        assert result["unit"] == "m"
        assert result["details"]["overlap_dims"] == pytest.approx([1.3, 2.2, 0.12])
        assert result["distance"] == 0.0

    def test_measure_modes_convert_every_length(self, maya_env):
        maya_env.scene.linear_unit = "m"
        maya_env.scene.add_mesh("GEO_a", bbox_min=(0, 0, 0), bbox_max=(100, 100, 100))
        maya_env.scene.add_mesh(
            "GEO_b", bbox_min=(0, 0, 0), bbox_max=(100, 100, 100), t=(200, 0, 0)
        )

        center = maya_env.module.measure("GEO_a", "GEO_b", mode="center")
        assert center["distance"] == pytest.approx(2.0)
        assert center["details"]["center_a"] == pytest.approx([0.5, 0.5, 0.5])
        assert center["details"]["center_b"] == pytest.approx([2.5, 0.5, 0.5])

        surface = maya_env.module.measure("GEO_a", "GEO_b", mode="surface")
        assert surface["distance"] == pytest.approx(1.0)
        assert surface["details"]["surface_a"] == pytest.approx([1.0, 0.5, 0.5])
        assert surface["details"]["surface_b"] == pytest.approx([2.0, 0.5, 0.5])

        clearance = maya_env.module.measure("GEO_a", "GEO_b", mode="clearance")
        assert clearance["distance"] == pytest.approx(1.0)
        assert clearance["details"]["clearances_xyz"] == pytest.approx([1.0, -1.0, -1.0])

    def test_measure_keeps_centimetre_numbers(self, maya_env):
        maya_env.scene.add_mesh("GEO_a", bbox_min=(0, 0, 0), bbox_max=(100, 100, 100))
        maya_env.scene.add_mesh(
            "GEO_b", bbox_min=(0, 0, 0), bbox_max=(100, 100, 100), t=(200, 0, 0)
        )

        result = maya_env.module.measure("GEO_a", "GEO_b", mode="clearance")

        assert result["distance"] == 100.0
        assert result["details"]["clearances_xyz"] == [100.0, -100.0, -100.0]

    def test_spatial_index_distances_follow_the_working_unit(self, maya_env):
        maya_env.scene.linear_unit = "m"
        maya_env.scene.add_mesh("GEO_a", bbox_min=(0, 0, 0), bbox_max=(10, 10, 10))
        maya_env.scene.add_mesh("GEO_b", bbox_min=(0, 0, 0), bbox_max=(10, 10, 10), t=(100, 0, 0))

        index = maya_env.module.get_spatial_index(max_distance=2.0)

        assert index["threshold"] == pytest.approx(2.0)
        assert index["pairs"] == [[0, 1, pytest.approx(1.0)]]

    def test_full_detail_vertex_positions_follow_the_working_unit(self, maya_env, monkeypatch):
        class FakeMesh:
            numVertices = 1  # noqa: N815 - mirrors Maya's API
            numPolygons = 1  # noqa: N815 - mirrors Maya's API

            def __init__(self, dag):
                pass

            def getPoint(self, index, space):  # noqa: N802 - mirrors Maya's API
                return maya_env.om2.MPoint(100, 50, 25)

        monkeypatch.setattr(maya_env.om2, "MFnMesh", FakeMesh)
        maya_env.scene.linear_unit = "m"
        maya_env.scene.add_mesh("GEO_cube", bbox_min=(0, 0, 0), bbox_max=(100, 100, 100))

        graph = maya_env.module.get_scene_graph(detail_level="full")
        cube = next(obj for obj in graph["objects"] if obj["n"] == "GEO_cube")

        assert cube["verts"] == pytest.approx([1.0, 0.5, 0.25])

    def test_zone_map_display_units_scales_boxes(self, maya_env):
        maya_env.scene.linear_unit = "m"
        maya_env.scene.add_mesh(
            "GEO_door", bbox_min=(0, 0, 0), bbox_max=(100, 100, 100), t=(200, 0, 0)
        )

        display = next(
            zone
            for zone in maya_env.module.get_zone_map(display_units=True)["zones"]
            if zone["name"] == "entrance"
        )
        internal = next(
            zone for zone in maya_env.module.get_zone_map()["zones"] if zone["name"] == "entrance"
        )

        assert display["center"] == pytest.approx([2.5, 0.5, 0.5])
        assert display["bbox_min"] == pytest.approx([2.0, 0.0, 0.0])
        assert display["bbox_max"] == pytest.approx([3.0, 1.0, 1.0])
        assert display["unit"] == "m"
        assert internal["center"] == [250.0, 50.0, 50.0]
        assert internal["bbox_min"] == [200.0, 0.0, 0.0]
        assert internal["bbox_max"] == [300.0, 100.0, 100.0]
        assert "unit" not in internal
