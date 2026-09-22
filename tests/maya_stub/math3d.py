"""Semantically-correct matrix/bbox math for the maya stub.

Mirrors OpenMaya conventions: row-major 4x4 matrices, row-vector points
(p' = p * M), translation in elements [12],[13],[14], rotation order XYZ
(Maya default rotateOrder), degrees for cmds-level APIs.

If this math is wrong the stub produces false greens — keep it honest.
"""

from __future__ import annotations

import math


class MPoint:
    """Point — real OpenMaya MPoint: len()==4, carries w, distanceTo."""

    __slots__ = ("x", "y", "z", "w")

    def __init__(self, x=0.0, y=0.0, z=0.0, w=1.0):
        if isinstance(x, MVector):
            # Real API: MPoint(MVector) pins w to 1.0 (D-056④).
            self.x, self.y, self.z, self.w = x.x, x.y, x.z, 1.0
        elif isinstance(x, MPoint):
            self.x, self.y, self.z, self.w = x.x, x.y, x.z, x.w
        elif isinstance(x, (list, tuple)):
            self.x, self.y, self.z = float(x[0]), float(x[1]), float(x[2])
            self.w = float(x[3]) if len(x) > 3 else 1.0
        else:
            self.x, self.y, self.z, self.w = float(x), float(y), float(z), float(w)

    def __len__(self):
        return 4

    def __getitem__(self, i):
        return (self.x, self.y, self.z, self.w)[i]

    def __iter__(self):
        return iter((self.x, self.y, self.z, self.w))

    def __mul__(self, m):
        """p * MMatrix (row-vector convention), or scalar scale."""
        if isinstance(m, MMatrix):
            x, y, z, w = self.x, self.y, self.z, self.w
            rx = x * m[0] + y * m[4] + z * m[8] + w * m[12]
            ry = x * m[1] + y * m[5] + z * m[9] + w * m[13]
            rz = x * m[2] + y * m[6] + z * m[10] + w * m[14]
            rw = x * m[3] + y * m[7] + z * m[11] + w * m[15]
            if rw not in (0.0, 1.0):
                rx, ry, rz = rx / rw, ry / rw, rz / rw
            return MPoint(rx, ry, rz)
        k = float(m)
        return MPoint(self.x * k, self.y * k, self.z * k, self.w)

    def __add__(self, other):
        # MPoint + MVector -> MPoint; MPoint + MPoint/seq -> MPoint.
        return MPoint(self.x + other[0], self.y + other[1], self.z + other[2])

    def __sub__(self, other):
        # Real API: MPoint - MVector -> MPoint; MPoint - MPoint -> MVector.
        if isinstance(other, MVector):
            return MPoint(self.x - other.x, self.y - other.y, self.z - other.z)
        return MVector(self.x - other[0], self.y - other[1], self.z - other[2])

    def __eq__(self, other):
        try:
            return (self.x, self.y, self.z, self.w) == (
                other[0],
                other[1],
                other[2],
                other[3],
            )
        except Exception:
            return NotImplemented

    def distanceTo(self, other):
        dx, dy, dz = self.x - other[0], self.y - other[1], self.z - other[2]
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def isEquivalent(self, other, tolerance=1.0e-5):
        return (
            abs(self.x - other[0]) <= tolerance
            and abs(self.y - other[1]) <= tolerance
            and abs(self.z - other[2]) <= tolerance
        )

    def __repr__(self):
        return f"MPoint({self.x}, {self.y}, {self.z})"


