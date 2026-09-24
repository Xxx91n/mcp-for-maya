# t20 movement — true-involute gear train caliber (idempotent)
import math

import maya.cmds as cmds
import t20kit as K


ROOT = "GRP_t20_movement"


def involute_pts(m, Z, alpha_deg=20.0, n_flank=7, n_tip=3, n_root=3):
    """Closed [(x,z)] outline of a spur gear; tooth #0 centered on +X."""
    alpha = math.radians(alpha_deg)
    rp = 0.5 * m * Z
    rb = rp * math.cos(alpha)
    ra = rp + m
    rd = rp - 1.25 * m
    inv_a = math.tan(alpha) - alpha
    half_tooth = math.pi / (2.0 * Z)
    t_max = math.sqrt(ra * ra - rb * rb) / rb
    t_min = 0.0 if rd <= rb else math.sqrt(rd * rd - rb * rb) / rb

    def ip(t):
        x = rb * (math.cos(t) + t * math.sin(t))
        y = rb * (math.sin(t) - t * math.cos(t))
        return x, y

    off = -half_tooth - inv_a
    step = 2.0 * math.pi / Z
    out = []
    for k in range(Z):
        ca = k * step
        flank = []
        for i in range(n_flank + 1):
            t = t_min + (t_max - t_min) * i / n_flank
            x, y = ip(t)
            a = math.atan2(y, x) + off + ca
            r = math.hypot(x, y)
            flank.append((r * math.cos(a), r * math.sin(a)))
        if rd < rb:
            a_b = off + ca
            out.append((rd * math.cos(a_b), rd * math.sin(a_b)))
        out += flank
        tip_a = math.atan2(ip(t_max)[1], ip(t_max)[0]) + off + ca
        for i in range(1, n_tip + 1):
            f = i / (n_tip + 1)
            a = tip_a + (2.0 * ca - 2.0 * tip_a) * f
            out.append((ra * math.cos(a), ra * math.sin(a)))
        for x, y in reversed(flank):
            a = math.atan2(y, x)
            r = math.hypot(x, y)
            am = 2.0 * ca - a
            out.append((r * math.cos(am), r * math.sin(am)))
        if rd < rb:
            a_bl = 2.0 * ca - (off + ca)
            out.append((rd * math.cos(a_bl), rd * math.sin(a_bl)))
            a0 = a_bl
        else:
            a0 = math.atan2(out[-1][1], out[-1][0])
        a_next = ca + step + off
        for i in range(1, n_root + 1):
            f = i / (n_root + 1)
            a = a0 + (a_next - a0) * f
            out.append((rd * math.cos(a), rd * math.sin(a)))
    return out


def wheel(name, m, Z, y0, th, pos, parent, sg, hub_r=3.0, phase_deg=0.0):
    """Gear sub-assembly: involute prism + hub, moved to (pos.x, 0, pos.z)."""
    g = cmds.group(em=True, name=name, parent=parent)
    pts = involute_pts(m, Z)
    b = K.prism(name + "_teeth", pts, y0, y0 + th, parent=g)
    K.smooth(b, 40)
    K.assign(b, sg)
    K.cyl(name + "_hub", hub_r, th + 1.6, (0, y0 + th / 2.0, 0), sx=16, parent=g, sg=sg)
    cmds.move(pos[0], 0, pos[1], g)
    if phase_deg:
        cmds.rotate(0, phase_deg, 0, g, pivot=(pos[0], 0, pos[1]))
    return g


