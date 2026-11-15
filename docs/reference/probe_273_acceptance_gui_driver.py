"""#273 acceptance probe: run the shipped scene module on live Maya 2024.

Exec's maya_scene_module.py from MAYA_MCP_SRC (default: this checkout's
src/maya_mcp_server) into one namespace, builds throwaway scenes, and writes
out.json. Every cell in
docs/evidence/probes/probe-273-world-bbox-shape-walk-gui-maya2024.json comes
from this script's output.

How to run (the driver needs a GUI session; maya.standalone is broken on the
recording box): write a MEL wrapper that calls this file, then launch Maya:

    python("import runpy; runpy.run_path('C:/probe_273.py', run_name='__main__')");
    maya.exe -script C:/run_probe.mel

It is read-only about the user's scene: only triage273_-prefixed nodes are
created and deleted in a finally block, currentUnit is restored there too, and
file(new=True) is never called. The driver does not close Maya by default; set
MAYA273_QUIT=1 when launching a throwaway -script process and you want it gone
afterwards. Never set it on a session that may hold unsaved work.
"""

import hashlib
import json
import os
import tempfile
import time
import traceback

import maya.api.OpenMaya as om2  # noqa: N813
import maya.cmds as cmds


_DEFAULT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "src", "maya_mcp_server")
)
ROOT = os.environ.get("MAYA_MCP_SRC", _DEFAULT_ROOT)
_OUT_DIR = os.environ.get("MAYA273_OUT_DIR", os.path.join(tempfile.gettempdir(), "maya273probe"))
OUT = os.path.join(_OUT_DIR, "out.json")
STATUS = os.path.join(_OUT_DIR, "status.json")
os.makedirs(_OUT_DIR, exist_ok=True)

out = {"stage": "start"}
created = []
orig_unit = None
orig_angle = None


def status(stage):
    out["stage"] = stage
    with open(STATUS, "w", encoding="utf-8") as f:
        json.dump({"stage": stage}, f)


def load():
    ns = {"__name__": "_mcp_scene_probe"}
    for name in ("maya_scene_module.py",):
        with open(os.path.join(ROOT, name), encoding="utf-8") as f:
            exec(compile(f.read(), name, "exec"), ns)  # noqa: S102
    return ns


def as_name(result):
    return result[0] if isinstance(result, (list, tuple)) else result


def long_name(node):
    return cmds.ls(node, long=True)[0]


def rounded(values):
    return [round(v, 4) for v in values]


def box_list(box):
    return rounded([box.min[i] for i in range(3)] + [box.max[i] for i in range(3)])


def dag_of(path):
    sel = om2.MSelectionList()
    sel.add(path)
    return sel.getDagPath(0)


def old_world_bbox(dag):
    bbox = om2.MFnDagNode(dag).boundingBox
    wm = dag.exclusiveMatrix() if dag.hasFn(om2.MFn.kTransform) else dag.inclusiveMatrix()
    box = om2.MBoundingBox()
    for i in range(8):
        corner = om2.MPoint(
            bbox.min[0] if i & 1 else bbox.max[0],
            bbox.min[1] if i & 2 else bbox.max[1],
            bbox.min[2] if i & 4 else bbox.max[2],
        )
        box.expand(corner * wm)
    return box


def new_world_bbox(path):
    return box_list(_ns["_world_bbox"](dag_of(path)))


def size_of(box_values):
    return rounded(
        [
            box_values[3] - box_values[0],
            box_values[4] - box_values[1],
            box_values[5] - box_values[2],
        ]
    )


def time_call(fn, repeats=3):
    best = None
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        took = (time.perf_counter() - start) * 1000.0
        best = took if best is None else min(best, took)
    return round(best, 2)


def measure_loops():
    transforms = cmds.ls(type="transform", long=True) or []
    dags = []
    for path in transforms:
        sel = om2.MSelectionList()
        sel.add(path)
        dags.append(sel.getDagPath(0))

    def old_loop():
        for dag in dags:
            old_world_bbox(dag)

    def new_loop():
        for dag in dags:
            _ns["_world_bbox"](dag)

    return {
        "objects": len(dags),
        "get_scene_graph_ms": time_call(_ns["get_scene_graph"]),
        "old_cached_box_loop_ms": time_call(old_loop),
        "new_shape_walk_loop_ms": time_call(new_loop),
    }


