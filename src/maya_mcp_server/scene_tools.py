"""MCP scene tools for spatial awareness.

Provides 4 high-level tools following the snapshot → inspect → measure → assert pattern.
Each tool auto-injects the _mcp_scene module into Maya on first call.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypedDict

from maya_mcp_server import polyhaven
from maya_mcp_server.asset_recommendation import format_recommend_cos, gather_recommendations
from maya_mcp_server.client import ensure_module_injected, exec_module_code, module_call
from maya_mcp_server.cos_formatter import (
    format_assert_cos,
    format_inspect_cos,
    format_measure_cos,
    format_scene_cos,
    format_zone_map_cos,
)
from maya_mcp_server.pipeline import TOOL_ANNOTATIONS
from maya_mcp_server.scene_cache import SceneCache
from maya_mcp_server.security import InputValidationError


if TYPE_CHECKING:
    from fastmcp import FastMCP


logger = logging.getLogger(__name__)

# Module source paths for _mcp_scene. The separate files are concatenated
# into the SAME injected module in this order: introspection, checks you
# register, zone geometry, scene state. One module name, one trigger; a syntax
# or import-time error in any of them stops the whole module from loading.
# The host-side files are still maintained separately.
_MODULE_SOURCE = Path(__file__).parent / "maya_scene_module.py"
_INTROSPECT_FRAGMENT = Path(__file__).parent / "introspect_module.py"
_VALIDATOR_FRAGMENT = Path(__file__).parent / "validator_module.py"
_ZONE_GEOMETRY_FRAGMENT = Path(__file__).parent / "zone_geometry_module.py"
_SCENE_STATE_FRAGMENT = Path(__file__).parent / "scene_state_module.py"

# Global cache per session (keyed by session_key)
_caches: dict[str, SceneCache] = {}

# Track which sessions have the module injected
_injected_sessions: set[str] = set()


def _get_cache(session_key: str | None) -> SceneCache:
    """Get or create cache for a session."""
    key = session_key or "_default"
    if key not in _caches:
        _caches[key] = SceneCache(ttl_seconds=5.0)
    return _caches[key]


def mark_dirty(session_key: str | None = None) -> None:
    """Mark cache as dirty after scene modification.

    Call this from session_manager after execute_code/write_module.
    """
    key = session_key or "_default"
    if key in _caches:
        _caches[key].mark_dirty()


async def _ensure_module_injected(client: Any, session_key: str | None) -> None:
    """Ensure _mcp_scene module is injected into Maya session.

    Delegates to client.ensure_module_injected; reads the module
    source from disk and writes it via write_module. Only injects once
    per session.
    """
    await ensure_module_injected(
        client,
        session_key,
        module_name="_mcp_scene",
        source_path=_MODULE_SOURCE,
        tmp_prefix="_mcp_scene_src_",
        injected_sessions=_injected_sessions,
        extra_source_paths=[
            _INTROSPECT_FRAGMENT,
            _VALIDATOR_FRAGMENT,
            _ZONE_GEOMETRY_FRAGMENT,
            _SCENE_STATE_FRAGMENT,
        ],
    )


async def _execute_scene_code(
    client: Any,
    code: str,
    session_key: str | None,
    use_cache: bool = True,
    cache_key: str | None = None,
) -> Any:
    """Execute scene query code with optional caching.

    Args:
        client: MayaClient instance.
        code: Python code to execute.
        session_key: Session key for cache lookup.
        use_cache: Whether to use cache.
        cache_key: Cache key for this query.

    Returns:
        Parsed result.
    """

    # The decoded reply is whatever JSON Maya sent back, so it stays Any:
    # exec_module_code already declares -> Any and no narrower type can be
    # proven at this layer.
    async def fetch() -> Any:
        return await exec_module_code(client, code)

    if use_cache and cache_key:
        return await _get_cache(session_key).get_or_fetch(cache_key, fetch)
    return await fetch()


async def _read_scene_modified(client: Any, session_key: str | None, caller: str) -> bool:
    """Read Maya's unsaved-changes flag, fresh, through the _mcp_scene unit.

    One read for scene_snapshot and scene_rollback: never cached, because a
    change made one second ago has to show up, and one error message when
    Maya cannot answer. The caller's name goes into that message so a reader
    knows which tool failed. Nothing here turns the flag into a decision —
    it is reported, never acted on.
    """
    reply = await _execute_scene_code(
        client,
        module_call("_mcp_scene", "get_scene_modified"),
        session_key,
        use_cache=False,
    )
    scene_modified = reply.get("scene_modified")
    if not isinstance(scene_modified, bool):
        raise RuntimeError(f"{caller} could not read the unsaved-changes flag: {reply!r}")
    return scene_modified


# Wired to scene_plan's opt-in recommend_assets (#177/#217): the helper stays
# out of the default path, so default output remains byte-identical.
async def get_zone_geometry(client: Any, session_key: str | None = None) -> Any:
    """Read fresh zone boxes and object sizes through the _mcp_scene unit.

    Internal host-side seam, not an MCP tool. Geometry is never cached here:
    a moved object must be measured again on the next call. scene_plan's
    recommendation pass composes this with the host-side asset search.
    """
    await _ensure_module_injected(client, session_key)
    return await _execute_scene_code(
        client,
        module_call("_mcp_scene", "get_zone_geometry"),
        session_key,
        use_cache=False,
    )


async def _recommend_for_plan(
    client: Any, session_key: str | None, objective: str = ""
) -> dict[str, Any]:
    """Compose scene_plan's recommendations section; search and geometry
    failures never break the plan.

    The Maya-side geometry read is wrapped into the same error-dict shape the
    Maya side already reports, so gather_recommendations stays the single
    place that turns problems into structured errors. The search runs on the
    calling loop for now: the worker thread arrives together with the soft
    time budget in T4 (Q8 of #31), which owns the timeout machinery.
    """
    geometry: Any
    try:
        geometry = await get_zone_geometry(client, session_key)
    except Exception as e:  # transport-level failure; the Maya side has its own
        geometry = {"error": {"code": "query_failed", "message": f"{type(e).__name__}: {e}"}}
    return gather_recommendations(geometry, polyhaven.search_assets, objective=objective)


# --- Token Budget Management ---


class _BudgetEntry(TypedDict):
    max_tokens: int
    detail: str
    max_objects: int


class TokenBudget:
    """Auto-adjust detail level based on scene size."""

    BUDGETS: dict[str, _BudgetEntry] = {
        "small": {"max_tokens": 2000, "detail": "compact", "max_objects": 50},
        "medium": {"max_tokens": 5000, "detail": "compact", "max_objects": 200},
        "large": {"max_tokens": 10000, "detail": "summary", "max_objects": 500},
        "huge": {"max_tokens": 15000, "detail": "hierarchy_only", "max_objects": 1000},
    }

    @staticmethod
    def auto_select_level(object_count: int) -> str:
        if object_count <= 50:
            return "small"
        if object_count <= 200:
            return "medium"
        if object_count <= 500:
            return "large"
        return "huge"

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Rough token estimate: ~4 chars per token."""
        return len(text) // 4


# --- MCP Tool Registration ---


def register_scene_tools(mcp: FastMCP) -> None:
    """Register scene tools on the FastMCP instance.

    Args:
        mcp: FastMCP server instance.
    """

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_snapshot"])
    async def scene_snapshot(
        detail: str = "compact",
        format: str = "cos",
        session_key: str | None = None,
    ) -> str:
        """Get a complete spatial overview of the current Maya scene.

        Returns a structured description of ALL objects with positions, sizes, and types.
        Call this once at the start of each task to see the whole scene before changing it.

        The first line ends with MODIFIED=y or MODIFIED=n. y means the scene
        has changes that were never saved; n means it has none. This is
        Maya's own flag for the whole scene, so it says nothing about which
        object changed. Changes made through this server's own tools count
        too, so y does not mean a person edited the scene. JSON output
        carries the same fact as the top-level scene_modified field. The flag
        is read again on every call and never comes from the cache, while the
        object list may be a few seconds old.

        Boundary: Disambiguated from scene_inspect (deep-dive inspection of
        specific objects or zones) and scene_nodes (granular DAG/DG node
        name discovery with pagination).

        Args:
            detail: Detail level - "compact" (fast),
                "standard" (+materials/mesh stats), "full" (+vertices).
            format: Output format - "cos" (CoS: short one-line-per-object text,
                compact) or "json" (full JSON).
            session_key: Maya session key (auto-selected if only one session).

        Returns:
            CoS-formatted scene description (default) or JSON, either with
            the unsaved-changes flag.

        Performance: 100 objects < 50ms, 1000 objects < 200ms.

        Example:
            scene_snapshot() → SCENE[100obj, 3zones] UNIT=cm UP=y MODIFIED=n\\nENTRANCE: ...
            scene_snapshot(format="json") → {"scene": {...}, "scene_modified": false}
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)

        # Ensure module is injected
        await _ensure_module_injected(client, session_key)

        # Get scene graph
        scene_data = await _execute_scene_code(
            client,
            module_call("_mcp_scene", "get_scene_graph", detail),
            session_key,
            use_cache=True,
            cache_key=f"scene_graph_{detail}",
        )

        # Also get zone map
        zone_data = await _execute_scene_code(
            client,
            module_call("_mcp_scene", "get_zone_map"),
            session_key,
            use_cache=True,
            cache_key="zone_map",
        )

        # Read the unsaved-changes flag fresh on every call. The object list
        # above may come from the cache; this fact may not. Nothing caches it,
        # so a change made after the previous call shows up right away.
        scene_modified = await _read_scene_modified(client, session_key, "scene_snapshot")

        # Auto-adjust token budget
        obj_count = scene_data.get("stats", {}).get("total", 0)
        budget_level = TokenBudget.auto_select_level(obj_count)
        budget = TokenBudget.BUDGETS[budget_level]
        max_objects = budget["max_objects"]

        if format == "json":
            result = {
                "scene": scene_data,
                "zones": zone_data.get("zones", []),
                "budget": budget_level,
                "object_count": obj_count,
                "scene_modified": scene_modified,
            }
            output = json.dumps(result, indent=2)
        else:
            output = format_scene_cos(
                scene_data,
                zones=zone_data.get("zones", []),
                max_objects=max_objects,
                scene_modified=scene_modified,
            )

        return output

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_inspect"])
    async def scene_inspect(
        target: str,
        include_neighbors: bool = True,
        format: str = "cos",
        session_key: str | None = None,
    ) -> str:
        """Deep inspection of a specific object or zone.

        Returns detailed properties including transform, BBox, material, mesh stats,
        and optionally nearby objects with distances.

        Boundary: Disambiguated from scene_snapshot (broad whole-scene
        spatial overview) and scene_describe (API-level attribute metadata,
        types, and connection wiring).

        Args:
            target: Object name or zone name to inspect.
            include_neighbors: Whether to include nearby objects (default True).
            format: Output format - "cos" or "json".
            session_key: Maya session key.

        Returns:
            Detailed inspection in CoS or JSON format.

        Example:
            scene_inspect("wall_north") → INSPECT: wall_north[mesh]@(0,0,500) ...
            scene_inspect("entrance", include_neighbors=True) → zone details + neighbors
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)

        # Ensure module is injected
        await _ensure_module_injected(client, session_key)

        # First try as a zone name
        zone_data = await _execute_scene_code(
            client,
            module_call("_mcp_scene", "get_zone_map"),
            session_key,
            use_cache=True,
            cache_key="zone_map",
        )

        zones = zone_data.get("zones", [])
        matched_zone = None
        for zone in zones:
            if zone.get("name", "").lower() == target.lower():
                matched_zone = zone
                break

        if matched_zone:
            # Zone inspection
            if format == "json":
                return json.dumps({"zone": matched_zone}, indent=2)
            else:
                return format_zone_map_cos([matched_zone])

        # Object inspection
        code = f"""import _mcp_scene, json
result = {{}}
try:
    import maya.cmds as cmds
    import maya.api.OpenMaya as om2

    sel = om2.MSelectionList()
    sel.add(json.loads({json.dumps(json.dumps(target))}))
    dag = sel.getDagPath(0)
    fn = om2.MFnDagNode(dag)
    bbox = fn.boundingBox
    world = dag.inclusiveMatrix()

    result = {{
        "name": fn.name(),
        "type": _mcp_scene._classify_node(dag),
        "position": _mcp_scene._matrix_to_pos(world),
        "bbox": {{
            "min": _mcp_scene._vec3_to_list(bbox.min),
            "max": _mcp_scene._vec3_to_list(bbox.max),
        }},
        "size": _mcp_scene._get_bbox_size(bbox),
        "material": _mcp_scene._get_material_for_dag(dag),
        "unit": cmds.currentUnit(query=True, linear=True),
        "parent": None,
    }}

    # Parent
    if dag.length() > 1:
        parent_dag = om2.MDagPath(dag)
        parent_dag.pop()
        result["parent"] = om2.MFnDagNode(parent_dag).name()

    # Children
    children = []
    for i in range(dag.childCount()):
        child = dag.child(i)
        children.append(om2.MFnDagNode(child).name())
    result["children"] = children

    # Mesh stats
    if result["type"] == "mesh":
        dag_path = om2.MDagPath.getAPathTo(dag)
        mesh_fn = om2.MFnMesh(dag_path)
        result["vertex_count"] = mesh_fn.numVertices
        result["face_count"] = mesh_fn.numPolygons
except Exception as e:
    result = {{"error": {{"code": "inspect_failed", "message": str(e)}}}}

result
"""
        obj_data = await _execute_scene_code(client, code, session_key, use_cache=False)

        # Neighbors
        neighbors = None
        if include_neighbors and "error" not in obj_data:
            spatial_code = module_call("_mcp_scene", "get_spatial_index")
            spatial_data = await _execute_scene_code(
                client,
                spatial_code,
                session_key,
                use_cache=True,
                cache_key="spatial_index",
            )

            # Find neighbors for this object
            obj_names = spatial_data.get("objects", [])
            pairs = spatial_data.get("pairs", [])
            try:
                obj_idx = obj_names.index(target)
                neighbor_indices = set()
                for pair in pairs:
                    if pair[0] == obj_idx:
                        neighbor_indices.add((pair[1], pair[2]))
                    elif pair[1] == obj_idx:
                        neighbor_indices.add((pair[0], pair[2]))

                neighbors = []
                for idx, dist in sorted(neighbor_indices, key=lambda x: x[1]):
                    neighbors.append({"name": obj_names[idx], "distance": dist})
            except (ValueError, IndexError):
                pass

        if format == "json":
            result = {"object": obj_data, "neighbors": neighbors}
            return json.dumps(result, indent=2)
        else:
            return format_inspect_cos(obj_data, neighbors=neighbors)

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_measure"])
    async def scene_measure(
        obj_a: str,
        obj_b: str,
        mode: str = "center",
        format: str = "cos",
        session_key: str | None = None,
    ) -> str:
        """Measure the spatial relationship between two objects.

        Call this in the compute step (the second of ICEV's four steps), to turn a spatial
        question into a number before you execute a change: size a clearance
        before moving something, prove two objects interpenetrate before you
        separate them, or get the axis detail behind an overlap that
        scene_validate reported.

        Read-only and idempotent: it queries world-space bounding boxes and
        never modifies the scene, so no checkpoint file is written.
        Requires an active Maya session.

        Every mode measures world-space AABBs, not the mesh surface and not
        the object origin. The modes differ in what the number means:
          center     distance between the AABB midpoints.
          surface    distance between the closest facing AABB corners — an
                     axis-aligned approximation, so it over-reports clearance
                     for rotated or concave geometry.
          clearance  SIGNED, and 0 is NOT a "merely touching" signal. Per
                     axis the gap is +separated / 0=touching / -penetrating:
                     > 0  euclidean distance across the STRICTLY SEPARATED
                          axes only. Penetrating axes contribute 0, so they
                          are invisible in this number.
                     = 0  no axis is strictly separated and at least one axis
                          is exactly touching. The other axes may be deeply
                          penetrating, so 0 does NOT mean the boxes just touch.
                     < 0  all three axes penetrate; the value is the
                          SHALLOWEST penetration depth, the minimum
                          translation needed to pull them apart.
                     bbox_overlap is true if and only if all three axes
                     strictly penetrate. A single penetrating axis already
                     makes it read false, so it can never be read as "no
                     penetration".
                     Read details.clearances_xyz for the signed per-axis truth
                     before concluding anything from distance alone.
          bbox       overlap test. On overlap, distance is 0 and overlap_dims
                     holds the per-axis penetration extents; otherwise
                     distance is euclidean and gaps_xyz holds the per-axis gaps.

        Distances are in the scene's current linear unit (cm, m or mm), not
        always centimetres.

        Boundary: Disambiguated from scene_inspect (per-object property
        deep-dive), scene_snapshot (whole-scene spatial overview) and
        scene_assert (checks the scene against expected values rather than
        measuring one pair).

        Args:
            obj_a: First object name.
            obj_b: Second object name.
            mode: What the returned number means — see the list above.
            format: Output format - "cos" or "json".
            session_key: Maya session key.

        Returns:
            Measurement result with the mode's distance, per-axis details,
            and bbox_overlap flag.

        Example:
            scene_measure("wall_north", "counter_A", mode="clearance")
            → MEASURE[clearance]: wall_north ↔ counter_A = 45cm
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)

        # Ensure module is injected
        await _ensure_module_injected(client, session_key)

        code = module_call("_mcp_scene", "measure", obj_a, obj_b, mode)
        result = await _execute_scene_code(client, code, session_key, use_cache=False)

        if format == "json":
            return json.dumps(result, indent=2)
        else:
            return format_measure_cos(result)

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_assert"])
    async def scene_assert(
        expectations: str,
        format: str = "cos",
        session_key: str | None = None,
    ) -> str:
        """Verify scene state matches expected values.

        Use this after modifications to confirm the scene is in the desired state.
        This is the check step (the last of ICEV's four steps).

        Boundary: Disambiguated from scene_validate (checks relational
        spatial constraints across zones rather than exact expected values
        for named objects).

        Args:
            expectations: JSON string defining expected state.
                Format: {"obj_name": {"position": [x,y,z], "bbox_max": [x,y,z], ...}}
                Supported properties: position, bbox_max, bbox_min, exists, material.
            format: Output format - "cos" or "json".
            session_key: Maya session key.

        Returns:
            Pass/fail result with mismatches.

        Example:
            scene_assert('{"wall_north": {"position": [0,0,500], "exists": true}}')
            → ASSERT[PASS]: 2 checks
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)

        # Ensure module is injected
        await _ensure_module_injected(client, session_key)

        try:
            json.loads(expectations)
        except json.JSONDecodeError as e:
            raise InputValidationError(f"expectations must be valid JSON: {e}") from e
        code = module_call("_mcp_scene", "assert_scene_state", expectations)
        result = await _execute_scene_code(client, code, session_key, use_cache=False)

        if format == "json":
            return json.dumps(result, indent=2)
        else:
            return format_assert_cos(result)

    # ============================================================
    # P0: Spatial Constraint Validation
    # ============================================================

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_validate"])
    async def scene_validate(
        rules: str,
        format: str = "cos",
        session_key: str | None = None,
    ) -> str:
        """Validate scene against spatial constraints.

        Checks the scene for constraint violations like minimum clearance,
        object limits, overlaps, and height requirements. This is a read-only
        check without auto_fix mutations (it cannot modify or repair objects;
        for automated fixes, see scene_plan with auto_fix=True). Because it is
        non-destructive, it needs no undo or rollback checkpoint.
        Requires an active Maya session.

        Boundary: Disambiguated from scene_review (a full check of scene
        quality across 11 checks) and scene_assert (verifies specific numeric
        values or object existence).

        Args:
            rules: JSON string with constraint rules. Format:
                [{"type": "min_clearance", "zone": "entrance", "value": 180},
                 {"type": "max_objects", "value": 5000},
                 {"type": "no_overlap", "objects": ["wall_a", "shelf_b"]},
                 {"type": "min_height", "objects": ["door"], "value": 250}]
                Types: min_clearance, max_objects, no_overlap, min_height, max_height
            format: Output format - "cos" or "json".
            session_key: Maya session key.

        Returns:
            Validation result with violations list.
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)
        await _ensure_module_injected(client, session_key)

        try:
            rules_obj = json.loads(rules)
        except json.JSONDecodeError as e:
            raise InputValidationError(f"rules must be valid JSON: {e}") from e
        code = module_call("_mcp_scene", "check_constraints", rules_obj)
        result = await _execute_scene_code(client, code, session_key, use_cache=False)

        if format == "json":
            return json.dumps(result, indent=2)
        else:
            passed = "PASS" if result.get("passed") else "FAIL"
            lines = [
                f"VALIDATE[{passed}]: {result.get('checked', 0)} checks, {result.get('violation_count', 0)} violations"
            ]
            for v in result.get("violations", [])[:10]:
                lines.append(f"  VIOLATION: {v.get('type')} - {v}")
            return "\n".join(lines)

    # ============================================================
    # P0: Scene Checkpoint / Rollback
    # ============================================================

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_checkpoint"])
    async def scene_checkpoint(
        name: str | None = None,
        overwrite: bool = False,
        session_key: str | None = None,
    ) -> str:
        """Save the current scene to a `.ma` file on disk under checkpoints/.

        Boundary: Disambiguated from scene_checkpoint_list (list the
        checkpoint files already written) and scene_rollback (open one and
        point the scene at it) — scene_checkpoint is the save half.

        Writes a self-contained .ma into a checkpoints/ directory next to
        the scene file. A scene that was never saved to disk needs an
        explicit name, and its temporary checkpoint goes under the Maya
        workspace — returned with original_file_status="no_original_file"
        and scene_rebound_to=null. Same-name checkpoints are rejected
        unless overwrite=True (the old file is preserved via rename).

        Honest bounds: the file contains no undo history \u2014 after
        scene_rollback, call scene_snapshot to rebuild context.
        References are flattened (self-contained, no write-back).
        Assumes one scene file per session.

        Args:
            name: Checkpoint name (^[A-Za-z0-9_-]+$). Required when the scene
                was never saved to disk.
            overwrite: Replace a same-name checkpoint, preserving the old file.
            session_key: Maya session key.

        Returns:
            Checkpoint info: filename, path, counts, original_file_status,
            adhoc flag.
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)
        await _ensure_module_injected(client, session_key)

        code = module_call("_mcp_scene", "save_checkpoint", name=name, overwrite=overwrite)
        result = await _execute_scene_code(client, code, session_key, use_cache=False)
        return json.dumps(result, indent=2)

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_rollback"])
    async def scene_rollback(
        filename: str,
        discard_current_state: bool = False,
        session_key: str | None = None,
    ) -> str:
        """Open a checkpoint file and point the scene at its original path (S2).

        Boundary: Disambiguated from scene_checkpoint (save a checkpoint from
        the current scene) and scene_checkpoint_list (list the ones
        already written) — scene_rollback is the read-back half.

        Before opening, the current scene is saved to a file first
        (auto_before_rollback); if that fails, the read-back aborts \u2014 pass
        discard_current_state=True to escape (the result reports
        safety_snapshot="skipped_by_user"). The scene points back only when
        it has a file path at read-back time; otherwise it stays on the
        checkpoint path (S1) and scene_rebound_to is null.

        The checkpoint file carries no undo history \u2014 call scene_snapshot
        afterwards to rebuild context.

        The result also says scene_modified_before: whether the scene still had
        changes that were never saved at the moment this call read the flag \u2014
        a read of its own, just before the rollback request and before any file
        is opened. It is the same Maya flag scene_snapshot reports; after the
        open, that flag describes the checkpoint, not the scene being replaced.
        The value never changes what this tool does: a changed scene and a clean
        scene take the same path, and the copy written before the switch behaves
        exactly as before (safety_snapshot reports "skipped_by_user" only when
        discard_current_state lets a failed save through). The one new failure
        is Maya refusing to answer that question: the call then errors, with
        nothing opened yet, instead of printing a made-up "clean".

        That read is its own round trip, so it is worth saying what it covers
        when calls overlap: two scene_rollback calls for one session can each
        run their own read and their own switch. The value then describes the
        scene as it was at that read, which may be a scene the other call has
        already replaced. Nothing is gated by that difference, and
        scene_name_before still names the scene the rollback itself read (empty
        when the scene was never saved).

        Args:
            filename: Checkpoint filename from scene_checkpoint_list
                (cp_*.ma or prev_*.ma).
            discard_current_state: Escape hatch \u2014 proceed even if saving
                the current scene fails.
            session_key: Maya session key.

        Returns:
            Structured result: success, scene_name_before/after,
            original_file_status, scene_rebound_to, safety_snapshot,
            scene_modified_before.
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)
        await _ensure_module_injected(client, session_key)

        # Read the unsaved-changes flag while the scene is still the one being
        # replaced. After the open it would describe the checkpoint instead.
        scene_modified_before = await _read_scene_modified(client, session_key, "scene_rollback")

        code = module_call(
            "_mcp_scene",
            "rollback_to_checkpoint",
            filename,
            discard_current_state=discard_current_state,
        )
        result = await _execute_scene_code(client, code, session_key, use_cache=False)
        mark_dirty(session_key)
        result["scene_modified_before"] = scene_modified_before
        return json.dumps(result, indent=2)

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_checkpoint_list"])
    async def scene_checkpoint_list(
        session_key: str | None = None,
    ) -> str:
        """List all saved checkpoints for the current scene state.

        Boundary: Disambiguated from scene_checkpoint (save a new checkpoint)
        and scene_rollback (open one and point the scene at it) —
        scene_checkpoint_list only reads what is already on disk.

        Saved scenes list <scene_dir>/checkpoints; a scene never saved to
        disk lists the workspace checkpoints instead (adhoc flag per entry).

        Args:
            session_key: Maya session key.

        Returns:
            List of checkpoints with filenames, sizes, and timestamps.
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)
        await _ensure_module_injected(client, session_key)

        code = module_call("_mcp_scene", "list_checkpoints")
        result = await _execute_scene_code(client, code, session_key, use_cache=False)
        return json.dumps(result, indent=2)

    # ============================================================
    # P1: Camera / Shot Planning
    # ============================================================

    @mcp.tool(annotations=TOOL_ANNOTATIONS["camera_create"])
    async def camera_create(
        target: str,
        shot_type: str = "medium",
        name: str = "CAM_shot",
        azimuth: float = 30,
        elevation: float = 15,
        session_key: str | None = None,
    ) -> str:
        """Create a camera positioned for a specific shot type.

        Boundary: Disambiguated from camera_orbit (animates a turntable around
        a point over many frames) — camera_create frames one static shot and
        adds no animation.

        Supports the 8 built-in shot types: extreme_wide, wide, medium,
        close, extreme_close, over_shoulder, bird_eye, low_angle.

        Args:
            target: Target object name to look at.
            shot_type: Shot type (default "medium").
            name: Camera name.
            azimuth: Horizontal angle in degrees (default 30).
            elevation: Vertical angle in degrees (default 15).
            session_key: Maya session key.

        Returns:
            Camera info with position, focal length, and distance.
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)
        await _ensure_module_injected(client, session_key)

        code = module_call(
            "_mcp_scene",
            "create_camera_shot",
            target,
            shot_type,
            name,
            {"azimuth": azimuth, "elevation": elevation},
        )
        result = await _execute_scene_code(client, code, session_key, use_cache=False)
        mark_dirty(session_key)
        return json.dumps(result, indent=2)

    @mcp.tool(annotations=TOOL_ANNOTATIONS["camera_orbit"])
    async def camera_orbit(
        center: str,
        radius: float = 500,
        frames: int = 120,
        name: str = "CAM_orbit",
        session_key: str | None = None,
    ) -> str:
        """Create an orbiting camera with turntable animation around a point.

        Side effects: creates a new camera and animation curves in the
        scene and marks the scene dirty. Not idempotent — each call adds
        another camera. Requires an active Maya session.

        Boundary: Disambiguated from camera_create (static shot-type
        framing; use camera_orbit only when an animated orbit is needed).

        Args:
            center: Orbit center as a JSON string "[x, y, z]".
            radius: Orbit radius in scene units.
            frames: Number of frames for one full orbit.
            name: Camera name.
            session_key: Maya session key.

        Returns:
            Camera and animation info.
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)
        await _ensure_module_injected(client, session_key)

        try:
            center_obj = json.loads(center)
        except json.JSONDecodeError as e:
            raise InputValidationError(f"center must be a JSON array [x, y, z]: {e}") from e
        code = module_call("_mcp_scene", "create_orbit_camera", center_obj, radius, frames, name)
        result = await _execute_scene_code(client, code, session_key, use_cache=False)
        mark_dirty(session_key)
        return json.dumps(result, indent=2)

    # ============================================================
    # P1: Aesthetic Analysis
    # ============================================================

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_aesthetics"])
    async def scene_aesthetics(
        format: str = "json",
        session_key: str | None = None,
    ) -> str:
        """Score the scene's look on 5 design dimensions.

        Scores the scene's look across 5 design dimensions:
        1. Color Theory: 60-30-10 rule, temperature balance, harmony type, saturation variety, contrast
        2. Spatial Composition: golden ratio proportions, rule-of-thirds alignment, visual weight balance
        3. Proportion & Scale: human ergonomic reference, size hierarchy (hero/secondary/tertiary)
        4. Lighting Quality: layer composition (key/fill/rim/accent), color temperature consistency
        5. Visual Flow: sight line clarity, circulation paths, visual rhythm patterns

        Returns an overall score (0-100) with grade (S/A/B/C/D/F) and improvement suggestions.

        Boundary: Disambiguated from scene_review (scene_aesthetics evaluates
        visual design theory and artistic harmony in depth, while
        scene_review is a broad check of the whole scene).

        Args:
            format: Output format - "json" (default) or "cos" (a short score
                summary: the overall score, each dimension's score, and the
                suggestions).
            session_key: Maya session key.

        Returns:
            Comprehensive aesthetic analysis report with scores per dimension.
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)
        await _ensure_module_injected(client, session_key)

        code = module_call("_mcp_scene", "analyze_aesthetics")
        result = await _execute_scene_code(client, code, session_key, use_cache=False)

        if format == "json":
            return json.dumps(result, indent=2)
        else:
            # COS format: compact token-efficient output
            overall = result.get("overall_score", 0)
            grade = result.get("grade", "?")
            dims = result.get("dimensions", {})
            suggestions = result.get("improvement_suggestions", [])

            out = [
                "AESTHETIC_SCORE[%s/100] GRADE=%s" % (overall, grade),
                "  COLOR[%s] SPATIAL[%s] SCALE[%s]"
                % (
                    dims.get("color_theory", "?"),
                    dims.get("spatial_composition", "?"),
                    dims.get("proportion_scale", "?"),
                ),
                "  LIGHT[%s] FLOW[%s]"
                % (dims.get("lighting_quality", "?"), dims.get("visual_flow", "?")),
            ]

            # Detail sub-scores
            detail = result.get("detail", {})
            ct = detail.get("color_theory", {})
            if ct.get("sub_scores"):
                ss = ct["sub_scores"]
                out.append(
                    "  COLOR_DETAIL: 60-30-10=%s temp=%s sat=%s harmony=%s contrast=%s"
                    % (
                        ss.get("60_30_10", "?"),
                        ss.get("temperature", "?"),
                        ss.get("saturation", "?"),
                        ss.get("harmony", "?"),
                        ss.get("contrast", "?"),
                    )
                )

            sc = detail.get("spatial_composition", {})
            if sc.get("sub_scores"):
                ss = sc["sub_scores"]
                out.append(
                    "  SPATIAL_DETAIL: golden=%s thirds=%s balance=%s"
                    % (
                        ss.get("golden_ratio", "?"),
                        ss.get("rule_of_thirds", "?"),
                        ss.get("visual_balance", "?"),
                    )
                )

            if suggestions:
                improve_parts = []
                for s in suggestions:
                    improve_parts.append("%s(%s,%s)" % (s["dimension"], s["score"], s["priority"]))
                out.append("  IMPROVE: " + " | ".join(improve_parts))

            return "\n".join(out)

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_review"])
    async def scene_review(
        checks: str = "all",
        format: str = "json",
        session_key: str | None = None,
    ) -> str:
        """Check a whole scene - all the aspects worth checking after operations.

        Runs spatial integrity, overlap detection, zone coverage, aesthetics,
        constraint validation, orphan detection, naming, componentization, conflicts, lighting quality, and scene organization. Returns a score (0-100)
        and detailed issue list.

        Checks you add in the Maya session with
        `_mcp_scene.register_validator(...)` (call it through execute_code) are
        reported in a separate "custom" section - `validators` per rule,
        `score`/`max_score` in weight points, `issues` for what did not pass.
        The built-in score is unchanged and the section is absent when nothing
        is registered.

        Boundary: Disambiguated from scene_validate (narrow rule-based
        spatial constraint checking) and scene_aesthetics (in-depth
        5-dimension aesthetic theory scoring).

        Use this after any major scene modification to verify quality.

        Args:
            checks: Comma-separated check names or "all".
                Options: spatial, overlaps, zones, aesthetics, constraints, orphans, naming, components, conflicts, lighting, organization
            format: Output format - "json" or "cos".
            session_key: Maya session key.

        Returns:
            Audit report with score, issues, and per-check details.
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)
        await _ensure_module_injected(client, session_key)

        checks_obj = None if checks == "all" else [c.strip() for c in checks.split(",")]
        code = module_call("_mcp_scene", "scene_review_with_validators", checks_obj)
        result = await _execute_scene_code(client, code, session_key, use_cache=False)

        if format == "json":
            return json.dumps(result, indent=2)
        else:
            score = result.get("score", 0)
            errors = result.get("errors", 0)
            warnings = result.get("warnings", 0)
            issues = result.get("issues", [])

            def rows(items: list[dict[str, Any]], label_key: str) -> list[str]:
                """[SEVERITY] label: msg — the row shape every issue list shares."""
                return [
                    f"  [{i.get('severity', '?').upper()}] {i.get(label_key)}: {i.get('msg')}"
                    for i in items[:10]
                ]

            lines = [f"REVIEW: score={score}/100 | errors={errors} | warnings={warnings}"]
            lines += rows(issues, "check")
            # Checks you registered keep their own score line: a compact view
            # that dropped them would read as "your rules all passed".
            custom = result.get("custom")
            if custom:
                failing = custom["issues"]
                validators = custom["validators"]
                # check_error split out: a broken rule is not a rule the
                # scene violated, and one summary number would mix them.
                broken = sum(1 for v in validators if v["status"] == "check_error")
                lines.append(
                    f"CUSTOM: score={custom['score']}/{custom['max_score']}"
                    f" | validators={len(validators)} | failing={len(failing) - broken}"
                    f" | check_error={broken}"
                )
                lines += rows(failing, "name")
            return "\n".join(lines)

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_plan"])
    async def scene_plan(
        objective: str = "",
        auto_fix: bool = False,
        format: str = "json",
        session_key: str | None = None,
        recommend_assets: bool = False,
    ) -> str:
        """Plan a scene layout: organization checks plus layout suggestions.

        Checks the scene and produces an actionable plan:
        - Organization check: finds orphan meshes, empty groups, default names
        - Zone analysis: coverage and spatial balance across zones
        - Layout suggestions: spacing, overlap, and clustering detection
        - Conflict prevention: predicts near-miss collisions
        - Action plan: prioritized step-by-step execution guide

        With recommend_assets=True, also recommends Poly Haven models across
        the built-in scene zones (entrance, display, furniture, lighting;
        shell, ip_core, and path are skipped with no search): reads fresh
        zone geometry, resolves a target object per zone from objective
        (full DAG path, unique short name, or single measurable zone object;
        otherwise falls back to the zone's world-axis bounding box), searches
        the models index with each zone's fixed query words (word-level
        checked and deduplicated per zone, capped at 3 per zone and 12 total),
        and screens candidates in metres (0.5x-1.5x per sorted axis for an
        object target; upper limit only for zone_bbox). Recommendations are
        advisory references — search only, no download and no import — and
        a search or network failure never changes the plan itself. Clearances
        and collisions are not verified.

        Blockout first: check organization and proportions
        before committing to detailed modeling. Accepts a plain-language objective.

        Boundary: Disambiguated from scene_review (scene_plan focuses on
        forward-looking layout planning and actionable auto_fix
        reorganization, whereas scene_review gives an overall
        diagnostic score).

        Args:
            objective: Natural language goal description.
                e.g., "set up entrance area with display window and clear circulation"
            auto_fix: If True, auto-fix safe issues (remove empty groups, reparent orphans).
            format: Output format - "json" (default) or "cos".
            session_key: Maya session key.
            recommend_assets: If True, attach advisory Poly Haven model
                recommendations across the mapped built-in zones (entrance,
                display, furniture, lighting; shell/ip_core/path skipped)
                to the plan. This reaches the Poly Haven search index over
                the network; default False keeps the output byte-identical
                and fully offline.

        Returns:
            Scene health report with organization status, zone analysis,
            layout suggestions, conflict predictions, and action plan. With
            recommend_assets=True, also a "recommendations" section (JSON)
            or a RECOMMEND block (CoS).
        """
        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)
        await _ensure_module_injected(client, session_key)

        code = module_call(
            "_mcp_scene", "scene_plan", objective=objective or None, auto_fix=auto_fix
        )
        result = await _execute_scene_code(client, code, session_key, use_cache=False)

        if recommend_assets:
            result["recommendations"] = await _recommend_for_plan(
                client, session_key, objective=objective
            )

        if format == "json":
            return json.dumps(result, indent=2)
        else:
            # COS format
            health = result.get("overall_health", 0)
            grade = result.get("grade", "?")
            org = result.get("organization_status", {})
            zone = result.get("zone_analysis", {})
            actions = result.get("action_plan", [])

            org_stats = org.get("stats", {})
            out = [
                f"SCENE_PLAN[{health}/100] GRADE={grade}",
                f"  ORG: score={org.get('health_score', '?')} "
                f"orphans={org_stats.get('orphan_meshes', 0)} "
                f"defaults={org_stats.get('default_names', 0)}",
                f"  ZONE: coverage={zone.get('coverage', '?')} "
                f"balance={zone.get('balance_score', '?')}",
            ]

            if actions:
                out.append("  ACTIONS:")
                for a in actions[:5]:
                    pri = a.get("priority", "?").upper()
                    out.append(f"    {a['step']}. [{pri}] {a.get('description', '')}")

            if "recommendations" in result:
                out.append(format_recommend_cos(result["recommendations"]))

            return "\n".join(out)
