"""Scene graph model backing the maya stub.

A Scene holds nodes (transforms + shapes + shading engines + materials),
a connection graph, and recorded side effects (constraints, keyframes,
file ops) that tests can assert on.
"""

from __future__ import annotations

from .math3d import MBoundingBox, MMatrix, MPoint, euler_from_matrix, trs_matrix


LIGHT_TYPES = {
    "spotLight",
    "pointLight",
    "directionalLight",
    "areaLight",
    "volumeLight",
    "ambientLight",
}
SHAPE_TYPES = LIGHT_TYPES | {"mesh", "camera", "locator", "nurbsCurve", "joint"}

# Type-defined attrs the stub seeds on creation - objExists("n.attr")
# answers like real Maya only if the type's standard attrs exist.
# Live-probe pinned (D-082e, .scratch/t21/probe-displacement.json):
# blinn carries reflectivity/specularRollOff but NO specularRoughness;
# standardSurface/aiStandardSurface carry the PBR set (base, baseColor,
# metalness, specularRoughness, specularColor, normalCamera, outColor)
# and none of the legacy color/diffuse/ambientColor/reflectivity names.
_MATERIAL_TYPES = {
    "lambert",
    "blinn",
    "phong",
    "phongE",
    "aiStandardSurface",
    "standardSurface",
    "surfaceShader",
    "StingrayPBS",
}
_COMMON_MAT_ATTRS = {
    "color": (0.5, 0.5, 0.5),
    "ambientColor": (0.0, 0.0, 0.0),
    "normalCamera": (0.0, 0.0, 1.0),
    "diffuse": 0.8,
    "outColor": (0.0, 0.0, 0.0),
}
_SPECULAR_ATTRS = {"specularRoughness": 0.5, "specularColor": (0.5, 0.5, 0.5)}
_METAL_ATTRS = {"metalness": 0.0, "baseColor": (0.5, 0.5, 0.5)}
_SG_ATTRS = {"surfaceShader": None, "displacementShader": None, "volumeShader": None}


# --- Attribute metadata model (D-094 scene-graph introspection) ---------
# Per-type attribute specs back the stub surface of cmds.listAttr,
# cmds.attributeQuery and the flag forms of cmds.getAttr. Each spec dict
# mirrors one attributeQuery facet row; values model the real Maya
# contract closely enough for contract tests (never a census).


def _aspec(attr_type, **kw):
    spec = {
        "attr_type": attr_type,
        "readable": True,
        "writable": True,
        "connectable": True,
        "keyable": False,
        "channel_box": False,
        "multi": False,
        "enum": False,
        "enums": [],
        "min": None,
        "max": None,
        "smin": None,
        "smax": None,
        "hidden": False,
        "locked": False,
        "storable": True,
        "children": [],
        "index_matters": False,
        "user_defined": False,
    }
    spec.update(kw)
    if "default" not in spec:
        spec["default"] = _default_value(attr_type)
    return spec


def _default_value(attr_type):
    if attr_type in ("double", "doubleLinear", "doubleAngle", "long", "byte", "float"):
        return 0.0
    if attr_type == "bool":
        return False
    if attr_type == "enum":
        return 0
    if attr_type in ("double3", "float3"):
        return [(0.0, 0.0, 0.0)]
    if attr_type == "string":
        return ""
    return None  # message/typed attrs carry no direct value


def _dynamic_aspec(value, user_defined):
    """Spec for node.attrs entries outside the type table."""
    if isinstance(value, bool):
        t = "bool"
    elif isinstance(value, float):
        t = "double"
    elif isinstance(value, int):
        t = "long"
    elif isinstance(value, str):
        t = "string"
    elif isinstance(value, (list, tuple)):
        t = "double3" if len(value) == 3 else "doubleArray"
    elif value is None:
        t = "message"
    else:
        t = "typed"
    return _aspec(t, keyable=user_defined, channel_box=user_defined, user_defined=user_defined)


