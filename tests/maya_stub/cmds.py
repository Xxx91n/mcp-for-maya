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
from .scene import LIGHT_TYPES, SHAPE_TYPES, _isa_family


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
    # ls(selection=True) returns the current selection (real Maya).
    if kwargs.get("selection") or kwargs.get("sl"):
        return list(sc.selection) or None
    ntype = kwargs.get("type") or kwargs.get("t")
    exact_type = kwargs.get("exactType") or kwargs.get("et")
    dag_only = kwargs.get("dagObjects") or kwargs.get("dag") or kwargs.get("do")
    dep_only = kwargs.get("dependencyNodes") or kwargs.get("dep")
    long_ = kwargs.get("long") or kwargs.get("l")
    materials = kwargs.get("materials")

    # ls(assemblies=True) returns root-level objects only (real Maya).
    if kwargs.get("assemblies") or kwargs.get("as"):
        roots = [n for n in sc.all_nodes() if n.parent is None]
        out = [sc.long_name(n) if long_ else n.name for n in roots]
        return out or None

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
    if exact_type is not None:
        exacts = {exact_type} if isinstance(exact_type, str) else set(exact_type)
        nodes = [n for n in nodes if n.type in exacts]
    if dag_only:
        nodes = [n for n in nodes if _isa_family(n, "dagNode")]
    if dep_only:
        nodes = [n for n in nodes if not _isa_family(n, "dagNode")]
    if ntype is not None:
        names_ = [ntype] if isinstance(ntype, str) else list(ntype)
        nodes = [n for n in nodes if any(_isa_family(n, t) for t in names_)]
    if materials:
        nodes = [n for n in nodes if n.type in _MATERIAL_TYPES]

    out = [sc.long_name(n) if (long_ and _isa_family(n, "dagNode")) else n.name for n in nodes]
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
    return _isa_family(node, isa)


def listRelatives(ref, parent=False, children=False, type=None, fullPath=False, shapes=False, **kw):
    sc = _s()
    node = sc.resolve(ref)
    if parent:
        if node.parent is None:
            return None
        return [sc.long_name(node.parent) if fullPath else node.parent.name]
    if kw.get("allDescendents") or kw.get("ad"):
        out = []

        def _walk(n):
            for c in n.children:
                out.append(sc.long_name(c) if fullPath else c.name)
                _walk(c)

        _walk(node)
        return out or None
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


def listConnections(*args, **kwargs):
    sc = _s()
    ref = args[0] if args else None
    type = kwargs.get("type") or kwargs.get("t")
    plugs = kwargs.get("plugs") or kwargs.get("p")
    pairs_flag = kwargs.get("connections") or kwargs.get("c")
    want_src = kwargs.get("source", kwargs.get("s", True))
    want_dst = kwargs.get("destination", kwargs.get("d", True))
    if ref is None:
        return None
    ref = str(ref)
    node_ref, attr = ref.split(".", 1) if "." in ref else (ref, "")
    try:
        node = sc.resolve(node_ref)
    except RuntimeError:
        return None

    if plugs or pairs_flag:
        # Plug-level surface (D-094): parallel plug_connections map.
        # With connections=True each pair is (plug on queried node,
        # remote plug) - matches the official "the one on the specified
        # object is given first" contract.
        if attr:
            srcs = list(sc.plug_connections.get(node.name + "." + attr, []))
            out = [s if plugs else s.split(".")[0] for s in srcs]
            if type is not None:
                out = [s for s in out if _isa_family(sc.resolve(s.split(".")[0]), type)]
            return out or None
        found = []  # (local_plug, remote_plug)
        for dst_plug, srcs in sc.plug_connections.items():
            dst_node = dst_plug.split(".")[0]
            for s_plug in srcs:
                src_node = s_plug.split(".")[0]
                if dst_node == node.name and want_src:
                    found.append((dst_plug, s_plug))
                if src_node == node.name and want_dst:
                    found.append((s_plug, dst_plug))
        if type is not None:
            found = [pr for pr in found if _isa_family(sc.resolve(pr[1].split(".")[0]), type)]
        if pairs_flag:
            flat = []
            for local, remote in found:
                flat.extend([local, remote])
            return flat or None
        return [remote for _, remote in found] or None

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
            sc.plug_connections.setdefault(node.name + ".instObjGroups[0]", []).append(
                sgn + ".dagSetMembers[0]"
            )
        return None
    if kwargs.get("query") or kwargs.get("q"):
        return sc.set_members.get(sc.resolve(args[0]).name, []) or None
    return None


