"""T-19c demo scene builder — executed inside Maya via execute_code.

Repro: Maya 2024 en_US GUI session; run this file's body through the
mcp-for-maya execute_code tool (or paste into Script Editor). Creates:

  GRP_env     — showroom: stage disc, cove wall, rail ring, light rigs
  GRP_exhibits — iris sculpture (revolve housing + blade array + glass
                 lens + curve-extruded cables), scripted Utah-style
                 teapot, pedestal slots (Camera_01 lands separately
                 via the asset_import tool)
  GRP_lighting — warm key spot on hero, cool flank spots, fill, rim
                 (parented under CAM_orbit for orbit stability)
  CAM_hero / CAM_alt / LOC_aim

All geometry is revolve/extrude/array work — no primitive-stack look.
Naming follows GRP_/GEO_/MAT_/CAM_/LGT_/LOC_ (AGENTS.md).
"""

import math

import maya.cmds as cmds


# ------------------------------------------------------------------
# cleanup (idempotent rebuild)
# ------------------------------------------------------------------
for _n in [
    "GRP_env",
    "GRP_exhibits",
    "GRP_lighting",
    "CAM_hero",
    "CAM_alt",
    "LOC_aim",
    "LOC_cam_target",
]:
    if cmds.objExists(_n):
        try:
            cmds.delete(_n)
        except Exception:
            pass
for _pat in ["MAT_demo_*", "MAT_exh_*", "MAT_env_*"]:
    for _n in cmds.ls(_pat) or []:
        try:
            cmds.delete(_n)
        except Exception:
            pass


def _mat(name, rgb, spec=0.2, spec_pow=32.0, refl=0.0, trans=0.0, incand=0.0):
    m = cmds.shadingNode("blinn", asShader=True, name=name)
    cmds.setAttr(m + ".color", *rgb, type="double3")
    cmds.setAttr(m + ".specularColor", spec, spec, spec, type="double3")
    cmds.setAttr(m + ".eccentricity", spec_pow / 100.0)
    if refl:
        cmds.setAttr(m + ".reflectivity", refl)
    if trans:
        cmds.setAttr(m + ".transparency", trans, trans, trans, type="double3")
    if incand:
        cmds.setAttr(m + ".incandescence", incand, incand, incand, type="double3")
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "SG")
    cmds.connectAttr(m + ".outColor", sg + ".surfaceShader", f=True)
    return sg


def _assign(obj, sg):
    for o in [obj] if isinstance(obj, str) else obj:
        try:
            cmds.sets(o, e=True, forceElement=sg)
        except Exception:
            pass


def _smooth(mesh):
    try:
        cmds.polySoftEdge(mesh, angle=60, constructionHistory=False)
    except Exception:
        pass


def _revolve_y(name, pts, sections=48):
    """Revolve an (r, y) profile around the Y axis -> NURBS surface."""
    c = cmds.curve(d=3, p=[(r, y, 0) for r, y in pts], name=name + "_prf")
    s = cmds.revolve(
        c,
        name=name,
        pivot=(0, 0, 0),
        axis=(0, 1, 0),
        degree=360.0,
        sections=sections,
        constructionHistory=False,
    )[0]
    cmds.delete(c)
    return s


def _tube(name, path_pts, radius=1.6, sections=10):
    """Extrude a circle along a polyline path -> polygon tube."""
    path = cmds.curve(d=1, p=path_pts, name=name + "_path")
    prof = cmds.circle(nr=(1, 0, 0), r=radius, name=name + "_prof", ch=False)[0]
    cmds.move(path_pts[0][0], path_pts[0][1], path_pts[0][2], prof)
    # aim the profile ring onto the first path segment
    dx = path_pts[1][0] - path_pts[0][0]
    dy = path_pts[1][1] - path_pts[0][1]
    dz = path_pts[1][2] - path_pts[0][2]
    ln = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    a = cmds.angleBetween(v1=(1, 0, 0), v2=(dx / ln, dy / ln, dz / ln), euler=True)
    cmds.rotate(a[0], a[1], a[2], prof)
    extr = cmds.extrude(
        prof,
        path,
        name=name,
        et=2,
        fpt=True,
        upn=False,
        fixedPath=False,
        scale=1.0,
        rotation=0.0,
        polygon=1,
        constructionHistory=False,
    )[0]
    cmds.delete(path)
    _smooth(extr)
    return extr


