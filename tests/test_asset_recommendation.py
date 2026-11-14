"""Unit tests for the host-side recommendation pass (#217, T1).

The module is pure: zone geometry and search results are plain dicts and
the search callable is a fake, so nothing here touches the network or
Maya. Tool-layer behavior (JSON/CoS output, byte-identical default) is
covered in test_scene_tools_json.py.
"""

from __future__ import annotations

import pytest

from maya_mcp_server.asset_recommendation import (
    SEARCH_ASSET_TYPE,
    SEARCH_LIMIT,
    ZONE_SEARCH_QUERIES,
    format_recommend_cos,
    gather_recommendations,
)
from maya_mcp_server.polyhaven import AssetError


# ------------------------------------------------------------
# fixtures: fake geometry and a recording search callable
# ------------------------------------------------------------


def make_geometry(unit: str = "cm", zones: list | None = None) -> dict:
    return {
        "unit": unit,
        "up_axis": "y",
        "zones": zones if zones is not None else [],
        "unassigned_count": 0,
        "total_objects": 0,
    }


FURNITURE_ZONE = {
    "name": "furniture",
    "bbox_min": [0, 0, 0],
    "bbox_max": [320, 260, 250],
    "size": [320, 260, 250],  # cm -> 3.2 x 2.6 x 2.5 m
    "object_count": 3,
    "unmeasured_count": 0,
    "objects": [{"name": "|GEO_chair_a", "size": [50, 50, 90]}],
}


def chair_hit(asset_id: str = "chair_henry", dims: list | None = [0.55, 0.6, 0.95]) -> dict:
    return {
        "id": asset_id,
        "name": asset_id.replace("_", " ").title(),
        "categories": ["furniture"],
        "tags": ["chair"],
        "dimensions": dims,
        "polycount": 1200,
    }


def make_search(results: list, total: int | None = None, error: Exception | None = None):
    calls: list[dict] = []

    def search(query: str = "", asset_type: str = "models", limit: int = 20) -> dict:
        calls.append({"query": query, "asset_type": asset_type, "limit": limit})
        if error is not None:
            raise error
        return {
            "results": results,
            "total_count": total if total is not None else len(results),
            "limit": limit,
            "query": query,
            "asset_type": asset_type,
            "source": "api.polyhaven.com",
        }

    return search, calls


def gather(
    geometry,
    results: list | None = None,
    total: int | None = None,
    error: Exception | None = None,
):
    search, calls = make_search(
        results if results is not None else [chair_hit()], total=total, error=error
    )
    recs = gather_recommendations(geometry, search)
    return recs, calls


# ------------------------------------------------------------
# the T1 mapping table: furniture only, one query
# ------------------------------------------------------------


class TestZoneTable:
    def test_t1_maps_only_the_furniture_zone_to_chair(self):
        assert ZONE_SEARCH_QUERIES == {"furniture": ["chair"]}

    def test_a_scene_without_the_zone_is_never_searched(self):
        recs, calls = gather(make_geometry())
        assert calls == []
        assert recs["zones"] == []
        assert recs["status"] == "empty"

    def test_non_table_zones_are_ignored(self):
        display = dict(FURNITURE_ZONE, name="display")
        recs, calls = gather(make_geometry(zones=[display]))
        assert calls == []
        assert recs["zones"] == []


# ------------------------------------------------------------
# search contract and privacy boundary at the seam
# ------------------------------------------------------------


class TestSearchContract:
    def test_search_gets_the_t1_query_and_limit_only(self):
        _, calls = gather(make_geometry(zones=[FURNITURE_ZONE]))
        assert calls == [{"query": "chair", "asset_type": SEARCH_ASSET_TYPE, "limit": SEARCH_LIMIT}]
        # no scene data ever crosses the seam: no objective, no DAG path,
        # no bbox — only the query word and the fixed index parameters
        sent = "".join(str(v) for v in calls[0].values())
        assert "furniture" not in sent and "GEO_" not in sent and "3.2" not in sent


# ------------------------------------------------------------
# units and the zone envelope screen
# ------------------------------------------------------------


