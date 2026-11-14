"""Host-side Poly Haven model recommendations for scene_plan (opt-in).

With ``scene_plan(recommend_assets=True)`` the plan gains a
``recommendations`` section. Everything here runs on the host: the Maya
side never goes online. The module reads the zone geometry the
``_mcp_scene`` module reports (through the ``get_zone_geometry`` host
helper in scene_tools), identifies the target per zone in deterministic
order (explicit full DAG path -> unique short name -> unique measurable
zone object -> zone bbox fallback), searches the Poly Haven models index
via ``polyhaven.search_assets``, and screens candidates in metres
(three-axis 0.5x-1.5x tolerance for an object target; upper-limit-only
for a zone bbox fallback).

Advisory only: recommendations name candidates and say why; nothing is
downloaded, imported, or placed, and a search failure never changes the
plan itself.

T1 scope (#217): the furniture zone with the single query ``chair``.
T3 scope (#219): target resolution, ambiguity/fallback reporting, unit
conversion, and three-axis 0.5x-1.5x size screening.
The remaining zones, cross-keyword dedup, and rank-band sorting are T2;
the soft time budget and whole-scene candidate cap are T4.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass
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

# Q7: explicit or unique object targets screen sorted axes against
# 0.5x-1.5x of the target's sorted axes; zone_bbox fallback stays
# upper-limit only.
MIN_SIZE_RATIO = 0.5
MAX_SIZE_RATIO = 1.5

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

_ZONE_ENVELOPE_NOTE = (
    "Screening compares axis extents as an upper size limit only; "
    "clearance, collision, and placement are not verified, and a "
    "partially measured zone only bounds what was measured."
)
_OBJECT_TOLERANCE_NOTE = (
    "Screening compares sorted world-AABB axis extents against the target "
    "object within a 0.5x-1.5x per-axis tolerance; clearance, collision, "
    "and placement are not verified."
)

_DAG_REF_RE = re.compile(r"\|[A-Za-z0-9_:|]+")
_PREFIX_REF_RE = re.compile(r"(?<![A-Za-z0-9_:|])(?:GEO|GRP|LOC|LGT|CAM)_[A-Za-z0-9_]+")


@dataclass(frozen=True)
class _FallbackNote:
    reason: str
    detail: str
    matches: tuple[str, ...] = ()


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
    screen.
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


def _measurable_size_m(values: Any, factor: float) -> tuple[list[float] | None, list[float] | None]:
    """Return ``(display_m, unrounded_screen_m)`` when values are positive 3-extents."""
    screen_m = _to_metres(values, factor, rounded=False)
    if not _valid_dimensions(screen_m):
        return None, None
    display_m = _to_metres(values, factor, rounded=True)
    return display_m, list(screen_m)


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
    return all(mm <= zz + 1e-12 * max(1.0, zz) for mm, zz in zip(m, z))


def _fits_three_axis_tolerance(model: list[float], target: list[float]) -> bool:
    """Sorted three-axis tolerance check (0.5x-1.5x per axis).

    Both model and target extents are sorted largest-to-smallest and each
    corresponding axis must fall within [0.5 * t, 1.5 * t] (with a
    picometre IEEE-754 guard so exact unit conversions like 0.3 * 1.5
    never fail due to float representation).
    """
    m_sorted = sorted(model, reverse=True)
    t_sorted = sorted(target, reverse=True)
    for mm, tt in zip(m_sorted, t_sorted):
        eps = 1e-12 * max(1.0, tt)
        if mm < tt * MIN_SIZE_RATIO - eps or mm > tt * MAX_SIZE_RATIO + eps:
            return False
    return True


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


def _valid_dimensions(dims: Any) -> TypeGuard[list[float] | tuple[float, ...]]:
    """Three finite, strictly positive numbers — a size the screen may use."""
    if not isinstance(dims, (list, tuple)) or len(dims) != 3:
        return False
    return all(
        not isinstance(v, bool) and isinstance(v, (int, float)) and math.isfinite(v) and v > 0
        for v in dims
    )


def _unverified_reason(dims: Any) -> tuple[str, str]:
    if dims is None:
        return (
            "missing_dimensions",
            "Poly Haven publishes no usable dimensions for this asset; "
            "size screening was not performed",
        )
    if isinstance(dims, (list, tuple)) and len(dims) == 3:
        for v in dims:
            if (
                not isinstance(v, bool)
                and isinstance(v, (int, float))
                and math.isfinite(v)
                and v <= 0
            ):
                return (
                    "invalid_dimensions",
                    "Poly Haven asset dimensions contain zero or non-positive values; "
                    "size screening was not performed",
                )
    return (
        "invalid_dimensions",
        "Poly Haven asset dimensions are malformed or non-finite; size screening was not performed",
    )


def _screen(
    results: list[Any],
    query: str,
    target_m: list[float],
    screening_mode: str = "zone_envelope",
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split one query's hits into size-eligible and unverified candidates.

    Assets the index returned but whose text fields do not carry the query
    word are dropped (word-level check); assets that fail the size screen
    are dropped too. Neither shows up as a candidate — only assets that
    pass, and assets whose size could not be checked.
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
            cand["dimensions_m"] = _to_metres(dims, 1.0, rounded=False)
            code, reason = _unverified_reason(dims)
            cand["reason_code"] = code
            cand["match_reason"] = reason
            unverified.append(cand)
            continue
        model_m = [float(v) for v in dims]
        if screening_mode == "three_axis_tolerance":
            if _fits_three_axis_tolerance(model_m, target_m):
                m_sorted = sorted(model_m, reverse=True)
                t_sorted = sorted(target_m, reverse=True)
                ratios = "/".join(f"{mm / tt:.2f}x" for mm, tt in zip(m_sorted, t_sorted))
                cand["size_status"] = "pass"
                cand["reason_code"] = "fits_target_three_axis"
                cand["match_reason"] = (
                    f"sorted axes {_fmt_dims(m_sorted)} m within "
                    f"{MIN_SIZE_RATIO:g}x-{MAX_SIZE_RATIO:g}x of target "
                    f"{_fmt_dims(t_sorted)} m (ratios {ratios}; "
                    "world AABB, clearance and collision not verified)"
                )
                eligible.append(cand)
        elif _fits_envelope(model_m, target_m):
            largest = max(model_m)
            zone_largest = max(target_m)
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


def _token_in_objective(objective: str, token: str) -> bool:
    """Match a DAG path or short name token without partial-identifier false hits."""
    if not objective or not token:
        return False
    pattern = rf"(?<![A-Za-z0-9_:|]){re.escape(token)}(?![A-Za-z0-9_:|])"
    return re.search(pattern, objective) is not None


def _match_zone_object(
    zone_name: str,
    valid_objects: list[dict[str, Any]],
    obj_count: Any,
    unmeasured: Any,
    factor: float,
    objective: str,
) -> tuple[dict[str, Any] | None, str | None, _FallbackNote | None]:
    """Run Q6 target matching: DAG path -> short name -> unique zone object."""
    dag_matches = [obj for obj in valid_objects if _token_in_objective(objective, obj["name"])]
    if len(dag_matches) == 1:
        return dag_matches[0], "dag_path", None
    if len(dag_matches) > 1:
        paths = tuple(obj["name"] for obj in dag_matches)
        detail = (
            f"objective matched {len(dag_matches)} DAG paths in zone '{zone_name}': "
            f"{', '.join(paths)}; fell back to zone_bbox"
        )
        return None, None, _FallbackNote("ambiguous_dag_path", detail, paths)

    short_matches = [
        obj
        for obj in valid_objects
        if _token_in_objective(objective, obj["name"].rsplit("|", 1)[-1])
    ]
    if len(short_matches) == 1:
        return short_matches[0], "short_name", None
    if len(short_matches) > 1:
        paths = tuple(obj["name"] for obj in short_matches)
        shorts = {obj["name"].rsplit("|", 1)[-1] for obj in short_matches}
        if len(shorts) == 1:
            reason = "ambiguous_short_name"
            detail = (
                f"short name '{next(iter(shorts))}' matched {len(short_matches)} objects in "
                f"zone '{zone_name}': {', '.join(paths)}; fell back to zone_bbox"
            )
        else:
            reason = "ambiguous_target"
            detail = (
                f"objective matched {len(short_matches)} objects in zone '{zone_name}': "
                f"{', '.join(paths)}; fell back to zone_bbox"
            )
        return None, None, _FallbackNote(reason, detail, paths)

    explicit_refs = list(
        dict.fromkeys(
            m.group(0) for pat in (_DAG_REF_RE, _PREFIX_REF_RE) for m in pat.finditer(objective)
        )
    )
    if explicit_refs:
        refs_text = ", ".join(explicit_refs)
        return (
            None,
            None,
            _FallbackNote(
                "target_not_found",
                (
                    f"objective named '{refs_text}' which was not found in zone '{zone_name}'; "
                    "fell back to zone_bbox upper limit"
                ),
            ),
        )

    measurable = [
        obj for obj in valid_objects if _measurable_size_m(obj.get("size"), factor)[1] is not None
    ]
    # Keep synthetic fixtures whose object_count > len(objects) in zone_bbox mode.
    count_matches_list = not (
        isinstance(obj_count, int)
        and isinstance(unmeasured, int)
        and (obj_count - unmeasured) != len(measurable)
    )
    if len(measurable) == 1 and count_matches_list:
        return measurable[0], "unique_zone_object", None

    if len(measurable) > 1 or (
        isinstance(obj_count, int) and isinstance(unmeasured, int) and (obj_count - unmeasured) > 1
    ):
        return (
            None,
            None,
            _FallbackNote(
                "multiple_zone_objects",
                (
                    f"no unique target specified across multiple objects in zone '{zone_name}'; "
                    "fell back to zone_bbox upper limit"
                ),
            ),
        )
    return (
        None,
        None,
        _FallbackNote(
            "no_explicit_target",
            (
                f"no measurable target object resolved in zone '{zone_name}'; "
                "fell back to zone_bbox upper limit"
            ),
        ),
    )


def _build_object_target(
    zone_name: str,
    matched_obj: dict[str, Any],
    match_source: str,
    obj_display_m: list[float],
    obj_count: Any,
    unmeasured: Any,
) -> dict[str, Any]:
    partial_zone = (
        match_source == "unique_zone_object" and isinstance(unmeasured, int) and unmeasured > 0
    )
    target: dict[str, Any] = {
        "source": match_source,
        "screening_mode": "three_axis_tolerance",
        "tolerance_band": [MIN_SIZE_RATIO, MAX_SIZE_RATIO],
        "geometry": "world_aabb",
        "name": matched_obj["name"],
        "short_name": matched_obj["name"].rsplit("|", 1)[-1],
        "object_count": obj_count,
        "unmeasured_count": unmeasured,
        "size_m": obj_display_m,
        "bbox_min_m": None,
        "bbox_max_m": None,
        "measurement": "partial_zone_objects" if partial_zone else "complete",
        "measurement_complete": not partial_zone,
    }
    if partial_zone:
        target["fallback_detail"] = (
            f"{unmeasured} other object(s) in zone '{zone_name}' could not be measured"
        )
    return target


def _build_zone_fallback_target(
    zone_name: str,
    zone_display_m: list[float] | None,
    zone_bbox_min_m: list[float] | None,
    zone_bbox_max_m: list[float] | None,
    obj_count: Any,
    unmeasured: Any,
    fallback: _FallbackNote | None = None,
) -> tuple[dict[str, Any], str | None]:
    has_unmeasured = isinstance(unmeasured, int) and unmeasured > 0
    unmeasurable = zone_display_m is None
    target: dict[str, Any] = {
        "source": "zone_bbox",
        "screening_mode": "none" if unmeasurable else "zone_envelope",
        "geometry": "world_aabb",
        "name": zone_name,
        "object_count": obj_count,
        "unmeasured_count": unmeasured,
        "size_m": zone_display_m,
        "bbox_min_m": zone_bbox_min_m,
        "bbox_max_m": zone_bbox_max_m,
        "measurement": (
            "unmeasurable_target"
            if unmeasurable
            else ("partial_zone_envelope" if has_unmeasured else "complete")
        ),
        "measurement_complete": False if unmeasurable else not has_unmeasured,
    }
    if not unmeasurable:
        target["upper_limit_only"] = True
    if fallback is not None:
        target["fallback_reason"] = fallback.reason
        target["fallback_detail"] = fallback.detail
        if fallback.matches:
            target["ambiguous_matches"] = list(fallback.matches)
    return target, ("unmeasurable_target" if unmeasurable else None)


def _resolve_target(
    zone: dict[str, Any], factor: float, objective: str
) -> tuple[dict[str, Any], list[float] | None, str | None]:
    """Identify the zone's sizing target in Q6 deterministic order.

    Order: explicit full DAG path -> unique matching short name -> unique
    measurable object in the zone -> zone_bbox fallback. Ambiguous matches
    never pick a winner arbitrarily and always explain the fallback.
    """
    name = zone.get("name", "")
    obj_count = zone.get("object_count")
    unmeasured = zone.get("unmeasured_count")
    if obj_count == 0:
        target, _ = _build_zone_fallback_target(name, None, None, None, 0, unmeasured)
        target["measurement"] = "empty_zone"
        return target, None, "empty_zone"

    raw_objects = zone.get("objects")
    valid_objects = [
        obj
        for obj in (raw_objects if isinstance(raw_objects, list) else [])
        if isinstance(obj, dict) and isinstance(obj.get("name"), str) and obj["name"]
    ]
    matched_obj, match_source, fallback = _match_zone_object(
        name, valid_objects, obj_count, unmeasured, factor, objective
    )
    if matched_obj is not None and match_source is not None:
        obj_display_m, obj_screen_m = _measurable_size_m(matched_obj.get("size"), factor)
        if obj_screen_m is not None and obj_display_m is not None:
            return (
                _build_object_target(
                    name, matched_obj, match_source, obj_display_m, obj_count, unmeasured
                ),
                obj_screen_m,
                None,
            )
        fallback = _FallbackNote(
            "matched_target_unmeasurable",
            (
                f"matched object '{matched_obj['name']}' has no usable bounding box; "
                "fell back to zone_bbox"
            ),
        )

    zone_display_m, zone_screen_m = _measurable_size_m(zone.get("size"), factor)
    zone_bbox_min_m = _to_metres(zone.get("bbox_min"), factor)
    zone_bbox_max_m = _to_metres(zone.get("bbox_max"), factor)
    fallback_target, skip_reason = _build_zone_fallback_target(
        name,
        zone_display_m,
        zone_bbox_min_m,
        zone_bbox_max_m,
        obj_count,
        unmeasured,
        fallback,
    )
    return fallback_target, (None if skip_reason else zone_screen_m), skip_reason


def _process_zone(
    zone: dict[str, Any],
    queries: list[str],
    factor: float,
    search_fn: Callable[..., dict[str, Any]],
    errors: list[dict[str, str]],
    truncation: dict[str, bool],
    objective: str = "",
) -> dict[str, Any]:
    """Build one zone's recommendation entry, searching only when measurable."""
    name = zone.get("name", "")
    scope = f"recommendations:{name}"
    target, size_screen, skip_reason = _resolve_target(zone, factor, objective)
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
    if size_screen is None or skip_reason is not None:
        entry["status"] = "skipped"
        entry["skip_reason"] = skip_reason or "unmeasurable_target"
        entry["queries"] = [_unsearched_query(q) for q in queries]
        return entry

    screening_mode = str(target.get("screening_mode", "zone_envelope"))
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
        fits, unverified_hits = _screen(results, query, size_screen, screening_mode=screening_mode)
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


