# --- _mcp_scene zone geometry file (issue #176): own file, one injected module ---
#
# scene_tools._ensure_module_injected appends this file after
# validator_module.py and injects the whole assembly as _mcp_scene.
# It is not a separate injected module. The assembled namespace provides
# get_zone_map(), get_unit_info() and _world_bbox(); this file deliberately
# reuses them so zone membership and the eight-corner world bbox stay the
# same as the existing scene queries.
#
# Not wired up yet: #177 connects the host helper to the recommendation pass.
# scene_plan does not call this file, so its default output stays unchanged.
#
# Runtime floor: Maya >=2023 (Python 3.9). No __future__ import here: it would
# land mid-file in the assembled payload. The big module's future import makes
# the annotations below lazy. Do not import this file standalone on py3.9.

import math
from typing import Any

import maya.cmds as cmds
from maya.api import OpenMaya


def _zone_vector(value: Any) -> list[float] | None:
    """Return three finite numbers, or None when the bbox is not usable."""
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        return None
    try:
        if any(not math.isfinite(v) for v in value):
            return None
        return [float(v) for v in value]
    except (TypeError, ValueError, OverflowError):
        return None


def _zone_size(low: Any, high: Any) -> list[float] | None:
    """World-space [x, y, z] extent, rounded like the existing scene queries."""
    mn = _zone_vector(low)
    mx = _zone_vector(high)
    if mn is None or mx is None or any(lo > hi for lo, hi in zip(mn, mx)):
        return None
    return _zone_vector([round(abs(hi - lo), 3) for lo, hi in zip(mn, mx)])


def get_zone_geometry() -> dict[str, Any]:
    """Read the zones scene_plan already uses, with their boxes and object sizes.

    Returns {unit, up_axis, zones, unassigned_count, total_objects}. Each zone
    carries name, bbox_min, bbox_max, size, object_count, unmeasured_count and
    objects[{name, size}]. Sizes are [x, y, z] extents in the scene's linear
    unit; object names are full DAG paths. A zone or object whose bbox cannot
    be read gets null instead of a made-up zero box. Empty scenes return an
    empty zone list. This read does not change the scene and does not sample
    or truncate the object list; failed measurements are counted per zone.

    This is an internal Maya-side helper for the host get_zone_geometry()
    seam, not a new MCP tool. #177 is the first planned production caller.
    """
    try:
        zone_data = globals()["get_zone_map"]()
        unit_info = globals()["get_unit_info"]()
        transforms = cmds.ls(type="transform", long=True) or []
        world_bbox = globals()["_world_bbox"]

        # get_zone_map stores short names. A leaf name always maps to the same
        # zone because the same regex matched it; resolving the full path below
        # keeps duplicate leaf names from picking the wrong object's geometry.
        zone_for_object = {
            name: zone["name"] for zone in zone_data["zones"] for name in zone["objects"]
        }
        objects_by_zone: dict[str, list[dict[str, Any]]] = {
            zone["name"]: [] for zone in zone_data["zones"]
        }
        measured_zones: set[str] = set()

        for path in transforms:
            zone_name = zone_for_object.get(path.rsplit("|", 1)[-1])
            if zone_name is None:
                continue
            entry: dict[str, Any] = {"name": path, "size": None}
            try:
                sel = OpenMaya.MSelectionList()
                sel.add(path)
                bbox = world_bbox(sel.getDagPath(0))
                # MPoint carries a fourth w component; the bbox contract is xyz.
                entry["size"] = _zone_size(
                    [bbox.min[i] for i in range(3)], [bbox.max[i] for i in range(3)]
                )
                if entry["size"] is not None:
                    measured_zones.add(zone_name)
            except Exception:
                # One unreadable object must not hide the rest of the zone.
                pass
            objects_by_zone[zone_name].append(entry)

        zones: list[dict[str, Any]] = []
        for zone in zone_data["zones"]:
            name = zone["name"]
            objects = objects_by_zone[name]
            bbox_min: list[float] | None = None
            bbox_max: list[float] | None = None
            size: list[float] | None = None
            if name in measured_zones:
                low = _zone_vector(zone["bbox_min"])
                high = _zone_vector(zone["bbox_max"])
                size = _zone_size(low, high)
                if size is not None:
                    bbox_min, bbox_max = low, high
            zones.append(
                {
                    "name": name,
                    "bbox_min": bbox_min,
                    "bbox_max": bbox_max,
                    "size": size,
                    "object_count": len(objects),
                    "unmeasured_count": sum(1 for obj in objects if obj["size"] is None),
                    "objects": objects,
                }
            )

        return {
            "unit": unit_info["linear"],
            "up_axis": str(unit_info["up_axis"]).lower(),
            "zones": zones,
            "unassigned_count": zone_data["unassigned_count"],
            "total_objects": zone_data["total_objects"],
        }
    except Exception as e:
        return {"error": {"code": "query_failed", "message": f"{type(e).__name__}: {e}"}}