class TestUnitsAndScreening:
    def test_cm_zone_converts_to_metres_and_passes_a_fitting_chair(self):
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]))
        assert recs["status"] == "ok"
        zone = recs["zones"][0]
        assert zone["target"]["size_m"] == [3.2, 2.6, 2.5]
        assert zone["target"]["measurement"] == "complete"
        assert zone["target"]["geometry"] == "world_aabb"
        assert zone["target"]["source"] == "zone_bbox"
        cand = zone["candidates"][0]
        assert cand["asset_id"] == "chair_henry"
        assert cand["dimensions_m"] == [0.55, 0.6, 0.95]
        assert cand["polycount"] == 1200
        assert cand["matched_queries"] == [{"query": "chair", "rank": 1}]
        assert cand["best_source_rank"] == 1
        assert cand["size_status"] == "pass"
        assert cand["reason_code"] == "fits_zone_envelope"
        assert "upper limit" in cand["match_reason"]
        assert zone["eligible_count"] == 1
        assert zone["unverified_count"] == 0

    def test_mm_and_ft_zones_convert_with_their_own_factor(self):
        mm_zone = {
            "name": "furniture",
            "bbox_min": [0, 0, 0],
            "bbox_max": [3200, 2600, 2500],
            "size": [3200, 2600, 2500],
            "object_count": 1,
            "unmeasured_count": 0,
            "objects": [],
        }
        recs, _ = gather(make_geometry(unit="mm", zones=[mm_zone]))
        assert recs["zones"][0]["target"]["size_m"] == [3.2, 2.6, 2.5]

        ft_zone = dict(FURNITURE_ZONE, size=[10.5, 8.5, 8.2], bbox_max=[10.5, 8.5, 8.2])
        recs, _ = gather(make_geometry(unit="ft", zones=[ft_zone]))
        assert recs["zones"][0]["target"]["size_m"] == [3.2, 2.591, 2.499]

    def test_a_model_that_cannot_fit_is_excluded(self):
        too_long = chair_hit("shelf_jumbo", dims=[4.0, 1.0, 1.0])
        wrong_middle_axis = chair_hit("counter_wide", dims=[3.0, 2.7, 1.0])
        recs, _ = gather(
            make_geometry(zones=[FURNITURE_ZONE]), results=[too_long, wrong_middle_axis]
        )
        assert recs["zones"][0]["candidates"] == []
        assert recs["status"] == "empty"

    def test_missing_and_zero_dimensions_go_to_unverified(self):
        no_dims = chair_hit("chair_mystery", dims=None)
        zero_dims = chair_hit("chair_flat", dims=[0, 0, 0])
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]), results=[no_dims, zero_dims])
        zone = recs["zones"][0]
        assert zone["candidates"] == []
        unverified = zone["unverified_candidates"]
        assert [c["reason_code"] for c in unverified] == [
            "missing_dimensions",
            "invalid_dimensions",
        ]
        assert all(c["size_status"] == "unverified" for c in unverified)
        assert recs["status"] == "empty"

    def test_a_hit_without_the_query_word_is_dropped(self):
        unrelated = {
            "id": "design_book",
            "name": "Design Book",
            "categories": ["books"],
            "tags": ["design"],
            "dimensions": [0.3, 0.2, 0.1],
            "polycount": 90,
        }
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]), results=[unrelated])
        assert recs["zones"][0]["candidates"] == []
        assert recs["zones"][0]["unverified_candidates"] == []


# ------------------------------------------------------------
# zone states that skip the search
# ------------------------------------------------------------


class TestSkippedZones:
    def test_unmeasurable_zone_is_skipped_without_searching(self):
        dead_zone = dict(FURNITURE_ZONE, size=None, bbox_min=None, bbox_max=None)
        recs, calls = gather(make_geometry(zones=[dead_zone]))
        assert calls == []
        zone = recs["zones"][0]
        assert zone["status"] == "skipped"
        assert zone["skip_reason"] == "unmeasurable_target"
        assert zone["target"]["measurement"] == "unmeasurable_target"
        assert zone["queries"] == [{"query": "chair", "searched": False, "total_matches": None}]
        assert recs["status"] == "empty"

    def test_partially_measured_zone_still_searches_but_flags_it(self):
        partial_zone = dict(FURNITURE_ZONE, unmeasured_count=1)
        recs, calls = gather(make_geometry(zones=[partial_zone]))
        assert len(calls) == 1
        assert recs["zones"][0]["target"]["measurement"] == "partial_zone_envelope"
        assert recs["zones"][0]["status"] == "ok"

    def test_unknown_unit_reports_partial_and_never_guesses(self):
        recs, calls = gather(make_geometry(unit="foom", zones=[FURNITURE_ZONE]))
        assert calls == []
        assert recs["status"] == "partial"
        assert recs["zones"] == []
        assert recs["errors"][0]["code"] == "unit_unknown"

    def test_geometry_error_payload_reports_partial(self):
        recs, calls = gather({"error": {"code": "query_failed", "message": "bbox unreadable"}})
        assert calls == []
        assert recs["status"] == "partial"
        assert recs["zones"] == []
        assert recs["errors"][0] == {
            "scope": "zone_geometry",
            "code": "query_failed",
            "message": "bbox unreadable",
        }


