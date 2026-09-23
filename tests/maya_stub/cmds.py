"""Fake maya.cmds over the stub Scene.

Implements the subset of cmds used by maya_scene_module and generated
scene_tools code. Long names, type filters, connections, keyframes,
file ops and constraints are all recorded on the Scene for assertions.
"""

from __future__ import annotations

import json
import math
import re

from . import runtime
from .scene import LIGHT_TYPES, SHAPE_TYPES


def _s():
    if runtime.scene is None:
        raise RuntimeError("maya stub not installed")
    return runtime.scene


_TYPE_FILTERS = {
    "transform": lambda n: n.type == "transform",
    "mesh": lambda n: n.type == "mesh",
    "camera": lambda n: n.type == "camera",
    "locator": lambda n: n.type == "locator",
    "nurbsCurve": lambda n: n.type == "nurbsCurve",
    "joint": lambda n: n.type == "joint",
    "light": lambda n: n.type in LIGHT_TYPES,
    "shadingEngine": lambda n: n.type == "shadingEngine",
}

_MATERIAL_TYPES = {"lambert", "phong", "blinn", "surfaceShader", "aiStandardSurface"}


def _maya_glob(pattern: str, name: str) -> bool:
    """Maya ls glob semantics, verified live on Maya 2024:
    ``*`` and ``?`` match within a namespace segment only — they never
    cross ``:``. ``ls("*x*")`` does NOT match ``ns:x``; you need
    ``ls("*:*x*")``.
    """
    rx = "".join("[^:]*" if ch == "*" else "[^:]" if ch == "?" else re.escape(ch) for ch in pattern)
    return re.fullmatch(rx, name) is not None


def ls(*args, **kwargs):
    sc = _s()
    ntype = kwargs.get("type")
    long_ = kwargs.get("long") or kwargs.get("l")
    materials = kwargs.get("materials")

    if args and isinstance(args[0], (list, tuple)):
        names = []
        for nm in args[0]:
            try:
                node = sc.resolve(nm)
            except RuntimeError:
                continue
            if materials and node.type not in _MATERIAL_TYPES:
                continue
            names.append(sc.long_name(node) if long_ else node.name)
        return names or None

    nodes = sc.all_nodes()
    patterns = [a for a in args if isinstance(a, str)]
    if patterns:
        nodes = [
            n
            for n in nodes
            if any(_maya_glob(p, n.name) or _maya_glob(p, sc.long_name(n)) for p in patterns)
        ]
    if ntype is not None:
        if isinstance(ntype, (list, tuple)):
            preds = [_TYPE_FILTERS.get(t) or (lambda n, t=t: n.type == t) for t in ntype]
            nodes = [n for n in nodes if any(p(n) for p in preds)]
        else:
            pred = _TYPE_FILTERS.get(ntype) or (lambda n: n.type == ntype)
            nodes = [n for n in nodes if pred(n)]
    if materials:
        nodes = [n for n in nodes if n.type in _MATERIAL_TYPES]

    out = [sc.long_name(n) if long_ else n.name for n in nodes]
    return out if out else None


def objExists(ref):
    sc = _s()
    ref = str(ref)
    if "." in ref:
        node_ref, attr = ref.split(".", 1)
        try:
            node = sc.resolve(node_ref)
        except RuntimeError:
            return False
        return attr.split("[")[0] in node.attrs
    return sc.exists(ref)


def nodeType(ref):
    return _s().resolve(ref).type


def objectType(ref, **kwargs):
    """cmds.objectType(ref, isAType=t): type query + ancestry check.

    DAG membership (isAType='dagNode') = transforms + shape types -
    DG nodes (materials, file textures, shadingEngines) are NOT DAG.
    """
    node = _s().resolve(ref)
    isa = kwargs.get("isAType") or kwargs.get("isa")
    if isa is None:
        return node.type
    if isa == "dagNode":
        return node.type == "transform" or node.type in SHAPE_TYPES
    return node.type == isa


