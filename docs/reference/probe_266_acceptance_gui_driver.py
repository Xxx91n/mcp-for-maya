"""Issue #266 acceptance probe: run the SHIPPED scene module on live Maya 2024.

Exec's maya_scene_module.py + zone_geometry_module.py into one namespace (the
assembly scene_tools injects), builds a throwaway scene, and compares the
module's numbers with cmds.exactWorldBoundingBox. Every cell in
docs/evidence/probes/probe-266-world-bbox-units-gui-maya2024.json comes from
this script's output.

It is read-only about the user's scene: only `triage266_`/`GEO_door_triage266`
nodes are created and they are deleted in a finally block, the scene linear
unit is restored there too, and file(new=True) is never called.

How to run: deliver this file to a live Maya session through the native
commandPort (transport documented in docs/reference/gui_verify.py: a socket to
127.0.0.1:<port>). Send the file text as ONE expression wrapped in a private
exec namespace, so the port replies with the RESULT variable:

    (lambda d: (exec(<file text>, d), d.get("RESULT"))[1])({})
"""

import json
import os
import traceback

import maya.api.OpenMaya as om2  # noqa: N813
import maya.cmds as cmds


ROOT = os.environ.get("MAYA_MCP_SRC", r"D:\Aworker\maya\maya-mcp-server\src\maya_mcp_server")
out = {}
orig_unit = cmds.currentUnit(query=True, linear=True)
orig_angle = cmds.currentUnit(query=True, angle=True)
# Measure in a centimetre scene no matter what the session uses: OpenMaya
# values are centimetres while cmds follows currentUnit, so building geometry
# in a metre scene would compare two different units. The unit row below
# switches to metres on purpose and switches back to cm.
cmds.currentUnit(linear="cm")
# cmds.rotate reads the angular unit, so pin degrees: a radian session would
# turn the 45 into 45 radians and quietly stop testing the issue's case.
cmds.currentUnit(angle="deg")
# Names this probe created, so cleanup can never touch the user's scene.
created = []


def load():
    """Exec the shipped source (the same assembly scene_tools injects)."""
    ns = {"__name__": "_mcp_scene_probe"}
    for name in ("maya_scene_module.py", "zone_geometry_module.py"):
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            exec(compile(f.read(), name, "exec"), ns)  # noqa: S102
    return ns


def as_name(result):
    """Maya returns a bare name or a one-element list, depending on the command."""
    return result[0] if isinstance(result, (list, tuple)) else result


def long_name(node):
    """Full DAG path of a node Maya may have renamed to avoid a clash."""
    return cmds.ls(node, long=True)[0]


def rounded(values):
    return [round(v, 4) for v in values]


def box_list(box):
    return rounded([box.min[i] for i in range(3)] + [box.max[i] for i in range(3)])


def dag_of(path):
    sel = om2.MSelectionList()
    sel.add(path)
    return sel.getDagPath(0)


def raw_fn_bbox(path):
    """MFnDagNode.boundingBox as Maya hands it over (no matrix applied)."""
    box = om2.MFnDagNode(dag_of(path)).boundingBox
    return rounded([box.min[i] for i in range(3)] + [box.max[i] for i in range(3)])


def old_world_bbox(path):
    """The pre-#266 algorithm: corners x inclusiveMatrix (transform applied twice)."""
    dag = dag_of(path)
    bbox = om2.MFnDagNode(dag).boundingBox
    m = dag.inclusiveMatrix()
    box = om2.MBoundingBox()
    for i in range(8):
        corner = om2.MPoint(
            bbox.min[0] if i & 1 else bbox.max[0],
            bbox.min[1] if i & 2 else bbox.max[1],
            bbox.min[2] if i & 4 else bbox.max[2],
        )
        box.expand(corner * m)
    return box_list(box)


def new_world_bbox(path):
    """The shipped _world_bbox."""
    return box_list(_ns["_world_bbox"](dag_of(path)))


def size_of(box_values):
    return rounded(
        [
            box_values[3] - box_values[0],
            box_values[4] - box_values[1],
            box_values[5] - box_values[2],
        ]
    )


def probe_class(cls):
    methods = {}
    for name in dir(cls):
        if name.startswith("__"):
            continue
        attr = getattr(cls, name, None)
        if callable(attr) or isinstance(attr, (property, classmethod, staticmethod)):
            methods[name] = None
    return methods


