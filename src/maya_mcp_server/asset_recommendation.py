"""Host-side Poly Haven model recommendations for scene_plan (opt-in).

With ``scene_plan(recommend_assets=True)`` the plan gains a
``recommendations`` section. Everything here runs on the host: the Maya
side never goes online. The module reads the zone geometry the
``_mcp_scene`` module reports (through the ``get_zone_geometry`` host
helper in scene_tools), identifies each zone's target in deterministic
order (explicit full DAG path -> unique short name -> unique measurable
zone object -> zone bbox fallback), searches the Poly Haven models index
for each zone's mapped query words via ``polyhaven.search_assets``,
filters hits with a normalized word-level check, deduplicates across
keywords, screens candidates in metres (three-axis 0.5x-1.5x tolerance
for an object target; upper-limit-only for a zone bbox fallback), sorts
by rank band and size difference, and caps results per zone and for the
whole scene.

Advisory only: recommendations name candidates and say why; nothing is
downloaded, imported, or placed, and a search failure never changes the
plan itself.

T1 scope (#217): furniture zone with ``chair``.
T2 scope (#218): all 7 built-in zones, normalized word-level check,
cross-keyword dedup, rank-band + size-difference sorting, and the
3-per-zone / 12-per-scene caps.
T3 scope (#219): target resolution, ambiguity/fallback reporting, unit
conversion, and three-axis 0.5x-1.5x size screening.
T4 scope (#220): 5-second monotonic soft time budget, remaining timeout
forwarding, shared-index offline circuit-breaker, corrupt metadata
hardening, and worker-thread offloading in scene_tools.
"""

from __future__ import annotations

import inspect
import math
import re
import time
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeGuard


# Q13's 7-zone -> query-word table. Zones mapped to () get no search
# traffic and no recommendations; nothing else in this file may invent
# a second mapping or alter zone detection.
ZONE_SEARCH_QUERIES: dict[str, tuple[str, ...]] = {
    "shell": (),
    "entrance": ("door", "sign"),
    "display": ("shelf", "counter", "showcase", "podium"),
    "ip_core": (),
    "furniture": ("chair", "table", "sofa", "bench"),
    "lighting": ("lamp", "light"),
    "path": (),
}

# Q5: only the first 20 index hits per query are examined; the search
# truncation flag reports when the index held more.
SEARCH_LIMIT = 20
SEARCH_ASSET_TYPE = "models"

# Q8: 5-second monotonic soft budget for the whole recommendation pass.
DEFAULT_RECOMMEND_BUDGET_S = 5.0
_SHARED_INDEX_FATAL_CODES = frozenset(
    {
        "network_unavailable",
        "http_error",
        "bad_response",
        "download_too_large",
        "url_not_allowed",
    }
)

# Q9: at most 3 candidates per zone and 12 across the whole scene
# (eligible first, then unverified; both kinds share the cap).
MAX_PER_ZONE = 3
MAX_PER_SCENE = 12

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
_MIXED_POLICY_NOTE = (
    "Screening uses 0.5x-1.5x sorted-axis tolerance for identified target "
    "objects and upper-limit-only screening for zone_bbox fallbacks; "
    "clearance, collision, and placement are not verified, and a partially "
    "measured zone only bounds what was measured."
)

_DAG_REF_RE = re.compile(r"\|[A-Za-z0-9_:|]+")
_PREFIX_REF_RE = re.compile(
    r"(?<![A-Za-z0-9_:|])(?:[A-Za-z0-9_]+:)*(?:GEO|GRP|LOC|LGT|CAM)_[A-Za-z0-9_]+"
)


@dataclass(frozen=True)
class _FallbackNote:
    reason: str
    detail: str
    matches: tuple[str, ...] = ()


def _error(scope: str, code: str, message: str) -> dict[str, str]:
    return {"scope": scope, "code": code, "message": message}