def listRelatives(ref, parent=False, children=False, type=None, fullPath=False, shapes=False, **kw):
    sc = _s()
    node = sc.resolve(ref)
    if parent:
        if node.parent is None:
            return None
        return [sc.long_name(node.parent) if fullPath else node.parent.name]
    if children or shapes:
        kids = list(node.children)
        if type is not None:
            pred = _TYPE_FILTERS.get(type) or (lambda n: n.type == type)
            kids = [k for k in kids if pred(k)]
        if shapes:
            kids = [k for k in kids if k.type in SHAPE_TYPES]
        out = [sc.long_name(k) if fullPath else k.name for k in kids]
        return out if out else None
    return None


def listConnections(ref, type=None, **kwargs):
    sc = _s()
    ref = str(ref)
    node_ref, attr = ref.split(".", 1) if "." in ref else (ref, "")
    try:
        node = sc.resolve(node_ref)
    except RuntimeError:
        return None

    if attr.startswith("instObjGroups"):
        targets = []
        cand = [node] if node.type in SHAPE_TYPES else []

        def walk(n):
            for c in n.children:
                if c.type in SHAPE_TYPES:
                    cand.append(c)
                walk(c)

        walk(node)
        for c in cand:
            for t in sc.connections.get(c.name + "." + attr, []):
                if type is None or sc.resolve(t).type == type:
                    targets.append(t)
        return targets or None

    targets = sc.connections.get(node.name + "." + attr, [])
    if type is not None:
        targets = [t for t in targets if sc.resolve(t).type == type]
    return targets or None


def sets(*args, **kwargs):
    """Stub cmds.sets: create shadingEngine (renderable+empty), assign
    members (edit+forceElement), or query membership."""
    sc = _s()
    if kwargs.get("renderable") and (kwargs.get("empty") or kwargs.get("em")):
        name = kwargs.get("name") or "shadingEngine1"
        node = sc.add_node(name, "shadingEngine")
        sc.set_members.setdefault(node.name, [])
        return node.name
    if kwargs.get("edit") or kwargs.get("e"):
        sg = kwargs.get("forceElement") or kwargs.get("fe")
        if sg is None:
            return None
        sgn = sc.resolve(sg).name
        for a in args:
            node = sc.resolve(a)
            sc.set_members.setdefault(sgn, []).append(sc.long_name(node))
            sc.connections.setdefault(node.name + ".instObjGroups[0]", []).append(sgn)
        return None
    if kwargs.get("query") or kwargs.get("q"):
        return sc.set_members.get(sc.resolve(args[0]).name, []) or None
    return None


def getAttr(ref):
    sc = _s()
    node_ref, attr = str(ref).split(".", 1)
    node = sc.resolve(node_ref)
    attr = attr.split("[")[0]
    if attr in node.attrs:
        v = node.attrs[attr]
        if isinstance(v, tuple):
            return [v]
        return v
    raise RuntimeError("No attribute: " + ref)


def currentUnit(query=False, linear=False, angle=False, time=False, **kw):
    sc = _s()
    if linear:
        return sc.linear_unit
    if angle:
        return sc.angular_unit
    if time:
        return sc.time_unit
    return sc.linear_unit


def upAxis(query=False, axis=False, **kw):
    return _s().up_axis


def about(version=False, batch=False, **kw):
    if batch or kw.get("b"):
        return _s().batch
    return "2024.0-stub" if version else "MayaStub"


