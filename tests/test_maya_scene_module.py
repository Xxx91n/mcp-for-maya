"""Regression tests for maya_scene_module running on the maya stub.

Each test pins a P0/P1 fix from the grill handoff (rui.txt). The stub's
matrix/bbox math is verified independently in test_maya_stub.py, so
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
        Node names must be unique per call -- the stub keys transforms by name,
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
