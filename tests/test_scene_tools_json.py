"""T-02 regression tests: tool-layer JSON serialization + error passthrough.

The ExecClient executes the code scene_tools generates against the fake-bound
_mcp_scene module using the REAL helper result-capture transform — so these
tests exercise the full chain: arg serialization -> generated code ->
Maya-side module -> returned dict.
"""

from __future__ import annotations

import ast
import json
import os
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from maya_mcp_server.maya_mcp_helper import prepare_code_for_result_capture
from maya_mcp_server.scene_tools import (
    _caches,
    _injected_sessions,
    get_zone_geometry,
    register_scene_tools,
)
from maya_mcp_server.types import CommandResponse, OutputBuffer, ResultType


class ExecClient:
    """Fake client: runs generated code on the fake scene module."""

    def __init__(self, module):
        self.module = module
        self.calls = []

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

    async def get_buffered_output(self):
        return OutputBuffer()

    def append_output(self, stdout, stderr):
        pass

    async def write_module(self, name, code, overwrite=False):
        return name


class ErrorClient(ExecClient):
    """Client whose Maya side raises — error must propagate, not vanish."""

    async def execute_code(self, code, result_type=ResultType.NONE):
        self.calls.append(code)
        return CommandResponse(
            result=None,
            error={
                "type": "builtins.RuntimeError",
                "message": "kaboom in maya",
                "traceback": "Traceback...\nRuntimeError: kaboom in maya",
            },
        )


@pytest.fixture
def tools(maya_env, monkeypatch):
    sys.modules["_mcp_scene"] = maya_env.module
    _injected_sessions.add("_default")
    _caches.clear()
    client = ExecClient(maya_env.module)
    manager = MagicMock()
    manager.get_client = AsyncMock(return_value=client)
    monkeypatch.setattr("maya_mcp_server.server.get_session_manager", lambda: manager)
    mock_mcp = MagicMock()
    fns = {}

    def capture(fn=None, **_kwargs):
        if fn is None:
            return lambda f: capture(f)
        fns[fn.__name__] = fn
        return fn

    mock_mcp.tool = capture
    register_scene_tools(mock_mcp)
    yield SimpleNamespace(fns=fns, client=client, manager=manager, env=maya_env)
    _injected_sessions.discard("_default")
    _caches.clear()
    sys.modules.pop("_mcp_scene", None)


# ------------------------------------------------------------
# JSON-serialized arguments (P0-2: injection surface removal)
# ------------------------------------------------------------


class TestJsonArgSerialization:
    async def test_validate_rules_via_json(self, tools):
        tools.env.scene.add_mesh("GEO_a")
        out = await tools.fns["scene_validate"](
            rules=json.dumps([{"type": "max_objects", "value": 100}]),
            format="json",
        )
        res = json.loads(out)
        assert res["passed"] is True
        code = tools.client.calls[-1]
        assert "json.loads" in code, "rules must go through JSON"
        assert "rules_escaped" not in code
        ast.parse(code)  # generated code must always be valid python

    async def test_validate_rejects_bad_json(self, tools):
        from maya_mcp_server.security import InputValidationError

        with pytest.raises(InputValidationError):
            await tools.fns["scene_validate"](rules="not json {{{")

    async def test_injection_in_measure_args_is_inert(self, tools):
        tools.env.scene.add_mesh("GEO_a", t=(5, 0, 0))
        evil = "x'); import os; os.system('echo PWNED') #"
        out = await tools.fns["scene_measure"](
            obj_a=evil, obj_b="GEO_a", mode="center", format="json"
        )
        res = json.loads(out)
        # the hostile string arrived as DATA (object doesn't exist -> error)
        assert res["obj_a"] == evil
        assert "error" in res

    async def test_quotes_in_checkpoint_name_verbatim(self, tools):
        seen = {}

        def spy(name=None, overwrite=False):
            seen["name"] = name
            return {"ok": True, "name": name}

        tools.env.module.save_checkpoint = spy
        name = 'cp "quoted" \\ ; import os'
        await tools.fns["scene_checkpoint"](name=name)
        assert seen["name"] == name

    async def test_rollback_filename_verbatim(self, tools):
        seen = {}

        def spy(filename, discard_current_state=False):
            seen["fn"] = filename
            return {"success": True, "rolled_back_to": filename}

        tools.env.module.rollback_to_checkpoint = spy
        fn = 'cp_20250101_x"); pass #.ma'
        await tools.fns["scene_rollback"](filename=fn)
        assert seen["fn"] == fn

    async def test_checkpoint_passes_overwrite_kwarg(self, tools):
        seen = {}

        def spy(name=None, overwrite=False):
            seen["name"] = name
            seen["overwrite"] = overwrite
            return {"ok": True}

        tools.env.module.save_checkpoint = spy
        await tools.fns["scene_checkpoint"](name="v1", overwrite=True)
        assert seen == {"name": "v1", "overwrite": True}

    async def test_checkpoint_default_name_is_none(self, tools):
        seen = {}

        def spy(name=None, overwrite=False):
            seen["name"] = name
            return {"ok": True}

        tools.env.module.save_checkpoint = spy
        await tools.fns["scene_checkpoint"]()
        assert seen["name"] is None, (
            "default must reach the module as None so untitled scenes can error"
        )

    async def test_rollback_passes_discard_flag(self, tools):
        seen = {}

        def spy(filename, discard_current_state=False):
            seen["filename"] = filename
            seen["discard"] = discard_current_state
            return {"success": True}

        tools.env.module.rollback_to_checkpoint = spy
        await tools.fns["scene_rollback"](filename="cp_x.ma", discard_current_state=True)
        assert seen == {"filename": "cp_x.ma", "discard": True}

    async def test_scene_assert_expectations_json(self, tools):
        tools.env.scene.add_mesh("GEO_box", t=(1, 2, 3))
        expectations = json.dumps({"GEO_box": {"position": [1, 2, 3]}})
        out = await tools.fns["scene_assert"](expectations=expectations, format="json")
        res = json.loads(out)
        assert res["passed"] is True

    async def test_scene_inspect_target_serialized(self, tools):
        tools.env.scene.add_mesh("GEO_a", t=(7, 8, 9))
        out = await tools.fns["scene_inspect"](target="GEO_a", format="json")
        res = json.loads(out)
        assert res["object"]["name"] == "GEO_a"
        assert res["object"]["position"] == [7, 8, 9]  # not just name echo
        code = tools.client.calls[-1]
        ast.parse(code)

    async def test_camera_orbit_center_json(self, tools):
        out = await tools.fns["camera_orbit"](
            center="[10, 5, 0]", radius=100, frames=24, name="CAM_orb"
        )
        res = json.loads(out)
        assert "error" not in res
        assert res["center"] == [10, 5, 0]