_ns = {}
try:
    status("load")
    orig_unit = cmds.currentUnit(query=True, linear=True)
    orig_angle = cmds.currentUnit(query=True, angle=True)
    cmds.currentUnit(linear="cm")
    cmds.currentUnit(angle="deg")
    _ns = load()
    out["loaded"] = sorted(k for k in ("_world_bbox", "get_scene_graph") if k in _ns)
    module_bytes = open(os.path.join(ROOT, "maya_scene_module.py"), "rb").read()
    out["env"] = {
        "maya_version": cmds.about(version=True),
        "api_version": cmds.about(apiVersion=True),
        "qt": cmds.about(qtVersion=True),
        "module_sha256": hashlib.sha256(module_bytes).hexdigest(),
        "module_source": os.path.join(ROOT, "maya_scene_module.py"),
    }
    for flag in ("build", "cutIdentifier"):
        try:
            out["env"][flag] = str(cmds.about(**{flag: True}))
        except Exception:
            out["env"][flag] = None

    # The launcher may leave a bystander node in the session to prove the
    # driver neither quits nor touches an unsaved scene.
    out["session"] = {
        "bystander_at_start": bool(cmds.objExists("triage273_bystander")),
        "modified_at_start": bool(cmds.file(query=True, modified=True)),
    }

    # --- API fact: what MDagPath.child() returns, and does push() exist ---
    status("api")
    api_cube = cmds.polyCube(w=1, h=1, d=1, name="triage273_api")[0]
    created.append(api_cube)
    api_path = dag_of(long_name(api_cube))
    api_child = api_path.child(0)
    out["api"] = {
        "child_returns": type(api_child).__name__,
        "child_is_dag_path": isinstance(api_child, om2.MDagPath),
        "mdagpath_has_push": hasattr(api_path, "push"),
    }
    try:
        pushed = om2.MDagPath(api_path)
        pushed.push(api_child)
        out["api"]["push_then_name"] = om2.MFnDagNode(pushed).name()
    except Exception:
        out["api"]["push_error"] = traceback.format_exc()
    cmds.delete(api_cube)
    created.remove(api_cube)

    # --- case 1: +30 parent over -30 child (the issue's own case) ---
    status("cancelled_rotation")
    grp = as_name(cmds.group(empty=True, name="triage273_grp"))
    created.append(grp)
    cmds.rotate(0, 30, 0, grp, absolute=True, objectSpace=True)
    child = cmds.polyCube(w=10, h=10, d=10, name="triage273_cube")[0]
    created.append(child)
    child_path = long_name(as_name((cmds.parent(child, grp) or [child])[0]))
    # parent() preserves world space, so the child's local rotate is already
    # -30 and its world rotate is 0; do NOT zero it or the case disappears.
    exact = rounded(cmds.exactWorldBoundingBox(child_path))
    new_box = new_world_bbox(child_path)
    out["cancelled_rotation"] = {
        "setup": "group rot Y30, child local rot -30 (world rotation identity), 10 cube",
        "new_world_bbox": new_box,
        "exact_world_bbox": exact,
        "new_size": size_of(new_box),
        "old_size": size_of(box_list(old_world_bbox(dag_of(child_path)))),
        "local_rotation": rounded(cmds.xform(child_path, q=True, ro=True)),
        "world_rotation": rounded(cmds.xform(child_path, q=True, ws=True, ro=True)),
        "match": new_box == exact,
    }

    # --- case 2: top-level translate ---
    status("translate")
    box = cmds.polyCube(w=100, h=100, d=100, name="triage273_moved")[0]
    created.append(box)
    cmds.move(200, 50, 300, box, absolute=True)
    path = long_name(box)
    out["translate"] = {
        "setup": "100 cube at (200, 50, 300)",
        "new_world_bbox": new_world_bbox(path),
        "exact_world_bbox": rounded(cmds.exactWorldBoundingBox(path)),
    }
    out["translate"]["match"] = (
        out["translate"]["new_world_bbox"] == out["translate"]["exact_world_bbox"]
    )

    # --- case 3: top-level rotation ---
    status("rotation")
    cmds.rotate(0, 45, 0, box, absolute=True, objectSpace=True)
    out["rotation"] = {
        "setup": "same 100 cube rotated 45 deg about Y",
        "new_world_bbox": new_world_bbox(path),
        "exact_world_bbox": rounded(cmds.exactWorldBoundingBox(path)),
        "new_size": size_of(new_world_bbox(path)),
    }
    out["rotation"]["match"] = (
        out["rotation"]["new_world_bbox"] == out["rotation"]["exact_world_bbox"]
    )

    # --- case 4: nested child under a moved parent, then a rotated parent ---
    status("nested")
    grp2 = as_name(cmds.group(empty=True, name="triage273_nested_grp"))
    created.append(grp2)
    cmds.move(500, 0, 0, grp2, absolute=True)
    child2 = cmds.polyCube(w=10, h=10, d=10, name="triage273_nested")[0]
    created.append(child2)
    child2_path = long_name(as_name((cmds.parent(child2, grp2) or [child2])[0]))
    cmds.setAttr(child2_path + ".translate", 10, 0, 0, type="double3")
    cmds.setAttr(child2_path + ".rotate", 0, 0, 0, type="double3")
    out["nested_moved_parent"] = {
        "setup": "group (500,0,0); child local translate (10,0,0); 10 cube",
        "new_world_bbox": new_world_bbox(child2_path),
        "exact_world_bbox": rounded(cmds.exactWorldBoundingBox(child2_path)),
    }
    out["nested_moved_parent"]["match"] = (
        out["nested_moved_parent"]["new_world_bbox"]
        == out["nested_moved_parent"]["exact_world_bbox"]
    )

    cmds.rotate(0, 30, 0, grp2, absolute=True, objectSpace=True)
    out["nested_rotated_parent"] = {
        "setup": "group (500,0,0) rot Y30; child local translate (10,0,0); 10 cube",
        "new_world_bbox": new_world_bbox(child2_path),
        "exact_world_bbox": rounded(cmds.exactWorldBoundingBox(child2_path)),
    }
    out["nested_rotated_parent"]["match"] = (
        out["nested_rotated_parent"]["new_world_bbox"]
        == out["nested_rotated_parent"]["exact_world_bbox"]
    )

    # --- case 5: shape path ---
    status("shape_path")
    shape_path = cmds.listRelatives(child2_path, shapes=True, fullPath=True)[0]
    out["shape_path"] = {
        "setup": shape_path,
        "new_world_bbox": new_world_bbox(shape_path),
        "exact_world_bbox": rounded(cmds.exactWorldBoundingBox(shape_path)),
    }
    out["shape_path"]["match"] = (
        out["shape_path"]["new_world_bbox"] == out["shape_path"]["exact_world_bbox"]
    )

    # --- case 6: a group with no shape -> cached path, on real Maya ---
    status("empty_group")
    empty = as_name(cmds.group(empty=True, name="triage273_empty"))
    created.append(empty)
    empty_box = _ns["_world_bbox"](dag_of(long_name(empty)))
    out["empty_group"] = {
        "setup": "empty group (no shape anywhere below)",
        "min": rounded([empty_box.min[i] for i in range(3)]),
        "max": rounded([empty_box.max[i] for i in range(3)]),
        "min_gt_max": bool(empty_box.min[0] > empty_box.max[0]),
        "has_no_extent": bool(_ns["_box_is_default"](empty_box)),
        "cached_fn_bbox": rounded(
            [om2.MFnDagNode(dag_of(long_name(empty))).boundingBox.min[i] for i in range(3)]
            + [om2.MFnDagNode(dag_of(long_name(empty))).boundingBox.max[i] for i in range(3)]
        ),
    }
    fresh = om2.MBoundingBox()
    out["empty_box_api"] = {
        "has_isEmpty": hasattr(fresh, "isEmpty"),
        "has_is_empty": hasattr(fresh, "is_empty"),
        "fresh_min": rounded([fresh.min[i] for i in range(3)]),
        "fresh_max": rounded([fresh.max[i] for i in range(3)]),
    }

    # --- case 7: intermediate shape is left out of the walk ---
    status("intermediate")
    try:
        inter = cmds.polyCube(w=10, h=10, d=10, name="triage273_inter")[0]
        created.append(inter)
        inter_path = long_name(inter)
        inter_shape = cmds.listRelatives(inter_path, shapes=True)[0]
        cmds.setAttr(inter_shape + ".intermediateObject", 1)
        shapes = _ns["_shape_dag_paths"](dag_of(inter_path))
        out["intermediate"] = {
            "setup": inter_shape + " intermediateObject=1",
            "walk_returns": [om2.MFnDagNode(p).name() for p in shapes],
            "skipped": len(shapes) == 0,
        }
    except Exception:
        out["intermediate"] = {"error": traceback.format_exc()}

    # --- case 7b: an empty mesh shape must not drag the union to the origin ---
    status("empty_mesh_mix")
    mix_grp = as_name(cmds.group(empty=True, name="triage273_mix"))
    created.append(mix_grp)
    far = cmds.polyCube(w=10, h=10, d=10, name="triage273_far")[0]
    created.append(far)
    cmds.move(1000, 0, 0, far, absolute=True)
    cmds.parent(far, mix_grp)
    empty_tr = cmds.createNode("transform", name="triage273_emptymesh")
    created.append(empty_tr)
    # It must sit under the measured group, or the case proves nothing.
    cmds.parent(empty_tr, mix_grp)
    empty_shape = cmds.createNode("mesh", parent=empty_tr, name="triage273_emptymeshShape")
    empty_shape_path = long_name(empty_shape)
    empty_shape_box = om2.MFnDagNode(dag_of(empty_shape_path)).boundingBox
    mix_path = long_name(mix_grp)
    out["empty_mesh_mix"] = {
        "setup": "group holds a 10 cube at (1000,0,0) and a mesh with no vertices",
        "empty_shape_bbox": rounded(
            [empty_shape_box.min[i] for i in range(3)] + [empty_shape_box.max[i] for i in range(3)]
        ),
        "new_world_bbox": new_world_bbox(mix_path),
        "exact_world_bbox": rounded(cmds.exactWorldBoundingBox(mix_path)),
    }
    out["empty_mesh_mix"]["match"] = (
        out["empty_mesh_mix"]["new_world_bbox"] == out["empty_mesh_mix"]["exact_world_bbox"]
    )
    out["empty_mesh_mix"]["origin_inside"] = bool(
        out["empty_mesh_mix"]["new_world_bbox"][0]
        <= 0
        <= out["empty_mesh_mix"]["new_world_bbox"][3]
    )
    # Negative control: the same union WITHOUT the empty-shape filter. If this
    # also reported no origin, the row above would not prove anything.
    unfiltered = om2.MBoundingBox()
    for shape_path in _ns["_shape_dag_paths"](dag_of(mix_path)):
        shape_box = om2.MFnDagNode(shape_path).boundingBox
        _ns["_expand_box"](unfiltered, shape_box, shape_path.inclusiveMatrix())
    out["empty_mesh_mix"]["unfiltered_bbox"] = box_list(unfiltered)
    out["empty_mesh_mix"]["unfiltered_includes_origin"] = bool(
        unfiltered.min[0] <= 0 <= unfiltered.max[0]
    )

    # --- case 8: performance, 100 then 1000 flat objects ---
    status("perf_100")
    for i in range(100):
        cube = cmds.polyCube(w=10, h=10, d=10, name=f"triage273_perf_{i}")[0]
        created.append(cube)
        cmds.move(i * 20.0, 0, 0, cube, absolute=True)
    out["perf_100"] = measure_loops()

    status("perf_1000")
    for i in range(100, 1000):
        cube = cmds.polyCube(w=10, h=10, d=10, name=f"triage273_perf_{i}")[0]
        created.append(cube)
        cmds.move(i * 20.0, 0, 0, cube, absolute=True)
    out["perf_1000"] = measure_loops()

    # --- case 9: the nested cost the flat scene cannot show ---
    # Every ancestor walks its whole subtree, so one 200-deep chain costs
    # O(depth^2) shape visits. This bounds the worst shape a venue scene can
    # have; it is not a claim about deep rigs.
    status("perf_chain")
    for cube in [c for c in created if c.startswith("triage273_perf_")]:
        if cmds.objExists(cube):
            cmds.delete(cube)
            created.remove(cube)
    prev = as_name(cmds.group(empty=True, name="triage273_chain_0"))
    created.append(prev)
    for i in range(1, 200):
        group = as_name(cmds.group(empty=True, name=f"triage273_chain_{i}", parent=prev))
        created.append(group)
        prev = group
    leaf = cmds.polyCube(w=10, h=10, d=10, name="triage273_chain_leaf")[0]
    created.append(leaf)
    cmds.parent(leaf, prev)
    out["perf_chain"] = measure_loops()

    out["ok"] = True
except Exception:
    out["ok"] = False
    out["error"] = traceback.format_exc()
finally:
    try:
        status("cleanup")
    except Exception:
        # A diagnostic write must never block the real cleanup below.
        pass
    try:
        if orig_unit:
            cmds.currentUnit(linear=orig_unit)
        if orig_angle:
            cmds.currentUnit(angle=orig_angle)
    except Exception:
        pass
    for name in created:
        try:
            if cmds.objExists(name):
                cmds.delete(name)
        except Exception:
            pass
    try:
        out["leftover"] = [x for x in created if cmds.objExists(x)]
        out["restored_unit"] = cmds.currentUnit(query=True, linear=True)
        out["restored_angle"] = cmds.currentUnit(query=True, angle=True)
        out.setdefault("session", {})
        out["session"]["bystander_at_end"] = bool(cmds.objExists("triage273_bystander"))
        out["session"]["modified_at_end"] = bool(cmds.file(query=True, modified=True))
    except Exception:
        pass
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, sort_keys=True)
    # Never close a session that might hold someone's unsaved work: quitting
    # is opt-in, for a throwaway -script process only.
    if os.environ.get("MAYA273_QUIT") == "1":
        cmds.quit(force=True)