class MVector:
    """Vector — real OpenMaya MVector: len()==3, NO w, cross product.

    Deliberately NOT an MPoint subclass (D-056④): inheriting made
    isinstance/len()/w/distanceTo all lie — stub-green, real-red.
    """

    __slots__ = ("x", "y", "z")

    kTolerance = 1.0e-5

    def __init__(self, x=0.0, y=0.0, z=0.0):
        if isinstance(x, (MPoint, MVector)):
            self.x, self.y, self.z = x.x, x.y, x.z
        elif isinstance(x, (list, tuple)):
            self.x, self.y, self.z = float(x[0]), float(x[1]), float(x[2])
        else:
            self.x, self.y, self.z = float(x), float(y), float(z)

    def __len__(self):
        return 3

    def __getitem__(self, i):
        return (self.x, self.y, self.z)[i]

    def __iter__(self):
        return iter((self.x, self.y, self.z))

    def __add__(self, other):
        return MVector(self.x + other[0], self.y + other[1], self.z + other[2])

    def __sub__(self, other):
        return MVector(self.x - other[0], self.y - other[1], self.z - other[2])

    def __neg__(self):
        return MVector(-self.x, -self.y, -self.z)

    def __mul__(self, other):
        """v * v -> dot (float); v * scalar -> MVector; v * M -> MVector.

        Matrix transform honors w=0 semantics: rotation+scale apply,
        translation does NOT, and there is no perspective divide.
        """
        if isinstance(other, MVector):
            return self.x * other.x + self.y * other.y + self.z * other.z
        if isinstance(other, MMatrix):
            m = other
            x, y, z = self.x, self.y, self.z
            return MVector(
                x * m[0] + y * m[4] + z * m[8],
                x * m[1] + y * m[5] + z * m[9],
                x * m[2] + y * m[6] + z * m[10],
            )
        if isinstance(other, MPoint):
            return NotImplemented
        k = float(other)
        return MVector(self.x * k, self.y * k, self.z * k)

    def __rmul__(self, other):
        k = float(other)
        return MVector(k * self.x, k * self.y, k * self.z)

    def __truediv__(self, other):
        k = float(other)
        return MVector(self.x / k, self.y / k, self.z / k)

    def __xor__(self, other):
        """v ^ w -> cross product (real MVector operator)."""
        return MVector(
            self.y * other[2] - self.z * other[1],
            self.z * other[0] - self.x * other[2],
            self.x * other[1] - self.y * other[0],
        )

    def __eq__(self, other):
        try:
            return (self.x, self.y, self.z) == (other[0], other[1], other[2])
        except Exception:
            return NotImplemented

    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def normal(self):
        """Normalized copy (non-destructive — real MVector.normal)."""
        n = self.length()
        if n == 0.0:
            return MVector(0.0, 0.0, 0.0)
        return MVector(self.x / n, self.y / n, self.z / n)

    def normalize(self):
        n = self.length()
        if n != 0.0:
            self.x, self.y, self.z = self.x / n, self.y / n, self.z / n
        return self

    def angle(self, other):
        """Angle to other vector in radians."""
        denom = self.length() * MVector(other).length()
        if denom == 0.0:
            return 0.0
        cos_a = (self * MVector(other)) / denom
        return math.acos(max(-1.0, min(1.0, cos_a)))

    def isEquivalent(self, other, tolerance=kTolerance):
        return (
            abs(self.x - other[0]) <= tolerance
            and abs(self.y - other[1]) <= tolerance
            and abs(self.z - other[2]) <= tolerance
        )

    def isParallel(self, other, tolerance=kTolerance):
        o = MVector(other)
        denom = self.length() * o.length()
        if denom == 0.0:
            return False
        cross_len = (self ^ o).length()
        return cross_len / denom <= tolerance

    def __repr__(self):
        return f"MVector({self.x}, {self.y}, {self.z})"


def _matmul(a, b):
    """Row-major 4x4 multiply: out[r][c] = sum_k a[r][k] * b[k][c]."""
    out = [0.0] * 16
    for r in range(4):
        for c in range(4):
            out[r * 4 + c] = (
                a[r * 4 + 0] * b[0 * 4 + c]
                + a[r * 4 + 1] * b[1 * 4 + c]
                + a[r * 4 + 2] * b[2 * 4 + c]
                + a[r * 4 + 3] * b[3 * 4 + c]
            )
    return out