def file(*args, **kwargs):
    """Stub cmds.file.

    exportAll writes a REAL file (//Maya ASCII header + serialized scene)
    so checkpoint tests exercise actual disk state; open restores the
    scene graph from it and raises on non-ASCII content, like real Maya.
    """
    sc = _s()
    sc.file_calls.append({"args": args, "kwargs": dict(kwargs)})
    if kwargs.get("query") or kwargs.get("q"):
        if (
            kwargs.get("sceneName")
            or kwargs.get("sn")
            or kwargs.get("expandName")
            or kwargs.get("exn")
            or kwargs.get("absoluteName")
            or kwargs.get("an")
        ):
            return sc.scene_path
        return None
    if kwargs.get("rename"):
        # Real Maya: -rename must be used by itself — no other flags.
        if len(kwargs) > 1 or args:
            raise RuntimeError("-rename flag must be used by itself")
        sc.scene_path = kwargs["rename"]
        return sc.scene_path
    if kwargs.get("open") or kwargs.get("o"):
        path = args[0]
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if "//Maya ASCII" not in text[:2048]:
            raise RuntimeError(f"Cannot open {path}: not a Maya ASCII file")
        sc.restore(json.loads(text.split("\n", 1)[1]))
        sc.scene_path = path
        return sc.scene_path
    if kwargs.get("i") or kwargs.get("import"):
        # FBX import: materialize the test fixture as real scene nodes.
        # fbx_fixture_error simulates a corrupt/damaged file (real Maya
        # raises on unreadable FBX); a None fixture imports nothing.
        if sc.fbx_fixture_error:
            raise RuntimeError(sc.fbx_fixture_error)
        fx = sc.fbx_fixture or {}
        created = []
        mat_nodes = {}
        for ms in fx.get("materials", []):
            mat = sc.add_node(ms["name"], ms.get("type", "phong"))
            sg = sc.add_node(ms["name"] + "SG", "shadingEngine")
            sc.connections[sg.name + ".surfaceShader"] = [mat.name]
            sc.set_members.setdefault(sg.name, [])
            mat_nodes[ms["name"]] = (mat, sg)
            created += ["|" + mat.name, "|" + sg.name]
        for ms in fx.get("meshes", []):
            tr = sc.add_mesh(ms["name"], num_polygons=ms.get("faces", 6))
            shape = tr.children[0]
            created += [sc.long_name(tr), sc.long_name(shape)]
            mref = ms.get("material")
            if mref in mat_nodes:
                sg = mat_nodes[mref][1]
                sc.connections.setdefault(shape.name + ".instObjGroups[0]", []).append(sg.name)
                sc.set_members[sg.name].append(sc.long_name(shape))
        sc.fbx_created = created
        if kwargs.get("returnNewNodes") or kwargs.get("rnn"):
            return list(created)
        return args[0] if args else None
    if kwargs.get("exportAll"):
        path = args[0]
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("//Maya ASCII 2024 scene (stub)\n")
            fh.write(json.dumps(sc.serialize()))
        return path
    if kwargs.get("save") or kwargs.get("saveAs"):
        sc.scene_path = args[0] if args else sc.scene_path
        return sc.scene_path
    return None


def workspace(**kwargs):
    """Stub cmds.workspace — returns the scene's workspace dir."""
    sc = _s()
    if kwargs.get("query") or kwargs.get("q"):
        want_dir = (
            kwargs.get("rootDirectory")
            or kwargs.get("rd")
            or kwargs.get("directory")
            or kwargs.get("dir")
        )
        if want_dir:
            return sc.workspace_dir
    return sc.workspace_dir


def move(x, y=None, z=None, *objects, **kwargs):
    sc = _s()
    if y is None and z is None:
        x, y, z = x
    for o in objects or sc.selection:
        sc.resolve(o).t = [x, y, z]


def rotate(x, y, z, *objects, **kwargs):
    sc = _s()
    for o in objects or sc.selection:
        sc.resolve(o).r = [x, y, z]


def scale(x, y, z, *objects, **kwargs):
    sc = _s()
    for o in objects or sc.selection:
        sc.resolve(o).s = [x, y, z]


def xform(ref, query=False, q=False, ws=False, t=False, ro=False, **kw):
    sc = _s()
    node = sc.resolve(ref)
    if q or query:
        if t:
            m = sc.inclusive_matrix(node)
            return [m[12], m[13], m[14]]
        if ro:
            return list(sc.world_rotation(node))
    return None


def camera(name="camera1", focalLength=35.0, **kw):
    sc = _s()
    tr = sc.add_transform(name)
    sh = sc.add_shape(name + "Shape", "camera", tr)
    sh.attrs["focalLength"] = focalLength
    return [tr.name, sh.name]


def spaceLocator(name="locator1", **kw):
    sc = _s()
    tr = sc.add_transform(name)
    sc.add_shape(name + "Shape", "locator", tr)
    return [tr.name, tr.name + "Shape"]


def rename(ref, new_name):
    sc = _s()
    node = sc.resolve(ref)
    lst = sc.nodes.get(node.name, [])
    if node in lst:
        lst.remove(node)
        if not lst:
            del sc.nodes[node.name]
    new_name = sc._unique_name(new_name)
    node.name = new_name
    sc.nodes.setdefault(new_name, []).append(node)
    return new_name


