# t20 workbench — PH assets staged: alarm clock + pocket watch + tool
# chest on a horologist's desk, scattered involute-gear spares.
import maya.cmds as cmds
import t20_movement as MV
import t20kit as K


ROOT = "GRP_t20_workbench"


def _scale_to(group, target_h):
    """Set ABSOLUTE scale so world height == target_h (cmds.scale sets,
    it does not multiply - recompute from current scale for idempotence)."""
    bb = cmds.exactWorldBoundingBox(group)
    h = bb[4] - bb[1]
    cur = cmds.getAttr(group + ".scaleX") or 1.0
    if h <= 0 or cur <= 0:
        return 1.0
    want = target_h * cur / h
    cmds.scale(want, want, want, group)
    return want


def _scale_w(group, target_w):
    bb = cmds.exactWorldBoundingBox(group)
    w = bb[3] - bb[0]
    cur = cmds.getAttr(group + ".scaleX") or 1.0
    if w <= 0 or cur <= 0:
        return 1.0
    want = target_w * cur / w
    cmds.scale(want, want, want, group)
    return want


def _ground(group, y):
    """Lift group so world-bbox min-Y sits exactly at y."""
    bb = cmds.exactWorldBoundingBox(group)
    dy = y - bb[1]
    if abs(dy) > 1e-6:
        cmds.move(0, dy, 0, group, relative=True)
    return bb


def _tune_imported(groups):
    """VP2-tame imported phongs: metal->reflectivity and arm->diffuse
    both wash to flat white; restore baked shading + sane spec."""
    for g in groups:
        if not cmds.objExists(g):
            continue
        for sh in cmds.listRelatives(g, ad=True, type="mesh") or []:
            for sg in cmds.listConnections(sh, type="shadingEngine") or []:
                for m in cmds.listConnections(sg + ".surfaceShader") or []:
                    if cmds.nodeType(m) not in ("phong", "blinn"):
                        continue
                    is_glass = "glass" in m.lower()
                    for att in (".reflectivity", ".diffuse"):
                        for src in cmds.listConnections(m + att, s=True, d=False) or []:
                            for ch in (".outColorR", ".outColor", ".outAlpha"):
                                try:
                                    cmds.disconnectAttr(src + ch, m + att)
                                except Exception:
                                    pass
                    for att, val in (
                        (".reflectivity", 0.22),
                        (".diffuse", 0.92),
                        (".cosinePower", 42),
                        (".specularRollOff", 0.55),
                    ):
                        if cmds.objExists(m + att):
                            try:
                                cmds.setAttr(m + att, val)
                            except Exception:
                                pass
                    try:
                        cmds.setAttr(m + ".specularColor", 0.42, 0.40, 0.36, type="double3")
                    except Exception:
                        pass
                    if is_glass:
                        for att in (".color", ".normalCamera"):
                            for src in cmds.listConnections(m + att, s=True, d=False) or []:
                                for ch in (".outColor", ".outColorR", ".outNormal"):
                                    try:
                                        cmds.disconnectAttr(src + ch, m + att)
                                    except Exception:
                                        pass
                        cmds.setAttr(m + ".color", 0.05, 0.05, 0.06, type="double3")
                        cmds.setAttr(m + ".transparency", 0.72, 0.72, 0.72, type="double3")
                        cmds.setAttr(m + ".specularColor", 0.9, 0.9, 0.9, type="double3")
                        cmds.setAttr(m + ".reflectivity", 0.6)