_BASE_ATTRS = {
    "caching": _aspec("bool", hidden=True),
    "frozen": _aspec("bool", hidden=True),
    "isHistoricallyInteresting": _aspec("byte", hidden=True),
    "nodeState": _aspec("enum", hidden=True, enums=["normal", "hasNoEffect", "blocking", "dead"]),
    "binMembership": _aspec("string", hidden=True),
}


def _vec3(name):
    return _aspec("double3", keyable=True, children=[name + "X", name + "Y", name + "Z"])


_TRANSFORM_ATTRS = {
    "translate": _vec3("translate"),
    "translateX": _aspec("doubleLinear", keyable=True),
    "translateY": _aspec("doubleLinear", keyable=True),
    "translateZ": _aspec("doubleLinear", keyable=True),
    "rotate": _vec3("rotate"),
    "rotateX": _aspec("doubleAngle", keyable=True),
    "rotateY": _aspec("doubleAngle", keyable=True),
    "rotateZ": _aspec("doubleAngle", keyable=True),
    "scale": _vec3("scale"),
    "scaleX": _aspec("double", keyable=True),
    "scaleY": _aspec("double", keyable=True),
    "scaleZ": _aspec("double", keyable=True),
    "shear": _aspec("double3", keyable=True, children=["shearXY", "shearXZ", "shearYZ"]),
    "shearXY": _aspec("double", keyable=True),
    "shearXZ": _aspec("double", keyable=True),
    "shearYZ": _aspec("double", keyable=True),
    "rotatePivot": _aspec("double3", children=["rotatePivotX", "rotatePivotY", "rotatePivotZ"]),
    "rotatePivotX": _aspec("double"),
    "rotatePivotY": _aspec("double"),
    "rotatePivotZ": _aspec("double"),
    "scalePivot": _aspec("double3", children=["scalePivotX", "scalePivotY", "scalePivotZ"]),
    "scalePivotX": _aspec("double"),
    "scalePivotY": _aspec("double"),
    "scalePivotZ": _aspec("double"),
    "visibility": _aspec("bool", keyable=True, channel_box=True, default=True),
    "rotateOrder": _aspec("enum", keyable=True, enums=["xyz", "yzx", "zxy", "xzy", "yxz", "zyx"]),
    "inheritsTransform": _aspec("bool", default=True),
    "intermediateObject": _aspec("bool"),
}

_SHAPE_ATTRS = {
    "visibility": _aspec("bool", keyable=True, channel_box=True, default=True),
    "intermediateObject": _aspec("bool"),
    "ghosting": _aspec("bool"),
}

_CAMERA_ATTRS = {
    "focalLength": _aspec("double", keyable=True, min=0.0, default=35.0),
    "orthographic": _aspec("bool", keyable=True),
}

_LIGHT_ATTRS = {
    "color": _aspec("double3", keyable=True, children=["colorR", "colorG", "colorB"]),
    "colorR": _aspec("double", keyable=True, default=1.0),
    "colorG": _aspec("double", keyable=True, default=1.0),
    "colorB": _aspec("double", keyable=True, default=1.0),
    "intensity": _aspec("double", keyable=True, default=1.0),
}

_SPOTLIGHT_ATTRS = {
    "coneAngle": _aspec("double", keyable=True, min=0.5, max=179.5, default=40.0),
    "penumbraAngle": _aspec("double", keyable=True, min=-10.0, max=10.0),
    "dropoff": _aspec("double", keyable=True, min=0.0, max=255.0),
    "decayRate": _aspec("enum", keyable=True, enums=["linear", "quadratic", "cubic", "noDecay"]),
    "emitDiffuse": _aspec("bool", keyable=True, default=True),
    "emitSpecular": _aspec("bool", keyable=True, default=True),
}

_SG_ATTRS_SPEC = {
    "surfaceShader": _aspec("message"),
    "displacementShader": _aspec("message"),
    "volumeShader": _aspec("message"),
}