def getAttr(ref, **kwargs):
    sc = _s()
    node_ref, attr = str(ref).split(".", 1)
    node = sc.resolve(node_ref)
    attr = attr.split("[")[0]
    spec = sc.attr_meta(node).get(attr)
    if spec is None:
        raise RuntimeError("No attribute: " + ref)
    if kwargs.get("type") or kwargs.get("t"):
        return spec["attr_type"]
    if kwargs.get("lock") or kwargs.get("l"):
        return spec["locked"]
    if kwargs.get("keyable") or kwargs.get("k"):
        return spec["keyable"]
    if kwargs.get("channelBox") or kwargs.get("cb"):
        return spec["keyable"] or spec["channel_box"]
    if kwargs.get("settable") or kwargs.get("se"):
        return spec["writable"] and not spec["locked"]
    if kwargs.get("asString"):
        v = node.attrs.get(attr, spec["default"])
        if spec["enum"] and isinstance(v, int) and 0 <= v < len(spec["enums"]):
            return spec["enums"][v]
        return v
    for flag in kwargs:
        sc.stub_note(f"getAttr flag {flag} unmodeled in stub")
    if attr in node.attrs:
        v = node.attrs[attr]
        if isinstance(v, tuple):
            return [v]
        return v
    # Type attrs with no stored value: trs live on Node fields, the rest
    # report their spec default (real getAttr returns defaults).
    if node.type == "transform" and attr in _TRS_VALUE_MAP:
        return _TRS_VALUE_MAP[attr](node)
    return spec["default"]


_TRS_VALUE_MAP = {
    "translate": lambda n: [tuple(n.t)],
    "translateX": lambda n: n.t[0],
    "translateY": lambda n: n.t[1],
    "translateZ": lambda n: n.t[2],
    "rotate": lambda n: [tuple(n.r)],
    "rotateX": lambda n: n.r[0],
    "rotateY": lambda n: n.r[1],
    "rotateZ": lambda n: n.r[2],
    "scale": lambda n: [tuple(n.s)],
    "scaleX": lambda n: n.s[0],
    "scaleY": lambda n: n.s[1],
    "scaleZ": lambda n: n.s[2],
}


def listAttr(*args, **kwargs):
    """cmds.listAttr - attribute listing over Scene.attr_meta (D-094).

    Models the filter-flag subset the introspection surface needs plus the
    common listing flags; unmodeled flags go through stub_note.
    """
    sc = _s()
    node = sc.resolve(args[0] if args else kwargs.get("node"))
    meta = sc.attr_meta(node)
    names = list(meta.keys())

    def flag(*ks):
        return any(kwargs.get(k) for k in ks)

    if flag("keyable", "k"):
        names = [a for a in names if meta[a]["keyable"]]
    if flag("channelBox", "cb"):
        names = [a for a in names if meta[a]["keyable"] or meta[a]["channel_box"]]
    if flag("connectable", "c"):
        names = [a for a in names if meta[a]["connectable"]]
    if flag("multi", "m"):
        names = [a for a in names if meta[a]["multi"]]
    if flag("locked", "l"):
        names = [a for a in names if meta[a]["locked"]]
    if flag("unlocked", "un"):
        names = [a for a in names if not meta[a]["locked"]]
    if flag("visible", "v"):
        names = [a for a in names if not meta[a]["hidden"]]
    if flag("hidden", "h"):
        names = [a for a in names if meta[a]["hidden"]]
    if flag("readOnly", "ro"):
        names = [a for a in names if meta[a]["readable"] and not meta[a]["writable"]]
    if flag("settable", "s"):
        names = [a for a in names if meta[a]["writable"] and not meta[a]["locked"]]
    if flag("userDefined", "ud"):
        names = [a for a in names if meta[a]["user_defined"]]
    if flag("read", "r"):
        names = [a for a in names if meta[a]["readable"]]
    if flag("write", "w"):
        names = [a for a in names if meta[a]["writable"]]
    if flag("scalar", "sc"):
        names = [a for a in names if not meta[a]["multi"] and not meta[a]["children"]]
    if flag("array", "a"):
        names = [a for a in names if meta[a]["multi"]]
    if flag("leaf", "lf"):
        names = [a for a in names if not meta[a]["children"]]
    at = kwargs.get("attributeType") or kwargs.get("at")
    if at:
        names = [a for a in names if meta[a]["attr_type"] == at]
    pat = kwargs.get("string") or kwargs.get("st")
    if pat:
        names = [a for a in names if _maya_glob(str(pat), a)]
    if flag("fullNodeName", "fnn"):
        names = [node.name + "." + a for a in names]
    known = {
        "keyable",
        "k",
        "channelBox",
        "cb",
        "connectable",
        "c",
        "multi",
        "m",
        "locked",
        "l",
        "unlocked",
        "un",
        "visible",
        "v",
        "hidden",
        "h",
        "readOnly",
        "ro",
        "settable",
        "s",
        "userDefined",
        "ud",
        "read",
        "r",
        "write",
        "w",
        "scalar",
        "sc",
        "array",
        "a",
        "leaf",
        "lf",
        "attributeType",
        "at",
        "string",
        "st",
        "fullNodeName",
        "fnn",
        "shortNames",
        "sn",
        "nodeName",
        "nn",
        "node",
        "o",
    }
    for k in kwargs:
        if k not in known:
            sc.stub_note(f"listAttr flag {k} unmodeled in stub")
    return names or None