# ------------------------------------------------------------
# Error passthrough (P0-1: result.error must not be dropped)
# ------------------------------------------------------------


class TestErrorPassthrough:
    async def test_scene_tool_raises_on_maya_error(self, tools, monkeypatch):
        err_client = ErrorClient(tools.env.module)
        tools.manager.get_client = AsyncMock(return_value=err_client)
        from maya_mcp_server.client import MayaExecutionError

        with pytest.raises(MayaExecutionError, match="kaboom"):
            await tools.fns["scene_snapshot"](format="json")

    async def test_server_execute_code_raises_on_error(self, monkeypatch):
        from maya_mcp_server import server
        from maya_mcp_server.client import MayaExecutionError

        client = AsyncMock()
        client.execute_code.return_value = CommandResponse(
            result=None,
            error={
                "type": "builtins.ValueError",
                "message": "bad thing happened",
                "traceback": "tb",
            },
        )
        client.get_buffered_output.return_value = OutputBuffer()
        client.append_output = MagicMock()
        manager = MagicMock()
        manager.get_client = AsyncMock(return_value=client)
        monkeypatch.setattr(server, "get_session_manager", lambda: manager)

        execute_fn = getattr(server.execute_code, "fn", server.execute_code)
        with pytest.raises(MayaExecutionError, match="bad thing happened"):
            await execute_fn(code="1+1", result_type="JSON")

    async def test_server_execute_code_ok(self, monkeypatch):
        from maya_mcp_server import server

        client = AsyncMock()
        client.execute_code.return_value = CommandResponse(result={"ok": 1}, error=None)
        client.get_buffered_output.return_value = OutputBuffer()
        client.append_output = MagicMock()  # sync def (client.py:342) — not AsyncMock
        manager = MagicMock()
        manager.get_client = AsyncMock(return_value=client)
        monkeypatch.setattr(server, "get_session_manager", lambda: manager)

        execute_fn = getattr(server.execute_code, "fn", server.execute_code)
        out = await execute_fn(code='{"a":1}', result_type="JSON")
        assert out == {"ok": 1}


# ------------------------------------------------------------
# Issue #79: a registered validator reaches the scene_review MCP tool
# ------------------------------------------------------------


class TestSceneReviewCustomValidators:
    async def test_builtin_shape_and_score_when_nothing_registered(self, tools):
        tools.env.scene.add_mesh("GEO_box")
        res = json.loads(await tools.fns["scene_review"](format="json"))

        assert "custom" not in res, "the section is omitted, not empty"
        assert set(res) == {
            "checks",
            "issues",
            "score",
            "total_issues",
            "errors",
            "warnings",
            "standards",
        }
        assert res == json.loads(json.dumps(tools.env.module.scene_review()))

    async def test_registered_validator_reaches_the_tool_answer(self, tools):
        tools.env.scene.add_mesh("GEO_box")
        before = json.loads(await tools.fns["scene_review"](format="json"))

        tools.env.module.register_validator(
            "no_free_roots",
            lambda: (False, "GEO_box sits at the scene root"),
            severity="warning",
            family="studio",
        )
        res = json.loads(await tools.fns["scene_review"](format="json"))

        assert res["custom"]["issues"][0]["name"] == "no_free_roots"
        assert res["custom"]["score"] == 0.0
        for key in ("score", "errors", "warnings", "total_issues", "checks"):
            assert res[key] == before[key], f"built-in {key} moved with a validator registered"
        assert "scene_review_with_validators" in tools.client.calls[-1]

    async def test_cos_view_keeps_its_own_line(self, tools):
        tools.env.module.register_validator("harsh", lambda: False, message="rule broken")
        out = await tools.fns["scene_review"](format="cos")

        assert "CUSTOM: score=0.0/1.0 | validators=1 | failing=1 | check_error=0" in out
        assert "[ERROR] harsh: rule broken" in out

    async def test_cos_separates_a_broken_rule_from_a_violated_one(self, tools):
        tools.env.module.register_validator("broken", lambda: 1 / 0)
        tools.env.module.register_validator("violated", lambda: False)
        out = await tools.fns["scene_review"](format="cos")

        assert "failing=1 | check_error=1" in out, "one number must not mix the two"

    async def test_no_issue_row_prints_none(self, tools):
        tools.env.module.register_validator("silent", lambda: False)
        out = await tools.fns["scene_review"](format="cos")

        assert "silent: None" not in out
        assert "[ERROR] silent: silent failed" in out