def select(*args, **kwargs):
    sc = _s()
    flat = []
    for a in args:
        flat.extend(a if isinstance(a, (list, tuple)) else [a])
    sc.selection = flat


def aimConstraint(*args, **kwargs):
    """Record the constraint AND apply the equivalent static aim rotation.

    Real Maya evaluates constraints every refresh; the stub computes the
    same orientation once so tests can assert the camera actually aims.
    A None target raises, matching Maya.
    """
    sc = _s()
    target = args[0] if args else None
    if target is None:
        raise RuntimeError("aimConstraint: target cannot be None")
    tnode = sc.resolve(target)
    constrained = sc.resolve(args[1])
    sc.constraints.append(
        {"target": tnode.name, "constrained": constrained.name, "kwargs": dict(kwargs)}
    )
    tp = sc.world_position(tnode)
    cp = sc.world_position(constrained)
    dx, dy, dz = tp[0] - cp[0], tp[1] - cp[1], tp[2] - cp[2]
    dist_xz = math.sqrt(dx * dx + dz * dz)
    if dist_xz > 1e-9 or abs(dy) > 1e-9:
        ry = math.degrees(math.atan2(-dx, -dz))
        rx = math.degrees(math.atan2(dy, dist_xz)) if dist_xz > 1e-9 else (-90 if dy > 0 else 90)
        constrained.r = [rx, ry, 0.0]
    return [constrained.name + "_aimConstraint1"]


def currentTime(t=None, edit=False, **kw):
    sc = _s()
    if edit and t is not None:
        sc.current_time = t
    return sc.current_time


def setKeyframe(ref, attribute=None, **kw):
    _s().keyed.append((str(ref), attribute))


def keyTangent(*args, **kwargs):
    return None


def playbackOptions(min=None, max=None, **kw):
    sc = _s()
    if min is not None or max is not None:
        sc.playback_range = [
            min if min is not None else sc.playback_range[0],
            max if max is not None else sc.playback_range[1],
        ]
    return sc.playback_range


def group(*args, name="group1", **kw):
    sc = _s()
    g = sc.add_transform(name)
    for a in args:
        node = sc.resolve(a)
        if node.parent is not None:
            node.parent.children.remove(node)
        elif node in sc.roots:
            sc.roots.remove(node)
        node.parent = g
        g.children.append(node)
    return g.name


def delete(*args):
    sc = _s()
    for a in args:
        node = sc.resolve(a)
        if node.parent is not None:
            node.parent.children.remove(node)
        elif node in sc.roots:
            sc.roots.remove(node)
        lst = sc.nodes.get(node.name, [])
        if node in lst:
            lst.remove(node)
            if not lst:
                del sc.nodes[node.name]
        sc.deleted.append(node.name)


def warning(msg):
    """Maya cmds.warning — surface a non-fatal warning."""
    _s().warnings.append(str(msg))


# ---- GUI surface (D-027 stateful-fake; visual tools contract) ----


def refresh(**kw):
    _s().refresh_calls += 1


def getPanel(**kw):
    sc = _s()
    if kw.get("withFocus") or kw.get("wf"):
        return sc.focus_panel
    ptype = kw.get("type")
    if ptype is not None:
        names = [n for n, p in sc.panels.items() if p["type"] == ptype]
        return names or None
    return list(sc.panels) or None


_UI_TYPES = {"modelPanel": "modelEditor"}


def objectTypeUI(name, **kw):
    panel = _s().panels.get(str(name))
    if panel is None:
        return None
    return _UI_TYPES.get(panel["type"], panel["type"])


def lsUI(**kw):
    sc = _s()
    if kw.get("editors"):
        names = [n for n, p in sc.panels.items() if p["type"] == "modelPanel"]
        return names or None
    if kw.get("panels"):
        return list(sc.panels) or None
    return None