_AQ_FLAG_MAP = {
    "exists": ("ex", lambda s: s is not None),
    "readable": ("r", lambda s: s["readable"]),
    "writable": ("w", lambda s: s["writable"]),
    "connectable": ("c", lambda s: s["connectable"]),
    "keyable": ("k", lambda s: s["keyable"]),
    "channelBox": ("cb", lambda s: s["keyable"] or s["channel_box"]),
    "multi": ("m", lambda s: s["multi"]),
    "hidden": ("h", lambda s: s["hidden"]),
    "storable": ("s", lambda s: s["storable"]),
    "indexMatters": ("im", lambda s: s["index_matters"]),
    "enum": ("e", lambda s: s["enum"]),
    "listEnum": ("le", lambda s: s["enums"] or None),
    "listChildren": ("lc", lambda s: s["children"] or None),
    "numberOfChildren": ("nc", lambda s: len(s["children"])),
    "minExists": ("mine", lambda s: s["min"] is not None),
    "minimum": ("min", lambda s: [s["min"]] if s["min"] is not None else None),
    "maxExists": ("maxe", lambda s: s["max"] is not None),
    "maximum": ("max", lambda s: [s["max"]] if s["max"] is not None else None),
    "softMinExists": ("smne", lambda s: s["smin"] is not None),
    "softMin": ("smn", lambda s: [s["smin"]] if s["smin"] is not None else None),
    "softMaxExists": ("smxe", lambda s: s["smax"] is not None),
    "softMax": ("smx", lambda s: [s["smax"]] if s["smax"] is not None else None),
    "rangeExists": ("re", lambda s: s["min"] is not None and s["max"] is not None),
    "range": ("ra", lambda s: [s["min"], s["max"]]),
    "internal": ("i", lambda s: False),
    "categories": (None, lambda s: []),
    "attributeType": ("at", lambda s: s["attr_type"]),
    "longName": ("ln", lambda s: None),
    "shortName": ("sn", lambda s: None),
    "niceName": ("nn", lambda s: None),
    "message": ("ms", lambda s: s["attr_type"] == "message"),
    "usedAsFilename": ("uaf", lambda s: False),
}


def attributeQuery(*args, **kwargs):
    """cmds.attributeQuery - per-attribute metadata over attr_meta (D-094).

    Real signature: attributeQuery('attr', node='node', flag=True[, ...]).
    Missing attrs raise like real Maya; unknown flags go to stub_note.
    """
    sc = _s()
    attr = args[0] if args else kwargs.pop("attribute", None)
    node_ref = kwargs.pop("node", kwargs.pop("nd", None))
    node = sc.resolve(node_ref)
    meta = sc.attr_meta(node)
    spec = meta.get(attr)
    results = []
    for flag, on in kwargs.items():
        if not on:
            continue
        entry = _AQ_FLAG_MAP.get(flag)
        if entry is None:
            sc.stub_note(f"attributeQuery flag {flag} unmodeled in stub")
            continue
        if spec is None and flag not in ("exists", "ex"):
            raise RuntimeError(f"attributeQuery: attribute '{attr}' not on {node.name}")
        results.append(entry[1](spec))
    if not results:
        raise RuntimeError("attributeQuery requires a query flag")
    return results[0] if len(results) == 1 else results


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
    if "modified" in kwargs or "m" in kwargs:
        # file(q, modified) -> dirty flag; file(modified=v) sets it.
        if kwargs.get("query") or kwargs.get("q"):
            return sc.modified
        sc.modified = bool(kwargs.get("modified", kwargs.get("m")))
        return None
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
    if kwargs.get("exportSelected") or kwargs.get("es"):
        # Real Maya exports the current selection; the stub resolves the
        # selection (a stale name raises, like Maya) and writes a real
        # file so size_bytes assertions stay honest.
        path = args[0]
        sel = [sc.resolve(n).name for n in sc.selection]
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("//Maya ASCII 2024 scene (stub, exportSelected)\n")
            fh.write(json.dumps({"exported": sel, "scene": sc.serialize()}))
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


