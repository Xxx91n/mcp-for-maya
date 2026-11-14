"""Host-side Poly Haven model recommendations for scene_plan (opt-in).

With ``scene_plan(recommend_assets=True)`` the plan gains a
``recommendations`` section. Everything here runs on the host: the Maya
side never goes online. The module reads the zone geometry the
``_mcp_scene`` module reports (through the ``get_zone_geometry`` host
helper in scene_tools), searches the Poly Haven models index for the
zone's query words via ``polyhaven.search_assets``, and screens the hits
against the zone's world-axis bounding box as a plain upper size limit.

Advisory only: recommendations name candidates and say why; nothing is
downloaded, imported, or placed, and a search failure never changes the
plan itself.

T1 scope (#217): the furniture zone with the single query ``chair``.
The remaining zones, cross-keyword dedup, and rank-band sorting are T2;
explicit target objects and the three-axis tolerance band are T3; the
soft time budget and whole-scene candidate cap are T4.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any, TypeGuard


# Q13's zone -> query-word table, T1 slice: furniture only. Zones missing
# from the table get no recommendations and no search traffic. T2 extends
# the table; nothing else in this file may invent a second mapping.
ZONE_SEARCH_QUERIES: dict[str, list[str]] = {
    "furniture": ["chair"],
}

# Q5: only the first 20 index hits per query are examined; the search
# truncation flag reports when the index held more.
SEARCH_LIMIT = 20
SEARCH_ASSET_TYPE = "models"

# Q9: at most 3 candidates per zone (eligible first, then unverified;
# both kinds share one limit). The 12-per-scene cap arrives with T2,
# when more than one zone can recommend.
MAX_PER_ZONE = 3

# Maya linear unit -> metres. get_unit_info() reports the scene's linear
# unit; a unit outside this table is a measurement failure, never a guess.
UNIT_TO_METRES: dict[str, float] = {
    "mm": 0.001,
    "cm": 0.01,
    "m": 1.0,
    "in": 0.0254,
    "ft": 0.3048,
    "yd": 0.9144,
    "mi": 1609.344,
    "km": 1000.0,
}

_POLICY: dict[str, Any] = {
    "mode": "zone_envelope",
    "geometry": "world_aabb",
    "upper_limit_only": True,
    "clearance_verified": False,
    "collision_verified": False,
    "note": (
        "Screening compares axis extents as an upper size limit only; "
        "clearance, collision, and placement are not verified, and a "
        "partially measured zone only bounds what was measured."
    ),
}


def _error(scope: str, code: str, message: str) -> dict[str, str]:
    return {"scope": scope, "code": code, "message": message}


def _to_metres(values: Any, factor: float, rounded: bool = True) -> list[float] | None:
    """Scene-unit [x, y, z] extents to metres.

    ``rounded=True`` (display fields) matches the Maya side's 3-decimal
    output. Screening passes ``rounded=False``: comparing a model against
    a rounded envelope could reject a fitting model over a sub-millimetre
    rounding gap, which is not "obviously too large". Anything that is not
    three finite numbers becomes None — the zone geometry contract already
    yields null for unreadable boxes, and a made-up size would poison the
    upper-limit screen.
    """
    if not isinstance(values, (list, tuple)) or len(values) != 3:
        return None
    out: list[float] = []
    for v in values:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            return None
        value = float(v) * factor
        out.append(round(value, 3) if rounded else value)
    return out


def _fits_envelope(model: list[float], envelope: list[float]) -> bool:
    """Conservative axis-aligned fit test against the zone envelope.

    Both extents are sorted largest-to-smallest and compared axis by axis,
    which sidesteps the Maya (Y-up) vs Poly Haven (published order) axis
    question. This screens for obviously-too-large models: a model that
    fails cannot fit the box in any axis-aligned orientation. A necessary
    condition only, not a proof — a model that would fit at a slant is
    excluded too, and nothing here verifies clearance, collision, or
    placement.
    """
    m = sorted(model, reverse=True)
    z = sorted(envelope, reverse=True)
    return all(mm <= zz for mm, zz in zip(m, z))


def _word_hit(entry: dict[str, Any], query: str) -> bool:
    """The query word appears in the asset's own text fields.

    Same substring semantics the index search uses; with the real
    search_assets this always passes, so it only guards a substitute
    search callable from slipping unrelated assets in.
    """
    q = query.lower()
    texts = [entry.get("id", ""), entry.get("name", "")]
    texts += [str(t) for t in entry.get("tags") or []]
    texts += [str(c) for c in entry.get("categories") or []]
    return any(q in str(t).lower() for t in texts)


def _candidate(entry: dict[str, Any], query: str, rank: int) -> dict[str, Any]:
    """One search hit with its provenance; size fields filled by the caller."""
    return {
        "asset_id": entry.get("id"),
        "name": entry.get("name"),
        "dimensions_m": entry.get("dimensions"),
        "polycount": entry.get("polycount"),
        "matched_queries": [{"query": query, "rank": rank}],
        "best_source_rank": rank,
        "size_status": "unverified",
        "reason_code": "missing_dimensions",
        "match_reason": "no size decision yet",
    }


def _valid_dimensions(dims: Any) -> TypeGuard[list[float]]:
    """Three finite, strictly positive numbers — a size the screen may use."""
    if not isinstance(dims, list) or len(dims) != 3:
        return False
    return all(
        not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v) and v > 0
        for v in dims
    )


def _screen(
    results: list[Any], query: str, envelope_m: list[float]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split one query's hits into size-eligible and unverified candidates.

    Assets the index returned but whose text fields do not carry the query
    word are dropped (word-level check); assets that clearly cannot fit
    the zone envelope are dropped too. Neither shows up as a candidate —
    only assets that fit, and assets whose size could not be checked.
    """
    eligible: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    for rank, entry in enumerate(results, start=1):
        if not isinstance(entry, dict) or not entry.get("id"):
            continue
        if not _word_hit(entry, query):
            continue
        cand = _candidate(entry, query, rank)
        dims = entry.get("dimensions")
        if not _valid_dimensions(dims):
            cand["reason_code"] = "missing_dimensions" if dims is None else "invalid_dimensions"
            cand["match_reason"] = (
                "Poly Haven publishes no usable dimensions for this asset; "
                "size screening was not performed"
            )
            unverified.append(cand)
            continue
        if _fits_envelope([float(v) for v in dims], envelope_m):
            largest = max(float(v) for v in dims)
            zone_largest = max(envelope_m)
            cand["size_status"] = "pass"
            cand["reason_code"] = "fits_zone_envelope"
            cand["match_reason"] = (
                f"largest side {largest:g} m within the zone envelope's "
                f"largest side {zone_largest:g} m (world AABB upper limit, "
                "per sorted axis)"
            )
            eligible.append(cand)
    return eligible, unverified