def build():
    K.kill(
        [
            ROOT,
            ROOT + "*",
            "MAT_t20wb_*",
            "CAM_t20wb_*",
            "LGT_t20wb_*",
            "LOC_t20wb_*",
            "GRP_t20wb_*",
            # legacy gallery/dressing residue
            "GRP_t20_gallery",
            "GRP_t20_gallery*",
            "GRP_t20ga_*",
            "MAT_t20ga_*",
            "CAM_t20ga_*",
            "LGT_t20ga_*",
            "LOC_t20ga_*",
            "GEO_ga_*",
            "GEO_mv_*",
            "MAT_t20mv_*",
            "CAM_t20mv_*",
            "LGT_t20mv_*",
            "LOC_t20mv_*",
            "GRP_t20_movement",
            "GRP_t20mv_*",
            "GEO_bn_*",
            "MAT_t20bn_*",
            "CAM_t20bn_*",
            "LGT_t20bn_*",
            "LOC_t20bn_*",
            "GRP_t20_bonsai",
            "GRP_t20bn_*",
        ]
    )
    root = cmds.group(em=True, name=ROOT)

    wood = K.mat("MAT_t20wb_wood", (0.24, 0.13, 0.06), spec=0.3, ecc=0.3, refl=0.15)
    wood_edge = K.mat("MAT_t20wb_woodedge", (0.16, 0.08, 0.04), spec=0.25, ecc=0.35)
    felt = K.mat("MAT_t20wb_felt", (0.05, 0.14, 0.11), spec=0.08, ecc=0.6)
    brass = K.mat("MAT_t20wb_brass", (0.5, 0.34, 0.12), spec=0.85, ecc=0.1, refl=0.4)
    steel = K.mat("MAT_t20wb_steel", (0.5, 0.53, 0.58), spec=0.85, ecc=0.09, refl=0.4)
    dark = K.mat("MAT_t20wb_dark", (0.05, 0.055, 0.07), spec=0.2, ecc=0.35)
    wall_m = K.mat("MAT_t20wb_wall", (0.09, 0.095, 0.11), spec=0.1, ecc=0.5)
    ruby = K.mat("MAT_t20wb_ruby", (0.55, 0.02, 0.05), spec=0.95, ecc=0.05, incand=0.2)
    blued = K.mat("MAT_t20wb_blued", (0.05, 0.10, 0.35), spec=0.85, ecc=0.08, refl=0.4)

    g_env = cmds.group(em=True, name="GRP_t20wb_env", parent=root)
    g_disp = cmds.group(em=True, name="GRP_t20wb_display", parent=root)
    g_parts = cmds.group(em=True, name="GRP_t20wb_parts", parent=root)

    # desk slab + modest edge + wall cove
    desk = cmds.polyCube(w=230, h=7, d=130, name="GEO_wb_desk")[0]
    cmds.move(0, 10.5, 0, desk)
    cmds.parent(desk, g_env)
    K.assign(desk, wood)
    edge = cmds.polyCube(w=230, h=1.6, d=130, name="GEO_wb_deskedge")[0]
    cmds.move(0, 6.6, 0, edge)
    cmds.parent(edge, g_env)
    K.assign(edge, wood_edge)
    wall = K.revolve_y(
        "GEO_wb_cove", [(95, 0), (160, 4), (190, 14), (200, 60), (202, 190)], sections=52
    )
    cmds.move(0, 8, 0, wall)
    cmds.parent(wall, g_env)
    for sh in cmds.listRelatives(wall, shapes=True) or []:
        cmds.setAttr(sh + ".doubleSided", 1)
    K.assign(wall, wall_m)
    DY = 14.0  # desk top y

    # felt pad under watch (tilted display like before)
    pad = cmds.polyCube(w=46, h=1.4, d=32, name="GEO_wb_pad")[0]
    cmds.move(48, DY + 0.8, 6, pad)
    cmds.rotate(0, -14, 0, pad)
    cmds.parent(pad, g_disp)
    K.assign(pad, felt)

    # ---- imported assets ----
    if cmds.objExists("GRP_asset_alarm_clock_01"):
        cmds.delete("GRP_asset_alarm_clock_01")  # rigged asset, baked
        # world-offset verts; not worth fighting for this still life
    if cmds.objExists("GRP_asset_vintage_pocket_watch"):
        cmds.showHidden("GRP_asset_vintage_pocket_watch")
        _scale_to("GRP_asset_vintage_pocket_watch", 26)
        cmds.move(42, 0, 5.0, "GRP_asset_vintage_pocket_watch")
        cmds.rotate(-66, -18, 0, "GRP_asset_vintage_pocket_watch")
        _ground("GRP_asset_vintage_pocket_watch", DY + 1.6)
    if cmds.objExists("GRP_asset_metal_tool_chest"):
        cmds.showHidden("GRP_asset_metal_tool_chest")
        _scale_w("GRP_asset_metal_tool_chest", 66)
        cmds.move(8, 0, -38, "GRP_asset_metal_tool_chest")
        cmds.rotate(0, 10, 0, "GRP_asset_metal_tool_chest")
        cmds.move(12, 0, -36, "GRP_asset_metal_tool_chest")
        _ground("GRP_asset_metal_tool_chest", DY)
    for g in [
        "GRP_asset_bronze_shark_statue",
        "GRP_asset_bronze_whale_statue",
        "GRP_asset_bronze_ray_statue",
    ]:
        if cmds.objExists(g):
            cmds.hide(g)
    _tune_imported(
        ["GRP_asset_alarm_clock_01", "GRP_asset_vintage_pocket_watch", "GRP_asset_metal_tool_chest"]
    )

    # ---- scattered involute-gear spares (ties back to the movement) ----
    specs = [
        (-78, 26, 1.05, 40, 0.0),
        (-58, 34, 0.85, 30, 12.0),
        (-20, 30, 1.0, 36, 25.0),
        (16, 36, 0.8, 28, 8.0),
        (82, 30, 0.9, 32, 40.0),
    ]
    for i, (gx, gz, mm, zz, rot) in enumerate(specs):
        pts = MV.involute_pts(mm, zz)
        g = K.prism(f"GEO_wb_gear_{i}", pts, DY + 0.02, DY + 1.5, parent=g_parts)
        K.assign(g, brass if i % 2 else steel)
        cmds.move(gx, 0, gz, g)
        cmds.rotate(0, rot, 0, g)
        K.cyl(
            f"GEO_wb_gearhub_{i}",
            2.4,
            2.0,
            (gx, DY + 1.0, gz),
            sx=12,
            parent=g_parts,
            sg=blued if i % 2 else steel,
        )
    # leaning gear against the chest (standing, adds vertical rhythm)
    lg_pts = MV.involute_pts(0.75, 26)
    lg_ = K.prism("GEO_wb_gear_lean", lg_pts, 0, 1.3, parent=g_parts)
    K.assign(lg_, brass)
    cmds.rotate(90, 0, 0, lg_)
    cmds.rotate(0, -20, -12, lg_, relative=True)
    cmds.move(62, DY + 9.5, -30, lg_)
    # loose screws + a driver
    for i, (sx_, sz_) in enumerate([(-70, 44), (30, 40), (-2, 46)]):
        K.cyl(f"GEO_wb_screw_{i}", 1.1, 1.0, (sx_, DY + 0.5, sz_), sx=10, parent=g_parts, sg=blued)
    drv = cmds.group(em=True, name="GRP_wb_driver", parent=g_parts)
    K.cyl("GEO_wb_drv_handle", 3.0, 16.0, (0, 0, 0), sx=14, parent=drv, sg=wood_edge)
    K.cyl("GEO_wb_drv_shaft", 0.9, 15.0, (0, -15.0, 0), sx=8, parent=drv, sg=steel)
    cmds.rotate(0, 0, 90, drv)
    cmds.rotate(0, -30, 0, drv)
    cmds.move(-95, DY + 3.0, 12, drv)
    # loupe — brass ring + dark glass disc
    lou = cmds.group(em=True, name="GRP_wb_loupe", parent=g_parts)
    K.ring("GEO_wb_loupe_ring", 9.0, 7.4, 0, 1.8, parent=lou, sg=brass, sx=40)
    K.cyl("GEO_wb_loupe_glass", 7.2, 0.5, (0, 0, 0), sx=32, parent=lou, sg=dark)
    cmds.rotate(0, 0, 0, lou)
    cmds.move(86, DY + 0.9, -12, lou)
    # ruby jewels on a small tray
    for i in range(4):
        K.cyl(
            f"GEO_wb_jewel_{i}",
            0.9,
            0.6,
            (-40 + i * 3.4, DY + 0.3, 44),
            sx=10,
            parent=g_parts,
            sg=ruby,
        )

    # lights
    lg = cmds.group(em=True, name="GRP_t20wb_lights", parent=root)
    K.spot(
        "LGT_t20wb_key",
        (-70, 180, 120),
        (-20, 20, -5),
        (1.0, 0.8, 0.55),
        4.6,
        cone=50,
        pen=16,
        parent=lg,
    )
    K.spot(
        "LGT_t20wb_watch",
        (95, 120, 80),
        (48, 18, 6),
        (1.0, 0.88, 0.62),
        3.0,
        cone=30,
        pen=12,
        parent=lg,
    )
    K.spot(
        "LGT_t20wb_rim",
        (-120, 90, -110),
        (-10, 20, -10),
        (0.4, 0.58, 1.0),
        2.6,
        cone=44,
        pen=12,
        parent=lg,
    )
    f2 = cmds.directionalLight(intensity=0.35, name="LGT_t20wb_fill")
    cmds.setAttr(f2 + ".color", 0.6, 0.68, 0.9, type="double3")
    cmds.rotate(-28, 40, 0, cmds.listRelatives(f2, parent=True)[0])
    cmds.parent(cmds.listRelatives(f2, parent=True)[0], lg)
    amb = cmds.ambientLight(intensity=0.16, name="LGT_t20wb_amb")
    cmds.parent(cmds.listRelatives(amb, parent=True)[0], lg)
    for lc in cmds.ls("LGT_t20wb_*_tgt") + cmds.ls("LOC_t20wb_*"):
        try:
            cmds.hide(lc)
        except Exception:
            pass

    # cameras
    aim = K.loc("LOC_t20wb_aim", (-2, 22, 0))
    ct, cs = K.cam("CAM_t20wb_hero", (118, 95, 148), aim, fl=56)
    cmds.setAttr(cs + ".depthOfField", 1)
    cmds.setAttr(cs + ".focusDistance", 190)
    cmds.setAttr(cs + ".fStop", 5.6)
    cmds.setAttr(cs + ".focusRegionScale", 0.45)
    K.cam("CAM_t20wb_clock", (40, 60, 92), K.loc("LOC_t20wb_aim2", (-34, 34, -8)), fl=62)
    K.cam("CAM_t20wb_watch", (92, 48, 62), K.loc("LOC_t20wb_aim3", (48, 21, 4)), fl=65)
    for lc in cmds.ls("LOC_t20wb_*"):
        try:
            cmds.hide(lc)
        except Exception:
            pass

    cmds.select(clear=True)
    return {"ok": True, "objects": len(cmds.ls(dag=True) or [])}