def polyCube(**kw):
    """cmds.polyCube — transform + mesh shape; returns [transform].

    constructionHistory=False skips the upstream polyCube history node
    (modeled: none is ever created in the stub either way).
    """
    sc = _s()
    w = float(kw.get("w", kw.get("width", 1.0)))
    h = float(kw.get("h", kw.get("height", 1.0)))
    d = float(kw.get("d", kw.get("depth", 1.0)))
    name = kw.get("name") or kw.get("n") or "pCube1"
    tr = sc.add_mesh(
        name,
        bbox_min=(-w / 2, -h / 2, -d / 2),
        bbox_max=(w / 2, h / 2, d / 2),
        num_polygons=6,
    )
    if kw.get("constructionHistory", kw.get("ch", True)) not in (False, 0):
        sc.add_node(tr.name + "_history", "polyCube")
    return [tr.name]


def undoInfo(**kw):
    """cmds.undoInfo — undo-queue state control.

    stateWithoutFlush / state flags are recorded on the scene; the query
    form returns the current flag. Used by the VP2 probe to keep its
    disposable setup out of the user's undo queue (D-082d).
    """
    sc = _s()
    sc.undo_calls.append(dict(kw))
    if "stateWithoutFlush" in kw or "stf" in kw:
        sc.undo_enabled = bool(kw.get("stateWithoutFlush", kw.get("stf")))
    if "state" in kw:
        sc.undo_enabled = bool(kw["state"])
    if kw.get("query") or kw.get("q"):
        return sc.undo_enabled
    return None


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
        # Deleting a transform removes its whole subtree (shapes too) —
        # real Maya does not leave orphaned shape nodes behind.
        doomed = []
        stack = [node]
        while stack:
            n = stack.pop()
            doomed.append(n)
            stack.extend(n.children)
        for n in doomed:
            if n.parent is not None and n in n.parent.children:
                n.parent.children.remove(n)
            if n in sc.roots:
                sc.roots.remove(n)
            lst = sc.nodes.get(n.name, [])
            if n in lst:
                lst.remove(n)
                if not lst:
                    del sc.nodes[n.name]
            sc.deleted.append(n.name)
        sc.modified = True


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
    base = attr.split("[")[0]
    if base not in sc.attr_meta(node, dynamic=False):
        node.user_attrs.add(base)
    value = args[0] if len(args) == 1 else (list(args) if args else None)
    node.attrs[base] = value
    return None


_SCALAR_OUT_SUFFIXES = ("outColorR", "outColorG", "outColorB", "outAlpha")


def connectAttr(src, dst, **kwargs):
    """cmds.connectAttr - records dst -> [src_node] on the graph."""
    sc = _s()
    src_node = sc.resolve(str(src).split(".")[0])
    dst_ref = str(dst)
    dst_node_name, dst_attr = dst_ref.split(".", 1)
    dst_node = sc.resolve(dst_node_name)  # raises if missing, like real Maya
    # Real Maya rejects scalar -> triple connects (e.g. outColorR -> ambientColor).
    src_attr = str(src).split(".", 1)[-1]
    if src_attr in _SCALAR_OUT_SUFFIXES and isinstance(
        getattr(dst_node, "attrs", {}).get(dst_attr), tuple
    ):
        raise RuntimeError(
            f"Connection not made: '{src}' -> '{dst}'. "
            "Data types of source and destination are not compatible."
        )
    sc.connections.setdefault(dst_node_name + "." + dst_attr, []).append(src_node.name)
    sc.plug_connections.setdefault(dst_node_name + "." + dst_attr, []).append(str(src))
    return None


def disconnectAttr(src, dst, **kwargs):
    sc = _s()
    src_node = sc.resolve(str(src).split(".")[0])
    dst_ref = str(dst)
    key = dst_ref
    if key in sc.connections and src_node.name in sc.connections[key]:
        sc.connections[key].remove(src_node.name)
    if key in sc.plug_connections and str(src) in sc.plug_connections[key]:
        sc.plug_connections[key].remove(str(src))
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