def _type_attrs(ntype):
    """Static per-type attribute spec table (no dynamic attrs)."""
    table = dict(_BASE_ATTRS)
    if ntype == "transform":
        table.update(_TRANSFORM_ATTRS)
    if ntype in SHAPE_TYPES:
        table.update(_SHAPE_ATTRS)
    if ntype == "camera":
        table.update(_CAMERA_ATTRS)
    if ntype in LIGHT_TYPES:
        table.update(_LIGHT_ATTRS)
    if ntype == "spotLight":
        table.update(_SPOTLIGHT_ATTRS)
    if ntype == "shadingEngine":
        table.update(_SG_ATTRS_SPEC)
    return table


# Type-family map for objectType(isAType=) / ls(type=) inherited matching
# (D-094): models the real Maya node hierarchy families the introspection
# surface needs - not the full type tree.
_TYPE_FAMILIES = {
    "dagNode": lambda n: n.type == "transform" or n.type in SHAPE_TYPES,
    "dependencyNode": lambda n: not (n.type == "transform" or n.type in SHAPE_TYPES),
    "shape": lambda n: n.type in SHAPE_TYPES,
    "light": lambda n: n.type in LIGHT_TYPES,
    "transform": lambda n: n.type == "transform",
    "lambert": lambda n: n.type in {"lambert", "blinn", "phong", "phongE"},
    "shadingEngine": lambda n: n.type == "shadingEngine",
}


def _isa_family(node, type_name):
    """isAType semantics: family membership or exact-type fallback."""
    fam = _TYPE_FAMILIES.get(type_name)
    if fam is not None:
        return fam(node)
    return node.type == type_name


class Node:
    __slots__ = (
        "scene",
        "name",
        "type",
        "parent",
        "children",
        "t",
        "r",
        "s",
        "bbox",
        "attrs",
        "intermediate",
        "num_vertices",
        "num_polygons",
        "keyframes",
        "user_attrs",
    )

    def __init__(self, scene, name, ntype, parent=None):
        self.scene = scene
        self.name = name
        self.type = ntype
        self.parent = parent
        self.children = []
        self.t = [0.0, 0.0, 0.0]
        self.r = [0.0, 0.0, 0.0]
        self.s = [1.0, 1.0, 1.0]
        self.bbox = None  # (min3, max3) object-space, shape nodes only
        self.attrs = {}
        self.intermediate = False
        self.num_vertices = 8
        self.num_polygons = 6
        self.keyframes = {}
        self.user_attrs = set()  # attrs created post-init via cmds.setAttr

    def path_nodes(self):
        """Nodes root -> self inclusive."""
        out = []
        n = self
        while n is not None:
            out.append(n)
            n = n.parent
        out.reverse()
        return out