def modelEditor(*args, **kw):
    """Panel-registry modelEditor: edit truly mutates, query reads it back."""
    sc = _s()
    name = str(args[0]) if args else None
    if kw.get("exists") or kw.get("ex"):
        return name in sc.panels
    panel = sc.panels.get(name)
    if panel is None:
        raise RuntimeError("Object not found: " + str(name))
    if kw.get("query") or kw.get("q"):
        if kw.get("camera") or kw.get("cam"):
            return panel["camera"]
        if kw.get("activeView") or kw.get("av"):
            return panel["activeView"]
        if kw.get("withFocus") or kw.get("wf"):
            return panel["withFocus"]
        return None
    if kw.get("edit") or kw.get("e"):
        if "camera" in kw or "cam" in kw:
            panel["camera"] = sc.resolve(kw.get("camera", kw.get("cam"))).name
        if "activeView" in kw or "av" in kw:
            want = bool(kw.get("activeView", kw.get("av")))
            for p in sc.panels.values():
                p["activeView"] = False
            panel["activeView"] = want
            if want:
                sc.focus_panel = name
        return None
    return None


def modelPanel(*args, **kw):
    """Panel-registry modelPanel (D-039).

    The -camera flag forwards to the panel's editor (query/edit),
    -exists checks registry membership - mirrors the real command,
    where -camera is a modelPanel flag and -ex is a standard UI flag.
    """
    sc = _s()
    name = str(args[0]) if args else None
    if kw.get("exists") or kw.get("ex"):
        return name in sc.panels
    panel = sc.panels.get(name)
    if panel is None or panel["type"] != "modelPanel":
        raise RuntimeError("Object not found: " + str(name))
    if kw.get("query") or kw.get("q"):
        if kw.get("camera") or kw.get("cam"):
            return panel["camera"]
        return None
    if kw.get("edit") or kw.get("e"):
        if "camera" in kw or "cam" in kw:
            panel["camera"] = sc.resolve(kw.get("camera", kw.get("cam"))).name
            sc.model_panel_calls.append((name, panel["camera"]))
        return None
    if name and name not in sc.panels:
        sc.panels[name] = {
            "type": "modelPanel",
            "camera": "persp",
            "activeView": False,
            "withFocus": False,
            "width": sc.viewport_size[0],
            "height": sc.viewport_size[1],
        }
    return name


def lookThru(*args, **kw):
    """lookThru([editorName] [object]): point a view at a camera/object.

    Fidelity note (verified against the 2025 CommandsPython page): the
    official synopsis is (editor, object) but the command classifies
    the two positional args by TYPE - a panel/editor name vs a DAG
    object - so both orders work in real Maya. A single positional
    arg is the object for the active (focus) view.

    Stub deviation policy (D-039): an arg that classifies as NEITHER
    a known panel nor a DAG node records a stub_note and the call
    degrades to a no-op. Real Maya errors on unknown names - but
    hard-raising by default would also reject inputs that are legal
    on real Maya when the stub registry is intentionally sparse.
    Set scene.stub_strict = True for the real-Maya raise.
    """
    sc = _s()
    panel_name, obj = None, None
    for a in (str(x) for x in args):
        if a in sc.panels:
            if panel_name is None:
                panel_name = a
            else:
                sc.stub_note(f"lookThru: second panel arg {a!r} ignored")
        elif sc.exists(a):
            if obj is None:
                obj = a
            else:
                sc.stub_note(f"lookThru: second object arg {a!r} ignored")
        else:
            sc.stub_note(f"lookThru: {a!r} is not a panel or DAG node")
    if panel_name is None:
        panel_name = kw.get("panel", sc.focus_panel)
    if obj is None:
        obj = kw.get("camera")
    if panel_name not in sc.panels:
        sc.stub_note("Cannot find panel: " + str(panel_name))
        return
    if obj is None:
        sc.stub_note("lookThru: no object resolvable")
        return
    if not sc.exists(obj):
        sc.stub_note(f"lookThru: {obj!r} is not a DAG node")
        return
    sc.look_thru_calls.append((panel_name, obj))
    sc.panels[panel_name]["camera"] = obj


def playblast(**kw):
    """Deterministic-image playblast (D-027).

    Writes a real PNG (or a zero-byte artifact when playblast_empty
    simulates the headless silent-failure quirk). Mirrors the undo
    bug #21 timeline slam: time jumps to the playback start unless
    the caller restores it.
    """
    sc = _s()
    sc.playblast_calls.append(dict(kw))
    sc.current_time = sc.playback_range[0]
    base = kw.get("completeFilename") or kw.get("filename") or "playblast"
    path = base if base.endswith(".png") else base + ".png"
    if sc.playblast_empty:
        with open(path, "wb"):
            pass
        return path
    from .fakeqt import png_bytes

    w, h = (kw.get("widthHeight") or [640, 480])[:2]
    with open(path, "wb") as fh:
        fh.write(png_bytes(int(w), int(h)))
    return path


