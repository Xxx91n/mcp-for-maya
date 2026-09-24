# t20 audit bench — metrology still life built to be measured:
# granite plate, gauge-block towers, dial indicator, height gauge,
# caliper, spaced artifacts with dimension arrows + 3D labels.
import math

import maya.cmds as cmds
import t20kit as K


ROOT = "GRP_t20_audit"


SEG7 = {
    "0": "abcefg",
    "1": "ce",
    "2": "acdeg",
    "3": "acdeg",
    "4": "bcde",
    "5": "abdfg",
    "6": "abdefg",
    "7": "ace",
    "8": "abcdefg",
    "9": "abcdef",
    ".": "p",
    "-": "d",
}


def _digit7(name, ch, x, y, z, h, parent, sg):
    """One seven-segment glyph; h = digit height (boxes, no fonts)."""
    w = h * 0.55
    th = h * 0.13
    seg = SEG7.get(ch, "")
    g = cmds.group(em=True, name=name, parent=parent)

    def box(n, bx, by, bw, bh):
        o = cmds.polyCube(w=bw, h=bh, d=th, name=name + "_" + n)[0]
        cmds.move(bx, by, 0, o)
        cmds.parent(o, g)
        K.assign(o, sg)

    if "a" in seg:
        box("a", 0, h, w - th, th)
    if "b" in seg:
        box("b", -w / 2 + th / 2, h * 0.75, th, h * 0.5 - th)
    if "c" in seg:
        box("c", w / 2 - th / 2, h * 0.75, th, h * 0.5 - th)
    if "d" in seg:
        box("d", 0, h * 0.5, w - th, th)
    if "e" in seg:
        box("e", w / 2 - th / 2, h * 0.25, th, h * 0.5 - th)
    if "f" in seg:
        box("f", -w / 2 + th / 2, h * 0.25, th, h * 0.5 - th)
    if "g" in seg:
        box("g", 0, 0, w - th, th)
    if "p" in seg:
        box("p", 0, th * 0.3, th, th)
    cmds.move(x, y, z, g)
    return g


def _text(name, s, pos, parent, sg, size=3.2):
    g = cmds.group(em=True, name=name, parent=parent)
    x = 0.0
    for i, ch in enumerate(s):
        _digit7(name + f"_c{i}", ch, x, 0, 0, size, g, sg)
        x += size * (0.30 if ch == "." else 0.70)
    # centre the label
    cmds.move(-x / 2.0 + size * 0.3, 0, 0, g, relative=True)
    cmds.move(pos[0], pos[1], pos[2], g)
    return g


def _dim_arrow(name, a, b, parent, sg, head=0.9):
    """Dimension line a->b with arrowheads + tick marks."""
    K.tube(name + "_line", [a, b], radius=0.14, parent=parent, sg=sg)
    d = [b[i] - a[i] for i in range(3)]
    L = math.sqrt(sum(v * v for v in d)) or 1
    u = [v / L for v in d]
    for i, (pt, sgn) in enumerate([(a, 1), (b, -1)]):
        cone = cmds.polyCone(r=head * 0.45, h=head * 1.4, sx=12, name=f"{name}_h{i}")[0]
        # aim cone axis (+Y default) along u*sgn
        if sgn < 0:
            cmds.rotate(180, 0, 0, cone)
        # axis-align: rotate +Y to u
        ang = math.degrees(math.acos(max(-1, min(1, u[1] * sgn))))
        ax = (u[2] * sgn, 0, -u[0] * sgn)
        if abs(ax[0]) + abs(ax[2]) > 1e-6:
            cmds.rotate(ang, 0, 0, cone)
            cmds.rotate(math.degrees(math.atan2(ax[0], ax[2])), 0, 0, cone, relative=True)
        cmds.move(pt[0] + u[0] * sgn * -0.0, pt[1], pt[2], cone)
        cmds.move(pt[0], pt[1], pt[2], cone)
        cmds.parent(cone, parent)
        K.assign(cone, sg)
    # end ticks
    for i, pt in enumerate([a, b]):
        t = cmds.polyCylinder(r=0.22, h=head * 2.2, sx=8, name=f"{name}_t{i}")[0]
        cmds.move(pt[0], pt[1], pt[2], t)
        cmds.parent(t, parent)
        K.assign(t, sg)