class Scene:
    """A fake Maya scene: node table + DAG hierarchy + recorded calls."""

    def __init__(self):
        self.nodes = {}  # short name -> [Node] (dup short names possible)
        self.roots = []
        self.scene_path = ""  # cmds.file(q, sceneName)
        self.linear_unit = "cm"
        self.angular_unit = "deg"
        self.time_unit = "film"
        self.up_axis = "y"
        self.current_time = 1
        self.playback_range = [1, 120]
        self.selection = []
        self.constraints = []  # recorded aimConstraint calls
        self.connections = {}  # "node.attr" -> [target node names]
        # Plug-level wiring for the introspection surface (D-094):
        # "dst_node.dst_attr" -> ["src_node.src_attr"]. Kept parallel to
        # `connections` (node-name view) so existing callers keep their shape.
        self.plug_connections = {}
        self.set_members = {}  # shadingEngine -> [member names]
        self.keyed = []  # (node, attribute) setKeyframe calls
        self.warnings = []  # cmds.warning calls
        self.file_calls = []  # recorded cmds.file invocations
        self.deleted = []
        self.workspace_dir = ""  # cmds.workspace(q, rootDirectory)

        # ---- GUI surface (D-027 stateful-fake; visual tools contract) ----
        self.gui = True  # modelPanel-based session (batch=False GUI)
        self.batch = False  # cmds.about(batch=True)
        self.panels = {}  # name -> {type,camera,activeView,withFocus,width,height}
        self.focus_panel = None  # getPanel(withFocus=True)
        self.viewport_size = (1280, 720)  # M3dView.portWidth/portHeight
        self.look_thru_calls = []  # (panel, camera) lookThru invocations
        self.model_panel_calls = []  # (panel, camera) modelPanel camera edits
        self.stub_strict = False  # D-039: True => unclassifiable args raise like real Maya
        self.stub_notes = []  # anomalies recorded in warn (non-strict) mode
        self.playblast_calls = []  # recorded playblast kwargs
        self.playblast_empty = False  # headless quirk: silent zero-byte artifact
        self.refresh_calls = 0  # cmds.refresh invocations
        # viewport pixel source for readColorBuffer fills (D-056⑤):
        # callable(x, y, w, h) -> (r,g,b,a) floats 0..1 in TOP-DOWN image
        # coords; None => uniform gray-blue. Tests install an asymmetric
        # pattern (top-left red block) to pin flip/channel-order honesty.
        self.viewport_pattern = None
        # asset-import surface (D-075): plugin registry, MEL record,
        # and the fixture that cmds.file(i=True) materializes.
        # plug-in registry pinned to the live Maya 2024 probe (D-092):
        # fbxmaya/objExport/mayaUsdPlugin/AbcExport ship with Maya.
        self.plugins_available = {"fbxmaya", "objExport", "mayaUsdPlugin", "AbcExport"}
        self.loaded_plugins = {"fbxmaya"}  # already-loaded plug-ins
        self.mel_calls = []  # recorded maya.mel.eval invocations
        self.fbx_fixture = None  # {"meshes":[...], "materials":[...]}
        self.fbx_fixture_error = None  # truthy => import raises this

        # ---- session-state surface (D-082d: VP2 probe net-zero proof) ----
        # cmds.file(q, modified) / file(modified=v): scene-dirty flag.
        # add_node/delete mark it like real Maya; file(open)/file(save)
        # clear it. cmds.undoInfo state flags land in undo_calls.
        self.modified = False
        self.undo_enabled = True
        self.undo_calls = []  # recorded undoInfo kwargs
        # vp2_readback_bottom_up: device-level knob for tests — when True
        # readColorBuffer fills the image in BOTTOM-UP row order (models a
        # GPU/driver whose readback disagrees with the 2024 pin).
        self.vp2_readback_bottom_up = False

    def setup_gui(self):
        """Seed a stock GUI layout: four model panels + default cameras.

        Opt-in (tests call it explicitly) so legacy scenes without a
        GUI surface keep their zero-panel, headless-ish shape.
        """
        for i, cam in enumerate(("persp", "top", "front", "side"), start=1):
            self.add_camera(cam)
            self.panels["modelPanel" + str(i)] = {
                "type": "modelPanel",
                "camera": cam,
                "activeView": i == 1,
                "withFocus": i == 1,
                "width": self.viewport_size[0],
                "height": self.viewport_size[1],
            }
        self.focus_panel = "modelPanel1"

    # ---- construction helpers (test-facing API) ----

    def _unique_name(self, name):
        if name not in self.nodes:
            return name
        i = 1
        while f"{name}{i}" in self.nodes:
            i += 1
        return f"{name}{i}"

    def add_node(self, name, ntype, parent=None, exists_ok=False):
        if isinstance(parent, str):
            parent = self.resolve(parent)
        if name in self.nodes and not exists_ok:
            name = self._unique_name(name)
        node = Node(self, name, ntype, parent)
        if ntype in _MATERIAL_TYPES:
            node.attrs.update(_COMMON_MAT_ATTRS)
        if ntype in {"blinn", "phong", "phongE"}:
            node.attrs.update(_SPECULAR_ATTRS)
        if ntype == "blinn":
            # Live probe (D-082e): real blinn has reflectivity +
            # specularRollOff but NO specularRoughness/metalness/roughness.
            node.attrs.pop("specularRoughness", None)
            node.attrs["reflectivity"] = 0.5
            node.attrs["specularRollOff"] = 0.7
        if ntype in {"aiStandardSurface", "standardSurface"}:
            # Live probe (D-082e): PBR attr set only — no legacy
            # color/diffuse/ambientColor; "base" is the scalar weight
            # over baseColor that AO-style maps target.
            for legacy in ("color", "ambientColor", "diffuse"):
                node.attrs.pop(legacy, None)
            node.attrs.update(_METAL_ATTRS)
            node.attrs.update(_SPECULAR_ATTRS)
            node.attrs["base"] = 1.0
        if ntype == "shadingEngine":
            node.attrs.update(_SG_ATTRS)
        self.modified = True  # creating a node dirties the scene (real Maya)
        self.nodes.setdefault(name, []).append(node)
        if parent is not None:
            parent.children.append(node)
        else:
            self.roots.append(node)
        return node

    def add_transform(self, name, t=(0, 0, 0), r=(0, 0, 0), s=(1, 1, 1), parent=None):
        node = self.add_node(name, "transform", parent)
        node.t, node.r, node.s = list(t), list(r), list(s)
        return node

    def add_shape(self, name, ntype, parent, bbox=None, **attrs):
        node = self.add_node(name, ntype, parent)
        node.bbox = bbox
        node.attrs.update(attrs)
        return node

    def add_mesh(
        self,
        name,
        bbox_min=(-50, -50, -50),
        bbox_max=(50, 50, 50),
        t=(0, 0, 0),
        r=(0, 0, 0),
        s=(1, 1, 1),
        parent=None,
        num_vertices=8,
        num_polygons=6,
    ):
        """Create transform + mesh shape child (Maya layout). Returns transform."""
        tr = self.add_transform(name, t=t, r=r, s=s, parent=parent)
        sh = self.add_shape(name + "Shape", "mesh", tr, bbox=(bbox_min, bbox_max))
        sh.num_vertices = num_vertices
        sh.num_polygons = num_polygons
        return tr

    def add_camera(self, name, t=(0, 0, 0), r=(0, 0, 0), parent=None):
        tr = self.add_transform(name, t=t, r=r, parent=parent)
        self.add_shape(name + "Shape", "camera", tr)
        return tr

    def add_light(self, name, ltype="spotLight", t=(0, 0, 0), r=(0, 0, 0), parent=None, **attrs):
        tr = self.add_transform(name, t=t, r=r, parent=parent)
        defaults = {
            "color": (1.0, 1.0, 1.0),
            "intensity": 1.0,
            "decayRate": 0,
            "useDepthMapShadow": 1,
        }
        if ltype == "spotLight":
            defaults.update(
                {"coneAngle": 40.0, "penumbraAngle": 10.0, "emitDiffuse": 1, "emitSpecular": 1}
            )
        if ltype == "areaLight":
            defaults.update(
                {"areaWidth": 10.0, "areaHeight": 10.0, "emitDiffuse": 1, "emitSpecular": 1}
            )
        defaults.update(attrs)
        self.add_shape(name + "Shape", ltype, tr, **defaults)
        return tr

    def add_locator(self, name, t=(0, 0, 0), parent=None):
        tr = self.add_transform(name, t=t, parent=parent)
        self.add_shape(name + "Shape", "locator", tr)
        return tr

    def add_group(self, name, parent=None):
        return self.add_transform(name, parent=parent)

    def add_material(self, name, color=(0.5, 0.5, 0.5), assign_to=()):
        """Material + shadingEngine + connections, like Maya's SG wiring."""
        mat = self.add_node(name, "lambert")
        mat.attrs["color"] = tuple(color)
        sg = self.add_node(name + "SG", "shadingEngine")
        self.connections[sg.name + ".surfaceShader"] = [mat.name]
        self.plug_connections[sg.name + ".surfaceShader"] = [mat.name + ".outColor"]
        members = []
        for target in assign_to:
            node = self.resolve(target)
            shape = next((c for c in node.children if c.type in SHAPE_TYPES), node)
            self.connections.setdefault(shape.name + ".instObjGroups[0]", []).append(sg.name)
            self.plug_connections.setdefault(shape.name + ".instObjGroups[0]", []).append(
                sg.name + ".dagSetMembers[0]"
            )
            members.append(self.long_name(shape))
        self.set_members[sg.name] = members
        return mat

    # ---- resolution ----

    def resolve(self, ref):
        """Resolve a name ref (long path |a|b or short name) to a Node."""
        if isinstance(ref, Node):
            return ref
        ref = str(ref).split(".")[0]  # strip .attr
        if ref.startswith("|"):
            parts = [p for p in ref.split("|") if p]
            node = None
            level = self.roots
            for p in parts:
                node = next((n for n in level if n.name == p), None)
                if node is None:
                    raise RuntimeError(f"No object matches name: {ref}")
                level = node.children
            return node
        matches = self.nodes.get(ref)
        if not matches:
            raise RuntimeError(f"No object matches name: {ref}")
        if len(matches) > 1:
            raise RuntimeError(f"Ambiguous object name: {ref}")
        return matches[0]

    def exists(self, ref):
        try:
            self.resolve(ref)
            return True
        except RuntimeError:
            return False

    def attr_meta(self, node, dynamic=True):
        """Attribute metadata table for cmds.listAttr/attributeQuery (D-094).

        dynamic=False restricts to type-seeded attrs (static table plus
        node.attrs entries NOT marked user-defined) - used by cmds.setAttr
        to tell a user attr from a type attr.
        """
        meta = _type_attrs(node.type)
        if not dynamic:
            pool = {k: v for k, v in node.attrs.items() if k not in node.user_attrs}
        else:
            pool = node.attrs
        for name, val in pool.items():
            if name not in meta:
                meta[name] = _dynamic_aspec(val, user_defined=name in node.user_attrs)
        return meta

    def stub_note(self, msg):
        """Record an anomaly; raise it when strict mode is on (D-039)."""
        self.stub_notes.append(msg)
        if self.stub_strict:
            raise RuntimeError(msg)

    def long_name(self, node):
        return "|" + "|".join(n.name for n in node.path_nodes())

    def all_nodes(self):
        out = []

        def walk(n):
            out.append(n)
            for c in n.children:
                walk(c)

        for r in self.roots:
            walk(r)
        return out

    def transforms(self):
        return [n for n in self.all_nodes() if n.type == "transform"]

    # ---- matrices ----

    def local_matrix(self, node):
        return trs_matrix(node.t, node.r, node.s)

    def inclusive_matrix(self, node):
        """world = p * L_self * L_parent * ... * L_root (row-vector)."""
        chain = node.path_nodes()  # [root .. self]
        acc = MMatrix()
        for n in chain[::-1]:  # L_self * L_parent * ... * L_root
            acc = acc * self.local_matrix(n)
        return acc

    def world_position(self, node):
        m = self.inclusive_matrix(node)
        return (m[12], m[13], m[14])

    def world_rotation(self, node):
        return euler_from_matrix(self.inclusive_matrix(node))

    def object_bbox(self, node):
        """MFnDagNode.boundingBox: shape -> stored; transform -> union of
        descendant shape bboxes transformed into this node's local space."""
        box = MBoundingBox()
        if node.type in SHAPE_TYPES and node.bbox is not None:
            box.expand(MPoint(*node.bbox[0]))
            box.expand(MPoint(*node.bbox[1]))
            return box

        # transform: gather descendant shapes into node-local space
        def walk(n, m_to_node):
            for c in n.children:
                rel = m_to_node  # matrix mapping c-local -> node-local
                c_local = self.local_matrix(c)
                c2node = c_local * rel  # p * L_c * (rest)
                if c.type in SHAPE_TYPES and c.bbox is not None:
                    cb = MBoundingBox(*c.bbox)
                    for corner in cb._corners():
                        box.expand(corner * c2node)
                walk(c, c2node)

        walk(node, MMatrix())
        return box

    def world_bbox(self, node):
        """exactWorldBoundingBox equivalent: object_bbox corners x world."""
        box = MBoundingBox()
        local = self.object_bbox(node)
        if local.is_empty:
            return box
        m = self.inclusive_matrix(node)
        for corner in local._corners():
            box.expand(corner * m)
        return box

    # ---- persistence (stub cmds.file exportAll/open) ----

    def serialize(self):
        """Snapshot the scene graph into a JSON-able dict.

        Mirrors exportAll semantics: the *memory* state is captured, not
        whatever happens to be on disk under scene_path.
        """
        nodes = []
        for n in self.all_nodes():
            nodes.append(
                {
                    "name": n.name,
                    "type": n.type,
                    "parent": self.long_name(n.parent) if n.parent else None,
                    "t": list(n.t),
                    "r": list(n.r),
                    "s": list(n.s),
                    "bbox": [list(n.bbox[0]), list(n.bbox[1])] if n.bbox else None,
                    "attrs": {
                        k: list(v) if isinstance(v, (list, tuple)) else v
                        for k, v in n.attrs.items()
                    },
                    "intermediate": n.intermediate,
                    "num_vertices": n.num_vertices,
                    "num_polygons": n.num_polygons,
                    "keyframes": n.keyframes,
                    "user_attrs": sorted(n.user_attrs),
                }
            )
        return {
            "nodes": nodes,
            "connections": self.connections,
            "plug_connections": {k: list(v) for k, v in self.plug_connections.items()},
            "set_members": self.set_members,
            "current_time": self.current_time,
            "playback_range": list(self.playback_range),
        }

    def restore(self, data):
        """Replace scene contents with a serialized snapshot (file open).

        Nodes arrive parent-first (all_nodes() walks depth-first from
        roots), so each node's parent is already registered in by_path.
        """
        self.nodes = {}
        self.roots = []
        self.selection = []
        by_path = {}
        for nd in data["nodes"]:
            parent = by_path[nd["parent"]] if nd["parent"] else None
            node = self.add_node(nd["name"], nd["type"], parent=parent, exists_ok=True)
            node.t = list(nd["t"])
            node.r = list(nd["r"])
            node.s = list(nd["s"])
            node.bbox = (tuple(nd["bbox"][0]), tuple(nd["bbox"][1])) if nd["bbox"] else None
            node.attrs = {
                k: tuple(v) if isinstance(v, list) else v for k, v in nd.get("attrs", {}).items()
            }
            node.intermediate = nd.get("intermediate", False)
            node.num_vertices = nd.get("num_vertices", 8)
            node.num_polygons = nd.get("num_polygons", 6)
            node.keyframes = nd.get("keyframes", {})
            node.user_attrs = set(nd.get("user_attrs", []))
            path = (nd["parent"] + "|" + nd["name"]) if nd["parent"] else "|" + nd["name"]
            by_path[path] = node
        self.connections = {k: list(v) for k, v in data.get("connections", {}).items()}
        self.plug_connections = {k: list(v) for k, v in data.get("plug_connections", {}).items()}
        self.set_members = {k: list(v) for k, v in data.get("set_members", {}).items()}
        self.current_time = data.get("current_time", 1)
        self.playback_range = list(data.get("playback_range", [1, 120]))
        self.modified = False  # a freshly-opened file is clean (real Maya)
