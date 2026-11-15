# --- _mcp_scene light payload file (issue #276): own file, one injected module ---
#
# scene_tools._ensure_module_injected appends this file after
# scene_state_module.py and injects the whole assembly as _mcp_scene. It is
# not a separate injected module.
#
# Why a separate file: maya_scene_module.py is capped by
# .github/monolith-budget.json, so the builder cannot grow there. The light
# payload used to be built twice in that file - once for the aesthetic engine
# (13 fields) and once for the scene review lighting check (7 fields) - from
# the same Maya attributes. Two copies could drift apart, and the short one
# silently dropped the fields that describe a light's shape. One builder here
# is the only place that reads those attributes, so both callers get the same
# dict.
#
# Cross-file call: maya_scene_module.py reaches collect_light_payloads()
# through globals(), the same declared seam zone_geometry_module.py uses for
# get_zone_map(). A direct name would be invisible to mypy, which checks each
# file on its own and would report it as undefined.
#
# Runtime floor: Maya >=2023 (Python 3.9). No __future__ import here: it would
# land mid-file in the assembled payload = SyntaxError. The annotations below
# are py3.9-safe ONLY because maya_scene_module.py's `from __future__ import
# annotations` governs the assembled unit and keeps every annotation a string.
# Do NOT exec/import this file standalone on py3.9.

from typing import TYPE_CHECKING, Any, cast

import maya.cmds as cmds


if TYPE_CHECKING:
    from .scene_module_types import LightPayload


def build_light_payload(shape_name: str) -> LightPayload | None:
    """Build one light's payload from its shape node; None when a read fails.

    The shape name is what ``cmds.ls(type="light")`` returns. The payload
    names the light by its transform, reports world position and rotation,
    and fills the shape-specific fields only for the light type that has
    them. A light whose attributes cannot be read is skipped by the caller:
    one broken light must not hide the rest.
    """
    try:
        parent = cmds.listRelatives(shape_name, parent=True, fullPath=True) or [shape_name]
        light_transform = parent[0]
        ltype = cmds.nodeType(shape_name)

        color = (
            cmds.getAttr(f"{shape_name}.color")[0]
            if cmds.objExists(f"{shape_name}.color")
            else [1, 1, 1]
        )
        intensity = (
            cmds.getAttr(f"{shape_name}.intensity")
            if cmds.objExists(f"{shape_name}.intensity")
            else 1.0
        )

        # Position and rotation come from the transform, in world space.
        pos = cast(Any, cmds.xform)(light_transform, q=True, ws=True, t=True) or [0, 0, 0]
        rot = cast(Any, cmds.xform)(light_transform, q=True, ws=True, ro=True) or [0, 0, 0]

        # Decay type (0=None, 1=Linear, 2=Quadratic, 3=Cubic)
        decay = 0
        if cmds.objExists(f"{shape_name}.decayRate"):
            decay = cmds.getAttr(f"{shape_name}.decayRate")

        # Depth-map shadows are the common case; a ray-traced light reports
        # the other flag. A light with neither attribute counts as shadowing,
        # which is the reading the aesthetic engine already used.
        shadow_on = True
        if cmds.objExists(f"{shape_name}.useDepthMapShadow"):
            shadow_on = bool(cmds.getAttr(f"{shape_name}.useDepthMapShadow"))
        elif cmds.objExists(f"{shape_name}.useRayTraceShadows"):
            shadow_on = bool(cmds.getAttr(f"{shape_name}.useRayTraceShadows"))

        # Spotlight cone angle (degrees) and soft edge.
        cone_angle = None
        penumbra = None
        if ltype == "spotLight" and cmds.objExists(f"{shape_name}.coneAngle"):
            cone_angle = cmds.getAttr(f"{shape_name}.coneAngle")
            if cmds.objExists(f"{shape_name}.penumbraAngle"):
                penumbra = cmds.getAttr(f"{shape_name}.penumbraAngle")

        # Area light size; Maya reports width and height as separate attrs.
        area_size = None
        if ltype == "areaLight" and cmds.objExists(f"{shape_name}.areaWidth"):
            aw = cmds.getAttr(f"{shape_name}.areaWidth")
            ah = (
                cmds.getAttr(f"{shape_name}.areaHeight")
                if cmds.objExists(f"{shape_name}.areaHeight")
                else aw
            )
            area_size = [aw, ah]

        # Diffuse/Specular contribution.
        diffuse = (
            cmds.getAttr(f"{shape_name}.emitDiffuse")
            if cmds.objExists(f"{shape_name}.emitDiffuse")
            else True
        )
        specular = (
            cmds.getAttr(f"{shape_name}.emitSpecular")
            if cmds.objExists(f"{shape_name}.emitSpecular")
            else True
        )

        return {
            "name": light_transform.split("|")[-1],
            "type": ltype,
            "color": list(color),
            "intensity": intensity,
            "position": [round(v, 1) for v in pos],
            "rotation": [round(v, 1) for v in rot],
            "decay": decay,
            "shadow": shadow_on,
            "cone_angle": round(cone_angle, 1) if cone_angle else None,
            "penumbra": round(penumbra, 1) if penumbra else None,
            "area_size": area_size,
            "diffuse": bool(diffuse),
            "specular": bool(specular),
        }
    except Exception:
        return None


def collect_light_payloads(shape_names: list[str] | None = None) -> list[LightPayload]:
    """Build the payload for every light in the scene, skipping unreadable ones.

    This is the one entry both consumers call: analyze_aesthetics() for the
    lighting dimension and scene_review() for its lighting check. They get the
    same list, so a field added here reaches both and the two cannot drift.

    shape_names is the list the caller already read with ``cmds.ls``; passing
    it saves the second Maya query in scene_review, which needs the list first
    to tell an empty scene from an unreadable one. Omit it when no list is at
    hand and this function lists the lights itself.
    """
    if shape_names is None:
        shape_names = cmds.ls(type="light") or []
    lights: list[LightPayload] = []
    for shape_name in shape_names:
        payload = build_light_payload(shape_name)
        if payload is not None:
            lights.append(payload)
    return lights
