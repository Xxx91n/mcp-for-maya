"""Fake maya.api.OpenMaya over the stub Scene."""

from __future__ import annotations

from . import runtime
from .math3d import MBoundingBox, MMatrix, MPoint, MVector


class MSpace:
    kWorld = 0
    kObject = 1


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

    def length(self):
        return len(self._path)

    def pop(self):
        if self._path:
            self._path = self._path[:-1]
            self._node = self._path[-1] if self._path else None

    def childCount(self):
        return len(self.node().children)

    def child(self, i):
        return MDagPath(self.node().children[i])


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