def _finite_float(value: Any) -> float | None:
    """Convert a numeric value to a finite float, rejecting bools and huge ints."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        out = float(value)
    except (OverflowError, TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


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
        num = _finite_float(v)
        if num is None:
            return None
        value = num * factor
        if not math.isfinite(value):
            return None
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


_WORD_BOUNDARY_RE = re.compile(
    r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|(?<=[A-Za-z])(?=[0-9])|(?<=[0-9])(?=[A-Za-z])"
)
_WORD_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalize_word(token: str) -> str:
    """Fold basic plurals and Poly Haven's ``lighting`` category to ``light``."""
    if token == "lighting":
        return "light"
    if token == "shelves":
        return "shelf"
    if (
        len(token) > 3
        and token.endswith("es")
        and token.endswith(("ches", "shes", "xes", "zes", "sses"))
    ):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokenize_words(text: str) -> set[str]:
    norm = _WORD_BOUNDARY_RE.sub(" ", unicodedata.normalize("NFKC", text))
    return {_normalize_word(tok) for tok in _WORD_TOKEN_RE.findall(norm.lower())}


def _iter_str_items(raw: Any) -> list[str]:
    if isinstance(raw, (list, tuple)):
        return [str(item) for item in raw]
    if isinstance(raw, str):
        return [raw]
    return []


def _word_hit(entry: dict[str, Any], query: str) -> bool:
    """Normalized word-level match on id, name, tags, and categories.

    Rejects substring false positives such as ``sign`` matching ``design``
    or ``door`` matching ``outdoor``. Purely a filter on the returned hit;
    never creates assets outside the search result.
    """
    q_tokens = _tokenize_words(query)
    if not q_tokens:
        return False
    texts = [str(entry.get("id") or ""), str(entry.get("name") or "")]
    texts += _iter_str_items(entry.get("tags"))
    texts += _iter_str_items(entry.get("categories"))
    asset_tokens: set[str] = set()
    for text in texts:
        asset_tokens |= _tokenize_words(text)
    return q_tokens.issubset(asset_tokens)


def _rank_band(rank: int) -> int:
    """Bucket source rank into 1-5, 6-10, 11-20 (Q9)."""
    if rank <= 5:
        return 0
    if rank <= 10:
        return 1
    if rank <= 20:
        return 2
    return 3


def _size_error(model: list[float], envelope: list[float]) -> float:
    """Mean-scaled relative axis difference on sorted extents (lower is closer)."""
    m = sorted(model, reverse=True)
    z = sorted(envelope, reverse=True)
    if any(zz <= 0 for zz in z):
        return float("inf")
    return round(sum(abs(mm - zz) / zz for mm, zz in zip(m, z)), 9)


