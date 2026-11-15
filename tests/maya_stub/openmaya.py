"""Fake maya.api.OpenMaya over the stub Scene."""

from __future__ import annotations

from . import runtime
from .math3d import MBoundingBox, MMatrix, MPoint, MVector
from .scene import CM_PER_UNIT, SHAPE_TYPES


class MSpace:
    kWorld = 0
    kObject = 1


class MFn:
    """Subset of MFn function-set constants used to probe a dag path."""

    kTransform = 1
    kShape = 2


class MDistance:
    """Linear length; the stored value is always internal centimetres.

    Stub subset: the conversion the scene module uses,
    MDistance(value).asUnits(MDistance.uiUnit()).
    """

    kMillimeters = 1
    kCentimeters = 2
    kMeters = 3
    kKilometers = 4
    kInches = 5
    kFeet = 6
    kYards = 7

    _UNIT_BY_NAME = {"mm": 1, "cm": 2, "m": 3, "km": 4, "in": 5, "ft": 6, "yd": 7}
    # Derived from the scene's single table so cmds and MDistance cannot drift.
    _CM_PER_UNIT = {unit: CM_PER_UNIT[name] for name, unit in _UNIT_BY_NAME.items()}

    def __init__(self, value=0.0, unit=kCentimeters):
        self.value = float(value) * MDistance._CM_PER_UNIT[unit]

    def asUnits(self, unit):
        """This length expressed in `unit`."""
        return self.value / MDistance._CM_PER_UNIT[unit]

    @staticmethod
    def uiUnit():
        """The scene's working linear unit (what cmds reports)."""
        if runtime.scene is None:
            return MDistance.kCentimeters
        return MDistance._UNIT_BY_NAME.get(runtime.scene.linear_unit, MDistance.kCentimeters)


class MDagPath:
    """Path to a DAG node: wraps a Node plus its root->node chain."""

    def __init__(self, other=None):
        if other is None:
            self._node = None
            self._path = []
        elif isinstance(other, MDagPath):
            self._node = other._node
            self._path = list(other._path)
        else:  # Node
            self._node = other
            self._path = other.path_nodes()

    @staticmethod
    def getAPathTo(node_or_path):
        if isinstance(node_or_path, MDagPath):
            return MDagPath(node_or_path)
        return MDagPath(node_or_path)

    def node(self):
        if self._node is None:
            raise RuntimeError("empty MDagPath")
        return self._node

    def inclusiveMatrix(self):
        return runtime.scene.inclusive_matrix(self.node())

    def exclusiveMatrix(self):
        return runtime.scene.exclusive_matrix(self.node())

    def hasFn(self, fn_type):
        """Only the two function sets the product asks about, both checked on
        Maya 2024: a shape path answers kShape, and a transform path answers
        kTransform *and* kShape when it owns a shape child, so kTransform is
        the reliable discriminator. Any other type answers False by choice —
        what real Maya does there is unmeasured, and a fake that says yes to
        API it does not model is the false-green direction.
        """
        node = self.node()
        if fn_type == MFn.kTransform:
            return node.type == "transform"
        if fn_type == MFn.kShape:
            return node.type in SHAPE_TYPES or any(c.type in SHAPE_TYPES for c in node.children)
        return False

    def length(self):
        return len(self._path)

    def pop(self):
        if self._path:
            self._path = self._path[:-1]
            self._node = self._path[-1] if self._path else None

    def push(self, node):
        """Extend this path by one child node (real API takes an MObject)."""
        self._path = [*self._path, node]
        self._node = node

    def childCount(self):
        return len(self.node().children)

    def child(self, i):
        """Maya 2024 API 2.0 returns an MObject from child(), not a path; the
        stub's Node stands in for it (probe: #273 GUI run saw
        "'OpenMaya.MObject' object has no attribute 'inclusiveMatrix'")."""
        return self.node().children[i]


class _NonDagNode:
    """Sentinel for a non-DAG selection item (defaultRenderLayer, time1…).

    Real MSelectionList.add("*") matches dependency-graph nodes too —
    getDagPath on those raises TypeError('item is not a DAG path'),
    the exact crash a dead iterator block caused on live Maya 2024.
    """


class MSelectionList:
    def __init__(self):
        self._nodes = []

    def add(self, name):
        if name == "*":
            self._nodes.extend(runtime.scene.all_nodes())
            self._nodes.append(_NonDagNode())  # wildcard matches non-DAG too
            return
        self._nodes.append(runtime.scene.resolve(name))

    def length(self):
        return len(self._nodes)

    def getDagPath(self, i):
        if isinstance(self._nodes[i], _NonDagNode):
            raise TypeError("item is not a DAG path")
        return MDagPath(self._nodes[i])


class MFnDagNode:
    def __init__(self, dag_or_node):
        if isinstance(dag_or_node, MDagPath):
            self._node = dag_or_node.node()
        else:
            self._node = dag_or_node

    @property
    def boundingBox(self):
        return runtime.scene.object_bbox(self._node)

    @property
    def typeName(self):
        return self._node.type

    @property
    def isIntermediateObject(self):
        return self._node.intermediate

    def name(self):
        return self._node.name

    def fullPathName(self):
        return runtime.scene.long_name(self._node)


class MFnMesh(MFnDagNode):
    @property
    def numVertices(self):
        return self._node.num_vertices

    @property
    def numPolygons(self):
        return self._node.num_polygons

    def getPoint(self, i, space=MSpace.kObject):
        node = self._node
        mn, mx = node.bbox or ((0, 0, 0), (0, 0, 0))
        corners = [
            MPoint(mn[0] if k & 1 else mx[0], mn[1] if k & 2 else mx[1], mn[2] if k & 4 else mx[2])
            for k in range(8)
        ]
        p = corners[i % 8]
        if space == MSpace.kWorld:
            p = p * runtime.scene.inclusive_matrix(node)
        return p


class MItDag:
    kBreadthFirst = 0
    kDepthFirst = 1

    def __init__(self, traversal=kDepthFirst):
        self._items = []

    def reset(self, dag=None):
        self._items = runtime.scene.all_nodes()

    def next(self):
        if self._items:
            self._items.pop(0)

    def isDone(self):
        return not self._items