def _build_policy(zones_recs: list[dict[str, Any]]) -> dict[str, Any]:
    modes = {
        z.get("target", {}).get("screening_mode")
        for z in zones_recs
        if z.get("status") != "skipped"
    }
    if "three_axis_tolerance" in modes:
        return {
            "mode": "object_tolerance",
            "geometry": "world_aabb",
            "upper_limit_only": False,
            "tolerance_band": [MIN_SIZE_RATIO, MAX_SIZE_RATIO],
            "clearance_verified": False,
            "collision_verified": False,
            "note": _OBJECT_TOLERANCE_NOTE,
        }
    return {
        "mode": "zone_envelope",
        "geometry": "world_aabb",
        "upper_limit_only": True,
        "clearance_verified": False,
        "collision_verified": False,
        "note": _ZONE_ENVELOPE_NOTE,
    }


def gather_recommendations(
    zone_geometry: Any,
    search_fn: Callable[..., dict[str, Any]],
    objective: str = "",
) -> dict[str, Any]:
    """Compose the ``recommendations`` section from geometry + search.

    ``zone_geometry`` is whatever the ``get_zone_geometry`` host helper
    returned (a dict with ``unit``/``zones``, or ``{"error": ...}``).
    ``search_fn`` is ``polyhaven.search_assets`` in production; tests may
    inject a fake. ``objective`` is used host-side only to resolve target
    objects by DAG path or short name and is never sent to ``search_fn``.
    Never raises: every failure becomes a structured error entry, so the
    caller's plan survives untouched.
    """
    objective_text = objective if isinstance(objective, str) else ""
    recs: dict[str, Any] = {
        "status": "empty",
        "provider": "poly_haven",
        "unit": "m",
        "policy": _build_policy([]),
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
        zone_rec = _process_zone(
            zone, queries, factor, search_fn, errors, truncation, objective=objective_text
        )
        recs["zones"].append(zone_rec)
        if zone_rec["eligible_count"] > 0:
            any_eligible = True
        if zone_rec.get("skip_reason") == "search_failed":
            search_failed = True

    recs["policy"] = _build_policy(recs["zones"])
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

    Carries the status, the target and its size basis (including
    completeness and any ambiguity/fallback reason), the candidate ids
    with sizes and match/unverified reasons, and the truncation note.
    Indented to sit under scene_plan's existing sections.
    """
    policy = recs.get("policy", {})
    mode = policy.get("mode", "zone_envelope")
    geom = policy.get("geometry", "world_aabb")
    if mode == "object_tolerance":
        policy_label = f"object_tolerance({geom} {MIN_SIZE_RATIO:g}-{MAX_SIZE_RATIO:g}x)"
    else:
        policy_label = f"{mode}({geom} upper-limit)"
    lines = [
        f"  RECOMMEND: status={recs.get('status')} provider={recs.get('provider')} "
        f"unit={recs.get('unit')} policy={policy_label}"
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
            target = zone.get("target", {})
            line = f"    {zone.get('zone')}: skipped ({zone.get('skip_reason')})"
            obj_count = target.get("object_count")
            if obj_count is not None:
                unmeasured = target.get("unmeasured_count")
                line += f" objects={obj_count} unmeasured={0 if unmeasured is None else unmeasured}"
            lines.append(line)
            continue
        target = zone.get("target", {})
        source = target.get("source", "zone_bbox")
        complete_yn = "y" if target.get("measurement_complete", True) else "n"
        if source == "zone_bbox":
            target_line = (
                f"    {zone.get('zone')}: target=zone_bbox "
                f"{_fmt_dims(target.get('size_m'))}m meas={target.get('measurement')} "
                f"complete={complete_yn}"
            )
            fb = target.get("fallback_reason")
            if fb:
                target_line += f" fallback={fb}"
                amb = target.get("ambiguous_matches")
                if amb:
                    target_line += f"({','.join(amb)})"
        else:
            target_line = (
                f"    {zone.get('zone')}: target={source}({target.get('name')}) "
                f"{_fmt_dims(target.get('size_m'))}m tol={MIN_SIZE_RATIO:g}-{MAX_SIZE_RATIO:g}x "
                f"meas={target.get('measurement')} complete={complete_yn}"
            )
        lines.append(target_line)
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
                f"{_fmt_dims(cand.get('dimensions_m'))}m {cand.get('reason_code')} "
                f"status={cand.get('size_status')}"
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