# ---- asset-import surface (D-075: _mcp_asset commands) ----


def pluginInfo(name, **kwargs):
    """cmds.pluginInfo(name, q=True, loaded=True) -> bool."""
    sc = _s()
    if kwargs.get("query") or kwargs.get("q"):
        if kwargs.get("loaded") or kwargs.get("l"):
            return name in sc.loaded_plugins
    return None


def loadPlugin(name, **kwargs):
    """cmds.loadPlugin - loads only if the plugin is 'available'."""
    sc = _s()
    if name not in sc.plugins_available:
        raise RuntimeError(f'Plug-in, "{name}", was not found')
    sc.loaded_plugins.add(name)
    return [name]


def shadingNode(ntype, **kwargs):
    """cmds.shadingNode - create a DG node; name kwarg honored."""
    sc = _s()
    name = kwargs.get("name") or ntype + "1"
    node = sc.add_node(name, ntype)
    return node.name


def createNode(ntype, **kwargs):
    sc = _s()
    name = kwargs.get("name") or ntype + "1"
    node = sc.add_node(name, ntype)
    return node.name


def setAttr(ref, *args, **kwargs):
    """cmds.setAttr - records the value on node.attrs."""
    sc = _s()
    node_ref, attr = str(ref).split(".", 1)
    node = sc.resolve(node_ref)
    value = args[0] if len(args) == 1 else (list(args) if args else None)
    node.attrs[attr.split("[")[0]] = value
    return None


def connectAttr(src, dst, **kwargs):
    """cmds.connectAttr - records dst -> [src_node] on the graph."""
    sc = _s()
    src_node = sc.resolve(str(src).split(".")[0])
    dst_ref = str(dst)
    dst_node_name, dst_attr = dst_ref.split(".", 1)
    sc.resolve(dst_node_name)  # raises if missing, like real Maya
    sc.connections.setdefault(dst_node_name + "." + dst_attr, []).append(src_node.name)
    return None


def disconnectAttr(src, dst, **kwargs):
    sc = _s()
    src_node = sc.resolve(str(src).split(".")[0])
    dst_ref = str(dst)
    key = dst_ref
    if key in sc.connections and src_node.name in sc.connections[key]:
        sc.connections[key].remove(src_node.name)
    return None


def polyEvaluate(ref, **kwargs):
    """cmds.polyEvaluate(node, face=True) -> polygon count of the shape."""
    sc = _s()
    node = sc.resolve(ref)
    if node.type != "mesh":
        shapes = [c for c in node.children if c.type == "mesh"]
        if not shapes:
            raise RuntimeError("No mesh under " + str(ref))
        node = shapes[0]
    if kwargs.get("face") or kwargs.get("f"):
        return node.num_polygons
    if kwargs.get("vertex") or kwargs.get("v"):
        return node.num_vertices
    return node.num_polygons


def exactWorldBoundingBox(*refs, **kwargs):
    """cmds.exactWorldBoundingBox -> [xmin,ymin,zmin,xmax,ymax,zmax]."""
    sc = _s()
    box = None
    for ref in refs:
        node = sc.resolve(ref)
        b = sc.world_bbox(node)
        if b.is_empty:
            continue
        if box is None:
            box = b
        else:
            for i, v in enumerate((b.min.x, b.min.y, b.min.z)):
                box.min = type(box.min)(
                    *[
                        min(cur, v) if j == i else cur
                        for j, cur in enumerate((box.min.x, box.min.y, box.min.z))
                    ]
                )
            for i, v in enumerate((b.max.x, b.max.y, b.max.z)):
                box.max = type(box.max)(
                    *[
                        max(cur, v) if j == i else cur
                        for j, cur in enumerate((box.max.x, box.max.y, box.max.z))
                    ]
                )
    if box is None or box.is_empty:
        return [0.0] * 6
    return [box.min.x, box.min.y, box.min.z, box.max.x, box.max.y, box.max.z]
