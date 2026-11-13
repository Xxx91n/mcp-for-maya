"""CoS formatter for scene data.

CoS (Chain-of-Symbol) writes scene data as very short one-line-per-object
text, which saves the number of tokens sent to the AI.
Research shows CoS yields +60.8% accuracy on spatial tasks while reducing tokens by 65.8%.

Reference: Hu et al., COLM 2023 - Chain-of-Symbol Prompting
"""

from __future__ import annotations

from typing import Any


def format_scene_cos(
    scene_data: dict[str, Any],
    zones: list[dict[str, Any]] | None = None,
    max_objects: int = 200,
) -> str:
    """Format scene data as CoS text: short one-line-per-object notation.

    Args:
        scene_data: Scene graph data with 'objects', 'stats', 'unit', 'up_axis'.
        zones: Optional zone map data.
        max_objects: Maximum objects to include (token budget control).

    Returns:
        CoS-formatted string.
    """
    objects = scene_data.get("objects", [])
    stats = scene_data.get("stats", {})
    unit = scene_data.get("unit", "cm")
    up_axis = scene_data.get("up_axis", "y")

    lines: list[str] = []

    # Header: scene summary
    obj_count = len(objects)
    zone_count = len(zones) if zones else 0
    lines.append(f"SCENE[{obj_count}obj, {zone_count}zones] UNIT={unit} UP={up_axis}")

    # If zones provided, group objects by zone
    if zones:
        zone_map = _build_zone_object_map(zones, objects)
        _format_by_zones(lines, zone_map, zones, max_objects)
    else:
        # Flat list, truncated to max_objects
        _format_flat(lines, objects[:max_objects])

    # Footer: truncation notice
    if obj_count > max_objects:
        omit = obj_count - max_objects
        lines.append(f"... {omit} more objects (use scene_inspect)")

    # Stats summary
    if stats:
        lines.append(f"STATS: {stats}")

    return "\n".join(lines)


def format_inspect_cos(
    obj_data: dict[str, Any],
    neighbors: list[dict[str, Any]] | None = None,
) -> str:
    """Format detailed inspection of a single object or zone.

    Args:
        obj_data: Object detail data.
        neighbors: Nearby objects with distances.

    Returns:
        CoS-formatted inspection result.
    """
    lines: list[str] = []

    name = obj_data.get("name", "?")
    ntype = obj_data.get("type", "?")
    pos = obj_data.get("position", [0, 0, 0])
    bbox = obj_data.get("bbox", {})
    material = obj_data.get("material")
    verts = obj_data.get("vertex_count")
    faces = obj_data.get("face_count")

    # Object header
    px, py, pz = _r3(pos[0]), _r3(pos[1]), _r3(pos[2])
    lines.append(f"INSPECT: {name}[{ntype}]@({px},{py},{pz})")

    # BBox as WxHxD
    if bbox:
        bmin = bbox.get("min", [0, 0, 0])
        bmax = bbox.get("max", [0, 0, 0])
        w = _r3(abs(bmax[0] - bmin[0]))
        h = _r3(abs(bmax[1] - bmin[1]))
        d = _r3(abs(bmax[2] - bmin[2]))
        lines.append(
            f"  SIZE: {w}x{h}x{d} " + f"BBOX:[{_r3(bmin[0])},{_r3(bmin[1])},{_r3(bmin[2])}]"
            f"-[{_r3(bmax[0])},{_r3(bmax[1])},{_r3(bmax[2])}]"
        )

    # Material and mesh info
    if material:
        lines.append(f"  MAT: {material}")
    if verts is not None:
        lines.append(f"  MESH: {verts}v {faces}f")

    # Children
    children = obj_data.get("children", [])
    if children:
        lines.append(f"  CHILDREN[{len(children)}]: {', '.join(children[:10])}")
        if len(children) > 10:
            lines.append(f"    ... +{len(children) - 10} more")

    # Neighbors
    if neighbors:
        lines.append(f"  NEIGHBORS[{len(neighbors)}]:")
        for n in neighbors[:8]:
            nname = n.get("name", "?")
            dist = _r3(n.get("distance", 0))
            lines.append(f"    {nname} @ {dist}{obj_data.get('unit', 'cm')}")

    # Parent
    parent = obj_data.get("parent")
    if parent:
        lines.append(f"  PARENT: {parent}")

    return "\n".join(lines)


def format_measure_cos(result: dict[str, Any]) -> str:
    """Format measurement result as CoS notation."""
    obj_a = result.get("obj_a", "?")
    obj_b = result.get("obj_b", "?")
    mode = result.get("mode", "center")
    distance = result.get("distance", 0)
    unit = result.get("unit", "cm")
    overlap = result.get("bbox_overlap", False)

    line = f"MEASURE[{mode}]: {obj_a} ↔ {obj_b} = {_r3(distance)}{unit}"
    if overlap:
        line += " [OVERLAP]"
    return line