# ------------------------------------------------------------
# Issue #120: the `checks` argument shape the card documents
# ------------------------------------------------------------


class TestChecksArgumentShape:
    """`checks` is a comma-separated string at the MCP boundary and a Python
    list at the Maya side; the tool splits it itself. The scene-review card
    carries the call shape and `skills/` sits outside check_doc_claims.py's
    surfaces, so nothing else pins it — this pins the behaviour the card
    describes, not the card's wording.

    Bounds, stated because a pin that cannot fail is worse than none. The spy
    reads what the generated code hands to `scene_review_with_validators`, so
    both failure modes are covered: a tool that stopped splitting hands the
    string through, and one that renamed the Maya-side entry point never calls
    the spy at all. What it does NOT cover is the card's prose — reverting the
    card to the list form leaves this green, because the ticket scopes the pin
    to the tool boundary.
    """

    async def test_two_names_reach_the_maya_side_call_as_a_list(self, tools):
        seen = {}

        def spy(checks=None):
            seen["checks"] = checks
            return {"checks": {}, "issues": [], "score": 0}

        tools.env.module.scene_review_with_validators = spy
        await tools.fns["scene_review"](checks="overlaps,conflicts", format="json")

        assert "checks" in seen, "the Maya-side entry point was never called - re-aim this pin"
        assert seen["checks"] == ["overlaps", "conflicts"]


# ------------------------------------------------------------
# Issue #176: internal zone-geometry host helper, no new MCP tool
# ------------------------------------------------------------


class TestZoneGeometryHostHelper:
    async def test_helper_reads_fresh_geometry_through_the_scene_module(self, tools):
        tools.env.scene.add_mesh("GEO_shelf_a", bbox_min=(0, 0, 0), bbox_max=(4, 2, 1), t=(0, 0, 0))

        first = await get_zone_geometry(tools.client)
        tools.env.cmds.move(10, 0, 0, "GEO_shelf_a")
        second = await get_zone_geometry(tools.client)

        assert first["zones"][0]["bbox_min"] == [0, 0, 0]
        assert second["zones"][0]["bbox_min"] == [10, 0, 0]
        assert second["zones"][0]["size"] == [4, 2, 1]
        assert "get_zone_geometry" in tools.client.calls[-1]
        assert not _caches, "geometry must not be cached by this helper"

    async def test_helper_passes_domain_errors_through(self, tools, monkeypatch):
        error = {"error": {"code": "query_failed", "message": "bbox unreadable"}}
        monkeypatch.setattr(tools.env.module, "get_zone_geometry", lambda: error)

        assert await get_zone_geometry(tools.client) == error

    async def test_helper_raises_on_maya_execution_error(self, tools):
        from maya_mcp_server.client import MayaExecutionError

        with pytest.raises(MayaExecutionError, match="kaboom"):
            await get_zone_geometry(ErrorClient(tools.env.module))

    @pytest.mark.parametrize("format", ["json", "cos"])
    async def test_default_scene_plan_bytes_do_not_use_the_helper(self, tools, monkeypatch, format):
        tools.env.scene.add_mesh("GEO_shelf_a", t=(10, 0, 0))
        tools.env.scene.add_mesh("GEO_door_a", t=(0, 0, 10))
        expected = await tools.fns["scene_plan"](format=format)

        def should_not_run():
            raise AssertionError("scene_plan's default path must not read zone geometry")

        monkeypatch.setattr(tools.env.module, "get_zone_geometry", should_not_run)
        actual = await tools.fns["scene_plan"](format=format)

        assert actual.encode("utf-8") == expected.encode("utf-8")
        assert "get_zone_geometry" not in tools.client.calls[-1]
        assert "scene_plan" in tools.client.calls[-1]


# ------------------------------------------------------------
# Issue #217: opt-in recommend_assets on scene_plan
# ------------------------------------------------------------


