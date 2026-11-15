"""Probe: real Maya shape of ``cmds.xform`` query results (issue #277).

Run inside a throwaway Maya GUI session, never in CI. ``maya.standalone`` is
broken on this box (``ImportError: DLL load failed`` under PowerShell, native
access violation under Git Bash), so the documented GUI lane is used. Put this
in a MEL wrapper and launch it with ``maya.exe -script <wrapper.mel>``:

    int $rc = catch(python("import runpy; runpy.run_path(r'<probe.py>', "
        + "run_name='__main__')"));
    if ($rc != 0) { print "probe277: python raised; read its output JSON\\n"; }
    evalDeferred "quit -f";

The probe only asks questions: it reads an existing transform in the default
scene, creates no nodes and changes nothing. It refuses to run on a scene that
has a file on disk or unsaved changes. Output goes to ``MAYA277_OUT`` (default:
a temp path) as one JSON object, so the caller can archive the file unchanged
as evidence. The object records the Maya executable and PID, the driver's
sha256, the node count and scene unit before and after, and whether the scene
stayed unmodified.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import traceback

import maya.cmds as cmds


_OUT = os.environ.get(
    "MAYA277_OUT",
    os.path.join(tempfile.gettempdir(), "probe277", "out.json"),
)


def describe(value: object) -> dict[str, object]:
    """What the value is, in the terms the type discussion needs."""
    if isinstance(value, (list, tuple)):
        return {
            "python_type": type(value).__name__,
            "length": len(value),
            "element_types": [type(item).__name__ for item in value],
            "values": list(value),
        }
    return {"python_type": type(value).__name__, "values": value}


def driver_sha256() -> str:
    """Hash of the file that ran, so a copied artifact can name its source."""
    try:
        with open(__file__, "rb") as handle:
            return hashlib.sha256(handle.read()).hexdigest()
    except OSError:
        return "unavailable"


def probe_transform() -> str | None:
    """The transform production code reaches for: a shape's parent."""
    # Prefer the perspective camera: it is in every default scene and has a
    # non-zero translation and rotation, so both queries return real values.
    for shape in cmds.ls(type="camera", long=True) or []:
        if shape.split("|")[-1].lower().startswith("persp"):
            parent = cmds.listRelatives(shape, parent=True, fullPath=True)
            if parent:
                return parent[0]
    for shape_type in ("camera", "light"):
        shapes = cmds.ls(type=shape_type, long=True) or []
        if shapes:
            parent = cmds.listRelatives(shapes[0], parent=True, fullPath=True)
            if parent:
                return parent[0]
    transforms = cmds.ls(type="transform", long=True) or []
    return transforms[0] if transforms else None


def main() -> dict[str, object]:
    result: dict[str, object] = {
        "maya_version": cmds.about(version=True),
        "api_version": cmds.about(apiVersion=True),
        "batch": cmds.about(batch=True),
        "python_version": sys.version,
        "maya_executable": sys.executable,
        "maya_pid": os.getpid(),
        "driver_sha256": driver_sha256(),
        "scene_modified": cmds.file(query=True, modified=True),
        "scene_name": cmds.file(query=True, sceneName=True),
        "node_count_before": len(cmds.ls(dag=True) or []),
        "unit_before": cmds.currentUnit(query=True, linear=True),
    }
    try:
        result["maya_build"] = cmds.about(cutIdentifier=True)
    except Exception:
        result["maya_build"] = "not reported by cmds.about"

    if result["scene_modified"] or result["scene_name"]:
        result["status"] = "refused-scene-not-empty"
        return result

    target = probe_transform()
    if target is None:
        result["status"] = "no-transform-in-scene"
        return result

    result["target_transform"] = target
    result["call_sites"] = {
        "short_flags_translation": describe(cmds.xform(target, q=True, ws=True, t=True)),
        "long_flags_translation": describe(
            cmds.xform(target, query=True, worldSpace=True, translation=True)
        ),
        "short_flags_rotation": describe(cmds.xform(target, q=True, ws=True, ro=True)),
        "long_flags_rotation": describe(
            cmds.xform(target, query=True, worldSpace=True, rotation=True)
        ),
    }
    result["transform_attributes"] = {
        "translate": describe(cmds.getAttr(target + ".translate")),
        "rotate": describe(cmds.getAttr(target + ".rotate")),
    }
    result["node_count_after"] = len(cmds.ls(dag=True) or [])
    result["unit_after"] = cmds.currentUnit(query=True, linear=True)
    result["scene_modified_after_probe"] = cmds.file(query=True, modified=True)
    return result


def write(payload: dict[str, object]) -> None:
    directory = os.path.dirname(_OUT)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(_OUT, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


if __name__ == "__main__":
    try:
        payload = {"status": "ok", **main()}
    except Exception:
        payload = {"status": "error", "traceback": traceback.format_exc()}
    write(payload)
    print("probe277 wrote", _OUT)