class MMatrix:
    """Row-major 4x4 matrix. m[i] flat indexing like OpenMaya."""

    def __init__(self, values=None):
        if values is None:
            self._m = [1.0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        else:
            assert len(values) == 16
            self._m = [float(v) for v in values]

    def __getitem__(self, i):
        return self._m[i]

    def __mul__(self, other):
        if isinstance(other, MMatrix):
            return MMatrix(_matmul(self._m, other._m))
        if isinstance(other, (MPoint, MVector)):
            return other * self
        return NotImplemented

    @property
    def translation(self):
        return (self._m[12], self._m[13], self._m[14])

    def __repr__(self):
        return f"MMatrix({self._m})"


def rotation_matrices(rx_deg, ry_deg, rz_deg):
    """Per-axis row-vector rotation matrices (degrees)."""
    rx, ry, rz = (math.radians(v) for v in (rx_deg, ry_deg, rz_deg))
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    Rx = [1, 0, 0, 0, 0, cx, sx, 0, 0, -sx, cx, 0, 0, 0, 0, 1]
    Ry = [cy, 0, -sy, 0, 0, 1, 0, 0, sy, 0, cy, 0, 0, 0, 0, 1]
    Rz = [cz, sz, 0, 0, -sz, cz, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    return Rx, Ry, Rz


def trs_matrix(t=(0, 0, 0), r=(0, 0, 0), s=(1, 1, 1)) -> MMatrix:
    """Maya local matrix: row-vector p * S * Rx * Ry * Rz * T."""
    S = [s[0], 0, 0, 0, 0, s[1], 0, 0, 0, 0, s[2], 0, 0, 0, 0, 1]
    T = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, t[0], t[1], t[2], 1]
    Rx, Ry, Rz = rotation_matrices(*r)
    return MMatrix(_matmul(_matmul(_matmul(_matmul(S, Rx), Ry), Rz), T))


def euler_from_matrix(m) -> tuple:
    """Extract XYZ-order euler (degrees) from row-vector rotation matrix.

    Rows are normalized first to strip uniform/non-uniform scale.
    For R = Rx*Ry*Rz: ry = asin(-R[0][2]), rx = atan2(R[1][2], R[2][2]),
    rz = atan2(R[0][1], R[0][0]).
    """
    rows = []
    for r in range(3):
        v = [m[r * 4 + c] for c in range(3)]
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        rows.append([x / n for x in v])
    ry = math.asin(max(-1.0, min(1.0, -rows[0][2])))
    rx = math.atan2(rows[1][2], rows[2][2])
    rz = math.atan2(rows[0][1], rows[0][0])
    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))


class MBoundingBox:
    """Axis-aligned box; empty until expand() is called."""

    __slots__ = ("min", "max")

    def __init__(self, min_point=None, max_point=None):
        if min_point is None:
            self.min = MPoint(float("inf"), float("inf"), float("inf"))
            self.max = MPoint(float("-inf"), float("-inf"), float("-inf"))
        else:
            self.min = MPoint(*min_point[:3])
            self.max = MPoint(*max_point[:3])

    def expand(self, p):
        mn = [self.min.x, self.min.y, self.min.z]
        mx = [self.max.x, self.max.y, self.max.z]
        for i in range(3):
            mn[i] = min(mn[i], p[i])
            mx[i] = max(mx[i], p[i])
        self.min = MPoint(*mn)
        self.max = MPoint(*mx)

    @property
    def is_empty(self):
        return self.min.x > self.max.x

    def _corners(self):
        """The 8 bbox corners — the ONLY correct way to get a world AABB.

        Stub-internal helper: real MBoundingBox has no corners() API, so
        this stays private to keep the signature audit honest (D-049b)."""
        out = []
        for i in range(8):
            out.append(
                MPoint(
                    self.min.x if i & 1 else self.max.x,
                    self.min.y if i & 2 else self.max.y,
                    self.min.z if i & 4 else self.max.z,
                )
            )
        return out

    def __repr__(self):
        return f"MBoundingBox(min={self.min}, max={self.max})"