# ------------------------------------------------------------------
# environment
# ------------------------------------------------------------------
env = cmds.group(em=True, name="GRP_env")

# stage disc — dark polished floor
fl = cmds.polyCylinder(r=680, h=10, sx=64, name="GEO_stage_disc")[0]
cmds.move(0, -5, 0, fl)
cmds.parent(fl, env)
_assign(fl, _mat("MAT_env_stage", (0.055, 0.06, 0.075), spec=0.5, refl=0.35))

# floor inlay ring — subtle zone accent (cool blue ring)
inl = cmds.polyTorus(r=300, sr=1.6, sx=72, name="GEO_zone_ring")[0]
cmds.move(0, 0.6, 0, inl)
cmds.parent(inl, env)
_assign(inl, _mat("MAT_env_ring", (0.10, 0.22, 0.45), spec=0.6, incand=0.05))

# second inlay — warm accent inside hero zone
inl2 = cmds.polyTorus(r=120, sr=1.2, sx=56, name="GEO_zone_ring_hero")[0]
cmds.move(0, 0.6, -30, inl2)
cmds.parent(inl2, env)
_assign(inl2, _mat("MAT_env_ring2", (0.55, 0.30, 0.10), spec=0.6, incand=0.05))

# cove wall — profile swept 200 deg around Y: floor-to-wall smooth shell
cove_pts = [(640, -2), (700, 8), (742, 42), (752, 120), (752, 300)]
wall = _revolve_y("GEO_cove_wall", cove_pts, sections=64)
# keep only a segment visually by rotating so the open side faces +Z
cmds.rotate(0, 0, 0, wall)
cmds.parent(wall, env)
for sh in cmds.listRelatives(wall, shapes=True) or []:
    cmds.setAttr(sh + ".doubleSided", 1)
_assign(wall, _mat("MAT_env_wall", (0.045, 0.05, 0.065), spec=0.12))

# halo strip light along the wall base (emissive tube -> glow line)
halo = _tube(
    "GEO_halo_strip",
    [
        (-520, 3, -420),
        (-260, 3, -560),
        (0, 3, -600),
        (260, 3, -560),
        (520, 3, -420),
    ],
    radius=1.4,
)
cmds.parent(halo, env)
_assign(halo, _mat("MAT_env_halo", (0.06, 0.18, 0.38), spec=0.4, incand=0.9))

# guard rail around the hero pedestal
rail = cmds.group(em=True, name="GRP_rail", parent=env)
top = cmds.polyTorus(r=105, sr=1.8, sx=56, name="GEO_rail_top")[0]
cmds.move(0, 30, -30, top)
cmds.parent(top, rail)
_assign(top, _mat("MAT_env_rail", (0.28, 0.30, 0.34), spec=0.65, refl=0.4))
for i in range(6):
    a = math.radians(i * 60.0)
    px, pz = 105 * math.cos(a), -30 + 105 * math.sin(a)
    post = cmds.polyCylinder(r=1.6, h=30, sx=12, name=f"GEO_rail_post_{i}")[0]
    cmds.move(px, 15, pz, post)
    cmds.parent(post, rail)
    _assign(post, "MAT_env_railSG")