def build():
    K.kill(
        [
            ROOT,
            ROOT + "*",
            "MAT_t20mv_*",
            "CAM_t20mv_*",
            "LGT_t20mv_*",
            "LOC_t20mv_*",
            "GRP_t20mv_*",
        ]
    )
    root = cmds.group(em=True, name=ROOT)

    brass = K.mat("MAT_t20mv_brass", (0.55, 0.38, 0.13), spec=0.85, ecc=0.10, refl=0.35)
    steel = K.mat("MAT_t20mv_steel", (0.55, 0.58, 0.62), spec=0.9, ecc=0.08, refl=0.45)
    steel_dk = K.mat("MAT_t20mv_steeldk", (0.30, 0.32, 0.36), spec=0.7, ecc=0.14, refl=0.3)
    plate_m = K.mat("MAT_t20mv_plate", (0.44, 0.37, 0.23), spec=0.55, ecc=0.22, refl=0.2)
    stripe = K.mat("MAT_t20mv_stripe", (0.56, 0.48, 0.33), spec=0.7, ecc=0.16, refl=0.25)
    ruby = K.mat("MAT_t20mv_ruby", (0.55, 0.02, 0.05), spec=0.95, ecc=0.05, incand=0.18)
    blued = K.mat("MAT_t20mv_blued", (0.05, 0.10, 0.35), spec=0.85, ecc=0.08, refl=0.4)
    dark = K.mat("MAT_t20mv_dark", (0.05, 0.055, 0.07), spec=0.25, ecc=0.3)

    g_train = cmds.group(em=True, name="GRP_t20mv_train", parent=root)
    g_plate = cmds.group(em=True, name="GRP_t20mv_plates", parent=root)
    g_bal = cmds.group(em=True, name="GRP_t20mv_balance", parent=root)
    g_det = cmds.group(em=True, name="GRP_t20mv_detail", parent=root)
    g_env = cmds.group(em=True, name="GRP_t20mv_env", parent=root)

    MOD, Y0, TH = 1.15, 6.0, 2.2
    zb, zc, zt, zf = 66, 48, 36, 30
    rb_, rc_, rt_, rf_ = MOD * zb / 2, MOD * zc / 2, MOD * zt / 2, MOD * zf / 2
    pb = (30.0, -18.0)
    pc = (pb[0] - (rb_ + rc_), pb[1])
    a1 = math.radians(-52)
    pt_ = (pc[0] + (rc_ + rt_) * math.cos(a1), pc[1] + (rc_ + rt_) * math.sin(a1))
    a2 = math.radians(72)
    pf = (pt_[0] + (rt_ + rf_) * math.cos(a2), pt_[1] + (rt_ + rf_) * math.sin(a2))
    a3 = math.radians(38)
    pe = (pf[0] + (rf_ + 11.0) * math.cos(a3), pf[1] + (rf_ + 11.0) * math.sin(a3))

    # ---- train: barrel -> center -> third -> fourth -> escape ----
    # barrel: tooth aimed at contact direction toward center (angle pi)
    wheel("GEO_mv_barrel", MOD, zb, Y0, TH + 0.8, pb, g_train, brass, hub_r=4.5)
    K.cyl(
        "GEO_mv_barrel_drum",
        rb_ - 2.5,
        1.2,
        (pb[0], Y0 - 0.4, pb[1]),
        sx=48,
        parent=g_train,
        sg=brass,
    )
    # center: gap at its contact direction (0 deg toward barrel)
    wheel("GEO_mv_center", MOD, zc, Y0, TH, pc, g_train, brass, hub_r=3.2, phase_deg=180.0 / zc)
    # third: gap toward center's contact (angle a1 back)
    wheel(
        "GEO_mv_third",
        MOD,
        zt,
        Y0,
        TH,
        pt_,
        g_train,
        brass,
        hub_r=2.6,
        phase_deg=math.degrees(a1 + math.pi) + 180.0 / zt,
    )
    # fourth: gap toward third
    wheel(
        "GEO_mv_fourth",
        MOD,
        zf,
        Y0,
        TH,
        pf,
        g_train,
        brass,
        hub_r=2.2,
        phase_deg=math.degrees(a2 + math.pi) + 180.0 / zf,
    )

    # lathe-cut accent rings on the two big wheels
    for nm_, p_, r_ in [("barrel_acc", pb, rb_ - 6.0), ("center_acc", pc, rc_ - 5.0)]:
        ar = K.ring(
            f"GEO_mv_{nm_}", r_, r_ - 1.4, Y0 + TH + 0.9, 0.5, parent=g_det, sg=steel_dk, sx=56
        )
        cmds.move(p_[0], Y0 + TH + 0.9, p_[1], ar)

    # pinions under each wheel
    for i, p in enumerate([pb, pc, pt_, pf]):
        K.cyl(
            f"GEO_mv_pinion_{i}",
            1.7,
            4.2,
            (p[0], Y0 - 1.2, p[1]),
            sx=12,
            parent=g_train,
            sg=steel_dk,
        )

    # escape wheel — spoked sawtooth (honest non-involute profile)
    g_esc = cmds.group(em=True, name="GRP_mv_escape", parent=g_train)
    esc_pts = []
    N, r_out, r_root = 15, 11.0, 8.2
    for k in range(N):
        a = 2 * math.pi * k / N
        st = 2 * math.pi / N
        esc_pts.append((r_root * math.cos(a), r_root * math.sin(a)))
        esc_pts.append((r_out * math.cos(a + st * 0.18), r_out * math.sin(a + st * 0.18)))
        esc_pts.append((r_root * math.cos(a + st * 0.72), r_root * math.sin(a + st * 0.72)))
    e = K.prism("GEO_mv_escape_teeth", esc_pts, Y0 + 0.2, Y0 + TH - 0.4, parent=g_esc)
    K.assign(e, steel)
    K.ring("GEO_mv_escape_rim", 7.6, 6.6, Y0 + TH / 2, TH - 0.8, parent=g_esc, sg=steel)
    for i in range(4):
        K.box(
            f"GEO_mv_escape_arm_{i}",
            6.8,
            TH - 1.0,
            1.4,
            (3.5 * math.cos(i * math.pi / 2), Y0 + TH / 2, 3.5 * math.sin(i * math.pi / 2)),
            parent=g_esc,
            sg=steel,
            rot=(0, -math.degrees(i * math.pi / 2), 0),
        )
    K.cyl("GEO_mv_escape_hub", 2.0, TH + 1.4, (0, Y0 + TH / 2, 0), parent=g_esc, sg=steel)
    cmds.move(pe[0], 0, pe[1], g_esc)

    # ---- balance wheel + hairspring ----
    bp = (-36.0, 32.0)
    g_bw = cmds.group(em=True, name="GRP_mv_balance", parent=g_bal)
    K.ring("GEO_mv_bal_rim", 19.0, 16.6, Y0 + 7.3, 2.6, parent=g_bw, sg=brass)
    for i in range(2):
        K.box(
            f"GEO_mv_bal_arm_{i}",
            32.8,
            2.2,
            3.0,
            (0, Y0 + 7.3, 0),
            parent=g_bw,
            sg=brass,
            rot=(0, i * 90.0, 0),
        )
    K.cyl("GEO_mv_bal_staff", 1.6, 11.0, (0, Y0 + 5.0, 0), parent=g_bw, sg=steel)
    for i in range(8):
        a = i * math.pi / 4
        K.cyl(
            f"GEO_mv_bal_screw_{i}",
            1.15,
            1.6,
            (19.2 * math.cos(a), Y0 + 7.3, 19.2 * math.sin(a)),
            sx=10,
            parent=g_bw,
            sg=blued,
        )
    sp = []
    turns, steps = 5.2, 150
    for i in range(steps + 1):
        t = i / steps
        a = turns * 2 * math.pi * t
        r = 2.6 + 13.4 * t
        sp.append((r * math.cos(a), Y0 + 9.9 + 0.12 * math.sin(3 * a), r * math.sin(a)))
    K.tube("GEO_mv_hairspring", sp, radius=0.32, parent=g_bw, sg=blued)
    K.cyl("GEO_mv_bal_stud", 1.5, 4.0, (15.6, Y0 + 9.9, 0), parent=g_bw, sg=steel_dk)
    K.cyl("GEO_mv_imp_jewel", 1.1, 1.4, (6.0, Y0 + 5.8, 4.0), parent=g_bw, sg=ruby)
    cmds.move(bp[0], 0, bp[1], g_bw)

    # ---- main plate + train bridge + balance cock ----
    K.cyl("GEO_mv_mainplate", 78.0, 3.0, (0, 1.5, 0), sx=72, parent=g_plate, sg=plate_m)
    K.ring("GEO_mv_plate_edge", 78.0, 74.0, 3.2, 0.8, parent=g_plate, sg=stripe)

    bridge_pts = []
    cx, cz = -8.0, -16.0
    for i in range(56):
        a = 2 * math.pi * i / 56
        r = 40.0 * (1.0 + 0.16 * math.cos(3 * a + 0.6))
        bridge_pts.append((cx + r * math.cos(a), cz + r * math.sin(a)))
    br = K.prism("GEO_mv_trainbridge", bridge_pts, 12.0, 14.0, parent=g_plate)
    K.assign(br, stripe)
    # geneva stripes — raised ribs on bridge top
    for i in range(9):
        K.box(
            f"GEO_mv_rib_{i}",
            4.6,
            0.28,
            58.0,
            (cx - 32 + i * 7.4, 14.12, cz - 2.0),
            parent=g_plate,
            sg=plate_m,
            rot=(0, 14.0, 0),
        )
    for i, (sx_, sz_) in enumerate([(cx - 26, cz - 24), (cx + 30, cz - 10), (cx - 6, cz + 30)]):
        K.cyl(f"GEO_mv_screw_{i}", 1.8, 1.6, (sx_, 14.6, sz_), sx=12, parent=g_det, sg=blued)
        K.box(
            f"GEO_mv_slot_{i}",
            2.4,
            0.25,
            0.5,
            (sx_, 15.45, sz_),
            parent=g_det,
            sg=dark,
            rot=(0, 25.0 * i, 0),
        )

    cock_pts = [
        (-72, 22),
        (-58, 16),
        (-44, 18),
        (-33, 24),
        (-31, 31),
        (-33, 37),
        (-42, 40),
        (-55, 41),
        (-68, 42),
        (-75, 37),
        (-76, 29),
    ]
    ck = K.prism("GEO_mv_balcock", cock_pts, 20.5, 22.0, parent=g_plate)
    K.assign(ck, stripe)
    K.cyl("GEO_mv_cock_screw", 1.8, 1.6, (-71, 22.7, 31), sx=12, parent=g_det, sg=blued)

    # jewels over train pivots (on the bridge)
    for i, p in enumerate([pc, pt_, pf]):
        K.cyl(f"GEO_mv_jewel_{i}", 2.4, 0.9, (p[0], 14.55, p[1]), sx=14, parent=g_det, sg=ruby)
        jr = K.ring(f"GEO_mv_jewelset_{i}", 3.2, 2.4, 14.65, 0.5, parent=g_det, sg=brass, sx=24)
        cmds.move(p[0], 14.65, p[1], jr)

    # winding stem + crown
    stem = K.cyl("GEO_mv_stem", 2.2, 26.0, (0, 6, 0), sx=16, parent=g_det, sg=steel_dk)
    cmds.rotate(0, 0, 90, stem)
    cmds.move(88, 6, -18, stem)
    crown = K.cyl("GEO_mv_crown", 7.0, 6.0, (0, 0, 0), sx=24, parent=g_det, sg=steel)
    cmds.rotate(0, 0, 90, crown)
    cmds.move(104, 6, -18, crown)
    for i in range(14):
        a = 2 * math.pi * i / 14
        K.box(
            f"GEO_mv_knurl_{i}",
            6.2,
            1.0,
            1.7,
            (104, 6 + 7.0 * math.cos(a), -18 + 7.0 * math.sin(a)),
            parent=g_det,
            sg=steel_dk,
            rot=(math.degrees(a), 0, 0),
        )

    # ratchet on barrel + click
    rat = K.prism("GEO_mv_ratchet", involute_pts(0.8, 40), 9.2, 10.6, parent=g_det)
    K.assign(rat, steel)
    cmds.move(pb[0], 0, pb[1], rat)
    K.cyl("GEO_mv_rat_hub", 4.5, 2.6, (pb[0], 10.0, pb[1]), parent=g_det, sg=steel)
    K.box(
        "GEO_mv_click",
        16.0,
        1.6,
        4.0,
        (pb[0] + 42, 10.4, pb[1] - 8),
        parent=g_det,
        sg=steel,
        rot=(0, -28.0, 0),
    )
    K.cyl(
        "GEO_mv_click_scr", 1.8, 1.6, (pb[0] + 48, 11.2, pb[1] - 9), sx=12, parent=g_det, sg=blued
    )

    # ---- environment ----
    K.cyl("GEO_mv_floor", 220.0, 2.0, (0, -1.2, 0), sx=72, parent=g_env, sg=dark)

    # ---- lights ----
    lg = cmds.group(em=True, name="GRP_t20mv_lights", parent=root)
    K.spot(
        "LGT_t20mv_key",
        (95, 150, 130),
        (5, 8, -8),
        (1.0, 0.82, 0.60),
        3.6,
        cone=46,
        pen=14,
        parent=lg,
    )
    K.spot(
        "LGT_t20mv_rim",
        (-120, 90, -110),
        (-20, 10, -10),
        (0.45, 0.62, 1.0),
        2.8,
        cone=42,
        pen=10,
        parent=lg,
    )
    fl2 = cmds.directionalLight(intensity=0.5, name="LGT_t20mv_fill")
    cmds.setAttr(fl2 + ".color", 0.6, 0.7, 0.95, type="double3")
    cmds.rotate(-35, 40, 0, cmds.listRelatives(fl2, parent=True)[0])
    cmds.parent(cmds.listRelatives(fl2, parent=True)[0], lg)
    amb = cmds.ambientLight(intensity=0.16, name="LGT_t20mv_amb")
    cmds.parent(cmds.listRelatives(amb, parent=True)[0], lg)

    # ---- cameras ----
    aim = K.loc("LOC_t20mv_aim", (-6, 9, -12))
    ct, cs = K.cam("CAM_t20mv_hero", (126, 100, 162), aim, fl=70)
    cmds.setAttr(cs + ".depthOfField", 1)
    cmds.setAttr(cs + ".focusDistance", 215)
    cmds.setAttr(cs + ".fStop", 4.5)
    cmds.setAttr(cs + ".focusRegionScale", 0.4)
    K.cam("CAM_t20mv_top", (8, 235, 40), aim)
    K.cam("CAM_t20mv_low", (195, 60, 150), aim, fl=55)

    cmds.select(clear=True)
    return {
        "ok": True,
        "objects": len(cmds.ls(dag=True) or []),
        "meshing": {
            "barrel": pb,
            "center": pc,
            "third": pt_,
            "fourth": pf,
            "escape": pe,
            "balance": bp,
        },
    }
