"""MCP scene-graph introspection tools (D-094): scene_describe + scene_nodes.

Both tools ride the _mcp_scene injection unit (D-095 / ADR-0027 c4):
their Maya-side code lives in introspect_module.py and is concatenated
into the _mcp_scene payload by scene_tools._ensure_module_injected -
same module name, same per-session trigger, same failure domain.

Read-only by design: no mark_dirty, no scene-cache lookup (attribute
metadata, values and enumeration must always be fresh).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from maya_mcp_server.client import raise_for_error
from maya_mcp_server.pipeline import TOOL_ANNOTATIONS
from maya_mcp_server.scene_tools import _ensure_module_injected, _scene_call
from maya_mcp_server.security import InputValidationError


logger = logging.getLogger(__name__)


async def _exec_scene(client: Any, code: str) -> Any:
    """Execute a _mcp_scene call; parse the JSON result."""
    response = await client.execute_code(code, result_type="JSON")
    raise_for_error(response)
    data = response.result
    if isinstance(data, str):
        return json.loads(data)
    return data


def register_introspect_tools(mcp: Any) -> None:
    """Register scene-graph introspection tools on the FastMCP instance.

    Args:
        mcp: FastMCP server instance.
    """

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_describe"])  # type: ignore[untyped-decorator]
    async def scene_describe(
        node: str,
        attrs: list[str] | None = None,
        include_values: bool = False,
        include_connections: bool = True,
        session_key: str | None = None,
    ) -> str:
        """API-level self-description of ONE node (not spatial).

        Boundary: scene_inspect answers WHERE an object is (position,
        bbox, neighbors); scene_describe answers WHAT the node is at the
        API level - exact node type, per-attribute metadata, and
        connection wiring - so you can compose accurate
        execute_code/setAttr/connectAttr calls against real names.

        Args:
            node: Node name (short name or long DAG path).
            attrs: Attribute names to describe; None (default) lists
                every attribute listAttr reports. A named attr that does
                not exist aborts the whole call (attr_not_found) - no
                partial metadata (same contract as scene_export's
                missing_objects).
            include_values: Also return value + soft_min/soft_max per
                attr (default False). Reading a value can trigger DG
                evaluation inside Maya - still read-only, but the eval
                may cost time on heavy graphs.
            include_connections: Return connection wiring
                {src_plug, dst_plug, direction} (default True).
            session_key: Maya session key (auto-selected if one session).

        Returns:
            JSON {node, type, attrs[{name, exists, attr_type, readable,
            writable, connectable, keyable, multi, hidden, locked,
            storable, children, index_matters, enum, enum_values, min,
            max, (soft_min, soft_max, value)}], connections?[{src_plug,
            dst_plug, direction}]}. Domain failures return
            {"error": {code, message}} - node_not_found, attr_not_found,
            query_failed.

        Example:
            scene_describe("pCube1") -> all attrs + connections
            scene_describe("spotLightShape1", attrs=["intensity","coneAngle"],
                           include_values=True)
        """
        if not isinstance(node, str) or not node.strip():
            raise InputValidationError("scene_describe requires a non-empty node name")
        if attrs is not None and (
            not isinstance(attrs, list) or not all(isinstance(a, str) for a in attrs)
        ):
            raise InputValidationError("attrs must be a list of attribute names")

        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)

        await _ensure_module_injected(client, session_key)

        result = await _exec_scene(
            client,
            _scene_call(
                "describe_node",
                node,
                attrs=attrs,
                include_values=bool(include_values),
                include_connections=bool(include_connections),
            ),
        )
        return json.dumps(result, indent=2)

    @mcp.tool(annotations=TOOL_ANNOTATIONS["scene_nodes"])  # type: ignore[untyped-decorator]
    async def scene_nodes(
        type: str | None = None,
        pattern: str | None = None,
        dag_only: bool = False,
        inherited: bool = True,
        limit: int = 50,
        cursor: str | None = None,
        include_type_counts: bool = False,
        session_key: str | None = None,
    ) -> str:
        """Bounded enumeration of scene nodes - including non-DAG nodes.

        Boundary: scene_snapshot is the low-resolution spatial overview
        you call once per workflow; scene_nodes is the name-discovery
        complement for the API layer - it lists nodes a spatial view
        never shows (materials, shadingEngines, tool nodes) and pages
        honestly: has_more/next_cursor tell you when the list was cut.

        Args:
            type: Node type filter. With inherited=True (default) derived
                types match too (ls type= semantics, e.g. type="light"
                matches spotLight/directionalLight); inherited=False pins
                the exact type.
            pattern: Maya glob pattern on names (e.g. "GEO_*").
            dag_only: Only DAG nodes (transforms/shapes); False includes
                dependency nodes such as materials and utility nodes.
            inherited: See type.
            limit: Page size (default 50, hard-capped at 100).
            cursor: Opaque page token from a previous call's next_cursor;
                valid while the scene is unchanged.
            include_type_counts: Also return per-type counts over the
                full match set (not just the page).
            session_key: Maya session key (auto-selected if one session).

        Returns:
            JSON {total_count, count, nodes[names], has_more,
            next_cursor, limit, type_counts?}. Domain failures return
            {"error": {code, message}} - invalid_cursor, query_failed.

        Example:
            scene_nodes(type="mesh") -> all mesh shapes (incl. derived)
            scene_nodes(pattern="GRP_*", dag_only=True, limit=100)
        """
        if type is not None and (not isinstance(type, str) or not type.strip()):
            raise InputValidationError("type must be a non-empty string")
        if pattern is not None and not isinstance(pattern, str):
            raise InputValidationError("pattern must be a string")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit < 1:
            raise InputValidationError("limit must be a positive int")
        if cursor is not None and not isinstance(cursor, str):
            raise InputValidationError("cursor must be a string token")

        from maya_mcp_server.server import get_session_manager

        manager = get_session_manager()
        client = await manager.get_client(session_key)

        await _ensure_module_injected(client, session_key)

        result = await _exec_scene(
            client,
            _scene_call(
                "list_nodes",
                node_type=type,
                pattern=pattern,
                dag_only=bool(dag_only),
                inherited=bool(inherited),
                limit=limit,
                cursor=cursor,
                include_type_counts=bool(include_type_counts),
            ),
        )
        return json.dumps(result, indent=2)
