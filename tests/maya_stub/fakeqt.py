"""Fake PySide6 surface for the _mcp_visual contract tests (D-027).

Honest about *dimensions and byte contracts*, never about pixels:
QImage parses a real PNG IHDR on load, does real KeepAspectRatio fit
math on scaled(), and save() emits deterministic bytes with the
correct format magic (real zlib PNG for PNG, JFIF magic for JPEG).
"""

from __future__ import annotations

import struct
import types
import zlib


def _chunk(tag, data):
    body = tag + data
    return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def png_bytes(w, h, rgb=(90, 120, 160)):
    """Deterministic, *valid* PNG (zlib-encoded) for the given size."""
    ihdr = struct.pack(">IIBBBBB", int(w), int(h), 8, 2, 0, 0, 0)
    row = b"\x00" + bytes(rgb) * int(w)
    raw = row * int(h)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
    )


def png_pixels(w, h, rgb_rows):
    """PNG from real per-pixel RGB rows (top-down order, filter-0).

    rgb_rows: h rows of flat bytes/bytearray, each w*3 bytes (R,G,B,...).
    This is what MImage.writeToFile needs so pixel assertions can be
    honest at the stub tier (D-056⑤)."""
    w, h = int(w), int(h)
    assert len(rgb_rows) == h, f"expected {h} rows, got {len(rgb_rows)}"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    raw = b"".join(b"\x00" + bytes(row) for row in rgb_rows)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", zlib.compress(raw))
        + _chunk(b"IEND", b"")
    )


def png_decode(data):
    """Decode a filter-0 RGB/RGBA PNG -> (w, h, rows of flat RGB bytes).

    Only handles what png_pixels/png_bytes emit (color type 2 or 6,
    filter byte 0 per row) — the stub writer never emits anything else.
    """
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a png")
    pos = 8
    w = h = None
    color = None
    idat = bytearray()
    while pos < len(data):
        (ln,) = struct.unpack(">I", data[pos : pos + 4])
        tag = data[pos + 4 : pos + 8]
        body = data[pos + 8 : pos + 8 + ln]
        pos += 12 + ln
        if tag == b"IHDR":
            w, h, _depth, color, _c, _f, _i = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat.extend(body)
        elif tag == b"IEND":
            break
    if w is None:
        raise ValueError("no IHDR")
    bpp = 4 if color == 6 else 3
    raw = zlib.decompress(bytes(idat))
    stride = w * bpp
    rows = []
    off = 0
    for _ in range(h):
        filt = raw[off]
        if filt != 0:
            raise ValueError(f"unsupported PNG filter {filt} — stub only writes filter 0")
        row = raw[off + 1 : off + 1 + stride]
        if bpp == 4:
            row = b"".join(row[i : i + 3] for i in range(0, stride, 4))
        rows.append(row)
        off += 1 + stride
    return w, h, rows


def _png_size(data):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a png")
    return struct.unpack(">II", data[16:24])


def jpeg_bytes(w, h, quality=80):
    """Deterministic JFIF-magic bytes (not a real jpeg; contract layer)."""
    payload = f"FAKEJPEG w={int(w)} h={int(h)} q={int(quality)}"
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + payload.encode()


class QImage:
    """Dimension/byte-contract QImage fake.

    Carries decoded pixels when loaded from a filter-0 PNG so pixel
    content survives load -> scaled -> save (nearest-neighbor resample);
    pixel fidelity is otherwise not asserted here (D-027)."""

    def __init__(self, *args):
        self._w = 0
        self._h = 0
        self._null = True
        self._pixels = None  # top-down rows of flat RGB bytes
        if len(args) == 1 and isinstance(args[0], str):
            with open(args[0], "rb") as fh:
                data = fh.read()
            try:
                self._w, self._h, self._pixels = png_decode(data)
            except ValueError:
                self._w, self._h = _png_size(data)
            self._null = False
        elif len(args) >= 2:
            self._w, self._h = int(args[0]), int(args[1])
            self._null = False

    def isNull(self):
        return self._null

    def width(self):
        return self._w

    def height(self):
        return self._h

    def scaled(self, w, h, aspectMode=None, transformMode=None):
        """QImage.scaled(w, h, aspectRatioMode, transformMode)."""
        out = QImage()
        if aspectMode == Qt.KeepAspectRatio:
            s = min(w / self._w, h / self._h)
            out._w = max(1, round(self._w * s))
            out._h = max(1, round(self._h * s))
        else:
            out._w, out._h = int(w), int(h)
        if self._pixels is not None and (out._w, out._h) != (self._w, self._h):
            # nearest-neighbor resample keeps per-pixel content honest
            rows = []
            for y in range(out._h):
                src = self._pixels[min(self._h - 1, int(y * self._h / out._h))]
                rows.append(
                    b"".join(
                        src[min(self._w - 1, int(x * self._w / out._w)) * 3 :][:3]
                        for x in range(out._w)
                    )
                )
            out._pixels = rows
        elif self._pixels is not None:
            out._pixels = list(self._pixels)
        out._null = False
        return out

    def save(self, target, fmt=None, quality=-1):
        fmt = (fmt or "PNG").upper()
        if fmt == "PNG":
            if self._pixels is not None:
                data = png_pixels(self._w, self._h, self._pixels)
            else:
                data = png_bytes(self._w, self._h)
        else:
            data = jpeg_bytes(self._w, self._h, quality)
        if isinstance(target, str):
            with open(target, "wb") as fh:
                fh.write(data)
            return True
        if hasattr(target, "write"):
            target.write(data)
            return True
        return False


class QBuffer:
    def __init__(self):
        self._buf = bytearray()
        self._open = False

    def open(self, mode):
        self._open = True
        return True

    def write(self, data):
        self._buf.extend(bytes(data))
        return len(data)

    def close(self):
        self._open = False

    def data(self):
        return bytes(self._buf)


class QIODevice:
    class OpenModeFlag:
        WriteOnly = 2

    WriteOnly = 2


class Qt:
    class AspectRatioMode:
        IgnoreAspectRatio = 0
        KeepAspectRatio = 1
        KeepAspectRatioByExpanding = 2

    class TransformationMode:
        FastTransformation = 0
        SmoothTransformation = 1

    IgnoreAspectRatio = 0
    KeepAspectRatio = 1
    SmoothTransformation = 1


def make_pyside6():
    """Build a fake 'PySide6' module exposing QtGui.QImage/QtCore.QBuffer/Qt."""
    mod = types.ModuleType("PySide6")
    qtgui = types.ModuleType("PySide6.QtGui")
    qtcore = types.ModuleType("PySide6.QtCore")
    qtgui.QImage = QImage
    qtcore.QBuffer = QBuffer
    qtcore.QIODevice = QIODevice
    qtcore.Qt = Qt
    mod.QtGui = qtgui
    mod.QtCore = qtcore
    return mod