class TestRecommendAssets:
    """The opt-in recommendation pass: JSON and CoS gain a recommendations
    section only when asked, search/geometry failures never break the plan,
    and the default path stays byte-identical and offline."""

    FURNITURE_GEOMETRY = {
        "unit": "cm",
        "up_axis": "y",
        "zones": [
            {
                "name": "furniture",
                "bbox_min": [0, 0, 0],
                "bbox_max": [320, 260, 250],
                "size": [320, 260, 250],
                "object_count": 3,
                "unmeasured_count": 0,
                "objects": [{"name": "|GEO_chair_a", "size": [50, 50, 90]}],
            }
        ],
        "unassigned_count": 0,
        "total_objects": 3,
    }

    @staticmethod
    def _fake_search(results, total=None):
        def search(query="", asset_type="models", limit=20):
            return {
                "results": results,
                "total_count": total if total is not None else len(results),
                "limit": limit,
                "query": query,
                "asset_type": asset_type,
                "source": "api.polyhaven.com",
            }

        return search

    @staticmethod
    def _chair_hit(asset_id="chair_henry"):
        return {
            "id": asset_id,
            "name": "Henry Chair",
            "categories": ["furniture"],
            "tags": ["chair"],
            "dimensions": [0.55, 0.6, 0.95],
            "polycount": 1200,
        }

    async def test_enabled_json_attaches_recommendations_and_keeps_the_plan(
        self, tools, monkeypatch
    ):
        monkeypatch.setattr(
            tools.env.module, "get_zone_geometry", lambda: dict(self.FURNITURE_GEOMETRY)
        )
        monkeypatch.setattr(
            "maya_mcp_server.polyhaven.search_assets",
            self._fake_search([self._chair_hit()]),
        )

        out = await tools.fns["scene_plan"](format="json", recommend_assets=True)
        res = json.loads(out)
        recs = res["recommendations"]
        assert recs["status"] == "ok"
        assert recs["provider"] == "poly_haven"
        assert recs["unit"] == "m"
        assert recs["policy"]["mode"] == "zone_envelope"
        assert recs["policy"]["geometry"] == "world_aabb"
        assert recs["policy"]["clearance_verified"] is False
        assert recs["truncation"] == {"search": False, "output": False, "budget": False}
        zone = recs["zones"][0]
        assert zone["zone"] == "furniture"
        assert zone["target"]["size_m"] == [3.2, 2.6, 2.5]
        assert zone["target"]["measurement"] == "complete"
        assert zone["queries"] == [
            {"query": q, "searched": True, "total_matches": 1}
            for q in ("chair", "table", "sofa", "bench")
        ]
        cand = zone["candidates"][0]
        assert cand["asset_id"] == "chair_henry"
        assert cand["dimensions_m"] == [0.55, 0.6, 0.95]
        assert cand["matched_queries"] == [{"query": "chair", "rank": 1}]
        assert cand["size_status"] == "pass"
        assert zone["eligible_count"] == 1
        # the plan itself is untouched
        for key in (
            "overall_health",
            "grade",
            "organization_status",
            "zone_analysis",
            "action_plan",
        ):
            assert key in res

    async def test_enabled_cos_appends_the_recommend_block(self, tools, monkeypatch):
        monkeypatch.setattr(
            tools.env.module, "get_zone_geometry", lambda: dict(self.FURNITURE_GEOMETRY)
        )
        monkeypatch.setattr(
            "maya_mcp_server.polyhaven.search_assets",
            self._fake_search([self._chair_hit()]),
        )

        out = await tools.fns["scene_plan"](format="cos", recommend_assets=True)
        assert out.startswith("SCENE_PLAN[")
        assert "  RECOMMEND: status=ok provider=poly_haven unit=m" in out
        assert (
            "furniture: target=zone_bbox 3.2x2.6x2.5m meas=complete "
            "queries=chair,table,sofa,bench (1 eligible, 0 unverified)" in out
        )
        assert "1. chair_henry rank=1 via=[chair@1] 0.55x0.6x0.95m fits_zone_envelope" in out
        assert "truncation: search=n output=n budget=n errors=0" in out

    async def test_search_failure_reports_offline_and_keeps_the_plan(self, tools, monkeypatch):
        from maya_mcp_server.polyhaven import AssetError

        monkeypatch.setattr(
            tools.env.module, "get_zone_geometry", lambda: dict(self.FURNITURE_GEOMETRY)
        )

        def boom(query="", asset_type="models", limit=20):
            raise AssetError("network_unavailable", "cannot reach api.polyhaven.com")

        monkeypatch.setattr("maya_mcp_server.polyhaven.search_assets", boom)

        out = await tools.fns["scene_plan"](format="json", recommend_assets=True)
        res = json.loads(out)
        assert res["recommendations"]["status"] == "offline"
        assert res["recommendations"]["zones"][0]["skip_reason"] == "search_failed"
        assert res["recommendations"]["errors"][0]["code"] == "network_unavailable"
        assert "zone_analysis" in res and "action_plan" in res

        out = await tools.fns["scene_plan"](format="cos", recommend_assets=True)
        assert "RECOMMEND: status=offline" in out
        assert "errors=4 (network_unavailable)" in out

    async def test_seven_zones_dedup_word_filter_and_cos_through_scene_plan(
        self, tools, monkeypatch
    ):
        # Populate Maya fake scene with all 7 built-in zones (using real get_zone_geometry).
        # Multi-object active zones fall back to zone_bbox without an explicit target.
        tools.env.scene.add_mesh("GEO_wall_main", bbox_min=(0, 0, 0), bbox_max=(1000, 300, 1000))
        tools.env.scene.add_mesh("GEO_door_front", bbox_min=(0, 0, 0), bbox_max=(150, 250, 50))
        tools.env.scene.add_mesh("GEO_door_side", bbox_min=(0, 0, 0), bbox_max=(150, 250, 50))
        tools.env.scene.add_mesh("GEO_shelf_a", bbox_min=(0, 0, 0), bbox_max=(200, 200, 80))
        tools.env.scene.add_mesh("GEO_shelf_b", bbox_min=(0, 0, 0), bbox_max=(200, 200, 80))
        tools.env.scene.add_mesh("GEO_mascot_hero", bbox_min=(0, 0, 0), bbox_max=(100, 150, 100))
        tools.env.scene.add_mesh("GEO_chair_main", bbox_min=(0, 0, 0), bbox_max=(300, 200, 300))
        tools.env.scene.add_mesh("GEO_chair_side", bbox_min=(0, 0, 0), bbox_max=(300, 200, 300))
        tools.env.scene.add_mesh("GEO_lamp_main", bbox_min=(0, 0, 0), bbox_max=(100, 200, 100))
        tools.env.scene.add_mesh("GEO_lamp_side", bbox_min=(0, 0, 0), bbox_max=(100, 200, 100))
        tools.env.scene.add_mesh("GEO_path_aisle", bbox_min=(0, 0, 0), bbox_max=(500, 10, 200))

        seen_queries: list[str] = []

        def fake_search(query="", asset_type="models", limit=20):
            seen_queries.append(query)
            if query == "sign":
                hits = [
                    {
                        "id": "design_book",
                        "name": "Design Book",
                        "categories": ["books"],
                        "tags": ["design"],
                        "dimensions": [0.3, 0.2, 0.1],
                        "polycount": 50,
                    },
                    {
                        "id": "street_sign_01",
                        "name": "Street Sign",
                        "categories": ["props"],
                        "tags": ["sign"],
                        "dimensions": [0.4, 1.2, 0.2],
                        "polycount": 300,
                    },
                ]
            elif query in ("lamp", "light"):
                hits = [
                    {
                        "id": "shared_pendant_lamp",
                        "name": "Shared Pendant Lamp",
                        "categories": ["lighting"],
                        "tags": ["lamp", "light"],
                        "dimensions": [0.4, 0.5, 0.4],
                        "polycount": 800,
                    }
                ]
            else:
                hits = [
                    {
                        "id": f"{query}_asset",
                        "name": f"{query.title()} Asset",
                        "categories": [query],
                        "tags": [query],
                        "dimensions": [0.5, 0.5, 0.5],
                        "polycount": 400,
                    }
                ]
            return {
                "results": hits,
                "total_count": len(hits),
                "limit": limit,
                "query": query,
                "asset_type": asset_type,
                "source": "api.polyhaven.com",
            }

        monkeypatch.setattr("maya_mcp_server.polyhaven.search_assets", fake_search)

        res = json.loads(await tools.fns["scene_plan"](format="json", recommend_assets=True))
        recs = res["recommendations"]
        assert recs["status"] == "ok"
        assert seen_queries == [
            "door",
            "sign",
            "shelf",
            "counter",
            "showcase",
            "podium",
            "chair",
            "table",
            "sofa",
            "bench",
            "lamp",
            "light",
        ]
        by_zone = {z["zone"]: z for z in recs["zones"]}
        assert list(by_zone) == [
            "shell",
            "entrance",
            "display",
            "ip_core",
            "furniture",
            "lighting",
            "path",
        ]
        for disabled in ("shell", "ip_core", "path"):
            assert by_zone[disabled]["status"] == "skipped"
            assert by_zone[disabled]["skip_reason"] == "recommendations_disabled"
            assert by_zone[disabled]["candidates"] == []

        entrance_ids = [c["asset_id"] for c in by_zone["entrance"]["candidates"]]
        assert "design_book" not in entrance_ids
        assert "street_sign_01" in entrance_ids

        # Display had 4 queries -> 4 eligible hits capped to 3 with output truncation.
        assert by_zone["display"]["eligible_count"] == 3
        assert recs["truncation"]["output"] is True

        # Lighting lamp+light both hit shared_pendant_lamp -> deduped to 1 entry.
        lighting_cands = by_zone["lighting"]["candidates"]
        assert len(lighting_cands) == 1
        assert lighting_cands[0]["asset_id"] == "shared_pendant_lamp"
        assert lighting_cands[0]["matched_queries"] == [
            {"query": "lamp", "rank": 1},
            {"query": "light", "rank": 1},
        ]

        cos = await tools.fns["scene_plan"](format="cos", recommend_assets=True)
        assert "shell: skipped (recommendations_disabled)" in cos
        assert "entrance: target=zone_bbox" in cos
        assert "display: target=zone_bbox" in cos
        assert "lighting: target=zone_bbox" in cos
        assert "via=[lamp@1,light@1]" in cos

    async def test_geometry_error_gives_partial_with_the_plan_intact(self, tools, monkeypatch):
        monkeypatch.setattr(
            tools.env.module,
            "get_zone_geometry",
            lambda: {"error": {"code": "query_failed", "message": "bbox unreadable"}},
        )

        out = await tools.fns["scene_plan"](format="json", recommend_assets=True)
        res = json.loads(out)
        assert res["recommendations"]["status"] == "partial"
        assert res["recommendations"]["zones"] == []
        assert res["recommendations"]["errors"][0]["scope"] == "zone_geometry"
        assert "zone_analysis" in res

    async def test_geometry_transport_failure_is_isolated(self, tools, monkeypatch):
        def kaboom():
            raise RuntimeError("session gone")

        monkeypatch.setattr(tools.env.module, "get_zone_geometry", kaboom)

        out = await tools.fns["scene_plan"](format="json", recommend_assets=True)
        res = json.loads(out)
        assert res["recommendations"]["status"] == "partial"
        assert res["recommendations"]["errors"][0]["code"] == "query_failed"
        assert "zone_analysis" in res

    async def test_default_call_never_searches_and_omits_the_section(self, tools, monkeypatch):
        tools.env.scene.add_mesh("GEO_chair_a", t=(0, 0, 0))

        def no_search(query="", asset_type="models", limit=20):
            raise AssertionError("search must not run with recommend_assets=False")

        monkeypatch.setattr("maya_mcp_server.polyhaven.search_assets", no_search)

        res = json.loads(await tools.fns["scene_plan"](format="json"))
        assert "recommendations" not in res
        assert "RECOMMEND" not in await tools.fns["scene_plan"](format="cos")