def format_assert_cos(result: dict[str, Any]) -> str:
    """Format assertion result as CoS notation."""
    passed = result.get("passed", False)
    checked = result.get("checked_count", 0)
    mismatches = result.get("mismatches", [])

    status = "PASS" if passed else "FAIL"
    lines = [f"ASSERT[{status}]: {checked} checks"]

    for m in mismatches[:5]:
        obj = m.get("object", "?")
        prop = m.get("property", "?")
        expected = m.get("expected")
        actual = m.get("actual")
        lines.append(f"  MISMATCH: {obj}.{prop} expected={expected} actual={actual}")

    if len(mismatches) > 5:
        lines.append(f"  ... +{len(mismatches) - 5} more mismatches")

    return "\n".join(lines)


def format_zone_map_cos(zones: list[dict[str, Any]], stats: dict[str, Any] | None = None) -> str:
    """Format zone map as CoS notation."""
    lines: list[str] = []
    lines.append(f"ZONES[{len(zones)}]")

    for zone in zones:
        name = zone.get("name", "?")
        count = zone.get("object_count", 0)
        center = zone.get("center", [0, 0, 0])
        pattern = zone.get("pattern_matched", "")
        cx, cy, cz = _r3(center[0]), _r3(center[1]), _r3(center[2])
        lines.append(f"  {name}: {count}obj @({cx},{cy},{cz}) [{pattern}]")

        # List top objects in zone
        obj_names = zone.get("objects", [])[:5]
        if obj_names:
            lines.append(f"    [{', '.join(obj_names)}]")

    if stats:
        lines.append(f"STATS: {stats}")

    return "\n".join(lines)


# --- Internal helpers ---


def _r3(val: float) -> str:
    """Round to 3 decimal places, strip trailing zeros."""
    rounded = round(val, 3)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.3f}".rstrip("0").rstrip(".")


def _build_zone_object_map(
    zones: list[dict[str, Any]],
    objects: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Build a mapping from zone name to its objects."""
    zone_map: dict[str, list[dict[str, Any]]] = {}
    zone_map["_unassigned"] = []

    for zone in zones:
        zone_map[zone.get("name", "?")] = []

    for obj in objects:
        assigned = False
        for zone in zones:
            if obj.get("n", "") in zone.get("objects", []):
                zone_map[zone.get("name", "?")].append(obj)
                assigned = True
                break
        if not assigned:
            zone_map["_unassigned"].append(obj)

    return zone_map


def _format_by_zones(
    lines: list[str],
    zone_map: dict[str, list[dict[str, Any]]],
    zones: list[dict[str, Any]],
    max_objects: int,
) -> None:
    """Format objects grouped by zone."""
    count = 0
    for zone in zones:
        zname = zone.get("name", "?")
        zone_objs = zone_map.get(zname, [])
        if not zone_objs:
            continue

        zcenter = zone.get("center", [0, 0, 0])
        zc = f"({_r3(zcenter[0])},{_r3(zcenter[1])},{_r3(zcenter[2])})"
        lines.append(f"\n{zname.upper()} ({len(zone_objs)}obj) @ {zc}")

        for obj in zone_objs:
            if count >= max_objects:
                return
            lines.append(f"  {_format_obj_line(obj)}")
            count += 1

    # Unassigned objects
    unassigned = zone_map.get("_unassigned", [])
    if unassigned and count < max_objects:
        lines.append(f"\nOTHER ({len(unassigned)}obj)")
        for obj in unassigned:
            if count >= max_objects:
                return
            lines.append(f"  {_format_obj_line(obj)}")
            count += 1


def _format_flat(
    lines: list[str],
    objects: list[dict[str, Any]],
) -> None:
    """Format objects as flat list."""
    for obj in objects:
        lines.append(_format_obj_line(obj))


def _format_obj_line(obj: dict[str, Any]) -> str:
    """Format a single object as one CoS line."""
    name = obj.get("n", "?")
    ntype = obj.get("t", "?")
    pos = obj.get("p", [0, 0, 0])
    bbox = obj.get("b", [0, 0, 0, 0, 0, 0])
    children = obj.get("c")

    px, py, pz = _r3(pos[0]), _r3(pos[1]), _r3(pos[2])

    # BBox size from min/max
    if len(bbox) >= 6:
        w = _r3(abs(bbox[3] - bbox[0]))
        h = _r3(abs(bbox[4] - bbox[1]))
        d = _r3(abs(bbox[5] - bbox[2]))
        size_str = f" {w}x{h}x{d}"
    else:
        size_str = ""

    child_str = f" [{children}ch]" if children else ""
    return f"{name}[{ntype}]@({px},{py},{pz}){size_str}{child_str}"