_ns = {}
try:
    _ns = load()
    out["loaded"] = sorted(
        k for k in ("_world_bbox", "get_zone_geometry", "get_zone_map") if k in _ns
    )

    # --- rows 1-2: move, then rotate a plain box ---
    box = cmds.polyCube(w=100, h=100, d=100, name="triage266_A_box")[0]
    created.append(box)
    cmds.move(200, 50, 300, box, absolute=True)
    path = long_name(box)
    out["moved"] = {
        "setup": "100 cube moved to (200, 50, 300)",
        "fn_bbox": raw_fn_bbox(path),
        "old_world_bbox_inclusive": old_world_bbox(path),
        "new_world_bbox": new_world_bbox(path),
        "exact_world_bbox": rounded(cmds.exactWorldBoundingBox(path)),
    }
    out["moved"]["match"] = out["moved"]["new_world_bbox"] == out["moved"]["exact_world_bbox"]

    cmds.rotate(0, 45, 0, box, absolute=True, objectSpace=True)
    out["rotated"] = {
        "setup": "same 100 cube, rotated 45 deg about Y",
        "old_size": size_of(old_world_bbox(path)),
        "new_size": size_of(new_world_bbox(path)),
        "exact_size": size_of(rounded(cmds.exactWorldBoundingBox(path))),
    }
    out["rotated"]["match"] = out["rotated"]["new_size"] == out["rotated"]["exact_size"]

    # --- rows 3-5: nested child with its own translate, moved then rotated parent ---
    # cmds.parent preserves world space, so the child's local rotate is zeroed
    # after parenting to leave exactly the translate the row describes.
    grp = as_name(cmds.group(empty=True, name="triage266_B_grp"))
    created.append(grp)
    cmds.move(500, 0, 0, grp, absolute=True)
    child = cmds.polyCube(w=10, h=10, d=10, name="triage266_B_child")[0]
    created.append(child)
    parented = cmds.parent(child, grp) or [child]
    child_path = long_name(as_name(parented))
    cmds.setAttr(child_path + ".translate", 10, 0, 0, type="double3")
    cmds.setAttr(child_path + ".rotate", 0, 0, 0, type="double3")

    out["nested_moved_parent"] = {
        "setup": "group (500,0,0); child local translate (10,0,0), local rotate 0; 10 cube",
        "new_world_bbox": new_world_bbox(child_path),
        "exact_world_bbox": rounded(cmds.exactWorldBoundingBox(child_path)),
    }
    out["nested_moved_parent"]["match"] = (
        out["nested_moved_parent"]["new_world_bbox"]
        == out["nested_moved_parent"]["exact_world_bbox"]
    )

    cmds.rotate(0, 30, 0, grp, absolute=True, objectSpace=True)
    out["nested_rotated_parent"] = {
        "setup": "group (500,0,0) rot Y30; child local translate (10,0,0), local rotate 0; 10 cube",
        "new_world_bbox": new_world_bbox(child_path),
        "exact_world_bbox": rounded(cmds.exactWorldBoundingBox(child_path)),
    }
    out["nested_rotated_parent"]["match"] = (
        out["nested_rotated_parent"]["new_world_bbox"]
        == out["nested_rotated_parent"]["exact_world_bbox"]
    )

    shape_path = cmds.listRelatives(child_path, shapes=True, fullPath=True)[0]
    out["shape_path"] = {
        "setup": shape_path,
        "new_world_bbox": new_world_bbox(shape_path),
        "exact_world_bbox": rounded(cmds.exactWorldBoundingBox(shape_path)),
    }
    out["shape_path"]["match"] = (
        out["shape_path"]["new_world_bbox"] == out["shape_path"]["exact_world_bbox"]
    )

    # --- row 6: the discriminator the fix relies on ---
    out["hasfn"] = {
        "transform_path": {
            "hasFn_kTransform": dag_of(child_path).hasFn(om2.MFn.kTransform),
            "hasFn_kShape": dag_of(child_path).hasFn(om2.MFn.kShape),
        },
        "shape_path": {
            "hasFn_kTransform": dag_of(shape_path).hasFn(om2.MFn.kTransform),
            "hasFn_kShape": dag_of(shape_path).hasFn(om2.MFn.kShape),
        },
    }

    # --- row 7: units, OpenMaya stays in cm while cmds follows currentUnit ---
    # root-namespace absolute: a non-root current namespace would rename it
    # and the zone match would silently drop it
    door = cmds.polyCube(w=130, h=220, d=12, name=":GEO_door_triage266")[0]
    created.append(door)
    cmds.move(0, 0, -200, door, absolute=True)
    door_path = long_name(door)
    out["units"] = {
        "cm_scene": {
            "fn_bbox_size": size_of(raw_fn_bbox(door_path)),
            "exactWorldBoundingBox_extent": rounded(cmds.exactWorldBoundingBox(door_path))[0],
            "boundingBoxSize_attribute": rounded(cmds.getAttr(door_path + ".boundingBoxSize")[0]),
            "MDistance(1.0).asUnits(uiUnit())": round(
                om2.MDistance(1.0).asUnits(om2.MDistance.uiUnit()), 6
            ),
        }
    }
    cmds.currentUnit(linear="m")
    out["units"]["m_scene"] = {
        "unit": cmds.currentUnit(query=True, linear=True),
        "fn_bbox_size": size_of(raw_fn_bbox(door_path)),
        "exactWorldBoundingBox_extent": rounded(cmds.exactWorldBoundingBox(door_path))[0],
        "boundingBoxSize_attribute": rounded(cmds.getAttr(door_path + ".boundingBoxSize")[0]),
        "MDistance(1.0).asUnits(uiUnit())": round(
            om2.MDistance(1.0).asUnits(om2.MDistance.uiUnit()), 6
        ),
        "MDistance(130).asUnits(uiUnit())": round(
            om2.MDistance(130.0).asUnits(om2.MDistance.uiUnit()), 6
        ),
    }

    # --- row 8: get_zone_geometry reports the unit it declares ---
    geo_m = _ns["get_zone_geometry"]()
    zone_m = {z["name"]: z for z in geo_m["zones"]}.get("entrance")
    door_entry_m = None
    if zone_m is not None:
        door_entry_m = next((o["size"] for o in zone_m["objects"] if o["name"] == door_path), None)
    cmds.currentUnit(linear="cm")
    geo_cm = _ns["get_zone_geometry"]()
    zone_cm = {z["name"]: z for z in geo_cm["zones"]}.get("entrance")
    door_entry_cm = None
    if zone_cm is not None:
        door_entry_cm = next(
            (o["size"] for o in zone_cm["objects"] if o["name"] == door_path), None
        )
    out["zone_geometry"] = {
        "cm_read": {
            "unit": geo_cm["unit"],
            "door_size": door_entry_cm,
            "zone_size": None if zone_cm is None else zone_cm["size"],
        },
        "m_read": {
            "unit": geo_m["unit"],
            "door_size": door_entry_m,
            "zone_size": None if zone_m is None else zone_m["size"],
        },
        "door_exact_world_bbox": rounded(cmds.exactWorldBoundingBox(door_path)),
    }

    # --- row 9: presence of the classes the fake models ---
    out["presence"] = {
        "om.MDistance": probe_class(om2.MDistance),
        "om.MFn": probe_class(om2.MFn),
    }

    # --- row 10: the cached-box limitation, measured ---
    cmds.setAttr(child_path + ".rotate", 0, -30, 0, type="double3")
    out["known_limitation_cancelled_rotation"] = {
        "setup": "parent rot Y30, child local rot Y-30 (world rotation is identity), 10 cube",
        "new_world_bbox": new_world_bbox(child_path),
        "exact_world_bbox": rounded(cmds.exactWorldBoundingBox(child_path)),
    }
    cmds.setAttr(child_path + ".rotate", 0, 0, 0, type="double3")
except Exception:
    out["error"] = traceback.format_exc()
finally:
    try:
        cmds.currentUnit(linear=orig_unit)
        cmds.currentUnit(angle=orig_angle)
    except Exception:
        pass
    for name in created:
        if cmds.objExists(name):
            cmds.delete(name)
    out["leftover"] = [x for x in created if cmds.objExists(x)]
    out["restored_unit"] = cmds.currentUnit(query=True, linear=True)
    out["restored_angle"] = cmds.currentUnit(query=True, angle=True)

RESULT = "ACCEPT266 " + json.dumps(out, sort_keys=True)