# ------------------------------------------------------------
# Issue #219: target identification and three-axis sizing end-to-end
# ------------------------------------------------------------


class TestRecommendAssetsTargetAndSizing:
    """End-to-end scene_plan + fake Maya zone geometry + target sizing (#219)."""

    @staticmethod
    def _build_duplicate_chairs(scene):
        left = scene.add_group("GRP_left")
        right = scene.add_transform("GRP_right", t=(300, 0, 0))
        c_left = scene.add_node("GEO_chair", "transform", parent=left, exists_ok=True)
        c_right = scene.add_node("GEO_chair", "transform", parent=right, exists_ok=True)
        # 0.6 x 0.8 x 0.6 m vs 1.8 x 0.9 x 0.9 m (in cm)
        scene.add_shape("GEO_chairShape_l", "mesh", c_left, bbox=((0, 0, 0), (60, 80, 60)))
        scene.add_shape("GEO_chairShape_r", "mesh", c_right, bbox=((0, 0, 0), (180, 90, 90)))

    @staticmethod
    def _chair(asset_id, dims, name="Chair"):
        return {
            "id": asset_id,
            "name": name,
            "categories": ["furniture"],
            "tags": ["chair"],
            "dimensions": dims,
            "polycount": 800,
        }

    async def test_dag_path_disambiguates_and_short_name_ambiguity_falls_back(
        self, tools, monkeypatch
    ):
        self._build_duplicate_chairs(tools.env.scene)
        hits = [
            self._chair("chair_fit", [0.6, 0.8, 0.6]),
            self._chair("chair_big", [1.8, 0.9, 0.9]),
            self._chair("chair_tiny", [0.1, 0.1, 0.1]),
        ]
        sent_calls = []

        def fake_search(query="", asset_type="models", limit=20):
            sent_calls.append({"query": query, "asset_type": asset_type, "limit": limit})
            return {"results": hits, "total_count": len(hits), "limit": limit}

        monkeypatch.setattr("maya_mcp_server.polyhaven.search_assets", fake_search)

        # Explicit full DAG path picks the 0.6x0.8x0.6 chair only (0.5x-1.5x).
        out = await tools.fns["scene_plan"](
            objective="replace |GRP_left|GEO_chair",
            format="json",
            recommend_assets=True,
        )
        res = json.loads(out)
        zone = res["recommendations"]["zones"][0]
        assert zone["target"]["source"] == "dag_path"
        assert zone["target"]["name"] == "|GRP_left|GEO_chair"
        assert zone["target"]["size_m"] == [0.6, 0.8, 0.6]
        assert [c["asset_id"] for c in zone["candidates"]] == ["chair_fit"]
        assert sent_calls == [
            {"query": q, "asset_type": "models", "limit": 20}
            for q in ("chair", "table", "sofa", "bench")
        ]

        # Ambiguous short name falls back to zone_bbox (upper-limit only: tiny passes).
        out_amb = await tools.fns["scene_plan"](
            objective="replace GEO_chair",
            format="json",
            recommend_assets=True,
        )
        zone_amb = json.loads(out_amb)["recommendations"]["zones"][0]
        assert zone_amb["target"]["source"] == "zone_bbox"
        assert zone_amb["target"]["fallback_reason"] == "ambiguous_short_name"
        assert zone_amb["target"]["ambiguous_matches"] == [
            "|GRP_left|GEO_chair",
            "|GRP_right|GEO_chair",
        ]
        assert [c["asset_id"] for c in zone_amb["candidates"]] == [
            "chair_big",
            "chair_fit",
            "chair_tiny",
        ]

        cos_amb = await tools.fns["scene_plan"](
            objective="replace GEO_chair",
            format="cos",
            recommend_assets=True,
        )
        assert "fallback=ambiguous_short_name(|GRP_left|GEO_chair,|GRP_right|GEO_chair)" in cos_amb

    async def test_unique_object_rotated_world_aabb_and_linear_units(self, tools, monkeypatch):
        import math

        tools.env.scene.linear_unit = "m"
        parent = tools.env.scene.add_transform("GRP_rot", t=(5, 0, 0))
        parent.r = [0, 45, 0]
        # 2m x 1m x 1m rotated 45 deg around Y -> world AABB ~ [2.121, 1.0, 2.121] m
        tools.env.scene.add_mesh(
            "GEO_chair_rot",
            bbox_min=(0, 0, 0),
            bbox_max=(2, 1, 1),
            parent=parent,
        )
        side = round(math.sqrt(2) + math.sqrt(2) / 2, 3)
        hits = [
            self._chair("chair_rot_fit", [2.1, 1.0, 2.1]),
            self._chair("chair_too_small", [0.5, 0.5, 0.5]),
        ]
        monkeypatch.setattr(
            "maya_mcp_server.polyhaven.search_assets",
            TestRecommendAssets._fake_search(hits),
        )

        res = json.loads(await tools.fns["scene_plan"](format="json", recommend_assets=True))
        recs = res["recommendations"]
        assert recs["policy"]["geometry"] == "world_aabb"
        assert recs["policy"]["clearance_verified"] is False
        assert recs["policy"]["collision_verified"] is False
        zone = recs["zones"][0]
        assert zone["target"]["source"] == "unique_zone_object"
        assert zone["target"]["size_m"] == [side, 1.0, side]
        assert [c["asset_id"] for c in zone["candidates"]] == ["chair_rot_fit"]

    async def test_unmeasurable_and_partial_zones_with_unverified_models(self, tools, monkeypatch):
        # Unmeasurable furniture zone skips search completely.
        tools.env.scene.add_group("GRP_chair_empty")
        calls = []

        def no_search(query="", asset_type="models", limit=20):
            calls.append(query)
            return {"results": [], "total_count": 0, "limit": limit}

        monkeypatch.setattr("maya_mcp_server.polyhaven.search_assets", no_search)
        res_skip = json.loads(await tools.fns["scene_plan"](format="json", recommend_assets=True))
        assert calls == []
        assert res_skip["recommendations"]["zones"][0]["status"] == "skipped"
        assert res_skip["recommendations"]["zones"][0]["skip_reason"] == "unmeasurable_target"

        # Adding one measurable chair makes the zone partial and reports unverified models.
        tools.env.scene.add_mesh(
            "GEO_chair_a", bbox_min=(0, 0, 0), bbox_max=(60, 80, 60), t=(0, 0, 0)
        )
        hits = [
            self._chair("chair_ok", [0.6, 0.8, 0.6]),
            self._chair("chair_missing", None),
            self._chair("chair_zero", [0, 0, 0]),
        ]
        monkeypatch.setattr(
            "maya_mcp_server.polyhaven.search_assets",
            TestRecommendAssets._fake_search(hits),
        )
        res_part = json.loads(await tools.fns["scene_plan"](format="json", recommend_assets=True))
        zone = res_part["recommendations"]["zones"][0]
        assert zone["target"]["measurement_complete"] is False
        assert zone["eligible_count"] == 1
        assert zone["unverified_count"] == 2
        assert [c["asset_id"] for c in zone["unverified_candidates"]] == [
            "chair_missing",
            "chair_zero",
        ]

    @pytest.mark.parametrize("format", ["json", "cos"])
    async def test_default_off_with_objective_stays_byte_identical(
        self, tools, monkeypatch, format
    ):
        self._build_duplicate_chairs(tools.env.scene)
        expected = await tools.fns["scene_plan"](
            objective="replace |GRP_left|GEO_chair", format=format
        )

        def fail_search(*args, **kwargs):
            raise AssertionError("search must not run when recommend_assets=False")

        monkeypatch.setattr("maya_mcp_server.polyhaven.search_assets", fail_search)
        actual = await tools.fns["scene_plan"](
            objective="replace |GRP_left|GEO_chair",
            format=format,
            recommend_assets=False,
        )
        assert actual.encode("utf-8") == expected.encode("utf-8")

    async def test_mixed_scene_combines_object_tolerance_and_zone_envelope_across_zones(
        self, tools, monkeypatch
    ):
        self._build_duplicate_chairs(tools.env.scene)
        tools.env.scene.add_mesh("GEO_wall_main", bbox_min=(0, 0, 0), bbox_max=(800, 300, 800))
        tools.env.scene.add_mesh("GEO_lamp_a", bbox_min=(0, 0, 0), bbox_max=(80, 180, 80))
        tools.env.scene.add_mesh(
            "GEO_lamp_b", bbox_min=(0, 0, 0), bbox_max=(120, 200, 120), t=(200, 0, 0)
        )

        def fake_search(query="", asset_type="models", limit=20):
            if query in ("lamp", "light"):
                hits = [
                    {
                        "id": "pendant_lamp",
                        "name": "Pendant Lamp",
                        "categories": ["lighting"],
                        "tags": ["lamp", "light"],
                        "dimensions": [0.3, 0.4, 0.3],
                        "polycount": 600,
                    }
                ]
            elif query == "chair":
                hits = [self._chair("chair_fit", [0.6, 0.8, 0.6])]
            else:
                hits = []
            return {"results": hits, "total_count": len(hits), "limit": limit}

        monkeypatch.setattr("maya_mcp_server.polyhaven.search_assets", fake_search)

        out = await tools.fns["scene_plan"](
            objective="replace |GRP_left|GEO_chair",
            format="json",
            recommend_assets=True,
        )
        recs = json.loads(out)["recommendations"]
        assert recs["policy"]["mode"] == "mixed"
        assert recs["policy"]["upper_limit_only"] is False
        assert recs["policy"]["tolerance_band"] == [0.5, 1.5]
        by_zone = {z["zone"]: z for z in recs["zones"]}
        assert by_zone["shell"]["skip_reason"] == "recommendations_disabled"
        assert by_zone["furniture"]["target"]["source"] == "dag_path"
        assert by_zone["furniture"]["candidates"][0]["reason_code"] == "fits_target_three_axis"
        assert by_zone["lighting"]["target"]["source"] == "zone_bbox"
        assert by_zone["lighting"]["target"]["fallback_reason"] == "multiple_zone_objects"
        assert by_zone["lighting"]["candidates"][0]["reason_code"] == "fits_zone_envelope"
        assert by_zone["lighting"]["candidates"][0]["matched_queries"] == [
            {"query": "lamp", "rank": 1},
            {"query": "light", "rank": 1},
        ]

        cos = await tools.fns["scene_plan"](
            objective="replace |GRP_left|GEO_chair",
            format="cos",
            recommend_assets=True,
        )
        assert "policy=mixed(world_aabb 0.5-1.5x/upper-limit)" in cos
        assert "furniture: target=dag_path(|GRP_left|GEO_chair)" in cos
        assert "lighting: target=zone_bbox" in cos
        assert "fallback=multiple_zone_objects" in cos


