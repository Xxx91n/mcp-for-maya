# t20 shared kit — materials / helpers / builders (Maya-side)
import math

import maya.cmds as cmds


def kill(patterns):
    for pat in patterns:
        for n in cmds.ls(pat) or []:
            try:
                cmds.delete(n)
            except Exception:
                pass


def mat(name, rgb, spec=0.3, ecc=0.18, refl=0.0, incand=0.0, trans=0.0):
    if cmds.objExists(name):
        return name + "SG"
    m = cmds.shadingNode("blinn", asShader=True, name=name)
    cmds.setAttr(m + ".color", *rgb, type="double3")
    cmds.setAttr(m + ".specularColor", spec, spec, spec, type="double3")
    cmds.setAttr(m + ".eccentricity", ecc)
    if refl:
        cmds.setAttr(m + ".reflectivity", refl)
    if incand:
        cmds.setAttr(m + ".incandescence", incand, incand, incand, type="double3")
    if trans:
        cmds.setAttr(m + ".transparency", trans, trans, trans, type="double3")
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name + "SG")
    cmds.connectAttr(m + ".outColor", sg + ".surfaceShader", f=True)
    return sg


def assign(obj, sg):
    for o in [obj] if isinstance(obj, str) else obj:
        try:
            cmds.sets(o, e=True, forceElement=sg)
        except Exception:
            pass


def smooth(mesh, angle=50):
    try:
        cmds.polySoftEdge(mesh, angle=angle, constructionHistory=False)
    except Exception:
        pass


def prism(name, pts, y0, y1, parent=None):
    """Closed XZ outline -> solid prism y0..y1 (reversed winding = +Y normal)."""
    fp = [(x, y0, z) for x, z in reversed(list(pts))]
    b = cmds.polyCreateFacet(p=fp, constructionHistory=False, name=name)[0]
    cmds.polyExtrudeFacet(b, constructionHistory=False, keepFacesTogether=True, ltz=(y1 - y0))
    cmds.delete(b, constructionHistory=True)
    if parent:
        cmds.parent(b, parent)
    return b


def cyl(name, r, h, pos, sx=24, parent=None, sg=None):
    c = cmds.polyCylinder(r=r, h=h, sx=sx, name=name)[0]
    cmds.move(pos[0], pos[1], pos[2], c)
    if parent:
        cmds.parent(c, parent)
    if sg:
        assign(c, sg)
    return c


def ring(name, r_out, r_in, y, thick, parent=None, sg=None, sx=64):
    """Flat annulus centered on origin at height y."""
    p = cmds.polyPipe(r=r_out, h=thick, t=r_out - r_in, sa=sx, sh=1, sc=1, name=name)[0]
    cmds.move(0, y, 0, p)
    smooth(p, 40)
    if parent:
        cmds.parent(p, parent)
    if sg:
        assign(p, sg)
    return p


def box(name, w, h, d, pos, parent=None, sg=None, rot=None):
    b = cmds.polyCube(w=w, h=h, d=d, name=name)[0]
    if rot:
        cmds.rotate(rot[0], rot[1], rot[2], b)
    cmds.move(pos[0], pos[1], pos[2], b)
    if parent:
        cmds.parent(b, parent)
    if sg:
        assign(b, sg)
    return b


def tube(name, path_pts, radius=1.0, parent=None, sg=None, rect=None):
    path = cmds.curve(d=1, p=path_pts, name=name + "_path")
    if rect:
        w, h = rect
        prof = cmds.curve(
            d=1,
            p=[
                (-w / 2, -h / 2, 0),
                (w / 2, -h / 2, 0),
                (w / 2, h / 2, 0),
                (-w / 2, h / 2, 0),
                (-w / 2, -h / 2, 0),
            ],
            name=name + "_prof",
        )
    else:
        prof = cmds.circle(nr=(1, 0, 0), r=radius, name=name + "_prof", ch=False)[0]
    cmds.move(path_pts[0][0], path_pts[0][1], path_pts[0][2], prof)
    dx = path_pts[1][0] - path_pts[0][0]
    dy = path_pts[1][1] - path_pts[0][1]
    dz = path_pts[1][2] - path_pts[0][2]
    ln = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    a = cmds.angleBetween(v1=(1, 0, 0), v2=(dx / ln, dy / ln, dz / ln), euler=True)
    cmds.rotate(a[0], a[1], a[2], prof)
    ex = cmds.extrude(
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
    cmds.delete(prof)
    smooth(ex)
    if parent:
        cmds.parent(ex, parent)
    if sg:
        assign(ex, sg)
    return ex


def spot(name, pos, tgt, rgb, inten, cone=40, pen=12, parent=None, shadows=True):
    lt = cmds.spotLight(intensity=inten, coneAngle=cone, name=name)
    cmds.setAttr(lt + ".penumbraAngle", pen)
    cmds.setAttr(lt + ".dropoff", 4.0)
    tr = cmds.listRelatives(lt, parent=True)[0]
    cmds.move(pos[0], pos[1], pos[2], tr)
    cmds.setAttr(lt + ".color", rgb[0], rgb[1], rgb[2], type="double3")
    if shadows:
        cmds.setAttr(lt + ".useDepthMapShadows", 1)
        cmds.setAttr(lt + ".dmapResolution", 2048)
        cmds.setAttr(lt + ".dmapFilterSize", 10)
    t = cmds.spaceLocator(name=name + "_tgt")[0]
    cmds.move(tgt[0], tgt[1], tgt[2], t)
    cmds.aimConstraint(t, tr, aimVector=(0, 0, -1), upVector=(0, 1, 0))
    if parent:
        cmds.parent(tr, parent)
        cmds.parent(t, parent)
    return tr


def cam(name, eye, tgt, fl=None):
    ct, cs = cmds.camera()
    ct = cmds.rename(ct, name)
    cs = cmds.listRelatives(ct, shapes=True)[0]
    cmds.move(eye[0], eye[1], eye[2], ct)
    a = cmds.aimConstraint(
        tgt,
        ct,
        aimVector=(0, 0, -1),
        upVector=(0, 1, 0),
        worldUpType="vector",
        worldUpVector=(0, 1, 0),
    )[0]
    cmds.delete(a)
    if fl:
        cmds.setAttr(cs + ".focalLength", fl)
    return ct, cs


def loc(name, pos, parent=None):
    t = cmds.spaceLocator(name=name)[0]
    cmds.move(pos[0], pos[1], pos[2], t)
    cmds.hide(t)
    if parent:
        cmds.parent(t, parent)
    return t


def revolve_y(name, pts, parent=None, sg=None, sections=40):
    """Lathe a (r, y) profile about +Y. Profile curve is consumed."""
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
    if parent:
        cmds.parent(s, parent)
    if sg:
        assign(s, sg)
    return s
