# t20 teapot — Utah teapot recreation: lathe body (classic silhouette),
# lofted tapered spout + ear handle along bezier guides, lid + knob.
import math

import maya.cmds as cmds
import t20kit as K


ROOT = "GRP_t20_teapot"


def _bezier3(p0, p1, p2, p3, n):
    out = []
    for i in range(n + 1):
        t = i / float(n)
        u = 1.0 - t
        out.append(
            (
                u * u * u * p0[0]
                + 3 * u * u * t * p1[0]
                + 3 * u * t * t * p2[0]
                + t * t * t * p3[0],
                u * u * u * p0[1]
                + 3 * u * u * t * p1[1]
                + 3 * u * t * t * p2[1]
                + t * t * t * p3[1],
                u * u * u * p0[2]
                + 3 * u * u * t * p1[2]
                + 3 * u * t * t * p2[2]
                + t * t * t * p3[2],
            )
        )
    return out


def _tube_taper(name, p0, p1, p2, p3, r0, taper, parent, sg, seg=16):
    """Extrude a circle along a cubic-bezier guide; taper scales the
    exit radius. Orientation is handled by the extrude engine itself -
    no hand-rolled ring rotations to get wrong."""
    # profile normal must face the start tangent or the sweep ribbons
    tv = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    tl = math.sqrt(tv[0] ** 2 + tv[1] ** 2 + tv[2] ** 2) or 1.0
    prof = cmds.circle(
        r=r0, sections=seg, nr=(tv[0] / tl, tv[1] / tl, tv[2] / tl), name=name + "_prof"
    )[0]
    cmds.move(p0[0], p0[1], p0[2], prof)
    path = cmds.curve(d=3, p=[p0, p1, p2, p3], name=name + "_path")
    s = cmds.extrude(
        prof, path, fixedPath=True, scale=taper, extrudeType=2, name=name, constructionHistory=False
    )[0]
    cmds.delete(prof)
    cmds.delete(path)
    cmds.parent(s, parent)
    K.assign(s, sg)
    return s