def _int_value(value: Any) -> int | None:
    """Return ``value`` as a real int (excluding bool), or None."""
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _candidate(entry: dict[str, Any], query: str, rank: int) -> dict[str, Any]:
    """One search hit with its provenance; size fields filled by the caller."""
    raw_name = entry.get("name")
    name = raw_name if (raw_name is None or isinstance(raw_name, str)) else str(raw_name)
    raw_poly = _int_value(entry.get("polycount"))
    polycount = raw_poly if (raw_poly is not None and raw_poly >= 0) else None
    return {
        "asset_id": entry.get("id"),
        "name": name,
        "dimensions_m": entry.get("dimensions"),
        "polycount": polycount,
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
    for v in dims:
        num = _finite_float(v)
        if num is None or num <= 0:
            return False
    return True


@dataclass
class _ScoredHit:
    """Candidate paired with its precomputed zone-fit error for sorting."""

    candidate: dict[str, Any]
    size_error: float

    def sort_key(self) -> tuple[bool, int, float, int, str]:
        # Size-eligible candidates win the cap before unverified ones,
        # then rank band (1-5 / 6-10 / 11-20), size difference, best rank, id.
        cand = self.candidate
        return (
            cand["size_status"] != "pass",
            _rank_band(int(cand["best_source_rank"])),
            self.size_error,
            int(cand["best_source_rank"]),
            str(cand["asset_id"]),
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
            num = _finite_float(v)
            if num is not None and num <= 0:
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
) -> list[_ScoredHit]:
    """Filter one query's hits into scored candidates.

    Drops hits that fail the normalized word-level check or cannot fit
    the target size screen (three-axis tolerance for an object target;
    upper-limit-only for a zone_bbox fallback). Assets without usable
    dimensions stay in the returned list with ``size_status="unverified"``
    and ``size_error=0.0``.
    """
    screened: list[_ScoredHit] = []
    for rank, entry in enumerate(results, start=1):
        if not isinstance(entry, dict):
            continue
        asset_id = entry.get("id")
        if not isinstance(asset_id, str) or not asset_id:
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
            screened.append(_ScoredHit(cand, 0.0))
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
                screened.append(_ScoredHit(cand, _size_error(model_m, target_m)))
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
            screened.append(_ScoredHit(cand, _size_error(model_m, target_m)))
    return screened


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
    scene_refs: set[str] | None = None,
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
    missing_refs = [ref for ref in explicit_refs if scene_refs is None or ref not in scene_refs]
    if missing_refs:
        refs_text = ", ".join(missing_refs)
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
    obj_int = _int_value(obj_count)
    unmeasured_int = _int_value(unmeasured)
    count_matches_list = not (
        obj_int is not None
        and unmeasured_int is not None
        and (obj_int - unmeasured_int) != len(measurable)
    )
    if len(measurable) == 1 and count_matches_list:
        return measurable[0], "unique_zone_object", None

    if len(measurable) > 1 or (
        obj_int is not None and unmeasured_int is not None and (obj_int - unmeasured_int) > 1
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
    unmeasured_int = _int_value(unmeasured)
    partial_zone = (
        match_source == "unique_zone_object" and unmeasured_int is not None and unmeasured_int > 0
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
    unmeasured_int = _int_value(unmeasured)
    has_unmeasured = unmeasured_int is not None and unmeasured_int > 0
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
    zone: dict[str, Any],
    factor: float,
    objective: str,
    scene_refs: set[str] | None = None,
) -> tuple[dict[str, Any], list[float] | None, str | None]:
    """Identify the zone's sizing target in Q6 deterministic order.

    Order: explicit full DAG path -> unique matching short name -> unique
    measurable object in the zone -> zone_bbox fallback. Ambiguous matches
    never pick a winner arbitrarily and always explain the fallback.
    """
    name = zone.get("name", "")
    obj_count = zone.get("object_count")
    unmeasured = zone.get("unmeasured_count")
    if _int_value(obj_count) == 0:
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
        name, valid_objects, obj_count, unmeasured, factor, objective, scene_refs=scene_refs
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


def _merge_hits(seen: dict[str, _ScoredHit], screened: list[_ScoredHit]) -> None:
    """Deduplicate hits by asset_id, keeping all matched_queries and best rank."""
    for hit in screened:
        cand = hit.candidate
        aid = str(cand["asset_id"])
        hit_record = cand["matched_queries"][0]
        existing_hit = seen.get(aid)
        if existing_hit is None:
            seen[aid] = hit
            continue
        existing = existing_hit.candidate
        if hit_record not in existing["matched_queries"]:
            existing["matched_queries"].append(hit_record)
        if int(cand["best_source_rank"]) < int(existing["best_source_rank"]):
            existing["best_source_rank"] = cand["best_source_rank"]
        if existing["size_status"] != "pass" and cand["size_status"] == "pass":
            cand["matched_queries"] = existing["matched_queries"]
            cand["best_source_rank"] = existing["best_source_rank"]
            seen[aid] = hit


def _zone_candidates(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [*entry.get("candidates", []), *entry.get("unverified_candidates", [])]


def _assign_zone_candidates(entry: dict[str, Any], ordered_hits: list[_ScoredHit]) -> None:
    cands = [hit.candidate for hit in ordered_hits]
    shown_eligible = [c for c in cands if c["size_status"] == "pass"]
    shown_unverified = [c for c in cands if c["size_status"] != "pass"]
    entry["candidates"] = shown_eligible
    entry["unverified_candidates"] = shown_unverified
    entry["eligible_count"] = len(shown_eligible)
    entry["unverified_count"] = len(shown_unverified)


@dataclass
class _SearchRunState:
    """Shared per-pass soft budget and circuit-breaker state."""

    deadline: float
    clock: Callable[[], float]
    accepts_timeout: bool
    budget_exhausted: bool = False
    offline_circuit_broken: bool = False


def _accepts_timeout(search_fn: Callable[..., Any]) -> bool:
    """Return True when ``search_fn`` accepts a ``timeout`` keyword argument."""
    try:
        sig = inspect.signature(search_fn)
    except (TypeError, ValueError):
        return False
    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.VAR_KEYWORD or (
            param.name == "timeout"
            and param.kind
            in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        ):
            return True
    return False


def _refresh_zone_status(
    entry: dict[str, Any],
    *,
    failed: int = 0,
    succeeded: int = 0,
    budget_skipped: int = 0,
    offline_skipped: bool = False,
) -> None:
    if (failed > 0 or offline_skipped) and succeeded == 0:
        entry["status"] = "skipped"
        entry["skip_reason"] = "search_failed"
    elif budget_skipped > 0 and succeeded == 0:
        entry["status"] = "skipped"
        entry["skip_reason"] = "budget_exhausted"
    elif failed > 0 or budget_skipped > 0 or offline_skipped:
        entry["status"] = "partial"
    elif entry["status"] not in ("skipped", "partial"):
        entry["status"] = "ok" if entry["eligible_count"] > 0 else "empty"


def _process_zone(
    zone: dict[str, Any],
    queries: tuple[str, ...],
    factor: float,
    search_fn: Callable[..., dict[str, Any]],
    errors: list[dict[str, str]],
    truncation: dict[str, bool],
    state: _SearchRunState,
    objective: str = "",
    scene_refs: set[str] | None = None,
) -> tuple[dict[str, Any], list[_ScoredHit], int, int]:
    """Build one zone's recommendation entry, searching only when enabled & measurable."""
    name = zone.get("name", "")
    scope = f"recommendations:{name}"
    if not queries:
        disabled_target: dict[str, Any] = {
            "source": "zone_bbox",
            "screening_mode": "none",
            "geometry": "world_aabb",
            "name": name,
            "object_count": zone.get("object_count"),
            "unmeasured_count": zone.get("unmeasured_count"),
            "size_m": _to_metres(zone.get("size"), factor),
            "bbox_min_m": _to_metres(zone.get("bbox_min"), factor),
            "bbox_max_m": _to_metres(zone.get("bbox_max"), factor),
            "measurement": "disabled",
        }
        return (
            {
                "zone": name,
                "status": "skipped",
                "skip_reason": "recommendations_disabled",
                "target": disabled_target,
                "queries": [],
                "eligible_count": 0,
                "unverified_count": 0,
                "candidates": [],
                "unverified_candidates": [],
            },
            [],
            0,
            0,
        )

    target, size_screen, skip_reason = _resolve_target(
        zone, factor, objective, scene_refs=scene_refs
    )
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
        return entry, [], 0, 0

    screening_mode = str(target.get("screening_mode", "zone_envelope"))
    seen: dict[str, _ScoredHit] = {}
    succeeded = 0
    failed = 0
    budget_skipped = 0
    offline_skipped = False
    for query in queries:
        if state.offline_circuit_broken:
            offline_skipped = True
            entry["queries"].append(_unsearched_query(query))
            continue
        remaining = state.deadline - state.clock()
        if not state.budget_exhausted and (not math.isfinite(remaining) or remaining <= 0):
            state.budget_exhausted = True
            truncation["budget"] = True
            errors.append(
                _error(
                    scope,
                    "budget_exhausted",
                    f"recommendation {DEFAULT_RECOMMEND_BUDGET_S:g}s soft time budget "
                    "exhausted; remaining queries skipped",
                )
            )
        if state.budget_exhausted:
            budget_skipped += 1
            entry["queries"].append(_unsearched_query(query))
            continue
        try:
            call_kwargs: dict[str, Any] = {
                "query": query,
                "asset_type": SEARCH_ASSET_TYPE,
                "limit": SEARCH_LIMIT,
            }
            if state.accepts_timeout:
                call_kwargs["timeout"] = remaining
            data = search_fn(**call_kwargs)
            results = data.get("results") if isinstance(data, dict) else None
            total = data.get("total_count") if isinstance(data, dict) else None
            if not isinstance(results, list):
                raise ValueError(f"unexpected search payload: {type(data).__name__}")
        except Exception as e:  # network/index failure must never break the plan
            code = getattr(e, "code", None)
            err_code = code if isinstance(code, str) else "search_failed"
            errors.append(_error(scope, err_code, f"{type(e).__name__}: {e}"))
            failed += 1
            entry["queries"].append(_unsearched_query(query))
            if err_code in _SHARED_INDEX_FATAL_CODES:
                state.offline_circuit_broken = True
            continue
        succeeded += 1
        total_int = _int_value(total)
        entry["queries"].append(_searched_query(query, total_int))
        if total_int is not None and total_int > len(results):
            truncation["search"] = True
        _merge_hits(seen, _screen(results, query, size_screen, screening_mode=screening_mode))

    ordered_hits = sorted(seen.values(), key=lambda hit: hit.sort_key())
    if len(ordered_hits) > MAX_PER_ZONE:
        truncation["output"] = True
        ordered_hits = ordered_hits[:MAX_PER_ZONE]
    _assign_zone_candidates(entry, ordered_hits)
    _refresh_zone_status(
        entry,
        failed=failed,
        succeeded=succeeded,
        budget_skipped=budget_skipped,
        offline_skipped=offline_skipped,
    )
    return entry, ordered_hits, succeeded, failed


def _apply_scene_cap(
    zone_results: list[tuple[dict[str, Any], list[_ScoredHit]]],
    truncation: dict[str, bool],
) -> None:
    """Enforce MAX_PER_SCENE across all zones, keeping top-ranked candidates."""
    pooled = [
        (*hit.sort_key(), zone_idx, hit)
        for zone_idx, (_, hits) in enumerate(zone_results)
        for hit in hits
    ]
    if len(pooled) <= MAX_PER_SCENE:
        return
    truncation["output"] = True
    pooled.sort(key=lambda item: item[:-1])
    kept_by_zone: dict[int, list[_ScoredHit]] = {}
    for *_, zone_idx, hit in pooled[:MAX_PER_SCENE]:
        kept_by_zone.setdefault(zone_idx, []).append(hit)
    for zone_idx, (zone_rec, _) in enumerate(zone_results):
        kept = sorted(kept_by_zone.get(zone_idx, []), key=lambda hit: hit.sort_key())
        _assign_zone_candidates(zone_rec, kept)
        _refresh_zone_status(zone_rec)


def _build_policy(zones_recs: list[dict[str, Any]]) -> dict[str, Any]:
    modes = {
        z.get("target", {}).get("screening_mode")
        for z in zones_recs
        if z.get("status") != "skipped"
    }
    modes.discard(None)
    if modes == {"three_axis_tolerance"}:
        return {
            "mode": "object_tolerance",
            "geometry": "world_aabb",
            "upper_limit_only": False,
            "tolerance_band": [MIN_SIZE_RATIO, MAX_SIZE_RATIO],
            "clearance_verified": False,
            "collision_verified": False,
            "note": _OBJECT_TOLERANCE_NOTE,
        }
    if modes == {"three_axis_tolerance", "zone_envelope"}:
        return {
            "mode": "mixed",
            "geometry": "world_aabb",
            "upper_limit_only": False,
            "tolerance_band": [MIN_SIZE_RATIO, MAX_SIZE_RATIO],
            "clearance_verified": False,
            "collision_verified": False,
            "note": _MIXED_POLICY_NOTE,
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
    *,
    budget_s: float = DEFAULT_RECOMMEND_BUDGET_S,
    deadline: float | None = None,
    clock: Callable[[], float] | None = None,
) -> dict[str, Any]:
    """Compose the ``recommendations`` section from geometry + searches.

    ``zone_geometry`` is whatever the ``get_zone_geometry`` host helper
    returned (a dict with ``unit``/``zones``, or ``{"error": ...}``).
    ``search_fn`` is ``polyhaven.search_assets`` in production; tests may
    inject a fake. ``objective`` is used host-side only to resolve target
    objects by DAG path or short name and is never sent to ``search_fn``.
    ``budget_s`` / ``deadline`` enforce a monotonic soft time budget: the
    remaining budget is passed to ``search_fn`` when it accepts ``timeout``,
    no new searches start after it runs out, and an in-flight worker thread
    is never claimed to be forcibly killed. Never raises: every failure
    becomes a structured error entry, so the caller's plan survives untouched.
    """
    clock_fn = time.monotonic if clock is None else clock
    objective_text = objective if isinstance(objective, str) else ""
    if deadline is not None:
        dl = _finite_float(deadline)
        effective_deadline = dl if dl is not None else clock_fn() - 1.0
    else:
        bs = _finite_float(budget_s)
        safe_budget = bs if (bs is not None and bs > 0) else 0.0
        effective_deadline = clock_fn() + safe_budget
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

    scene_refs: set[str] = set()
    for z in zones_list:
        raw_objs = z.get("objects") if isinstance(z, dict) else None
        if not isinstance(raw_objs, list):
            continue
        for obj in raw_objs:
            if isinstance(obj, dict) and isinstance(obj.get("name"), str) and obj["name"]:
                scene_refs.add(obj["name"])
                scene_refs.add(obj["name"].rsplit("|", 1)[-1])

    state = _SearchRunState(
        deadline=effective_deadline,
        clock=clock_fn,
        accepts_timeout=_accepts_timeout(search_fn),
    )
    zone_results: list[tuple[dict[str, Any], list[_ScoredHit]]] = []
    total_succeeded = 0
    total_failed = 0
    for zone_name, queries in ZONE_SEARCH_QUERIES.items():
        zone = next(
            (z for z in zones_list if isinstance(z, dict) and z.get("name") == zone_name),
            None,
        )
        if zone is None:
            continue  # no such zone in this scene: nothing to report or search
        zone_rec, ordered_hits, succeeded, failed = _process_zone(
            zone,
            queries,
            factor,
            search_fn,
            errors,
            truncation,
            state,
            objective=objective_text,
            scene_refs=scene_refs,
        )
        recs["zones"].append(zone_rec)
        zone_results.append((zone_rec, ordered_hits))
        total_succeeded += succeeded
        total_failed += failed

    _apply_scene_cap(zone_results, truncation)
    recs["policy"] = _build_policy(recs["zones"])
    any_eligible = any(z["eligible_count"] > 0 for z in recs["zones"])

    if total_failed > 0 and total_succeeded == 0:
        recs["status"] = "offline"
    elif (
        total_failed > 0
        or truncation["budget"]
        or any(e["scope"] == "zone_geometry" for e in errors)
    ):
        recs["status"] = "partial"
    elif any_eligible:
        recs["status"] = "ok"
    else:
        recs["status"] = "empty"
    return recs


def _fmt_dims(dims: Any) -> str:
    if not isinstance(dims, (list, tuple)) or not dims:
        return "?"
    parts: list[str] = []
    for v in dims:
        num = _finite_float(v)
        if num is None:
            return "?"
        parts.append(f"{num:g}")
    return "x".join(parts)


def _fallback_suffix(target: dict[str, Any]) -> str:
    fb = target.get("fallback_reason")
    if not fb:
        return ""
    suffix = f" fallback={fb}"
    amb = target.get("ambiguous_matches")
    if amb:
        suffix += f"({','.join(amb)})"
    return suffix


def format_recommend_cos(recs: dict[str, Any]) -> str:
    """Short RECOMMEND block for scene_plan's CoS output (opt-in only).

    Carries the status, the target and its size basis (including
    completeness and any ambiguity/fallback reason), the candidate ids
    with matched queries, sizes, and match/unverified reasons, and the
    truncation note. Indented to sit under scene_plan's existing
    sections.
    """
    policy = recs.get("policy", {})
    mode = policy.get("mode", "zone_envelope")
    geom = policy.get("geometry", "world_aabb")
    if mode == "object_tolerance":
        policy_label = f"object_tolerance({geom} {MIN_SIZE_RATIO:g}-{MAX_SIZE_RATIO:g}x)"
    elif mode == "mixed":
        policy_label = f"mixed({geom} {MIN_SIZE_RATIO:g}-{MAX_SIZE_RATIO:g}x/upper-limit)"
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
            lines.append("    no zones in this scene")
    for zone in zones:
        if zone.get("status") == "skipped":
            if zone.get("skip_reason") == "recommendations_disabled":
                lines.append(f"    {zone.get('zone')}: skipped (recommendations_disabled)")
                continue
            target = zone.get("target", {})
            line = f"    {zone.get('zone')}: skipped ({zone.get('skip_reason')})"
            obj_count = target.get("object_count")
            if obj_count is not None:
                unmeasured = target.get("unmeasured_count")
                line += f" objects={obj_count} unmeasured={0 if unmeasured is None else unmeasured}"
            source = target.get("source")
            if source:
                line += (
                    f" target={source}({target.get('name')})"
                    if source != "zone_bbox" and target.get("name")
                    else f" target={source}"
                )
            line += _fallback_suffix(target)
            lines.append(line)
            continue
        target = zone.get("target", {})
        source = target.get("source", "zone_bbox")
        complete_yn = "y" if target.get("measurement_complete", True) else "n"
        q_names = ",".join(str(q.get("query")) for q in zone.get("queries", []))
        counts = (
            f"queries={q_names} ({zone.get('eligible_count', 0)} eligible, "
            f"{zone.get('unverified_count', 0)} unverified)"
        )
        if source == "zone_bbox":
            target_line = (
                f"    {zone.get('zone')}: target=zone_bbox "
                f"{_fmt_dims(target.get('size_m'))}m meas={target.get('measurement')} "
                f"{counts} complete={complete_yn}{_fallback_suffix(target)}"
            )
        else:
            target_line = (
                f"    {zone.get('zone')}: target={source}({target.get('name')}) "
                f"{_fmt_dims(target.get('size_m'))}m tol={MIN_SIZE_RATIO:g}-{MAX_SIZE_RATIO:g}x "
                f"meas={target.get('measurement')} {counts} complete={complete_yn}"
            )
        if zone.get("status") == "partial":
            searched_cnt = sum(1 for q in zone.get("queries", []) if q.get("searched"))
            total_cnt = len(zone.get("queries", []))
            target_line += f" status=partial({searched_cnt}/{total_cnt})"
        lines.append(target_line)
        n = 0
        for cand in _zone_candidates(zone):
            n += 1
            via = ",".join(
                f"{m.get('query')}@{m.get('rank')}" for m in cand.get("matched_queries", [])
            )
            lines.append(
                f"      {n}. {cand.get('asset_id')} rank={cand.get('best_source_rank')} "
                f"via=[{via}] {_fmt_dims(cand.get('dimensions_m'))}m {cand.get('reason_code')} "
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
        codes = ",".join(dict.fromkeys(str(e.get("code")) for e in errors if e.get("code")))
        if codes:
            tail += f" ({codes})"
    lines.append(tail)
    return "\n".join(lines)