# ------------------------------------------------------------
# Issue #206: the unsaved-changes flag is reported, read fresh, never cached
# ------------------------------------------------------------


class TestSceneModifiedFlag:
    """Tool-facing contract only: the field exists, its value is right, and
    the object-list cache can never hide a later change."""

    async def test_json_flag_is_false_on_a_clean_scene(self, tools):
        tools.env.scene.add_mesh("GEO_a")
        tools.env.scene.modified = False  # a save would clear it in real Maya

        out = await tools.fns["scene_snapshot"](format="json")

        assert json.loads(out)["scene_modified"] is False

    async def test_json_flag_is_true_after_the_scene_changes(self, tools):
        tools.env.scene.modified = False
        await tools.fns["scene_snapshot"](format="json")
        tools.env.scene.modified = True

        out = await tools.fns["scene_snapshot"](format="json")

        assert json.loads(out)["scene_modified"] is True

    async def test_cos_header_writes_the_flag_in_both_states(self, tools):
        tools.env.scene.modified = False
        clean = await tools.fns["scene_snapshot"]()
        tools.env.scene.modified = True
        changed = await tools.fns["scene_snapshot"]()

        assert clean.splitlines()[0].endswith("MODIFIED=n")
        assert changed.splitlines()[0].endswith("MODIFIED=y")

    async def test_cached_object_list_does_not_hide_a_later_change(self, tools):
        tools.env.scene.add_mesh("GEO_a")
        tools.env.scene.modified = False
        await tools.fns["scene_snapshot"](format="json")  # object list now cached

        tools.env.scene.modified = True
        out = await tools.fns["scene_snapshot"](format="json")

        assert json.loads(out)["scene_modified"] is True
        graph_calls = [code for code in tools.client.calls if "get_scene_graph" in code]
        assert len(graph_calls) == 1, "the object list should still come from the cache"

    async def test_an_unreadable_flag_is_not_reported_as_clean(self, tools, monkeypatch):
        def unreadable():
            raise RuntimeError("flag unreadable")

        monkeypatch.setattr(tools.env.module, "get_scene_modified", unreadable)

        with pytest.raises(RuntimeError, match="flag unreadable"):
            await tools.fns["scene_snapshot"](format="json")

    async def test_a_payload_without_the_flag_is_not_reported_as_clean(self, tools, monkeypatch):
        monkeypatch.setattr(tools.env.module, "get_scene_modified", lambda: {})

        with pytest.raises(RuntimeError, match="unsaved-changes flag"):
            await tools.fns["scene_snapshot"](format="json")


