"""Run issue #229's six call-form checks inside a real Maya GUI session.

Why a GUI session: on the box that measured this batch, `mayapy` cannot
even import `maya.standalone` (DLL initialisation failure), so the
real-Maya interpreter test cannot run there. `maya.exe -script` is the
documented fallback; this file is the script that fallback runs.

How to run it (see docs/testing.md, the real-Maya section):

    python("exec(open(r'<repo>/docs/reference/six_callform_gui_driver.py',
                      encoding='utf-8').read())")

either pasted into a fresh GUI instance's Script Editor or executed by a
`-script` MEL file. Launch a *new* Maya instance: the driver forces a new
empty scene, and refuses to replace a scene that has a file on disk or
unsaved changes, unless MAYA253_FORCE=1 is set on purpose.

Paths come from the environment: MAYA253_REPO (repo root, used for the
import path), MAYA253_OUT (where the JSON goes), MAYA253_FORCE (override
the scene guard). The defaults are this repository on the box that ran
it first.

What it writes: one JSON file (path in `OUT_JSON`) with the environment,
the isolation steps, one row per call form (pass/fail plus the values Maya
returned), the shipped pytest function's own result, a self-check that a
raising probe still gets cleaned up, and the post-cleanup state.

Why the per-form rows repeat what the shipped test asserts: one failing
form must not hide the other five, and each row has to stand on its own
in the evidence file. The shipped function is called too, so a drift
between this driver and the test shows up as a disagreement rather than
as a silent second opinion.

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
# The shipped test makes its own GEO_stub* nodes, so the leftover scan
# looks for those too even though this driver never creates one.
STUB_PREFIX = "GEO_stub"


def _make_cube(cmds, suffix, created):
    """Make one prefixed cube and track it for cleanup."""
    node = cmds.polyCube(name=f"{NODE_PREFIX}_{suffix}")[0]
    created.append(node)
    return node


def _playback_range(cmds):
    """The current playback in/out points, as a two-item list."""
    return [
        cmds.playbackOptions(q=True, minTime=True),
        cmds.playbackOptions(q=True, maxTime=True),
    ]


def _exc_text(exc):
    """One-line description of an exception, for the JSON rows."""
    return "".join(traceback.format_exception_only(type(exc), exc)).strip()


def _reset_playback(cmds, start_range):
    """Put playback back where the run found it; return a problem or None."""
    try:
        cmds.playbackOptions(min=start_range[0], max=start_range[1])
    except Exception as exc:
        return f"playback restore failed: {exc}"
    return None


def _restore_selection(cmds, names):
    """Put the selection back where the run found it; return a problem or None."""
    try:
        cmds.select(names, replace=True)
    except Exception as exc:
        return f"selection restore failed: {exc}"
    return None


def _record(rows, name, fn, created):
    """Run one probe, keep its verdict, never let its exception escape."""
    row = {"form": name, "status": "fail", "detail": None}
    try:
        row["detail"] = fn(created)
        row["status"] = "pass"
    except Exception as exc:  # the evidence is the reason, not a crash
        row["detail"] = _exc_text(exc)
        row["traceback"] = traceback.format_exc()
    rows.append(row)
    return row


def _form_xform(created):
    """xform answers the short flags q/ws/t/ro; the stub lists long ones only."""
    import maya.cmds as cmds

    cube = _make_cube(cmds, "xform", created)
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

    # `holder` already owns the target name, so the rename has to come back
    # with a numbered name of its own instead of taking the holder's.
    holder = _make_cube(cmds, "name_holder", created)
    cube = _make_cube(cmds, "orig", created)
    renamed = cmds.rename(cube, f"{NODE_PREFIX}_name_holder")
    assert isinstance(renamed, str) and renamed, repr(renamed)
    created.append(renamed)
    assert cmds.objExists(holder), "the name clash cost a live node"
    assert cmds.objExists(renamed), "the renamed node vanished"
    return {
        "returned": renamed,
        "return_type": type(renamed).__name__,
        "holder_kept": holder,
        "renamed_has_shape": bool(cmds.listRelatives(renamed, shapes=True) or []),
    }


def _form_key_tangent(created):
    """keyTangent accepts itt/ott, the documented short flag names.

    The tangent types are set to values that are NOT Maya's default
    (`auto`), so the read-back proves the flags did something; with the
    default the call would look identical whether or not it ran.
    """
    import maya.cmds as cmds

    # Capture first: creating a node leaves it selected, so reading the
    # selection after the make would record the driver's own node.
    selected_before = cmds.ls(sl=True) or []
    cube = _make_cube(cmds, "tangent", created)
    cmds.setKeyframe(cube, attribute="translateX")
    selection_problem = None
    try:
        cmds.select(cube)
        cmds.keyTangent(edit=True, itt="linear", ott="step")
        in_types = list(cmds.keyTangent(cube, q=True, itt=True) or [])
        out_types = list(cmds.keyTangent(cube, q=True, ott=True) or [])
    finally:
        selection_problem = _restore_selection(cmds, selected_before)
    assert selection_problem is None, selection_problem
    assert in_types == ["linear"], in_types
    assert out_types == ["step"], out_types
    return {
        "in_tangent_types": in_types,
        "out_tangent_types": out_types,
        "selection_restored_to": cmds.ls(sl=True) or [],
    }


def _form_playback(created):
    """playbackOptions accepts min/max, the documented short flag names.

    It takes `created` only because every probe has the same signature.
    """
    import maya.cmds as cmds

    before = _playback_range(cmds)
    cmds.playbackOptions(min=1, max=12)
    after = _playback_range(cmds)
    assert after[1] == 12, after
    return {"before": before, "after": after}


def _form_aim_constraint(created):
    """aimConstraint takes three-number lists, not only tuples."""
    import maya.cmds as cmds

    target = _make_cube(cmds, "target", created)
    aimed = _make_cube(cmds, "aimed", created)
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

    cube = _make_cube(cmds, "mesh", created)
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
        except Exception as exc:
            problems.append(f"delete {name!r} failed: {exc}")
    return problems


def _failure_cleanup_self_check(cmds):
    """A probe that raises after creating nodes must still leave nothing.

    This is the measured half of the ticket's "a failing test must not
    pollute the scene" requirement; the `finally` in `run()` is the other.
    """
    created = []
    try:
        _make_cube(cmds, "doomed", created)
        _make_cube(cmds, "doomed2", created)
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
    scene_modified = cmds.file(q=True, modified=True)
    # Refuse to wipe anything that could be someone's work: a scene with a
    # file on disk, or an untitled scene that already has unsaved edits.
    if (scene_name or scene_modified) and not FORCE:
        raise SystemExit(
            f"refusing to replace the scene {scene_name!r} (modified={scene_modified}); "
            "run in a fresh Maya, or set MAYA253_FORCE=1 on purpose"
        )

    selection_before = cmds.ls(sl=True) or []
    result["isolation"] = {
        "scene_before_new": scene_name,
        "nodes_before_new": len(cmds.ls() or []),
        "modified_before_new": scene_modified,
        "selection_before_new": selection_before,
    }
    cmds.file(new=True, force=True)
    start_range = _playback_range(cmds)
    # State inside the scene this run works in: what cleanup must give back.
    selection_at_start = cmds.ls(sl=True) or []
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
        except BaseException as exc:  # recorded, then the run continues
            result["shipped_test"] = {
                "status": "fail",
                "test": "tests/test_mayapy_smoke.py::test_callform_stub_disagreement_forms",
                "detail": _exc_text(exc),
                "traceback": traceback.format_exc(),
            }

        for name, fn in FORMS:
            form_created = []
            _record(result["forms"], name, fn, form_created)
            created.extend(form_created)
            _reset_playback(cmds, start_range)

        result["failure_cleanup"] = _failure_cleanup_self_check(cmds)
    finally:
        problems = _delete_all(created, cmds)
        playback_problem = _reset_playback(cmds, start_range)
        if playback_problem:
            problems.append(playback_problem)
        selection_problem = _restore_selection(cmds, selection_at_start)
        if selection_problem:
            problems.append(selection_problem)
        result["cleanup"] = {
            "deleted_names": created,
            "problems": problems,
            "leftover_nodes": [
                n for n in (cmds.ls(f"{NODE_PREFIX}*") or []) + (cmds.ls(f"{STUB_PREFIX}*") or [])
            ],
            "nodes_after_cleanup": len(cmds.ls() or []),
            "playback_range_after_cleanup": _playback_range(cmds),
            "selection_after_cleanup": cmds.ls(sl=True) or [],
            "scene_after_cleanup": cmds.file(q=True, sceneName=True),
        }

    return result


def _overall_verdict(result):
    """Pass only when every form passed and nothing was left behind.

    A leaked node or a failed cleanup makes the run a failure even when all
    six rows are green: the scene is part of what the ticket asks for.
    """
    rows = result.get("forms", [])
    if not rows or any(row["status"] != "pass" for row in rows):
        return "fail"
    if result.get("shipped_test", {}).get("status") != "pass":
        return "fail"
    if result.get("failure_cleanup", {}).get("status") != "pass":
        return "fail"
    cleanup = result.get("cleanup", {})
    if cleanup.get("problems") or cleanup.get("leftover_nodes"):
        return "fail"
    return "pass"


def main():
    """Run, write the JSON, and report the verdict in Maya's own console."""
    result = {}
    try:
        result = run()
    except BaseException:  # a fatal error is still evidence
        result = {"fatal": traceback.format_exc()}
    result["verdict"] = _overall_verdict(result)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"issue #253 six call forms: {result['verdict']}; wrote {OUT_JSON}")
    return result


if __name__ == "__main__":
    main()