def _searched_query(query: str, total_matches: int | None) -> dict[str, Any]:
    return {"query": query, "searched": True, "total_matches": total_matches}


def _unsearched_query(query: str) -> dict[str, Any]:
    return {"query": query, "searched": False, "total_matches": None}


def _process_zone(
    zone: dict[str, Any],
    queries: list[str],
    factor: float,
    search_fn: Callable[..., dict[str, Any]],
    errors: list[dict[str, str]],
    truncation: dict[str, bool],
) -> dict[str, Any]:
    """Build one zone's recommendation entry, searching only when measurable."""
    name = zone.get("name", "")
    scope = f"recommendations:{name}"
    size_m = _to_metres(zone.get("size"), factor)
    # Unrounded for the size screen (rounded=False), rounded for display.
    size_screen = _to_metres(zone.get("size"), factor, rounded=False)
    unmeasured = zone.get("unmeasured_count")
    if size_m is None:
        measurement = "unmeasurable_target"
    elif isinstance(unmeasured, int) and unmeasured > 0:
        measurement = "partial_zone_envelope"
    else:
        measurement = "complete"
    target: dict[str, Any] = {
        "source": "zone_bbox",
        "geometry": "world_aabb",
        "name": name,
        "object_count": zone.get("object_count"),
        "unmeasured_count": unmeasured,
        "size_m": size_m,
        "bbox_min_m": _to_metres(zone.get("bbox_min"), factor),
        "bbox_max_m": _to_metres(zone.get("bbox_max"), factor),
        "measurement": measurement,
    }
    entry: dict[str, Any] = {
        "zone": name,
        "status": "empty",
        "target": target,
        "queries": [],
        "eligible_count": 0,
        "unverified_count": 0,
        "candidates": [],
        "unverified_candidates": [],
    }
    if size_screen is None:  # same condition that set measurement above
        entry["status"] = "skipped"
        entry["skip_reason"] = "unmeasurable_target"
        entry["queries"] = [_unsearched_query(q) for q in queries]
        return entry

    eligible: list[dict[str, Any]] = []
    unverified: list[dict[str, Any]] = []
    for query in queries:
        try:
            data = search_fn(query=query, asset_type=SEARCH_ASSET_TYPE, limit=SEARCH_LIMIT)
            results = data.get("results") if isinstance(data, dict) else None
            total = data.get("total_count") if isinstance(data, dict) else None
            if not isinstance(results, list):
                raise ValueError(f"unexpected search payload: {type(data).__name__}")
        except Exception as e:  # network/index failure must never break the plan
            code = getattr(e, "code", None)
            errors.append(
                _error(
                    scope,
                    code if isinstance(code, str) else "search_failed",
                    f"{type(e).__name__}: {e}",
                )
            )
            entry["status"] = "skipped"
            entry["skip_reason"] = "search_failed"
            entry["queries"].append(_unsearched_query(query))
            continue
        total_int = total if isinstance(total, int) else None
        entry["queries"].append(_searched_query(query, total_int))
        if total_int is not None and total_int > len(results):
            truncation["search"] = True
        fits, unverified_hits = _screen(results, query, size_screen)
        eligible.extend(fits)
        unverified.extend(unverified_hits)

    ordered = sorted(
        eligible + unverified,
        # Q9: size-eligible candidates win the cap before unverified ones,
        # so three dimension-less hits early in the search cannot starve a
        # fitting model that ranked below them.
        key=lambda c: (
            c["size_status"] != "pass",
            c["best_source_rank"],
            str(c["asset_id"]),
        ),
    )
    if len(ordered) > MAX_PER_ZONE:
        truncation["output"] = True
        ordered = ordered[:MAX_PER_ZONE]
    shown_eligible = [c for c in ordered if c["size_status"] == "pass"]
    shown_unverified = [c for c in ordered if c["size_status"] != "pass"]
    entry["candidates"] = shown_eligible
    entry["unverified_candidates"] = shown_unverified
    entry["eligible_count"] = len(shown_eligible)
    entry["unverified_count"] = len(shown_unverified)
    if entry["status"] != "skipped":  # a failed query already set skip_reason
        entry["status"] = "ok" if shown_eligible else "empty"
    return entry


