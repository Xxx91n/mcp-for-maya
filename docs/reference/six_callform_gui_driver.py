"""Run issue #229's six call-form checks inside a real Maya GUI session.

Why a GUI session: on the box that measured this batch, `mayapy` cannot
even import `maya.standalone` (DLL initialisation failure), so the
mayapy tier cannot run there. `maya.exe -script` is the documented
fallback; this file is the script that fallback runs.

How to run it (see docs/testing.md, Tier 2):

    python("exec(open(r'<repo>/docs/reference/six_callform_gui_driver.py',
                      encoding='utf-8').read())")

either pasted into a fresh GUI instance's Script Editor or executed by a
`-script` MEL file. Launch a *new* Maya instance: the driver forces a new
empty scene, and refuses to replace a scene that has a file on disk
unless MAYA253_FORCE=1 is set on purpose.

What it writes: one JSON file (path in `OUT_JSON`) with the environment,
the isolation steps, one row per call form (pass/fail plus the values Maya
returned), the shipped pytest function's own result, a self-check that a
raising probe still gets cleaned up, and the post-cleanup state.

What it does not do: it does not assert Maya's behaviour beyond the six
forms, and it does not clean up anything it did not create. The caller is
responsible for closing the throwaway Maya afterwards.
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path


REPO_ROOT = Path(os.environ.get("MAYA253_REPO", r"D:\Aworker\maya\maya-mcp-server"))
OUT_JSON = Path(
    os.environ.get(
        "MAYA253_OUT",
        r"C:\Users\Administrator\AppData\Local\Temp\maya253\six_forms_result.json",
    )
)
FORCE = os.environ.get("MAYA253_FORCE") == "1"

# Prefix for every node the driver makes, so the post-cleanup check can
# look for leftovers without guessing.
NODE_PREFIX = "GEO_cf253"
STUB_PREFIX = "GEO_stub"


def _record(rows, name, fn, created):
    """Run one probe, keep its verdict, never let its exception escape."""
    row = {"form": name, "status": "fail", "detail": None}
    try:
        row["detail"] = fn(created)
        row["status"] = "pass"
    except Exception as exc:  # noqa: BLE001 - the evidence is the reason, not a crash
        row["detail"] = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        row["traceback"] = traceback.format_exc()
    rows.append(row)
    return row


def _form_xform(created):
    """xform answers the short flags q/ws/t/ro; the stub lists long ones only."""
    import maya.cmds as cmds

    cube = cmds.polyCube(name=f"{NODE_PREFIX}_xform")[0]
    created.append(cube)
    cmds.move(10, 0, 0, cube)
    translation = cmds.xform(cube, q=True, ws=True, t=True)
    rotation = cmds.xform(cube, q=True, ws=True, ro=True)
    assert [round(v, 3) for v in translation] == [10.0, 0.0, 0.0], translation
    assert len(rotation) == 3, rotation
    return {
        "translation": [round(v, 3) for v in translation],
        "rotation": [round(v, 3) for v in rotation],
    }


def _form_rename(created):
    """rename returns the new name; the stub says it returns None."""
    import maya.cmds as cmds

    bystander = cmds.polyCube(name=f"{NODE_PREFIX}_renamed")[0]
    created.append(bystander)
    cube = cmds.polyCube(name=f"{NODE_PREFIX}_orig")[0]
    created.append(cube)
    renamed = cmds.rename(cube, f"{NODE_PREFIX}_renamed")
    assert isinstance(renamed, str) and renamed, repr(renamed)
    created.append(renamed)
    assert cmds.objExists(bystander), "the name clash cost a live node"
    assert cmds.objExists(renamed), "the renamed node vanished"
    return {
        "returned": renamed,
        "return_type": type(renamed).__name__,
        "bystander_kept": bystander,
        "renamed_has_shape": bool(cmds.listRelatives(renamed, shapes=True) or []),
    }


def _form_key_tangent(created):
    """keyTangent accepts itt/ott, the documented short flag names."""
    import maya.cmds as cmds

    cube = cmds.polyCube(name=f"{NODE_PREFIX}_tangent")[0]
    created.append(cube)
    cmds.setKeyframe(cube, attribute="translateX")
    cmds.select(cube)
    cmds.keyTangent(edit=True, itt="auto", ott="auto")
    return {"in_tangent_types": list(cmds.keyTangent(cube, q=True, itt=True) or [])}


def _form_playback(created):
    """playbackOptions accepts min/max, the documented short flag names."""
    import maya.cmds as cmds

    before = (
        cmds.playbackOptions(q=True, minTime=True),
        cmds.playbackOptions(q=True, maxTime=True),
    )
    cmds.playbackOptions(min=1, max=12)
    after = (
        cmds.playbackOptions(q=True, minTime=True),
        cmds.playbackOptions(q=True, maxTime=True),
    )
    assert after[1] == 12, after
    return {"before": list(before), "after": list(after)}


def _form_aim_constraint(created):
    """aimConstraint takes three-number lists, not only tuples."""
    import maya.cmds as cmds

    target = cmds.polyCube(name=f"{NODE_PREFIX}_target")[0]
    created.append(target)
    aimed = cmds.polyCube(name=f"{NODE_PREFIX}_aimed")[0]
    created.append(aimed)
    made = cmds.aimConstraint(
        target,
        aimed,
        aimVector=[0, 0, -1],
        upVector=[0, 1, 0],
        worldUpType="scene",
    )
    assert made, made
    made_list = list(made) if isinstance(made, (list, tuple)) else [made]
    created.extend(made_list)
    return {
        "returned": made_list,
        "return_type": type(made).__name__,
        "constraint_exists": bool(cmds.objExists(made_list[0])),
    }


def _form_get_point(created):
    """MFnMesh.getPoint takes MSpace.kWorld; the stub types that constant int."""
    import maya.cmds as cmds
    from maya.api import OpenMaya

    cube = cmds.polyCube(name=f"{NODE_PREFIX}_mesh")[0]
    created.append(cube)
    cmds.move(10, 0, 0, cube)
    selection = OpenMaya.MSelectionList()
    selection.add(cube)
    shape_dag = selection.getDagPath(0)
    shape_dag.extendToShape()
    mesh = OpenMaya.MFnMesh(shape_dag)
    world_point = mesh.getPoint(0, OpenMaya.MSpace.kWorld)
    object_point = mesh.getPoint(0, OpenMaya.MSpace.kObject)
    gap = round(world_point[0] - object_point[0], 3)
    assert gap == 10, (world_point, object_point)
    return {
        "world": [round(v, 4) for v in world_point],
        "object": [round(v, 4) for v in object_point],
        "x_gap": gap,
        "kWorld_type": type(OpenMaya.MSpace.kWorld).__name__,
    }


FORMS = (
    ("xform q/ws/t/ro", _form_xform),
    ("rename returns the new name", _form_rename),
    ("keyTangent itt/ott", _form_key_tangent),
    ("playbackOptions min/max", _form_playback),
    ("aimConstraint three-number lists", _form_aim_constraint),
    ("MFnMesh.getPoint MSpace.kWorld", _form_get_point),
)


def _delete_all(created, cmds):
    """Delete every created node, newest first; report what could not go."""
    problems = []
    for name in reversed(created):
        try:
            if cmds.objExists(name):
                cmds.delete(name)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"delete {name!r} failed: {exc}")
    return problems


def _failure_cleanup_self_check(cmds):
    """A probe that raises after creating nodes must still leave nothing.

    This is the measured half of the ticket's "a failing test must not
    pollute the scene" requirement; the `finally` in `run()` is the other.
    """
    created = []
    try:
        created.append(cmds.polyCube(name=f"{NODE_PREFIX}_doomed")[0])
        created.append(cmds.polyCube(name=f"{NODE_PREFIX}_doomed2")[0])
        raise RuntimeError("deliberate probe failure")
    except RuntimeError:
        pass
    finally:
        problems = _delete_all(created, cmds)
    leftovers = [n for n in (cmds.ls(f"{NODE_PREFIX}_doomed*") or [])]
    return {
        "delete_problems": problems,
        "leftovers": leftovers,
        "status": "pass" if not problems and not leftovers else "fail",
    }


def run():
    import maya.cmds as cmds

    result = {"meta": {}, "isolation": {}, "forms": [], "shipped_test": {}, "failure_cleanup": {}}

    result["meta"] = {
        "maya_version": cmds.about(version=True),
        "api_version": cmds.about(apiVersion=True),
        "batch": cmds.about(batch=True),
        "product": cmds.about(product=True),
        "operating_system": cmds.about(operatingSystem=True),
        "maya_python": sys.version.split()[0],
        "maya_executable": sys.executable,
        "session_pid": os.getpid(),
        # exec() hands this file no __file__ of its own; record what we have.
        "driver_file": globals().get("__file__", "<exec>"),
        "repo_root": str(REPO_ROOT),
        "out_json": str(OUT_JSON),
        "force_scene_replace": FORCE,
    }

    scene_name = cmds.file(q=True, sceneName=True)
    if scene_name and not FORCE:
        raise SystemExit(
            f"refusing to replace the scene {scene_name!r}; run in a fresh Maya, "
            "or set MAYA253_FORCE=1 on purpose"
        )

    result["isolation"] = {
        "scene_before_new": scene_name,
        "nodes_before_new": len(cmds.ls() or []),
        "modified_before_new": cmds.file(q=True, modified=True),
    }
    cmds.file(new=True, force=True)
    start_range = [
        cmds.playbackOptions(q=True, minTime=True),
        cmds.playbackOptions(q=True, maxTime=True),
    ]
    result["isolation"].update(
        {
            "scene_after_new": cmds.file(q=True, sceneName=True),
            "nodes_after_new": len(cmds.ls() or []),
            "playback_range_at_start": start_range,
        }
    )

    sys.path.insert(0, str(REPO_ROOT / "tests"))
    sys.path.insert(0, str(REPO_ROOT / "src"))

    created = []
    try:
        try:
            import test_mayapy_smoke as shipped

            shipped.test_callform_stub_disagreement_forms(real_maya=cmds)
            result["shipped_test"] = {
                "status": "pass",
                "test": "tests/test_mayapy_smoke.py::test_callform_stub_disagreement_forms",
            }
        except BaseException as exc:  # noqa: BLE001 - recorded, then the run continues
            result["shipped_test"] = {
                "status": "fail",
                "test": "tests/test_mayapy_smoke.py::test_callform_stub_disagreement_forms",
                "detail": "".join(traceback.format_exception_only(type(exc), exc)).strip(),
                "traceback": traceback.format_exc(),
            }

        for name, fn in FORMS:
            form_created = []
            _record(result["forms"], name, fn, form_created)
            created.extend(form_created)
            try:
                cmds.playbackOptions(min=start_range[0], max=start_range[1])
            except Exception:  # noqa: BLE001
                pass

        result["failure_cleanup"] = _failure_cleanup_self_check(cmds)
    finally:
        problems = _delete_all(created, cmds)
        try:
            cmds.playbackOptions(min=start_range[0], max=start_range[1])
        except Exception as exc:  # noqa: BLE001
            problems.append(f"playback restore failed: {exc}")
        result["cleanup"] = {
            "deleted_names": created,
            "problems": problems,
            "leftover_nodes": [
                n for n in (cmds.ls(f"{NODE_PREFIX}*") or []) + (cmds.ls(f"{STUB_PREFIX}*") or [])
            ],
            "nodes_after_cleanup": len(cmds.ls() or []),
            "playback_range_after_cleanup": [
                cmds.playbackOptions(q=True, minTime=True),
                cmds.playbackOptions(q=True, maxTime=True),
            ],
            "scene_after_cleanup": cmds.file(q=True, sceneName=True),
        }

    return result


def main():
    """Run, write the JSON, and report the verdict in Maya's own console."""
    result = {}
    try:
        result = run()
    except BaseException:  # noqa: BLE001 - a fatal error is still evidence
        result = {"fatal": traceback.format_exc()}
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    rows = result.get("forms", [])
    verdict = "pass" if rows and all(r["status"] == "pass" for r in rows) else "fail"
    print(f"issue #253 six call forms: {verdict}; wrote {OUT_JSON}")
    return result


if __name__ == "__main__":
    main()
