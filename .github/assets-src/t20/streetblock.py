# t20 street block — low-poly corner block: parametric buildings,
# awnings, street furniture, trees, parked micro-van. Faceted style
# is the deliberate look; density comes from variety, not prim count.
import random

import maya.cmds as cmds
import t20kit as K


ROOT = "GRP_t20_street"
rnd = random.Random(20260924)

PALETTE = [
    (0.82, 0.42, 0.30),  # terracotta
    (0.90, 0.62, 0.32),  # ochre
    (0.55, 0.68, 0.62),  # sage
    (0.72, 0.60, 0.50),  # taupe
    (0.52, 0.62, 0.72),  # slate blue
    (0.85, 0.75, 0.55),  # sand
    (0.62, 0.45, 0.52),  # dusty plum
]
ROOFS = [(0.45, 0.28, 0.24), (0.38, 0.40, 0.45), (0.55, 0.35, 0.28), (0.30, 0.32, 0.36)]


def _roof_gable(name, w, d, h, y, parent, sg):
    # wedge: cube with the top ridge verts pulled to centre. No
    # rotations - cmds.rotate is absolute-set and composes badly.
    ridge_x = w > d  # ridge runs along the LONG axis
    a = min(w, d)  # profile width  (short span)
    L = max(w, d)  # ridge length   (long span)
    cw = L if ridge_x else a
    cd = a if ridge_x else L
    s = cmds.polyCube(w=cw, h=h, d=cd, name=name)[0]
    cmds.move(0, y + h / 2.0, 0, s)
    for v in cmds.ls(s + ".vtx[*]", fl=True) or []:
        p = cmds.xform(v, q=True, ws=True, t=True)
        if p[1] > y + h * 0.5:
            t = [p[0], p[1], p[2]]
            if ridge_x:
                t[2] = 0.0  # top verts -> z=0 : ridge along x
            else:
                t[0] = 0.0  # top verts -> x=0 : ridge along z
            cmds.xform(v, ws=True, t=t)
    cmds.parent(s, parent)
    K.assign(s, sg)
    return s