def gather_recommendations(
    zone_geometry: Any, search_fn: Callable[..., dict[str, Any]]
) -> dict[str, Any]:
    """Compose the ``recommendations`` section from geometry + one search.

    ``zone_geometry`` is whatever the ``get_zone_geometry`` host helper
    returned (a dict with ``unit``/``zones``, or ``{"error": ...}``).
    ``search_fn`` is ``polyhaven.search_assets`` in production; tests may
    inject a fake. Never raises: every failure becomes a structured error
    entry, so the caller's plan survives untouched.
    """
    recs: dict[str, Any] = {
        "status": "empty",
        "provider": "poly_haven",
        "unit": "m",
        "policy": dict(_POLICY),
        "truncation": {"search": False, "output": False, "budget": False},
        "errors": [],
        "zones": [],
    }
    errors: list[dict[str, str]] = recs["errors"]
    truncation: dict[str, bool] = recs["truncation"]

    zones_list = zone_geometry.get("zones") if isinstance(zone_geometry, dict) else None
    if not isinstance(zones_list, list):
        err = (
            zone_geometry.get("error")
            if isinstance(zone_geometry, dict) and isinstance(zone_geometry.get("error"), dict)
            else None
        )
        code = err.get("code", "query_failed") if err else "query_failed"
        message = (
            err.get("message", "zone geometry unavailable")
            if err
            else f"unexpected zone geometry payload: {type(zone_geometry).__name__}"
        )
        errors.append(_error("zone_geometry", str(code), str(message)))
        recs["status"] = "partial"
        return recs

    unit = zone_geometry.get("unit")
    factor = UNIT_TO_METRES.get(unit) if isinstance(unit, str) else None
    if factor is None:
        errors.append(
            _error(
                "zone_geometry",
                "unit_unknown",
                f"cannot convert scene unit {unit!r} to metres",
            )
        )
        recs["status"] = "partial"
        return recs

    any_eligible = False
    search_failed = False
    for zone_name, queries in ZONE_SEARCH_QUERIES.items():
        zone = next(
            (z for z in zones_list if isinstance(z, dict) and z.get("name") == zone_name),
            None,
        )
        if zone is None:
            continue  # no such zone in this scene: nothing to search
        zone_rec = _process_zone(zone, queries, factor, search_fn, errors, truncation)
        recs["zones"].append(zone_rec)
        if zone_rec["eligible_count"] > 0:
            any_eligible = True
        if zone_rec.get("skip_reason") == "search_failed":
            search_failed = True

    if search_failed:
        recs["status"] = "offline"
    elif any(e["scope"] == "zone_geometry" for e in errors):
        recs["status"] = "partial"
    elif any_eligible:
        recs["status"] = "ok"
    else:
        recs["status"] = "empty"
    return recs


