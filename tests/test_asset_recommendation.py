"""Unit tests for the host-side recommendation pass (#217 T1, #218 T2).

The module is pure: zone geometry and search results are plain dicts and
the search callable is a fake, so nothing here touches the network or
Maya. Tool-layer behavior (JSON/CoS output, byte-identical default) is
covered in test_scene_tools_json.py.
"""

from __future__ import annotations

import pytest

from maya_mcp_server.asset_recommendation import (
    MAX_PER_SCENE,
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


def _search_response(
    results: list,
    *,
    query: str = "",
    asset_type: str = "models",
    limit: int = 20,
    total: int | None = None,
) -> dict:
    return {
        "results": results,
        "total_count": total if total is not None else len(results),
        "limit": limit,
        "query": query,
        "asset_type": asset_type,
        "source": "api.polyhaven.com",
    }


def make_search(results: list, total: int | None = None, error: Exception | None = None):
    calls: list[dict] = []

    def search(query: str = "", asset_type: str = "models", limit: int = 20) -> dict:
        calls.append({"query": query, "asset_type": asset_type, "limit": limit})
        if error is not None:
            raise error
        return _search_response(
            results, query=query, asset_type=asset_type, limit=limit, total=total
        )

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
# the 7-zone mapping table
# ------------------------------------------------------------


class TestZoneTable:
    def test_maps_all_seven_built_in_zones(self):
        assert ZONE_SEARCH_QUERIES == {
            "shell": (),
            "entrance": ("door", "sign"),
            "display": ("shelf", "counter", "showcase", "podium"),
            "ip_core": (),
            "furniture": ("chair", "table", "sofa", "bench"),
            "lighting": ("lamp", "light"),
            "path": (),
        }

    def test_a_scene_without_zones_is_never_searched(self):
        recs, calls = gather(make_geometry())
        assert calls == []
        assert recs["zones"] == []
        assert recs["status"] == "empty"

    def test_disabled_zones_never_search_and_produce_no_recommendations(self):
        disabled = [dict(FURNITURE_ZONE, name=n) for n in ("shell", "ip_core", "path")]
        recs, calls = gather(make_geometry(zones=disabled))
        assert calls == []
        assert recs["status"] == "empty"
        assert [z["zone"] for z in recs["zones"]] == ["shell", "ip_core", "path"]
        for zone_rec in recs["zones"]:
            assert zone_rec["status"] == "skipped"
            assert zone_rec["skip_reason"] == "recommendations_disabled"
            assert zone_rec["queries"] == []
            assert zone_rec["candidates"] == []
            assert zone_rec["unverified_candidates"] == []
            assert zone_rec["eligible_count"] == 0
            assert zone_rec["unverified_count"] == 0

    def test_unknown_zones_are_ignored(self):
        decor = dict(FURNITURE_ZONE, name="decor")
        recs, calls = gather(make_geometry(zones=[decor]))
        assert calls == []
        assert recs["zones"] == []

    def test_all_four_recommendable_zones_search_their_mapped_queries(self):
        zones = [
            dict(FURNITURE_ZONE, name=name)
            for name in ("shell", "entrance", "display", "ip_core", "furniture", "lighting", "path")
        ]

        def by_query(query: str = "", asset_type: str = "models", limit: int = 20) -> dict:
            hit = {
                "id": f"{query}_01",
                "name": f"{query.title()} 01",
                "categories": [query],
                "tags": [query],
                "dimensions": [0.5, 0.5, 0.5],
                "polycount": 500,
            }
            return _search_response([hit], query=query, asset_type=asset_type, limit=limit)

        calls: list[str] = []

        def recording(query: str = "", asset_type: str = "models", limit: int = 20) -> dict:
            calls.append(query)
            return by_query(query, asset_type, limit)

        recs = gather_recommendations(make_geometry(zones=zones), recording)
        assert calls == [
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
        assert recs["status"] == "ok"
        by_name = {z["zone"]: z for z in recs["zones"]}
        assert by_name["entrance"]["status"] == "ok"
        assert by_name["display"]["status"] == "ok"
        assert by_name["furniture"]["status"] == "ok"
        assert by_name["lighting"]["status"] == "ok"
        assert by_name["shell"]["skip_reason"] == "recommendations_disabled"
        assert by_name["ip_core"]["skip_reason"] == "recommendations_disabled"
        assert by_name["path"]["skip_reason"] == "recommendations_disabled"


# ------------------------------------------------------------
# search contract and privacy boundary at the seam
# ------------------------------------------------------------


class TestSearchContract:
    def test_search_gets_the_mapped_queries_and_limit_only(self):
        _, calls = gather(make_geometry(zones=[FURNITURE_ZONE]))
        assert calls == [
            {"query": q, "asset_type": SEARCH_ASSET_TYPE, "limit": SEARCH_LIMIT}
            for q in ("chair", "table", "sofa", "bench")
        ]
        # no scene data ever crosses the seam: no objective, no DAG path,
        # no bbox — only the query words and the fixed index parameters
        sent = "".join(str(v) for c in calls for v in c.values())
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

    @pytest.mark.parametrize(
        "zone_name, query, hit_id, hit_name, tags, categories, should_match",
        [
            # substring false positives must be rejected
            ("entrance", "sign", "design_poster", "Design Poster", ["design"], ["decor"], False),
            (
                "entrance",
                "sign",
                "designer_desk",
                "Signature Lamp",
                ["signature"],
                ["props"],
                False,
            ),
            (
                "entrance",
                "door",
                "outdoor_bench",
                "Outdoor Bench",
                ["outdoor", "indoor"],
                ["props"],
                False,
            ),
            (
                "furniture",
                "table",
                "portable_grill",
                "Comfortable Set",
                ["portable", "vegetable"],
                ["props"],
                False,
            ),
            ("lighting", "lamp", "bench_clamp", "Clamp Tool", ["clamp"], ["tools"], False),
            (
                "lighting",
                "light",
                "daylight_panel",
                "Lightweight Box",
                ["slight", "daylight"],
                ["props"],
                False,
            ),
            # normalized word hits (case, separators, camelCase, digit boundary, plurals, lighting)
            ("entrance", "sign", "StreetSign01", "Street Sign", [], ["props"], True),
            ("entrance", "door", "wooden_doors_02", "Wooden Doors", [], ["architecture"], True),
            ("display", "shelf", "wall_rack_01", "Wall Rack", ["shelves"], ["furniture"], True),
            ("display", "showcase", "glass_case_01", "Glass Showcases", [], ["furniture"], True),
            ("display", "counter", "bar_unit_01", "Bar Counters", [], ["furniture"], True),
            ("display", "podium", "award_stand_01", "Award Podiums", [], ["furniture"], True),
            ("furniture", "table", "oak_stand_01", "Oak Tables", [], ["furniture"], True),
            ("furniture", "sofa", "velvet_couch_01", "Velvet Sofas", [], ["furniture"], True),
            ("furniture", "bench", "park_seat_01", "Park Benches", [], ["furniture"], True),
            ("lighting", "lamp", "desk_fixture_01", "Desk Lamps", [], ["lighting"], True),
            ("lighting", "light", "brass_pendant", "Brass Pendant", [], ["lighting"], True),
        ],
    )
    def test_word_level_check_rejects_substring_false_positives(
        self, zone_name, query, hit_id, hit_name, tags, categories, should_match
    ):
        zone = dict(FURNITURE_ZONE, name=zone_name)
        hit = {
            "id": hit_id,
            "name": hit_name,
            "categories": categories,
            "tags": tags,
            "dimensions": [0.4, 0.4, 0.4],
            "polycount": 200,
        }

        def search_one(query: str = "", asset_type: str = "models", limit: int = 20) -> dict:
            hits = [hit] if query == target_query else []
            return _search_response(hits, query=query, asset_type=asset_type, limit=limit)

        target_query = query
        recs = gather_recommendations(make_geometry(zones=[zone]), search_one)
        cands = recs["zones"][0]["candidates"]
        if should_match:
            assert [c["asset_id"] for c in cands] == [hit_id]
        else:
            assert cands == []


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
        assert zone["queries"] == [
            {"query": q, "searched": False, "total_matches": None}
            for q in ("chair", "table", "sofa", "bench")
        ]
        assert recs["status"] == "empty"

    def test_empty_zone_with_zero_objects_does_not_search(self):
        empty_zone = dict(
            FURNITURE_ZONE,
            size=None,
            bbox_min=None,
            bbox_max=None,
            object_count=0,
            unmeasured_count=0,
            objects=[],
        )
        recs, calls = gather(make_geometry(zones=[empty_zone]))
        assert calls == []
        zone = recs["zones"][0]
        assert zone["status"] == "empty"
        assert zone["target"]["measurement"] == "empty"
        assert "skip_reason" not in zone
        assert zone["queries"] == [
            {"query": q, "searched": False, "total_matches": None}
            for q in ("chair", "table", "sofa", "bench")
        ]

    def test_partially_measured_zone_still_searches_but_flags_it(self):
        partial_zone = dict(FURNITURE_ZONE, unmeasured_count=1)
        recs, calls = gather(make_geometry(zones=[partial_zone]))
        assert len(calls) == 4
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

    def test_partial_query_failure_keeps_succeeded_results_and_reports_partial(self):
        def flaky(query: str = "", asset_type: str = "models", limit: int = 20) -> dict:
            if query == "table":
                raise AssetError("network_unavailable", "timeout on table")
            results = [chair_hit("chair_ok")] if query == "chair" else []
            return _search_response(results, query=query, asset_type=asset_type, limit=limit)

        recs = gather_recommendations(make_geometry(zones=[FURNITURE_ZONE]), flaky)
        assert recs["status"] == "partial"
        zone = recs["zones"][0]
        assert zone["status"] == "partial"
        assert [c["asset_id"] for c in zone["candidates"]] == ["chair_ok"]
        assert recs["errors"][0]["code"] == "network_unavailable"
        assert [q["searched"] for q in zone["queries"]] == [True, False, True, True]


# ------------------------------------------------------------
# caps, truncation, dedup, and deterministic order
# ------------------------------------------------------------


class TestDedupAndOrdering:
    def test_same_asset_across_queries_is_deduped_keeping_all_matched_queries(self):
        shared_in_chair = {
            "id": "dining_set_01",
            "name": "Dining Chair Table Set",
            "categories": ["furniture"],
            "tags": ["chair", "table"],
            "dimensions": [0.6, 0.6, 0.9],
            "polycount": 1500,
        }
        other_chair = chair_hit("chair_only")
        other_table = {
            "id": "table_only",
            "name": "Table Only",
            "categories": ["furniture"],
            "tags": ["table"],
            "dimensions": [0.8, 0.8, 0.75],
            "polycount": 900,
        }

        def multi_search(query: str = "", asset_type: str = "models", limit: int = 20) -> dict:
            if query == "chair":
                # dining_set_01 is rank 4
                hits = [
                    chair_hit("chair_a"),
                    chair_hit("chair_b"),
                    other_chair,
                    shared_in_chair,
                ]
            elif query == "table":
                # dining_set_01 is rank 1 here
                hits = [shared_in_chair, other_table]
            else:
                hits = []
            return _search_response(hits, query=query, asset_type=asset_type, limit=limit)

        recs = gather_recommendations(make_geometry(zones=[FURNITURE_ZONE]), multi_search)
        zone = recs["zones"][0]
        all_ids = [c["asset_id"] for c in zone["candidates"] + zone["unverified_candidates"]]
        assert all_ids.count("dining_set_01") == 1
        shared_cand = next(c for c in zone["candidates"] if c["asset_id"] == "dining_set_01")
        assert shared_cand["matched_queries"] == [
            {"query": "chair", "rank": 4},
            {"query": "table", "rank": 1},
        ]
        assert shared_cand["best_source_rank"] == 1

    def test_sort_order_rank_band_then_size_diff_then_best_rank_then_id(self):
        # Zone envelope is 3.2 x 2.6 x 2.5 m (sorted: [3.2, 2.6, 2.5]).
        # Ranks 1..5 share band 0: closer-to-zone-size rank 4 beats small rank 1;
        # rank 6 is band 1 so it stays behind band 0 even if its size matches closely;
        # equal band + equal size diff breaks tie by best_source_rank then asset_id.
        band0_small_r1 = chair_hit("chair_small_r1", dims=[0.5, 0.5, 0.8])
        band0_mid_r2 = chair_hit("chair_mid_r2", dims=[1.0, 1.0, 1.0])
        band0_mid_r3 = chair_hit("chair_mid_r3", dims=[1.0, 1.0, 1.0])
        band0_close_r4 = chair_hit("chair_close_r4", dims=[3.0, 2.4, 2.3])
        band0_filler_r5 = chair_hit("chair_filler_r5", dims=[0.4, 0.4, 0.4])
        band1_perfect_r6 = chair_hit("chair_perfect_r6", dims=[3.2, 2.6, 2.5])

        hits = [
            band0_small_r1,
            band0_mid_r2,
            band0_mid_r3,
            band0_close_r4,
            band0_filler_r5,
            band1_perfect_r6,
        ]
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]), results=hits)
        zone = recs["zones"][0]
        assert [c["asset_id"] for c in zone["candidates"]] == [
            "chair_close_r4",
            "chair_mid_r2",
            "chair_mid_r3",
        ]

    def test_band_six_to_ten_beats_eleven_to_twenty_even_if_smaller_size_diff(self):
        hits = (
            [
                chair_hit("chair_unfit_1", dims=[9.0, 9.0, 9.0]),
                chair_hit("chair_unfit_2", dims=[9.0, 9.0, 9.0]),
                chair_hit("chair_unfit_3", dims=[9.0, 9.0, 9.0]),
                chair_hit("chair_unfit_4", dims=[9.0, 9.0, 9.0]),
                chair_hit("chair_unfit_5", dims=[9.0, 9.0, 9.0]),
                chair_hit("chair_band1_r6", dims=[0.5, 0.5, 0.8]),
            ]
            + [chair_hit(f"chair_unfit_{i}", dims=[9.0, 9.0, 9.0]) for i in range(7, 11)]
            + [
                chair_hit("chair_band2_r11", dims=[3.2, 2.6, 2.5]),
            ]
        )
        recs, _ = gather(make_geometry(zones=[FURNITURE_ZONE]), results=hits)
        assert [c["asset_id"] for c in recs["zones"][0]["candidates"]] == [
            "chair_band1_r6",
            "chair_band2_r11",
        ]

    def test_tie_breaks_deterministically_by_asset_id(self):
        def same_rank_across_queries(
            query: str = "", asset_type: str = "models", limit: int = 20
        ) -> dict:
            if query == "chair":
                hits = [chair_hit("b_chair", dims=[1.0, 1.0, 1.0])]
            elif query == "table":
                hits = [
                    {
                        "id": "a_table",
                        "name": "A Table",
                        "categories": ["furniture"],
                        "tags": ["table"],
                        "dimensions": [1.0, 1.0, 1.0],
                        "polycount": 100,
                    }
                ]
            else:
                hits = []
            return _search_response(hits, query=query, asset_type=asset_type, limit=limit)

        recs = gather_recommendations(
            make_geometry(zones=[FURNITURE_ZONE]), same_rank_across_queries
        )
        assert [c["asset_id"] for c in recs["zones"][0]["candidates"]] == [
            "a_table",
            "b_chair",
        ]

    def test_whole_scene_cap_of_twelve_across_all_zones(self, monkeypatch):
        # Default 4 recommendable zones * 3 per zone == 12; raise per-zone cap
        # temporarily to verify the 12-per-scene cap enforces truncation["output"].
        monkeypatch.setattr("maya_mcp_server.asset_recommendation.MAX_PER_ZONE", 5)
        assert MAX_PER_SCENE == 12
        zones = [
            dict(FURNITURE_ZONE, name=name)
            for name in ("entrance", "display", "furniture", "lighting")
        ]

        def four_per_zone(query: str = "", asset_type: str = "models", limit: int = 20) -> dict:
            if query in ("door", "shelf", "chair", "lamp"):
                hits = [
                    {
                        "id": f"{query}_{i}",
                        "name": f"{query.title()} {i}",
                        "categories": [query],
                        "tags": [query],
                        "dimensions": [0.5, 0.5, 0.8],
                        "polycount": 300,
                    }
                    for i in range(4)
                ]
            else:
                hits = []
            return _search_response(hits, query=query, asset_type=asset_type, limit=limit)

        recs = gather_recommendations(make_geometry(zones=zones), four_per_zone)
        total_kept = sum(z["eligible_count"] + z["unverified_count"] for z in recs["zones"])
        assert total_kept == 12
        assert recs["truncation"]["output"] is True


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
        assert (
            "furniture: target=zone_bbox 3.2x2.6x2.5m meas=complete "
            "queries=chair,table,sofa,bench (1 eligible, 0 unverified)" in block
        )
        assert "1. chair_henry rank=1 via=[chair@1] 0.55x0.6x0.95m fits_zone_envelope" in block
        assert "truncation: search=n output=n budget=n errors=0" in block

    def test_disabled_zone_is_shown_as_skipped_without_queries(self):
        shell_zone = dict(FURNITURE_ZONE, name="shell")
        recs, _ = gather(make_geometry(zones=[shell_zone]))
        block = format_recommend_cos(recs)
        assert "shell: skipped (recommendations_disabled)" in block

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
        assert "truncation: search=n output=n budget=n errors=4 (network_unavailable)" in block

    def test_empty_scene_block_says_so(self):
        recs, _ = gather(make_geometry())
        block = format_recommend_cos(recs)
        assert "RECOMMEND: status=empty" in block
        assert "no zones in this scene" in block

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
