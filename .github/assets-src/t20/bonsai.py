# t20 bonsai — L-system recursive branching + low-poly foliage pads
import math
import random

import maya.cmds as cmds
import t20kit as K


ROOT = "GRP_t20_bonsai"
SEED = 20260924


# ----------------------------------------------------------------
# L-system: axiom 'A'; A -> F[&A][+A][-A]F[^A] ; F -> F (sometimes FF)
# turtle: heading/left/up frame, radius & length decay per depth
# ----------------------------------------------------------------
def _norm(v):
    l = math.sqrt(sum(c * c for c in v)) or 1.0
    return (v[0] / l, v[1] / l, v[2] / l)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _rot(v, axis, deg):
    """Rodrigues rotation of v about unit axis by deg."""
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    ax = _norm(axis)
    d = ax[0] * v[0] + ax[1] * v[1] + ax[2] * v[2]
    cr = _cross(ax, v)
    return (
        v[0] * c + cr[0] * s + ax[0] * d * (1 - c),
        v[1] * c + cr[1] * s + ax[1] * d * (1 - c),
        v[2] * c + cr[2] * s + ax[2] * d * (1 - c),
    )


ANG = 26.0


def expand(depth):
    s = "A"
    rnd = random.Random(SEED)
    for _ in range(depth):
        out = []
        for ch in s:
            if ch == "A":
                # asymmetric branching, slight bias -> windswept bonsai
                r = rnd.random()
                if r < 0.72:
                    out.append("F[&A][+A]F[-A]")
                elif r < 0.9:
                    out.append("F[+A][^A]F[&A]")
                else:
                    out.append("F[&A][+A][-A][^A]")
            elif ch == "F":
                out.append("FF" if rnd.random() < 0.35 else "F")
            else:
                out.append(ch)
        s = "".join(out)
    return s