def building(name, x, z, w, d, h, mat, roof, style, parent, awn_sg=None, side_face=None):
    g = cmds.group(em=True, name=name, parent=parent)
    body = cmds.polyCube(w=w, h=h, d=d, name=name + "_body")[0]
    cmds.move(0, h / 2.0, 0, body)
    cmds.parent(body, g)
    K.assign(body, mat)
    # roof
    rh = h * (0.18 if style == "gable" else 0.05)
    if style == "gable":
        _roof_gable(name + "_roof", w + 1.2, d + 1.2, max(3.0, rh), h, g, roof)
    else:
        rim = cmds.polyCube(w=w + 1.0, h=1.4, d=d + 1.0, name=name + "_parapet")[0]
        cmds.move(0, h + 0.7, 0, rim)
        cmds.parent(rim, g)
        K.assign(rim, roof)
    # window grid on +z facade (inset dark quads) + storefront at ground
    win = K.mat("MAT_t20" + name[3:] + "_win", (0.10, 0.12, 0.16), spec=0.6, ecc=0.15, refl=0.3)
    cols = max(2, int(w // 4.5))
    rows = max(1, int((h - 6) // 5))
    wy0 = 6.5
    for r in range(rows):
        for c in range(cols):
            wq = cmds.polyCube(w=2.2, h=2.6, d=0.3, name=f"{name}_w{r}_{c}")[0]
            wx = -w / 2 + (c + 0.5) * (w / cols)
            cmds.move(wx, wy0 + r * 5.0, d / 2 + 0.05, wq)
            cmds.parent(wq, g)
            K.assign(wq, win)
    # storefront band
    shop = cmds.polyCube(w=w * 0.8, h=4.2, d=0.4, name=name + "_shop")[0]
    cmds.move(0, 2.6, d / 2 + 0.1, shop)
    cmds.parent(shop, g)
    K.assign(shop, win)
    # awning — striped: slanted box + scallop edge
    awn_sg = awn_sg or roof
    awn = cmds.polyCube(w=w * 0.85, h=0.35, d=3.2, name=name + "_awn")[0]
    cmds.rotate(18, 0, 0, awn)
    cmds.move(0, 5.4, d / 2 + 1.4, awn)
    cmds.parent(awn, g)
    K.assign(awn, awn_sg)
    for k in range(int(w * 0.85 / 1.6)):
        sc = cmds.polyCylinder(r=0.8, h=0.35, sx=10, name=f"{name}_sc{k}")[0]
        cmds.rotate(90, 0, 0, sc)
        cmds.rotate(18, 0, 0, sc)
        cmds.move(-w * 0.42 + k * 1.6 + 0.8, 4.35, d / 2 + 2.8, sc)
        cmds.parent(sc, g)
        K.assign(sc, awn_sg)
    # optional second window face (+x or -x or -z) for corner buildings
    if side_face:
        sgn = {"+x": 1, "-x": -1}.get(side_face, 0)
        for r in range(rows):
            for c in range(max(2, int(d // 4.5))):
                wq = cmds.polyCube(w=0.3, h=2.6, d=2.2, name=f"{name}_sw{r}_{c}")[0]
                wz = -d / 2 + (c + 0.5) * (d / max(2, int(d // 4.5)))
                wx = sgn * (w / 2 + 0.05) if sgn else 0
                wz_ = wz if sgn else -d / 2 - 0.05
                cmds.move(wx if sgn else wz, wy0 + r * 5.0, wz_ if sgn else -d / 2 - 0.05, wq)
                if not sgn:
                    cmds.rotate(0, 90, 0, wq)
                cmds.parent(wq, g)
                K.assign(wq, win)
    # chimney / AC unit on tall buildings
    if h > 20 and rnd.random() < 0.8:
        ch = cmds.polyCube(w=2.4, h=4.0, d=2.4, name=name + "_chim")[0]
        cmds.move(w * 0.25, h + 2.0, -d * 0.2, ch)
        cmds.parent(ch, g)
        K.assign(ch, roof)
    cmds.move(x, 0, z, g)
    return g


def tree(name, x, z, parent, mat_t, mat_f):
    g = cmds.group(em=True, name=name, parent=parent)
    K.cyl(name + "_trunk", 0.9, 6.0, (0, 3, 0), sx=7, parent=g, sg=mat_t)
    for i, (ox, oy, oz, r) in enumerate(
        [(0, 7.5, 0, 3.6), (1.8, 6.2, 0.8, 2.4), (-1.6, 6.6, -0.6, 2.2)]
    ):
        s = cmds.polySphere(r=r, sx=8, sy=6, name=f"{name}_f{i}")[0]
        cmds.move(ox, oy, oz, s)
        cmds.parent(s, g)
        K.assign(s, mat_f)
    cmds.move(x, 0, z, g)
    return g


def lamp(name, x, z, parent, mat):
    g = cmds.group(em=True, name=name, parent=parent)
    K.cyl(name + "_p", 0.35, 9.0, (0, 4.5, 0), sx=8, parent=g, sg=mat)
    arm = K.cyl(name + "_arm", 0.28, 3.4, (0, 8.9, -1.4), sx=8, parent=g, sg=mat)
    cmds.rotate(75, 0, 0, arm)
    h = cmds.polySphere(r=0.9, sx=10, sy=8, name=name + "_h")[0]
    cmds.move(0, 8.6, -2.9, h)
    cmds.parent(h, g)
    K.assign(h, K.mat("MAT_t20" + name[3:] + "_hm", (1.0, 0.9, 0.6), incand=0.9))
    cmds.move(x, 0, z, g)
    return g


def bench(name, x, z, ry, parent, wood, iron):
    g = cmds.group(em=True, name=name, parent=parent)
    for i in range(3):
        sl = cmds.polyCube(w=8.0, h=0.35, d=0.9, name=f"{name}_s{i}")[0]
        cmds.move(0, 2.2, -1.0 + i * 1.0, sl)
        cmds.parent(sl, g)
        K.assign(sl, wood)
    for i in range(2):
        sl = cmds.polyCube(w=8.0, h=0.35, d=0.9, name=f"{name}_b{i}")[0]
        cmds.move(0, 3.4 + i * 1.0, -1.55, sl)
        cmds.parent(sl, g)
        K.assign(sl, wood)
    for sx in (-3.4, 3.4):
        leg = cmds.polyCube(w=0.5, h=2.4, d=2.6, name=f"{name}_l{sx}")[0]
        cmds.move(sx, 1.2, 0, leg)
        cmds.parent(leg, g)
        K.assign(leg, iron)
    cmds.rotate(0, ry, 0, g)
    cmds.move(x, 0, z, g)
    return g


def van(name, x, z, ry, parent, body_m, dark):
    g = cmds.group(em=True, name=name, parent=parent)
    b = cmds.polyCube(w=11.5, h=4.6, d=5.2, name=name + "_b")[0]
    cmds.move(0, 3.4, 0, b)
    cmds.parent(b, g)
    K.assign(b, body_m)
    cab = cmds.polyCube(w=4.6, h=3.6, d=5.0, name=name + "_c")[0]
    cmds.move(4.6, 2.6, 0, cab)
    cmds.parent(cab, g)
    K.assign(cab, body_m)
    ws = cmds.polyCube(w=2.8, h=1.6, d=4.6, name=name + "_ws")[0]
    cmds.move(4.9, 3.4, 0, ws)
    cmds.parent(ws, g)
    K.assign(ws, dark)
    for i, (wx, wz) in enumerate([(3.8, -2.6), (3.8, 2.6), (-3.4, -2.6), (-3.4, 2.6)]):
        wh = cmds.polyCylinder(r=1.5, h=0.9, sx=12, name=f"{name}_wh{i}")[0]
        cmds.rotate(90, 0, 0, wh)
        cmds.move(wx, 1.5, wz, wh)
        cmds.parent(wh, g)
        K.assign(wh, dark)
    cmds.rotate(0, ry, 0, g)
    cmds.move(x, 0, z, g)
    return g


def build():
    K.kill(
        [
            ROOT,
            ROOT + "*",
            "MAT_t20st_*",
            "CAM_t20st_*",
            "LGT_t20st_*",
            "LOC_t20st_*",
            "GRP_t20st_*",
            "GRP_t20_workbench*",
            "GRP_t20wb_*",
            "MAT_t20wb_*",
            "CAM_t20wb_*",
            "LGT_t20wb_*",
            "LOC_t20wb_*",
            "GEO_wb_*",
            "GRP_asset_*",
        ]
    )
    root = cmds.group(em=True, name=ROOT)
    g_env = cmds.group(em=True, name="GRP_t20st_env", parent=root)
    g_bld = cmds.group(em=True, name="GRP_t20st_build", parent=root)
    g_prop = cmds.group(em=True, name="GRP_t20st_props", parent=root)

    road = K.mat("MAT_t20st_road", (0.14, 0.14, 0.15), spec=0.1, ecc=0.5)
    walk = K.mat("MAT_t20st_walk", (0.5, 0.48, 0.44), spec=0.12, ecc=0.4)
    stripe = K.mat("MAT_t20st_stripe", (0.85, 0.83, 0.75), spec=0.05, ecc=0.5)
    trunk_m = K.mat("MAT_t20st_trunk", (0.30, 0.18, 0.10), spec=0.1, ecc=0.5)
    leaf_m = K.mat("MAT_t20st_leaf", (0.28, 0.48, 0.22), spec=0.15, ecc=0.4)
    leaf_m2 = K.mat("MAT_t20st_leaf2", (0.40, 0.55, 0.20), spec=0.15, ecc=0.4)
    iron = K.mat("MAT_t20st_iron", (0.16, 0.17, 0.18), spec=0.6, ecc=0.2)
    wood_b = K.mat("MAT_t20st_bench", (0.55, 0.35, 0.18), spec=0.3, ecc=0.3)
    grass = K.mat("MAT_t20st_grass", (0.32, 0.45, 0.25), spec=0.1, ecc=0.5)
    van_m = K.mat("MAT_t20st_van", (0.75, 0.25, 0.15), spec=0.5, ecc=0.15, refl=0.25)

    # ground: grass block + roads (L-shaped corner) + sidewalks
    gnd = cmds.polyCube(w=190, h=2, d=190, name="GEO_st_ground")[0]
    cmds.move(0, -1, 0, gnd)
    cmds.parent(gnd, g_env)
    K.assign(gnd, grass)
    for name, (cx, cz, w, d) in {"ew": (0, 0, 190, 22), "ns": (-58, 0, 22, 190)}.items():
        r = cmds.polyCube(w=w, h=0.4, d=d, name=f"GEO_st_road_{name}")[0]
        cmds.move(cx, 0.2, cz, r)
        cmds.parent(r, g_env)
        K.assign(r, road)
    for name, (cx, cz, w, d) in {
        "a": (0, -15, 190, 8),
        "b": (0, 15, 190, 8),
        "c": (-42, 0, 8, 190),
        "d": (-74, 0, 8, 190),
    }.items():
        s = cmds.polyCube(w=w, h=0.7, d=d, name=f"GEO_st_walk_{name}")[0]
        cmds.move(cx, 0.35, cz, s)
        cmds.parent(s, g_env)
        K.assign(s, walk)
    # crosswalk stripes across the EW road near the corner
    for i in range(7):
        cw = cmds.polyCube(w=2.4, h=0.12, d=9, name=f"GEO_st_cross_{i}")[0]
        cmds.move(-38 - i * 4.2, 0.45, 0, cw)
        cmds.parent(cw, g_env)
        K.assign(cw, stripe)
    # center line dashes
    for i in range(8):
        cl = cmds.polyCube(w=5, h=0.1, d=0.7, name=f"GEO_st_dash_{i}")[0]
        cmds.move(-30 + i * 24, 0.45, 0, cl)
        cmds.parent(cl, g_env)
        K.assign(cl, stripe)

    # buildings — NE block (along north sidewalk) + NW sliver + south row
    specs = [
        (-12, -34, 26, 20, 22, 0, "gable"),
        (16, -36, 24, 18, 30, 1, "flat"),
        (44, -34, 22, 20, 18, 2, "gable"),
        (72, -36, 26, 18, 26, 3, "flat"),
        (-88, -34, 22, 20, 24, 4, "gable"),
        (-88, 30, 24, 20, 20, 5, "flat"),
        (-88, 60, 20, 18, 28, 6, "gable"),
        (-16, 34, 30, 22, 16, 2, "flat"),
        (16, 36, 26, 20, 24, 0, "gable"),
        (50, 34, 28, 22, 20, 3, "flat"),
        (82, 34, 20, 18, 26, 5, "gable"),
    ]
    AWNS = [
        (0.55, 0.20, 0.16),
        (0.20, 0.38, 0.30),
        (0.55, 0.42, 0.18),
        (0.25, 0.32, 0.45),
        (0.50, 0.24, 0.30),
    ]
    for i, (bx, bz, w, d, h, ci, style) in enumerate(specs):
        fmat = K.mat(f"MAT_t20st_b{i}", PALETTE[ci % len(PALETTE)], spec=0.3, ecc=0.35)
        rmat = K.mat(f"MAT_t20st_br{i}", ROOFS[i % len(ROOFS)], spec=0.2, ecc=0.4)
        amat = K.mat(f"MAT_t20st_ba{i}", AWNS[i % len(AWNS)], spec=0.25, ecc=0.4)
        side = "+x" if bx < -70 else ("-x" if bx > 70 else None)
        building(
            f"GEO_st_bld{i}", bx, bz, w, d, h, fmat, rmat, style, g_bld, awn_sg=amat, side_face=side
        )

    # trees along sidewalks
    for i, (tx, tz, m) in enumerate(
        [
            (-30, -17, 0),
            (-2, -17, 1),
            (30, -17, 0),
            (62, -17, 1),
            (30, 17, 0),
            (62, 17, 1),
            (-46, 30, 1),
            (-46, 60, 0),
            (-46, -30, 1),
            (-46, -60, 0),
        ]
    ):
        tree(f"GEO_st_tree{i}", tx, tz, g_prop, trunk_m, leaf_m if m == 0 else leaf_m2)
    # lamps at corners + mid-block
    for i, (lx, lz) in enumerate(
        [(-24, -19), (24, -19), (-24, 19), (24, 19), (66, -19), (66, 19), (-50, 24), (-50, -24)]
    ):
        lamp(f"GEO_st_lamp{i}", lx, lz, g_prop, iron)
    # benches + hydrant + planters near corner plaza
    bench("GEO_st_bench0", -24, 26, -90, g_prop, wood_b, iron)
    bench("GEO_st_bench1", 34, -17, 0, g_prop, wood_b, iron)
    hyd = cmds.group(em=True, name="GRP_st_hydrant", parent=g_prop)
    K.cyl(
        "GEO_st_hyd_b",
        0.9,
        2.6,
        (0, 1.3, 0),
        sx=10,
        parent=hyd,
        sg=K.mat("MAT_t20st_hyd", (0.8, 0.15, 0.1), spec=0.5, ecc=0.2),
    )
    K.cyl("GEO_st_hyd_t", 0.6, 0.7, (0, 2.9, 0), sx=10, parent=hyd, sg=iron)
    cmds.move(-20, 0, 17, hyd)
    van("GEO_st_van0", 10, 4.5, -4, g_prop, van_m, iron)
    van(
        "GEO_st_van1",
        -90,
        0,
        90,
        g_prop,
        K.mat("MAT_t20st_van2", (0.30, 0.45, 0.55), spec=0.5, ecc=0.15, refl=0.25),
        iron,
    )

    # lights — low warm sun + cool sky fill
    lg = cmds.group(em=True, name="GRP_t20st_lights", parent=root)
    sun = cmds.directionalLight(intensity=2.6, name="LGT_t20st_sun")
    cmds.setAttr(sun + ".color", 1.0, 0.85, 0.62, type="double3")
    st = cmds.listRelatives(sun, parent=True)[0]
    cmds.rotate(-48, -55, 0, st)
    cmds.parent(st, lg)
    fill = cmds.directionalLight(intensity=0.7, name="LGT_t20st_fill")
    cmds.setAttr(fill + ".color", 0.55, 0.68, 0.95, type="double3")
    cmds.rotate(-25, 120, 0, cmds.listRelatives(fill, parent=True)[0])
    cmds.parent(cmds.listRelatives(fill, parent=True)[0], lg)
    amb = cmds.ambientLight(intensity=0.22, name="LGT_t20st_amb")
    cmds.parent(cmds.listRelatives(amb, parent=True)[0], lg)

    # cameras — 3/4 aerial hero + street level + top
    aim = K.loc("LOC_t20st_aim", (0, 8, -8))
    ct, cs = K.cam("CAM_t20st_hero", (150, 105, 150), aim, fl=52)
    cmds.setAttr(cs + ".depthOfField", 1)
    cmds.setAttr(cs + ".focusDistance", 210)
    cmds.setAttr(cs + ".fStop", 8.0)
    cmds.setAttr(cs + ".focusRegionScale", 0.55)
    K.cam("CAM_t20st_eye", (-30, 12, 60), K.loc("LOC_t20st_aim2", (10, 12, -20)), fl=38)
    K.cam("CAM_t20st_top", (40, 190, 40), aim, fl=58)
    for lc in cmds.ls("LOC_t20st_*"):
        try:
            cmds.hide(lc)
        except Exception:
            pass

    cmds.select(clear=True)
    return {"ok": True, "objects": len(cmds.ls(dag=True) or [])}