def build():
    K.kill(
        [
            ROOT,
            ROOT + "*",
            "MAT_t20tp_*",
            "CAM_t20tp_*",
            "LGT_t20tp_*",
            "LOC_t20tp_*",
            "GRP_t20tp_*",
        ]
    )
    root = cmds.group(em=True, name=ROOT)
    g_tp = cmds.group(em=True, name="GRP_t20tp_pot", parent=root)
    g_env = cmds.group(em=True, name="GRP_t20tp_env", parent=root)

    porc = K.mat("MAT_t20tp_porc", (0.88, 0.85, 0.80), spec=0.75, ecc=0.06, refl=0.35)
    porc2 = K.mat("MAT_t20tp_porc2", (0.30, 0.36, 0.50), spec=0.75, ecc=0.06, refl=0.35)
    K.mat("MAT_t20tp_dark", (0.05, 0.05, 0.06), spec=0.2, ecc=0.4)
    wall_m = K.mat("MAT_t20tp_wall", (0.10, 0.105, 0.12), spec=0.12, ecc=0.5)

    H = 15.0
    R = 7.0

    # ---- body: classic Newell silhouette (r, y) pairs ----
    body = [
        (2.6, 0.0),
        (4.4, 0.02),
        (5.9, 0.30),
        (6.8, 0.95),
        (7.0, 1.8),
        (6.85, 2.6),
        (6.3, 3.5),
        (5.5, 4.4),
        (4.9, 5.0),
        (4.6, 5.5),
        (4.55, 5.9),
        (4.5, 6.2),
    ]
    body = [(r / 7.0 * R, y / 6.2 * H * 0.74) for r, y in body]
    K.revolve_y("GEO_tp_body", body, g_tp, porc)
    # inner rim where the lid sits
    K.ring("GEO_tp_rim", R * 0.64, R * 0.60, H * 0.70, H * 0.75, parent=g_tp, sg=porc, sx=48)

    # ---- lid: shallow dome + rim lip ----
    lid = [
        (R * 0.06, H * 0.74),
        (R * 0.30, H * 0.75),
        (R * 0.52, H * 0.76),
        (R * 0.62, H * 0.75),
        (R * 0.60, H * 0.815),
        (R * 0.45, H * 0.88),
        (R * 0.22, H * 0.915),
        (0.4, H * 0.93),
    ]
    K.revolve_y("GEO_tp_lid", lid, g_tp, porc2)
    # knob — little bud on top
    knob = [(0.02, 0), (0.5, 0.08), (0.72, 0.32), (0.55, 0.62), (0.25, 0.85), (0.02, 0.95)]
    knob = [(r * 1.5, H * 0.93 + y * 1.5) for r, y in knob]
    K.revolve_y("GEO_tp_knob", knob, g_tp, porc2)

    # ---- spout: bezier path out+up, tapered loft ----
    _tube_taper(
        "GEO_tp_spout",
        (R * 0.52, H * 0.30, 0),
        (R * 1.02, H * 0.16, 0),
        (R * 1.50, H * 0.40, 0),
        (R * 1.58, H * 0.64, 0),
        R * 0.40,
        0.45,
        g_tp,
        porc,
    )

    # ---- handle: ear loop, mirrored side ----
    _tube_taper(
        "GEO_tp_handle",
        (-R * 0.50, H * 0.74, 0),
        (-R * 1.45, H * 0.82, 0),
        (-R * 1.72, H * 0.34, 0),
        (-R * 0.70, H * 0.14, 0),
        R * 0.235,
        0.72,
        g_tp,
        porc,
    )

    # ---- env: checkered floor (iconic), cove, rim of backdrop ----
    # checkered floor as real geometry tiles — guaranteed VP2 result
    dark_t = K.mat("MAT_t20tp_dk", (0.14, 0.15, 0.18), spec=0.3, ecc=0.2)
    lite_t = K.mat("MAT_t20tp_lt", (0.78, 0.76, 0.70), spec=0.3, ecc=0.2)
    T = 22.0
    for ix in range(-9, 10):
        for iz in range(-9, 10):
            tile = cmds.polyCube(w=T, h=0.4, d=T, name=f"GEO_tp_t{ix}_{iz}")[0]
            cmds.move(ix * T, -0.2, iz * T, tile)
            cmds.parent(tile, g_env)
            K.assign(tile, dark_t if (ix + iz) % 2 == 0 else lite_t)
    wall = K.revolve_y(
        "GEO_tp_cove", [(110, -2), (150, -1), (162, 6), (168, 40), (170, 150)], g_env, wall_m
    )
    for sh in cmds.listRelatives(wall, shapes=True) or []:
        cmds.setAttr(sh + ".doubleSided", 1)

    # ---- lights ----
    lg = cmds.group(em=True, name="GRP_t20tp_lights", parent=root)
    K.spot(
        "LGT_t20tp_key",
        (-70, 110, 90),
        (0, 8, 0),
        (1.0, 0.86, 0.68),
        4.2,
        cone=42,
        pen=14,
        parent=lg,
    )
    K.spot(
        "LGT_t20tp_rim",
        (90, 70, -80),
        (0, 10, 0),
        (0.45, 0.62, 1.0),
        2.8,
        cone=50,
        pen=12,
        parent=lg,
    )
    f2 = cmds.directionalLight(intensity=0.4, name="LGT_t20tp_fill")
    cmds.setAttr(f2 + ".color", 0.62, 0.70, 0.92, type="double3")
    cmds.rotate(-25, 30, 0, cmds.listRelatives(f2, parent=True)[0])
    cmds.parent(cmds.listRelatives(f2, parent=True)[0], lg)
    amb = cmds.ambientLight(intensity=0.15, name="LGT_t20tp_amb")
    cmds.parent(cmds.listRelatives(amb, parent=True)[0], lg)

    # ---- cameras ----
    aim = K.loc("LOC_t20tp_aim", (2, 7, 0))
    ct, cs = K.cam("CAM_t20tp_hero", (46, 26, 62), aim, fl=58)
    cmds.setAttr(cs + ".depthOfField", 1)
    cmds.setAttr(cs + ".focusDistance", 76)
    cmds.setAttr(cs + ".fStop", 7.1)
    cmds.setAttr(cs + ".focusRegionScale", 0.5)
    K.cam("CAM_t20tp_side", (70, 12, 8), aim, fl=62)
    K.cam("CAM_t20tp_top", (8, 70, 40), aim, fl=50)
    for lc in cmds.ls("LOC_t20tp_*"):
        try:
            cmds.hide(lc)
        except Exception:
            pass

    cmds.select(clear=True)
    return {"ok": True, "objects": len(cmds.ls(dag=True) or [])}