def grow(parent, bark_sg, leaf_sgs, base_pos, base_len=7.0, base_rad=1.5, max_depth=5):
    seq = expand(max_depth)
    rnd = random.Random(SEED + 1)
    state = {
        "pos": list(base_pos),
        "h": (0, 1, 0),
        "l": (1, 0, 0),
        "u": (0, 0, 1),
        "rad": base_rad,
        "ln": base_len,
        "d": 0,
    }
    stack = []
    segs = {"n": 0}
    terminals = []

    def seg(st, depth):
        h = _norm(st["h"])
        p0 = st["pos"]
        p1 = [p0[0] + h[0] * st["ln"], p0[1] + h[1] * st["ln"], p0[2] + h[2] * st["ln"]]
        r = max(0.10, st["rad"])
        # tapered look: cone apex forward
        c = cmds.polyCone(r=r, h=st["ln"], sx=5, name=f"GEO_bn_seg_{segs['n']}")[0]
        segs["n"] += 1
        # cone apex at +h/2: move so base at p0
        mid = [(p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2]
        ang = cmds.angleBetween(v1=(0, 1, 0), v2=h, euler=True)
        cmds.rotate(180, 0, 0, c)  # apex -> -Y then aim flips back
        cmds.rotate(ang[0], ang[1], ang[2], c)
        cmds.move(mid[0], mid[1], mid[2], c)
        cmds.parent(c, parent)
        K.assign(c, bark_sg)
        st["pos"] = p1

    cur = dict(state)
    for ch in seq:
        if ch == "F":
            seg(cur, cur["d"])
        elif ch == "+":
            cur["h"] = _rot(cur["h"], cur["u"], ANG)
            cur["l"] = _rot(cur["l"], cur["u"], ANG)
        elif ch == "-":
            cur["h"] = _rot(cur["h"], cur["u"], -ANG)
            cur["l"] = _rot(cur["l"], cur["u"], -ANG)
        elif ch == "&":
            cur["h"] = _rot(cur["h"], cur["l"], ANG)
            cur["u"] = _rot(cur["u"], cur["l"], ANG)
        elif ch == "^":
            cur["h"] = _rot(cur["h"], cur["l"], -ANG)
            cur["u"] = _rot(cur["u"], cur["l"], -ANG)
        elif ch == "[":
            stack.append(
                {
                    k: (v[:] if isinstance(v, list) else tuple(v) if isinstance(v, tuple) else v)
                    for k, v in cur.items()
                }
            )
            cur["d"] += 1
            cur["rad"] *= 0.68
            cur["ln"] *= 0.72
        elif ch == "]":
            terminals.append(tuple(cur["pos"]))
            cur = stack.pop()
    terminals.append(tuple(cur["pos"]))

    # foliage pads at terminals — clusters of squashed low-poly blobs
    li = 0
    for tp in terminals:
        n_pad = 3 + (li % 3)
        for j in range(n_pad):
            off = (rnd.uniform(-3.2, 3.2), rnd.uniform(-0.8, 2.2), rnd.uniform(-3.2, 3.2))
            r = rnd.uniform(2.0, 3.4)
            lf = cmds.polySphere(r=r, sx=5, sy=4, name=f"GEO_bn_leaf_{li}")[0]
            li += 1
            cmds.scale(1.35, 0.55, 1.1, lf)
            cmds.move(tp[0] + off[0], tp[1] + off[1] + 1.2, tp[2] + off[2], lf)
            cmds.parent(lf, parent)
            K.assign(lf, leaf_sgs[li % len(leaf_sgs)])
    return segs["n"], li


def build():
    K.kill(
        [
            ROOT,
            ROOT + "*",
            "MAT_t20bn_*",
            "CAM_t20bn_*",
            "LGT_t20bn_*",
            "LOC_t20bn_*",
            "GRP_t20bn_*",
        ]
    )
    root = cmds.group(em=True, name=ROOT)

    bark = K.mat("MAT_t20bn_bark", (0.30, 0.20, 0.12), spec=0.15, ecc=0.5)
    leaf1 = K.mat("MAT_t20bn_leaf1", (0.20, 0.42, 0.16), spec=0.25, ecc=0.4)
    leaf2 = K.mat("MAT_t20bn_leaf2", (0.30, 0.52, 0.20), spec=0.3, ecc=0.35)
    leaf3 = K.mat("MAT_t20bn_leaf3", (0.16, 0.34, 0.14), spec=0.2, ecc=0.45)
    pot_m = K.mat("MAT_t20bn_pot", (0.28, 0.38, 0.48), spec=0.75, ecc=0.12, refl=0.35)
    soil = K.mat("MAT_t20bn_soil", (0.14, 0.10, 0.07), spec=0.05, ecc=0.6)
    rock_m = K.mat("MAT_t20bn_rock", (0.38, 0.38, 0.36), spec=0.3, ecc=0.4)
    slab_m = K.mat("MAT_t20bn_slab", (0.08, 0.085, 0.10), spec=0.4, ecc=0.2, refl=0.3)
    moss = K.mat("MAT_t20bn_moss", (0.16, 0.30, 0.10), spec=0.1, ecc=0.6)

    g_pot = cmds.group(em=True, name="GRP_t20bn_pot", parent=root)
    g_tree = cmds.group(em=True, name="GRP_t20bn_tree", parent=root)
    g_env = cmds.group(em=True, name="GRP_t20bn_env", parent=root)

    # slab stage
    slab = cmds.polyCube(w=150, h=4, d=110, name="GEO_bn_slab")[0]
    cmds.move(0, -2, 0, slab)
    cmds.parent(slab, g_env)
    K.assign(slab, slab_m)

    # shallow pot — glazed lathe profile + rim + feet
    pot = K.revolve_y(
        "GEO_bn_pot",
        [
            (2, 0),
            (24, 0),
            (34, 2),
            (38, 6),
            (38, 12),
            (36, 14),
            (34, 14),
            (34, 13),
            (33, 12),
            (30, 10),
            (10, 9),
            (2, 9),
        ],
        sections=48,
    )
    cmds.parent(pot, g_pot)
    K.assign(pot, pot_m)
    rim = K.revolve_y(
        "GEO_bn_potrim",
        [(33, 12.4), (38, 12.4), (39.4, 13.6), (38.4, 15.2), (34, 15.4), (33, 14.4)],
        sections=48,
    )
    cmds.parent(rim, g_pot)
    K.assign(rim, pot_m)
    for i in range(3):
        a = math.radians(i * 120 + 30)
        K.cyl(
            f"GEO_bn_foot_{i}",
            3.2,
            3.0,
            (24 * math.cos(a), -1.4, 24 * math.sin(a)),
            sx=10,
            parent=g_pot,
            sg=pot_m,
        )
    # soil + moss mounds
    K.cyl("GEO_bn_soil", 32.0, 3.0, (0, 13.0, 0), sx=40, parent=g_pot, sg=soil)
    for i in range(7):
        a = i * 2.4
        r = 10 + 18 * ((i * 37) % 10) / 10.0
        mo = cmds.polySphere(r=3.4 + (i % 3), sx=5, sy=4, name=f"GEO_bn_moss_{i}")[0]
        cmds.scale(1.5, 0.45, 1.3, mo)
        cmds.move(r * math.cos(a), 14.6, r * math.sin(a), mo)
        cmds.parent(mo, g_pot)
        K.assign(mo, moss)
    # rocks
    rndr = random.Random(SEED + 7)
    for i, (rx, rz, s_) in enumerate([(-16, 8, 4.5), (18, -10, 3.2), (-10, -14, 2.4)]):
        rk = cmds.polySphere(r=s_, sx=6, sy=5, name=f"GEO_bn_rock_{i}")[0]
        cmds.scale(1.3, 0.75, 1.0, rk)
        cmds.rotate(0, rndr.uniform(0, 180), 0, rk)
        cmds.move(rx, 14.8, rz, rk)
        cmds.parent(rk, g_pot)
        K.assign(rk, rock_m)

    # tree — trunk base at soil level, slightly off-center + windswept lean
    nseg, nleaf = grow(
        g_tree,
        bark,
        [leaf1, leaf2, leaf3],
        base_pos=(-6.0, 14.5, 2.0),
        base_len=5.5,
        base_rad=1.4,
        max_depth=5,
    )

    # backdrop cove — dark wall behind
    cove_pts = [(95, -2), (150, -1), (188, 8), (198, 55), (200, 150)]
    wall = K.revolve_y("GEO_bn_cove", cove_pts, sections=48)
    cmds.parent(wall, g_env)
    for sh in cmds.listRelatives(wall, shapes=True) or []:
        cmds.setAttr(sh + ".doubleSided", 1)
    K.assign(wall, K.mat("MAT_t20bn_wall", (0.05, 0.055, 0.07), spec=0.1, ecc=0.4))

    # lights
    lg = cmds.group(em=True, name="GRP_t20bn_lights", parent=root)
    K.spot(
        "LGT_t20bn_key",
        (90, 170, 110),
        (-4, 45, 0),
        (1.0, 0.86, 0.66),
        4.0,
        cone=44,
        pen=14,
        parent=lg,
    )
    K.spot(
        "LGT_t20bn_rim",
        (-110, 130, -90),
        (-10, 50, 0),
        (0.45, 0.62, 1.0),
        2.6,
        cone=44,
        pen=10,
        parent=lg,
    )
    wl = cmds.spotLight(intensity=0.9, coneAngle=70, name="LGT_t20bn_wall")
    cmds.setAttr(wl + ".penumbraAngle", 18.0)
    wltr = cmds.listRelatives(wl, parent=True)[0]
    cmds.move(0, 90, 110, wltr)
    cmds.setAttr(wl + ".color", 0.35, 0.42, 0.55, type="double3")
    cmds.rotate(65, 0, 0, wltr)
    cmds.parent(wltr, lg)
    f2 = cmds.directionalLight(intensity=0.4, name="LGT_t20bn_fill")
    cmds.setAttr(f2 + ".color", 0.65, 0.75, 1.0, type="double3")
    cmds.rotate(-25, 45, 0, cmds.listRelatives(f2, parent=True)[0])
    cmds.parent(cmds.listRelatives(f2, parent=True)[0], lg)
    amb = cmds.ambientLight(intensity=0.22, name="LGT_t20bn_amb")
    cmds.parent(cmds.listRelatives(amb, parent=True)[0], lg)

    # cameras
    aim = K.loc("LOC_t20bn_aim", (-2, 46, 0))
    ct, cs = K.cam("CAM_t20bn_hero", (100, 66, 142), aim, fl=55)
    cmds.setAttr(cs + ".depthOfField", 1)
    cmds.setAttr(cs + ".focusDistance", 165)
    cmds.setAttr(cs + ".fStop", 6.3)
    cmds.setAttr(cs + ".focusRegionScale", 0.5)
    K.cam("CAM_t20bn_alt", (-110, 60, 110), aim, fl=52)

    cmds.select(clear=True)
    return {"ok": True, "segments": nseg, "leaves": nleaf, "objects": len(cmds.ls(dag=True) or [])}