# ------------------------------------------------------------
# error isolation: a broken search never raises
# ------------------------------------------------------------


class TestSearchFailureIsolation:
    def test_network_failure_is_reported_not_raised(self):
        recs, _ = gather(
            make_geometry(zones=[FURNITURE_ZONE]),
            error=AssetError("network_unavailable", "cannot reach api.polyhaven.com"),
        )
        assert recs["status"] == "offline"
        zone = recs["zones"][0]
        assert zone["status"] == "skipped"
        assert zone["skip_reason"] == "search_failed"
        assert recs["errors"][0]["code"] == "network_unavailable"
        assert recs["errors"][0]["scope"] == "recommendations:furniture"

    def test_unexpected_search_failure_is_isolated_too(self):
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]), error=RuntimeError("kaboom"))
        assert recs["status"] == "offline"
        assert recs["errors"][0]["code"] == "search_failed"

    def test_bad_search_payload_is_a_structured_error(self):
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]), results="not-a-list")
        assert recs["status"] == "offline"
        assert recs["errors"][0]["code"] == "search_failed"


# ------------------------------------------------------------
# caps, truncation, and deterministic order
# ------------------------------------------------------------


class TestCapsAndOrder:
    def test_per_zone_cap_is_three_with_output_truncation(self):
        hits = [chair_hit(f"chair_{i:02d}") for i in range(5)]
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]), results=hits)
        zone = recs["zones"][0]
        assert len(zone["candidates"]) == 3
        assert zone["eligible_count"] == 3
        assert recs["truncation"]["output"] is True
        assert [c["best_source_rank"] for c in zone["candidates"]] == [1, 2, 3]

    def test_eligible_candidates_win_the_cap_over_unverified(self):
        hits = [
            chair_hit("chair_a", dims=[0.5, 0.5, 0.9]),
            chair_hit("chair_b", dims=[0.5, 0.5, 0.9]),
            chair_hit("chair_m1", dims=None),
            chair_hit("chair_m2", dims=None),
        ]
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]), results=hits)
        zone = recs["zones"][0]
        assert [c["asset_id"] for c in zone["candidates"]] == ["chair_a", "chair_b"]
        assert [c["asset_id"] for c in zone["unverified_candidates"]] == ["chair_m1"]
        assert zone["unverified_count"] == 1
        assert recs["truncation"]["output"] is True

    def test_early_unverified_hits_cannot_starve_a_fitting_model(self):
        """Regression (CodeRabbit, #231): without size status as the first
        sort key, three dimension-less hits ahead of a fitting model ate
        the whole cap and the zone reported empty."""
        hits = [
            chair_hit("chair_m1", dims=None),
            chair_hit("chair_m2", dims=None),
            chair_hit("chair_m3", dims=None),
            chair_hit("chair_good", dims=[0.5, 0.5, 0.9]),
        ]
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]), results=hits)
        zone = recs["zones"][0]
        assert [c["asset_id"] for c in zone["candidates"]] == ["chair_good"]
        assert [c["asset_id"] for c in zone["unverified_candidates"]] == [
            "chair_m1",
            "chair_m2",
        ]
        assert zone["status"] == "ok"
        assert recs["truncation"]["output"] is True

    def test_rounding_cannot_reject_a_fitting_model(self):
        """Regression (CodeRabbit, #231): screening against the rounded
        envelope rejected a model that fits by 0.3 mm on every axis."""
        zone = dict(
            FURNITURE_ZONE,
            size=[55.04, 60.04, 95.04],
            bbox_max=[55.04, 60.04, 95.04],
        )
        recs, _ = gather(
            make_geometry(zones=[zone]),
            results=[chair_hit("chair_edge", dims=[0.5503, 0.6003, 0.9503])],
        )
        zone_rec = recs["zones"][0]
        assert zone_rec["status"] == "ok"
        assert zone_rec["candidates"][0]["asset_id"] == "chair_edge"
        # display fields stay rounded like the Maya side reports them
        assert zone_rec["target"]["size_m"] == [0.55, 0.6, 0.95]

    def test_search_truncation_is_flagged_when_the_index_held_more(self):
        hits = [chair_hit(f"chair_{i:02d}") for i in range(SEARCH_LIMIT)]
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]), results=hits, total=35)
        assert recs["truncation"]["search"] is True
        assert recs["zones"][0]["queries"][0]["total_matches"] == 35

    def test_no_truncation_when_the_index_fit(self):
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]))
        assert recs["truncation"] == {"search": False, "output": False, "budget": False}

    def test_repeated_calls_give_identical_output(self):
        hits = [chair_hit(f"chair_{i:02d}") for i in range(4)]
        first, _ = gather(make_geometry(zones=[FURNITURE_ZONE]), results=hits)
        second, _ = gather(make_geometry(zones=[FURNITURE_ZONE]), results=hits)
        assert first == second

    def test_budget_truncation_is_reserved_for_t4(self):
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]))
        assert recs["truncation"]["budget"] is False