class TestRollbackSceneModifiedBefore:
    """scene_rollback reports the state from before the scene was switched,
    and the copy written just before the switch is still a real file."""

    async def _scene_with_one_checkpoint(self, tools, tmp_path):
        """Real .ma on disk, plus a scene that has moved on since."""
        tools.env.scene.scene_path = str(tmp_path / "shot.ma")
        tools.env.scene.add_mesh("GEO_a")
        saved = json.loads(await tools.fns["scene_checkpoint"](name="v1"))
        assert "error" not in saved, saved

    async def test_clean_scene_reports_false(self, tools, tmp_path):
        await self._scene_with_one_checkpoint(tools, tmp_path)
        tools.env.scene.modified = False  # what a save would leave behind

        res = json.loads(await tools.fns["scene_rollback"](filename="cp_v1.ma"))

        assert res["success"] is True, res
        assert res["scene_modified_before"] is False

    async def test_changed_scene_reports_true_and_writes_the_copy(self, tools, tmp_path):
        await self._scene_with_one_checkpoint(tools, tmp_path)
        tools.env.scene.add_mesh("GEO_wip")

        res = json.loads(await tools.fns["scene_rollback"](filename="cp_v1.ma"))

        assert res["success"] is True, res
        assert res["scene_modified_before"] is True
        assert os.path.exists(res["safety_snapshot"]), (
            f"the copy taken before the switch must be on disk: {res['safety_snapshot']}"
        )

    async def test_the_object_cache_never_hides_a_later_change(self, tools, tmp_path):
        await self._scene_with_one_checkpoint(tools, tmp_path)
        tools.env.scene.modified = False
        await tools.fns["scene_snapshot"](format="json")  # fills the scene caches

        tools.env.scene.modified = True
        res = json.loads(await tools.fns["scene_rollback"](filename="cp_v1.ma"))

        assert res["scene_modified_before"] is True

    async def test_discard_flag_does_not_move_the_reported_state(self, tools, tmp_path):
        await self._scene_with_one_checkpoint(tools, tmp_path)
        tools.env.scene.add_mesh("GEO_wip")

        res = json.loads(
            await tools.fns["scene_rollback"](filename="cp_v1.ma", discard_current_state=True)
        )

        assert res["success"] is True, res
        assert res["scene_modified_before"] is True
        assert res["safety_snapshot"] != "skipped_by_user", (
            "discard_current_state keeps its old meaning: the save still happens"
        )
        assert "warning" in res

    async def test_an_unreadable_flag_stops_before_anything_opens(self, tools, monkeypatch):
        opened = []
        monkeypatch.setattr(
            tools.env.module,
            "rollback_to_checkpoint",
            lambda *args, **kwargs: opened.append(args) or {"success": True},
        )
        monkeypatch.setattr(tools.env.module, "get_scene_modified", lambda: {})

        with pytest.raises(RuntimeError, match="unsaved-changes flag"):
            await tools.fns["scene_rollback"](filename="cp_x.ma")

        assert opened == [], "a flag nobody could read must not be guessed at, and must stop first"