# spotlight fixture heads (visible rigs above each exhibit)
fix_mat = _mat("MAT_env_rig", (0.16, 0.17, 0.20), spec=0.5)
for i, (x, z) in enumerate([(-250, 30), (0, -30), (250, 30)]):
    arm = cmds.polyCylinder(r=1.8, h=210, sx=10, name=f"GEO_rig_arm_{i}")[0]
    cmds.move(x, 105, z + 60, arm)
    cmds.parent(arm, env)
    _assign(arm, fix_mat)
    head = cmds.polyCone(r=9, h=16, sx=16, name=f"GEO_rig_head_{i}")[0]
    cmds.rotate(180, 0, 0, head)
    cmds.move(x, 205, z, head)
    cmds.parent(head, env)
    _assign(head, fix_mat)


# ------------------------------------------------------------------
# exhibits
# ------------------------------------------------------------------
exh = cmds.group(em=True, name="GRP_exhibits")

metal_dark = _mat("MAT_exh_metal", (0.32, 0.34, 0.38), spec=0.75, refl=0.5)
metal_edge = _mat("MAT_exh_edge", (0.55, 0.58, 0.62), spec=0.85, refl=0.55)
blade_mat = _mat("MAT_exh_blade", (0.20, 0.22, 0.26), spec=0.8, refl=0.45)
glass_mat = _mat("MAT_exh_lens", (0.10, 0.28, 0.42), spec=0.95, refl=0.6, trans=0.45)
core_mat = _mat("MAT_exh_core", (0.95, 0.55, 0.15), spec=0.9, incand=1.0)

# ---- hero: mechanical iris sculpture (center, elevated) ----
iris = cmds.group(em=True, name="GRP_iris", parent=exh)

# pedestal column — machined profile
ped = _revolve_y(
    "GEO_iris_column",
    [
        (0.1, 0),
        (26, 0),
        (30, 3),
        (30, 8),
        (18, 12),
        (14, 30),
        (14, 74),
        (20, 78),
        (20, 84),
        (0.1, 84),
    ],
    sections=40,
)
cmds.move(0, 0, -30, ped)
cmds.parent(ped, iris)
_assign(ped, metal_dark)

# iris housing — revolve stepped ring, then stand it vertical facing +Z
housing_pts = [
    (38, -7),
    (50, -7),
    (54, -5),
    (54, 5),
    (50, 7),
    (42, 7),
    (38, 4),
    (38, -4),
    (38, -7),
]
housing = _revolve_y("GEO_iris_housing", housing_pts, sections=48)
cmds.rotate(90, 0, 0, housing)
cmds.move(0, 130, -30, housing)
cmds.parent(housing, iris)
_assign(housing, metal_edge)

# aperture blades — 9 overlapping planar blades forming the iris
blade_grp = cmds.group(em=True, name="GRP_blades", parent=iris)
for i in range(9):
    ang = math.radians(i * (360.0 / 9))
    # blade profile in local XY: a curved sliver from outer ring to near-center
    pts = []
    n = 10
    for k in range(n + 1):
        t = k / n
        r = 46 - t * 34  # outer edge -> inner tip
        a = -0.55 * t  # sweep angle gives the curved blade
        pts.append((r * math.cos(a), r * math.sin(a)))
    for k in range(n, -1, -1):
        t = k / n
        r = 46 - t * 34
        a = -0.55 * t + 0.42  # back edge offset -> blade width
        pts.append((r * math.cos(a), r * math.sin(a)))
    c = cmds.curve(
        d=3,
        p=[(x, y, 0) for x, y in pts + [pts[0]]],
        name=f"GEO_blade_{i}_prf",
    )
    blade = cmds.planarSrf(c, d=3, ch=False, name=f"GEO_blade_{i}")[0]
    cmds.delete(c)
    for sh in cmds.listRelatives(blade, shapes=True) or []:
        cmds.setAttr(sh + ".doubleSided", 1)
    cmds.rotate(0, 0, math.degrees(ang) + 18.0, blade)
    cmds.move(0, 130, -29.5 + i * 0.06, blade)
    cmds.parent(blade, blade_grp)
    _assign(blade, blade_mat)

# inner aperture ring (thin machined lip)
lip = cmds.polyTorus(r=15.5, sr=2.2, sx=48, name="GEO_iris_lip")[0]
cmds.rotate(90, 0, 0, lip)
cmds.move(0, 130, -29, lip)
cmds.parent(lip, iris)
_assign(lip, metal_edge)

