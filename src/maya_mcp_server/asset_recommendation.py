"""Host-side Poly Haven model recommendations for scene_plan (opt-in).

With ``scene_plan(recommend_assets=True)`` the plan gains a
``recommendations`` section. Everything here runs on the host: the Maya
side never goes online. The module reads the zone geometry the
``_mcp_scene`` module reports (through the ``get_zone_geometry`` host
helper in scene_tools), searches the Poly Haven models index for each
zone's mapped query words via ``polyhaven.search_assets``, filters hits
with a normalized word-level check, deduplicates across keywords, sorts
by rank band and size difference, and caps results per zone and for the
whole scene.

Advisory only: recommendations name candidates and say why; nothing is
downloaded, imported, or placed, and a search failure never changes the
plan itself.

T1 scope (#217): furniture zone with ``chair``.
T2 scope (#218): all 7 built-in zones, normalized word-level check,
cross-keyword dedup, rank-band + size-difference sorting, and the
3-per-zone / 12-per-scene caps.
Explicit target objects and the three-axis tolerance band are T3 (#219);
the soft time budget is T4 (#220).
"""

from __future__ import annotations

import math
import re
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

# Q9: at most 3 candidates per zone and 12 across the whole scene
# (eligible first, then unverified; both kinds share the cap).
MAX_PER_ZONE = 3
MAX_PER_SCENE = 12

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
    texts += [str(t) for t in entry.get("tags") or []]
    texts += [str(c) for c in entry.get("categories") or []]
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


def _screen(results: list[Any], query: str, envelope_m: list[float]) -> list[_ScoredHit]:
    """Filter one query's hits into scored candidates.

    Drops hits that fail the normalized word-level check or cannot fit
    the zone envelope. Assets without usable dimensions stay in the
    returned list with ``size_status="unverified"`` and ``size_error=0.0``.
    """
    screened: list[_ScoredHit] = []
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
            screened.append(_ScoredHit(cand, 0.0))
            continue
        dims_f = [float(v) for v in dims]
        if _fits_envelope(dims_f, envelope_m):
            largest = max(dims_f)
            zone_largest = max(envelope_m)
            cand["size_status"] = "pass"
            cand["reason_code"] = "fits_zone_envelope"
            cand["match_reason"] = (
                f"largest side {largest:g} m within the zone envelope's "
                f"largest side {zone_largest:g} m (world AABB upper limit, "
                "per sorted axis)"
            )
            screened.append(_ScoredHit(cand, _size_error(dims_f, envelope_m)))
    return screened


def _searched_query(query: str, total_matches: int | None) -> dict[str, Any]:
    return {"query": query, "searched": True, "total_matches": total_matches}


def _unsearched_query(query: str) -> dict[str, Any]:
    return {"query": query, "searched": False, "total_matches": None}


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


def _refresh_zone_status(entry: dict[str, Any], *, failed: int = 0, succeeded: int = 0) -> None:
    if failed > 0 and succeeded == 0:
        entry["status"] = "skipped"
        entry["skip_reason"] = "search_failed"
    elif failed > 0:
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
) -> tuple[dict[str, Any], list[_ScoredHit], int, int]:
    """Build one zone's recommendation entry, searching only when enabled & measurable."""
    name = zone.get("name", "")
    scope = f"recommendations:{name}"
    size_m = _to_metres(zone.get("size"), factor)
    # Unrounded for the size screen (rounded=False), rounded for display.
    size_screen = _to_metres(zone.get("size"), factor, rounded=False)
    unmeasured = zone.get("unmeasured_count")
    is_empty_zone = zone.get("object_count") == 0
    if is_empty_zone:
        measurement = "empty"
    elif size_m is None:
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
    if not queries:
        entry["status"] = "skipped"
        entry["skip_reason"] = "recommendations_disabled"
        return entry, [], 0, 0
    if is_empty_zone:
        entry["queries"] = [_unsearched_query(q) for q in queries]
        return entry, [], 0, 0
    if size_screen is None:  # same condition that set unmeasurable_target above
        entry["status"] = "skipped"
        entry["skip_reason"] = "unmeasurable_target"
        entry["queries"] = [_unsearched_query(q) for q in queries]
        return entry, [], 0, 0

    seen: dict[str, _ScoredHit] = {}
    succeeded = 0
    failed = 0
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
            failed += 1
            entry["queries"].append(_unsearched_query(query))
            continue
        succeeded += 1
        total_int = total if isinstance(total, int) else None
        entry["queries"].append(_searched_query(query, total_int))
        if total_int is not None and total_int > len(results):
            truncation["search"] = True
        _merge_hits(seen, _screen(results, query, size_screen))

    ordered_hits = sorted(seen.values(), key=lambda hit: hit.sort_key())
    if len(ordered_hits) > MAX_PER_ZONE:
        truncation["output"] = True
        ordered_hits = ordered_hits[:MAX_PER_ZONE]
    _assign_zone_candidates(entry, ordered_hits)
    _refresh_zone_status(entry, failed=failed, succeeded=succeeded)
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


def gather_recommendations(
    zone_geometry: Any, search_fn: Callable[..., dict[str, Any]]
) -> dict[str, Any]:
    """Compose the ``recommendations`` section from geometry + searches.

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
            zone, queries, factor, search_fn, errors, truncation
        )
        recs["zones"].append(zone_rec)
        zone_results.append((zone_rec, ordered_hits))
        total_succeeded += succeeded
        total_failed += failed

    _apply_scene_cap(zone_results, truncation)
    any_eligible = any(z["eligible_count"] > 0 for z in recs["zones"])

    if total_failed > 0 and total_succeeded == 0:
        recs["status"] = "offline"
    elif total_failed > 0 or any(e["scope"] == "zone_geometry" for e in errors):
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
    and its size basis, the candidate ids with matched queries and sizes,
    and the truncation note. Indented to sit under scene_plan's existing
    sections.
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
            lines.append("    no zones in this scene")
    for zone in zones:
        if zone.get("status") == "skipped":
            lines.append(f"    {zone.get('zone')}: skipped ({zone.get('skip_reason')})")
            continue
        target = zone.get("target", {})
        q_names = ",".join(str(q.get("query")) for q in zone.get("queries", []))
        lines.append(
            f"    {zone.get('zone')}: target=zone_bbox "
            f"{_fmt_dims(target.get('size_m'))}m meas={target.get('measurement')} "
            f"queries={q_names} ({zone.get('eligible_count', 0)} eligible, "
            f"{zone.get('unverified_count', 0)} unverified)"
        )
        n = 0
        for cand in _zone_candidates(zone):
            n += 1
            via = ",".join(
                f"{m.get('query')}@{m.get('rank')}" for m in cand.get("matched_queries", [])
            )
            lines.append(
                f"      {n}. {cand.get('asset_id')} rank={cand.get('best_source_rank')} "
                f"via=[{via}] {_fmt_dims(cand.get('dimensions_m'))}m {cand.get('reason_code')}"
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