# ------------------------------------------------------------
# the top-level contract shape
# ------------------------------------------------------------


class TestContractShape:
    def test_top_level_keys_match_the_q15_shape(self):
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]))
        assert set(recs) == {
            "status",
            "provider",
            "unit",
            "policy",
            "truncation",
            "errors",
            "zones",
        }
        assert recs["provider"] == "poly_haven"
        assert recs["unit"] == "m"
        policy = recs["policy"]
        assert policy["mode"] == "zone_envelope"
        assert policy["geometry"] == "world_aabb"
        assert policy["upper_limit_only"] is True
        assert policy["clearance_verified"] is False
        assert policy["collision_verified"] is False

    def test_never_raises_on_garbage_geometry(self):
        for bad in (None, "nope", 42, {"zones": "not-a-list"}):
            recs = gather_recommendations(bad, lambda **kw: {"results": []})
            assert recs["status"] in ("partial", "empty")
            assert recs["zones"] == []


# ------------------------------------------------------------
# CoS block
# ------------------------------------------------------------


class TestRecommendCos:
    def test_ok_block_carries_status_target_candidates_and_truncation(self):
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]))
        block = format_recommend_cos(recs)
        assert "RECOMMEND: status=ok provider=poly_haven unit=m " in block
        assert "policy=zone_envelope(world_aabb upper-limit)" in block
        assert "furniture: target=zone_bbox 3.2x2.6x2.5m meas=complete" in block
        assert "chair: 1 eligible, 0 unverified" in block
        assert "1. chair_henry rank=1 0.55x0.6x0.95m fits_zone_envelope" in block
        assert "truncation: search=n output=n budget=n errors=0" in block

    def test_skipped_zone_names_the_reason(self):
        dead_zone = dict(FURNITURE_ZONE, size=None, bbox_min=None, bbox_max=None)
        recs, _ = gather(make_geometry(zones=[dead_zone]))
        block = format_recommend_cos(recs)
        assert "furniture: skipped (unmeasurable_target)" in block

    def test_offline_block_names_the_first_error_code(self):
        recs, _ = gather(
            make_geometry(zones=[FURNITURE_ZONE]),
            error=AssetError("network_unavailable", "cannot reach api.polyhaven.com"),
        )
        block = format_recommend_cos(recs)
        assert "RECOMMEND: status=offline" in block
        assert "truncation: search=n output=n budget=n errors=1 (network_unavailable)" in block

    def test_empty_scene_block_says_so(self):
        recs, _ = gather(make_geometry())
        block = format_recommend_cos(recs)
        assert "RECOMMEND: status=empty" in block
        assert "no furniture zone in this scene" in block

    def test_partial_block_lists_the_geometry_error(self):
        recs, _ = gather({"error": {"code": "query_failed", "message": "bbox unreadable"}})
        block = format_recommend_cos(recs)
        assert "RECOMMEND: status=partial" in block
        assert "error: zone_geometry query_failed" in block


@pytest.mark.parametrize(
    "unit, size, expected",
    [
        ("m", [3.2, 2.6, 2.5], [3.2, 2.6, 2.5]),
        ("cm", [320, 260, 250], [3.2, 2.6, 2.5]),
        ("mm", [3200, 2600, 2500], [3.2, 2.6, 2.5]),
        ("in", [126, 102.4, 98.4], [3.2, 2.601, 2.499]),
    ],
)
def test_unit_conversion_table(unit: str, size: list, expected: list):
    zone = dict(FURNITURE_ZONE, size=size, bbox_max=size)
    recs, _ = gather(make_geometry(unit=unit, zones=[zone]))
    assert recs["zones"][0]["target"]["size_m"] == expected