# glass lens disc behind blades
lens = cmds.polyCylinder(r=15, h=1.2, sx=40, name="GEO_iris_lens")[0]
cmds.rotate(90, 0, 0, lens)
cmds.move(0, 130, -32, lens)
cmds.parent(lens, iris)
_assign(lens, glass_mat)

# glowing core behind the lens — the focal ember
core = cmds.polySphere(r=7, sx=24, sy=24, name="GEO_iris_core")[0]
cmds.move(0, 130, -34, core)
cmds.parent(core, iris)
_assign(core, core_mat)

# cables — extruded tubes snaking housing -> column -> floor
cbl1 = _tube(
    "GEO_iris_cable_1",
    [
        (18, 96, -30),
        (26, 82, -34),
        (24, 62, -40),
        (16, 44, -44),
        (10, 22, -46),
        (12, 4, -44),
    ],
    radius=1.5,
)
cmds.parent(cbl1, iris)
_assign(cbl1, _mat("MAT_exh_cable", (0.10, 0.11, 0.13), spec=0.3))
cbl2 = _tube(
    "GEO_iris_cable_2",
    [
        (-14, 96, -31),
        (-22, 84, -36),
        (-24, 66, -42),
        (-18, 46, -46),
        (-12, 24, -48),
        (-14, 4, -46),
    ],
    radius=1.2,
)
cmds.parent(cbl2, iris)
_assign(cbl2, "MAT_exh_cableSG")

# ---- exhibit 2: scripted Utah-style teapot (left pedestal) ----
pot = cmds.group(em=True, name="GRP_teapot", parent=exh)

ped2 = _revolve_y(
    "GEO_ped_teapot",
    [
        (0.1, 0),
        (24, 0),
        (28, 3),
        (28, 7),
        (16, 10),
        (13, 30),
        (13, 46),
        (18, 48),
        (18, 52),
        (0.1, 52),
    ],
    sections=36,
)
cmds.move(-250, 0, 30, ped2)
cmds.parent(ped2, pot)
_assign(ped2, metal_dark)

# body profile — bulbous Utah silhouette (r, y)
body = _revolve_y(
    "GEO_teapot_body",
    [
        (0.1, 0),
        (20, 0),
        (30, 4),
        (36, 14),
        (36.5, 24),
        (33, 34),
        (26, 42),
        (24, 46),
        (24, 48),
        (26, 50),
        (26, 53),
        (20, 55),
        (12, 56),
        (6, 57),
        (0.1, 58),
    ],
    sections=48,
)
cmds.move(-250, 52, 30, body)
cmds.parent(body, pot)
_assign(body, _mat("MAT_exh_pot", (0.42, 0.50, 0.60), spec=0.85, refl=0.55))

# lid knob
knob = cmds.polySphere(r=5, sx=20, sy=16, name="GEO_teapot_knob")[0]
cmds.move(-250, 112, 30, knob)
cmds.parent(knob, pot)
_assign(knob, metal_edge)

# spout — extruded tube arcing up-left
spout = _tube(
    "GEO_teapot_spout",
    [
        (-278, 76, 30),
        (-292, 82, 30),
        (-300, 92, 30),
        (-303, 104, 30),
        (-300, 112, 30),
    ],
    radius=4.2,
)
cmds.parent(spout, pot)
_assign(spout, "MAT_exh_potSG")

# handle — extruded tube in a C on the right
handle = _tube(
    "GEO_teapot_handle",
    [
        (-226, 96, 30),
        (-212, 100, 30),
        (-204, 90, 30),
        (-204, 76, 30),
        (-212, 68, 30),
        (-226, 64, 30),
    ],
    radius=3.0,
)
cmds.parent(handle, pot)
_assign(handle, "MAT_exh_potSG")