def build():
    K.kill(
        [
            ROOT,
            ROOT + "*",
            "MAT_t20au_*",
            "CAM_t20au_*",
            "LGT_t20au_*",
            "LOC_t20au_*",
            "GRP_t20au_*",
            # stale textCurves residue from the pre-seven-seg build
            "Char_*",
            "curve*",
        ]
    )
    root = cmds.group(em=True, name=ROOT)
    g_env = cmds.group(em=True, name="GRP_t20au_env", parent=root)
    g_obj = cmds.group(em=True, name="GRP_t20au_bench", parent=root)

    granite = K.mat("MAT_t20au_granite", (0.16, 0.17, 0.20), spec=0.5, ecc=0.15, refl=0.25)
    steel = K.mat("MAT_t20au_steel", (0.62, 0.65, 0.70), spec=0.9, ecc=0.07, refl=0.5)
    steel_d = K.mat("MAT_t20au_steeld", (0.30, 0.32, 0.36), spec=0.7, ecc=0.1, refl=0.4)
    brass = K.mat("MAT_t20au_brass", (0.55, 0.38, 0.14), spec=0.85, ecc=0.1, refl=0.4)
    dim_m = K.mat("MAT_t20au_dim", (0.85, 0.25, 0.15), spec=0.4, ecc=0.2)
    mark_m = K.mat("MAT_t20au_mark", (0.9, 0.85, 0.55), spec=0.3, ecc=0.3)
    wall_m = K.mat("MAT_t20au_wall", (0.10, 0.11, 0.13), spec=0.12, ecc=0.5)
    blue_m = K.mat("MAT_t20au_blue", (0.10, 0.25, 0.45), spec=0.6, ecc=0.15)

    # ---- granite plate on cabinet base ----
    cab = cmds.polyCube(w=90, h=30, d=56, name="GEO_au_cab")[0]
    cmds.move(0, 15, 0, cab)
    cmds.parent(cab, g_env)
    K.assign(cab, K.mat("MAT_t20au_cab", (0.42, 0.20, 0.16), spec=0.3, ecc=0.35))
    plate = cmds.polyCube(w=96, h=8, d=62, name="GEO_au_plate")[0]
    cmds.move(0, 34, 0, plate)
    cmds.parent(plate, g_env)
    K.assign(plate, granite)
    # plate edge line
    K.cyl("GEO_au_edge", 0.3, 96, (0, 38.1, -30), sx=8, parent=g_env, sg=steel_d)
    PY = 38.0  # plate top

    # ---- gauge-block towers (Jo blocks) ----
    for i, (bx, heights) in enumerate([(-34, [8, 5, 3]), (-18, [10, 4])]):
        yy = PY
        for j, hh in enumerate(heights):
            blk = cmds.polyCube(w=9, h=hh, d=3.4, name=f"GEO_au_jo{i}_{j}")[0]
            cmds.move(bx + j * 0.8, yy + hh / 2.0, -16, blk)
            cmds.parent(blk, g_obj)
            K.assign(blk, steel)
            yy += hh

    # ---- dial indicator on magnetic stand ----
    dg = cmds.group(em=True, name="GRP_au_dial", parent=g_obj)
    K.cyl("GEO_au_db", 4.5, 1.2, (0, 0.6, 0), sx=24, parent=dg, sg=steel_d)
    K.cyl("GEO_au_dp", 0.5, 26, (0, 13, 0), sx=10, parent=dg, sg=steel)
    arm = K.cyl("GEO_au_da", 0.45, 15, (6.5, 25.5, 0), sx=10, parent=dg, sg=steel)
    cmds.rotate(0, 0, -78, arm)
    face = cmds.polyCylinder(r=4.6, h=1.6, sx=32, name="GEO_au_df")[0]
    cmds.rotate(90, 0, 0, face)
    cmds.move(13.5, 22.5, 0, face)
    cmds.parent(face, dg)
    K.assign(face, brass)
    K.cyl("GEO_au_dface", 4.1, 0.5, (13.5, 22.5, -0.7), sx=32, parent=dg, sg=mark_m)
    nd = K.cyl("GEO_au_dnd", 0.16, 3.4, (13.5, 22.5, -1.2), sx=8, parent=dg, sg=dim_m)
    cmds.rotate(90, 0, 0, nd)
    cmds.rotate(0, 0, -35, nd)
    K.cyl("GEO_au_dstem", 0.3, 9, (13.5, 17.0, 0), sx=8, parent=dg, sg=steel)
    cmds.move(-38, PY, 6, dg)

    # ---- height gauge ----
    hg = cmds.group(em=True, name="GRP_au_hgauge", parent=g_obj)
    K.cyl("GEO_au_hb", 7.5, 2.0, (0, 1, 0), sx=24, parent=hg, sg=steel_d)
    K.cyl("GEO_au_hc", 0.8, 30, (0, 17, 0), sx=12, parent=hg, sg=steel)
    jw = cmds.polyCube(w=5, h=4, d=5, name="GEO_au_hj")[0]
    cmds.move(0, 16, 2.2, jw)
    cmds.parent(jw, hg)
    K.assign(jw, brass)
    scr = cmds.polyCube(w=0.2, h=6, d=3.2, name="GEO_au_hs")[0]
    cmds.move(0, 12.5, 2.4, scr)
    cmds.parent(scr, hg)
    K.assign(scr, steel)
    cmds.move(-2, PY, -20, hg)

    # ---- caliper silhouette ----
    cp = cmds.group(em=True, name="GRP_au_caliper", parent=g_obj)
    beam = cmds.polyCube(w=26, h=0.7, d=3.0, name="GEO_au_cb")[0]
    cmds.move(0, 0.35, 0, beam)
    cmds.parent(beam, cp)
    K.assign(beam, steel)
    for nm, ox in [("fj", -12), ("mj", -4)]:
        j1 = cmds.polyCube(w=1.4, h=5.5, d=3.0, name=f"GEO_au_c{nm}")[0]
        cmds.move(ox, 2.6, 0, j1)
        cmds.parent(j1, cp)
        K.assign(j1, steel)
    sc = cmds.polyCube(w=4.5, h=3.2, d=3.2, name="GEO_au_cs")[0]
    cmds.move(-4, 2.0, 0, sc)
    cmds.parent(sc, cp)
    K.assign(sc, steel_d)
    cmds.rotate(0, -18, 0, cp)
    cmds.move(28, PY, 12, cp)

    # ---- measured artifacts: sphere / cube / gear at 10/20/30 ----
    K.cyl("GEO_au_art1", 4.0, 1.2, (6, PY + 0.6, 26), sx=24, parent=g_obj, sg=blue_m)
    sph = cmds.polySphere(r=3.4, sx=20, sy=16, name="GEO_au_art2")[0]
    cmds.move(16, PY + 4.6, 26, sph)
    cmds.parent(sph, g_obj)
    K.assign(sph, blue_m)
    cu = cmds.polyCube(w=5.5, h=5.5, d=5.5, name="GEO_au_art3")[0]
    cmds.move(26, PY + 2.75, 26, cu)
    cmds.parent(cu, g_obj)
    K.assign(cu, brass)

    # ---- dimension annotations ----
    _dim_arrow("GEO_au_d10", (6, PY + 9.5, 26), (16, PY + 9.5, 26), g_obj, dim_m)
    _text("GEO_au_t10", "10.0", (8.2, PY + 10.5, 26), g_obj, mark_m)
    _dim_arrow("GEO_au_d20", (6, PY + 13.5, 26), (26, PY + 13.5, 26), g_obj, dim_m)
    _text("GEO_au_t20", "20.0", (13.2, PY + 14.5, 26), g_obj, mark_m)
    _dim_arrow("GEO_au_d30", (6, PY + 17.5, 26), (36, PY + 17.5, 26), g_obj, dim_m)
    _text("GEO_au_t30", "30.0", (18.2, PY + 18.5, 26), g_obj, mark_m)

    # ---- backdrop wall with blueprint grid ----
    wall = cmds.polyCube(w=300, h=170, d=4, name="GEO_au_wall")[0]
    cmds.move(0, 40, -70, wall)
    cmds.parent(wall, g_env)
    K.assign(wall, wall_m)
    grid_m = K.mat("MAT_t20au_grid", (0.16, 0.30, 0.40), spec=0.2, ecc=0.5)
    for gx in range(-6, 7):
        gl = cmds.polyCube(w=0.18, h=150, d=0.1, name=f"GEO_au_gx{gx}")[0]
        cmds.move(gx * 20, 40, -67.8, gl)
        cmds.parent(gl, g_env)
        K.assign(gl, grid_m)
    for gy in range(-3, 6):
        gl = cmds.polyCube(w=280, h=0.18, d=0.1, name=f"GEO_au_gy{gy}")[0]
        cmds.move(0, 10 + gy * 20, -67.8, gl)
        cmds.parent(gl, g_env)
        K.assign(gl, grid_m)

    # ---- lights ----
    lg = cmds.group(em=True, name="GRP_t20au_lights", parent=root)
    K.spot(
        "LGT_t20au_key",
        (-80, 130, 110),
        (-10, 45, 0),
        (1.0, 0.88, 0.70),
        4.4,
        cone=48,
        pen=14,
        parent=lg,
    )
    K.spot(
        "LGT_t20au_rim",
        (100, 80, -60),
        (0, 45, 0),
        (0.4, 0.6, 1.0),
        2.8,
        cone=46,
        pen=12,
        parent=lg,
    )
    f2 = cmds.directionalLight(intensity=0.4, name="LGT_t20au_fill")
    cmds.setAttr(f2 + ".color", 0.62, 0.70, 0.92, type="double3")
    cmds.rotate(-28, 35, 0, cmds.listRelatives(f2, parent=True)[0])
    cmds.parent(cmds.listRelatives(f2, parent=True)[0], lg)
    amb = cmds.ambientLight(intensity=0.16, name="LGT_t20au_amb")
    cmds.parent(cmds.listRelatives(amb, parent=True)[0], lg)

    # ---- cameras ----
    aim = K.loc("LOC_t20au_aim", (0, 46, -4))
    ct, cs = K.cam("CAM_t20au_hero", (95, 80, 120), aim, fl=56)
    cmds.setAttr(cs + ".depthOfField", 1)
    cmds.setAttr(cs + ".focusDistance", 150)
    cmds.setAttr(cs + ".fStop", 7.1)
    cmds.setAttr(cs + ".focusRegionScale", 0.5)
    K.cam("CAM_t20au_flat", (0, 52, 130), aim, fl=52)
    for lc in cmds.ls("LOC_t20au_*"):
        try:
            cmds.hide(lc)
        except Exception:
            pass

    cmds.select(clear=True)
    return {"ok": True, "objects": len(cmds.ls(dag=True) or [])}
