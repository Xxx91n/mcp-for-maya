"""Issue #266 acceptance: the five-zone table, on a real Maya 2024 session.

Runs the shipped code, not a copy:
  - src/maya_mcp_server/maya_scene_module.py + zone_geometry_module.py, exec'd
    into one namespace the way scene_tools injects them, provides
    get_zone_geometry();
  - src/maya_mcp_server/asset_recommendation.gather_recommendations builds the
    `recommendations` section from that geometry, the same function scene_plan
    calls when recommend_assets=True.

The only thing missing versus the MCP tool is the tool wrapper itself.

Scene: five zones with several objects each, all unrotated, positions spread
out — the configuration the issue says already went wrong (a zone with two
objects had its box inflated by the double translate).

Output: prints FIVEZONE266 <json> and also writes it to OUT_FILE.
"""

import json
import os
import sys
import traceback

import maya.cmds as cmds


SRC = os.environ.get("MAYA_MCP_SRC", r"D:\Aworker\maya\maya-mcp-server\src")
OUT_FILE = os.environ.get(
    "MAYA_MCP_FIVEZONE_OUT",
    r"C:\Users\Administrator\AppData\Local\Temp\triage266\fivezone_result.json",
)

# zone -> {name: (width, height, depth, center)} in centimetres
ZONE_OBJECTS = {
    "shell": {
        "GEO_wall_back": (400, 250, 5, (200, 125, 2.5)),
        "GEO_wall_side": (5, 250, 300, (2.5, 125, 150)),
    },
    "entrance": {
        # both names match the entrance zone but neither is the one obvious
        # object for a search query, so the target is the zone envelope
        "GEO_entrance_frame": (150, 220, 10, (-200, 110, 290)),
        "GEO_entrance_panel": (60, 200, 4, (-290, 100, 290)),
    },
    "display": {
        "GEO_shelf_a": (90, 180, 40, (-260, 90, -60)),
        "GEO_shelf_b": (90, 180, 40, (-160, 90, -60)),
    },
    "furniture": {
        "GEO_chair_a": (50, 90, 50, (140, 45, 60)),
        "GEO_table_a": (80, 75, 80, (240, 37.5, 60)),
    },
    "lighting": {
        "GEO_lamp_a": (40, 40, 40, (300, 20, -200)),
        "GEO_lamp_b": (30, 30, 30, (300, 15, -140)),
    },
}

out = {}
orig_unit = cmds.currentUnit(query=True, linear=True)
created = []


def load_scene_module():
    ns = {"__name__": "_mcp_scene_probe"}
    for name in ("maya_scene_module.py", "zone_geometry_module.py"):
        with open(SRC + "\\maya_mcp_server\\" + name, encoding="utf-8") as f:
            exec(compile(f.read(), name, "exec"), ns)  # noqa: S102
    return ns


def build_scene():
    """Explicit w/h/d in the scene's working unit (cm), then place the centre.

    Refuses to run on a scene that already holds one of these names: Maya would
    rename the new node and the zone lookup could land on someone else's object.
    """
    clashes = [n for z in ZONE_OBJECTS.values() for n in z if cmds.objExists(n)]
    if clashes:
        raise RuntimeError(f"scene already has {clashes}; run this in an empty scene")
    for zone, objects in ZONE_OBJECTS.items():
        for name, (w, h, d, center) in objects.items():
            cube = cmds.polyCube(w=w, h=h, d=d, name=name)[0]
            created.append(cube)
            cmds.setAttr(cube + ".translate", center[0], center[1], center[2], type="double3")
    out["zone_members"] = {z: sorted(o) for z, o in ZONE_OBJECTS.items()}


def exact_zone_box(objects):
    box = cmds.exactWorldBoundingBox(*objects)
    return [round(v, 4) for v in box]