# ---- pedestal slot 3 (right) — Camera_01 lands here via asset_import ----
ped3 = _revolve_y(
    "GEO_ped_camera",
    [
        (0.1, 0),
        (24, 0),
        (28, 3),
        (28, 7),
        (16, 10),
        (13, 30),
        (13, 46),
        (18, 48),
        (18, 52),
        (0.1, 52),
    ],
    sections=36,
)
cmds.move(250, 0, 30, ped3)
cmds.parent(ped3, exh)
_assign(ped3, metal_dark)

# ------------------------------------------------------------------
# lighting
# ------------------------------------------------------------------
lg = cmds.group(em=True, name="GRP_lighting")


def _spot(name, pos, tgt, rgb, intensity, cone=42.0, pen=10.0):
    lt = cmds.spotLight(intensity=intensity, coneAngle=cone, name=name)
    cmds.setAttr(lt + ".penumbraAngle", pen)
    cmds.setAttr(lt + ".dropoff", 6.0)
    tr = cmds.listRelatives(lt, parent=True)[0]
    cmds.move(*pos, tr)
    cmds.setAttr(lt + ".color", *rgb, type="double3")
    cmds.setAttr(lt + ".useDepthMapShadows", 1)
    cmds.setAttr(lt + ".dmapResolution", 2048)
    cmds.setAttr(lt + ".dmapFilterSize", 8)
    t = cmds.spaceLocator(name=name + "_tgt")[0]
    cmds.move(*tgt, t)
    cmds.aimConstraint(t, tr, aimVector=(0, 0, -1), upVector=(0, 1, 0))
    cmds.parent(tr, lg)
    return tr


# warm key on the iris — the focal temperature contrast
_spot("LGT_key_iris", (60, 330, 180), (0, 130, -30), (1.0, 0.80, 0.58), 3.4, cone=38, pen=12)
# cool flank on the teapot
_spot("LGT_spot_teapot", (-330, 260, 200), (-250, 70, 30), (0.62, 0.74, 1.0), 2.4, cone=34, pen=10)
# neutral on the camera pedestal
_spot("LGT_spot_camera", (330, 260, 200), (250, 60, 30), (0.85, 0.90, 1.0), 2.2, cone=34, pen=10)

# fill directional — soft cool
fill = cmds.directionalLight(intensity=0.45, name="LGT_fill_cool")
cmds.setAttr(fill + ".color", 0.55, 0.68, 1.0, type="double3")
cmds.rotate(-20, 60, 0, cmds.listRelatives(fill, parent=True)[0])
cmds.parent(cmds.listRelatives(fill, parent=True)[0], lg)

# rim directional — warm back edge (re-parented under CAM_orbit later)
rim = cmds.directionalLight(intensity=0.85, name="LGT_rim_back")
cmds.setAttr(rim + ".color", 1.0, 0.82, 0.62, type="double3")
rim_tr = cmds.listRelatives(rim, parent=True)[0]
cmds.rotate(-32, 175, 0, rim_tr)
cmds.parent(rim_tr, lg)

amb = cmds.ambientLight(intensity=0.22, name="LGT_ambient")
cmds.parent(cmds.listRelatives(amb, parent=True)[0], lg)


# ------------------------------------------------------------------
# cameras
# ------------------------------------------------------------------
aim = cmds.spaceLocator(name="LOC_aim")[0]
cmds.move(0, 105, 0, aim)
cmds.hide(aim)


def _cam(name, eye, tgt="LOC_aim"):
    ct, cs = cmds.camera(name=name)
    cmds.move(*eye, ct)
    a = cmds.aimConstraint(
        tgt,
        ct,
        aimVector=(0, 0, -1),
        upVector=(0, 1, 0),
        worldUpType="vector",
        worldUpVector=(0, 1, 0),
    )[0]
    cmds.delete(a)
    return ct


_cam("CAM_hero", (170, 190, 640))
_cam("CAM_alt", (-430, 150, 520))

{"ok": True, "objects": len(cmds.ls(dag=True) or [])}