def _fmt_dims(dims: Any) -> str:
    if not isinstance(dims, (list, tuple)) or not dims:
        return "?"
    return "x".join(f"{float(v):g}" for v in dims)


def format_recommend_cos(recs: dict[str, Any]) -> str:
    """Short RECOMMEND block for scene_plan's CoS output (opt-in only).

    Carries the four things the contract asks for: the status, the target
    and its size basis, the candidate ids with sizes, and the truncation
    note. Indented to sit under scene_plan's existing sections.
    """
    policy = recs.get("policy", {})
    lines = [
        f"  RECOMMEND: status={recs.get('status')} provider={recs.get('provider')} "
        f"unit={recs.get('unit')} policy={policy.get('mode')}({policy.get('geometry')} upper-limit)"
    ]
    zones = recs.get("zones", [])
    errors = recs.get("errors", [])
    if not zones:
        if errors:
            for e in errors:
                lines.append(f"    error: {e.get('scope')} {e.get('code')}")
        else:
            lines.append("    no furniture zone in this scene")
    for zone in zones:
        if zone.get("status") == "skipped":
            lines.append(f"    {zone.get('zone')}: skipped ({zone.get('skip_reason')})")
            continue
        target = zone.get("target", {})
        lines.append(
            f"    {zone.get('zone')}: target=zone_bbox "
            f"{_fmt_dims(target.get('size_m'))}m meas={target.get('measurement')}"
        )
        for q in zone.get("queries", []):
            lines.append(
                f"    {q.get('query')}: {zone.get('eligible_count', 0)} eligible, "
                f"{zone.get('unverified_count', 0)} unverified"
            )
        n = 0
        for cand in zone.get("candidates", []) + zone.get("unverified_candidates", []):
            n += 1
            lines.append(
                f"      {n}. {cand.get('asset_id')} rank={cand.get('best_source_rank')} "
                f"{_fmt_dims(cand.get('dimensions_m'))}m {cand.get('reason_code')}"
            )

    def _yn(value: Any) -> str:
        return "y" if value else "n"

    tr = recs.get("truncation", {})
    tail = (
        f"    truncation: search={_yn(tr.get('search'))} output={_yn(tr.get('output'))} "
        f"budget={_yn(tr.get('budget'))} errors={len(errors)}"
    )
    if errors:
        tail += f" ({errors[0].get('code')})"
    lines.append(tail)
    return "\n".join(lines)