def run_case(label, scene_module):
    geometry = scene_module["get_zone_geometry"]()
    zones = {z["name"]: z for z in geometry.get("zones", [])}

    sys.path.insert(0, SRC)
    from maya_mcp_server import asset_recommendation, polyhaven  # noqa: PLC0415

    recs = asset_recommendation.gather_recommendations(
        geometry, polyhaven.search_assets, budget_s=6.0
    )
    targets = {z["zone"]: z.get("target") for z in recs.get("zones", [])}

    # The expectation must not come from the value under test: read the session
    # unit straight from Maya, and assert the geometry agrees with it.
    session_unit = cmds.currentUnit(query=True, linear=True)
    case = {
        "unit": geometry.get("unit"),
        "session_unit": session_unit,
        "unit_label_matches": geometry.get("unit") == session_unit,
        "rows": {},
    }
    for zone, objects in ZONE_OBJECTS.items():
        exact_cm = exact_zone_box(list(objects))
        g = zones.get(zone) or {}
        target = targets.get(zone) or {}
        # exactWorldBoundingBox follows the working unit, so convert to metres
        # the same way the host does: cmds values are already working units.
        factor = {"mm": 0.1, "cm": 0.01, "m": 1.0}.get(session_unit, 0.01)
        case["rows"][zone] = {
            "objects": len(objects),
            "module_box": [g.get("bbox_min"), g.get("bbox_max")],
            "cmds_box": [exact_cm[:3], exact_cm[3:]],
            "target_bbox_min_m": target.get("bbox_min_m"),
            "target_bbox_max_m": target.get("bbox_max_m"),
            "target_size_m": target.get("size_m"),
            "expected_m": [
                [round(v * factor, 4) for v in exact_cm[:3]],
                [round(v * factor, 4) for v in exact_cm[3:]],
            ],
            "source": target.get("source"),
        }
    out[label] = case
    out[label + "_status"] = recs.get("status")


def check(label):
    """Every zone's reported metre box must equal its cmds box."""
    bad = []
    if not out[label].get("unit_label_matches"):
        bad.append(
            f"geometry unit {out[label]['unit']!r} != session unit {out[label]['session_unit']!r}"
        )
    for zone, row in out[label]["rows"].items():
        exp_min, exp_max = row["expected_m"]
        got_min, got_max = row["target_bbox_min_m"], row["target_bbox_max_m"]
        if row["source"] != "zone_bbox":
            # the issue's table is about zone envelopes; an object-based target
            # carries size_m only, by design
            bad.append(f"{zone}: target source is {row['source']}, expected zone_bbox")
            continue
        if got_min is None or got_max is None:
            bad.append(f"{zone}: zone_bbox target box is null")
            continue
        if len(got_min) != 3 or len(got_max) != 3 or len(exp_min) != 3 or len(exp_max) != 3:
            bad.append(f"{zone}: vector length is not 3 ({got_min}, {got_max})")
            continue
        if any(abs(a - b) > 2e-3 for a, b in zip(got_min, exp_min)) or any(
            abs(a - b) > 2e-3 for a, b in zip(got_max, exp_max)
        ):
            bad.append(f"{zone}: got {got_min}..{got_max} want {exp_min}..{exp_max}")
        exp_size = [round(hi - lo, 4) for lo, hi in zip(exp_min, exp_max)]
        got_size = row["target_size_m"]
        if got_size is None or len(got_size) != 3 or len(exp_size) != 3:
            bad.append(f"{zone}: size_m is not a 3-vector ({got_size})")
        elif any(abs(a - b) > 2e-3 for a, b in zip(got_size, exp_size)):
            bad.append(f"{zone}: size_m {got_size} want {exp_size}")
        mod_min, mod_max = row["module_box"]
        cmds_min, cmds_max = row["cmds_box"]
        if mod_min is None or any(
            abs(a - b) > 2e-3 for a, b in zip(mod_min + mod_max, cmds_min + cmds_max)
        ):
            bad.append(f"{zone}: geometry box {mod_min}..{mod_max} vs cmds {cmds_min}..{cmds_max}")
    out[label + "_mismatches"] = bad


try:
    # geometry is built once, in centimetres, then only the display unit moves
    cmds.currentUnit(linear="cm")
    scene_module = load_scene_module()
    build_scene()
    run_case("cm_scene", scene_module)
    check("cm_scene")

    cmds.currentUnit(linear="m")
    run_case("m_scene", scene_module)
    check("m_scene")
    cmds.currentUnit(linear="cm")
    run_case("cm_after", scene_module)
    check("cm_after")
except Exception:
    out["error"] = traceback.format_exc()
finally:
    try:
        cmds.currentUnit(linear=orig_unit)
    except Exception:
        pass
    for name in created:
        if cmds.objExists(name):
            cmds.delete(name)
    out["leftover"] = [n for n in created if cmds.objExists(n)]
    out["restored_unit"] = cmds.currentUnit(query=True, linear=True)
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=True)

RESULT = "FIVEZONE266 " + json.dumps({"written": OUT_FILE, "error": out.get("error")})
