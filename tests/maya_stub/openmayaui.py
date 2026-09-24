"""Fake maya.api.OpenMayaUI over the stub Scene (D-027).

Models the M3dView/MImage surface the _mcp_visual module uses:
active3dView + portWidth/portHeight + getRendererName +
readColorBuffer + MImage create/pixels/flip/writeToFile.

Pixel model (D-056⑤): readColorBuffer fills the image with GL-truth —
buffer rows are TOP-DOWN (row 0 = top - live-verified on Maya
2024.0.0.4640, T-18a re-pin) and channels
are stored BGRA (MImage's de-facto order; isRGBA() reports the flag).
verticalFlip() physically reverses row order; writeToFile emits buffer
order to file rows, interpreting channels via the RGBA/BGRA marker —
so forgetting setRGBA(True) after a manual RGBA fill really does swap
R/B in the output, and skipping the flip really does produce an
upside-down PNG. The scene pattern comes from Scene.viewport_pattern
(x, y in TOP-DOWN image coords -> (r, g, b, a) floats 0..1).
"""

from __future__ import annotations

from . import runtime
from .fakeqt import png_bytes, png_pixels


def _default_pattern(x, y, w, h):
    return (90 / 255.0, 120 / 255.0, 160 / 255.0, 1.0)


class MImage:
    kByte = 1
    kFloat = 2  # real pixelType enum (callform matrix row 22)

    def __init__(self):
        self.width = 0
        self.height = 0
        self.channels = 4
        self.format = self.kByte
        self._rgba = False  # BGRA is MImage's de-facto storage order
        self._rows = None  # buffer rows, row 0 = TOP (real readback)

    def create(self, width, height, channels=4, format=kByte):
        self.width = int(width)
        self.height = int(height)
        self.channels = int(channels)
        self.format = format
        self._rows = None

    # ---- size / format introspection ----

    def getSize(self):
        return (self.width, self.height)

    def pixelType(self):
        return self.format

    def depth(self):
        return self.channels

    def isRGBA(self):
        return self._rgba

    def setRGBA(self, flag):
        """Channel-order MARKER, not a rearranger — real setRGBA()."""
        self._rgba = bool(flag)
        return self

    # ---- raw buffer access ----

    def _flat(self, cast):
        if self._rows is None:
            raise RuntimeError("MImage has no image data")
        return [cast(c) for row in self._rows for px in row for c in px]

    def pixels(self):
        """Flat byte sequence in buffer order (top-down, current order)."""
        if self.format == self.kFloat:
            return bytes(self._flat(lambda c: max(0, min(255, int(round(c * 255))))))
        return bytes(self._flat(lambda c: max(0, min(255, int(round(c))))))

    def floatPixels(self):
        """Flat float sequence in buffer order (top-down, stored order)."""
        return [float(c) for c in self._flat(float)]

    def setPixels(self, data, width, height):
        """Fill the buffer from a flat byte sequence in buffer order
        (row 0 = top); bytes are stored verbatim - the RGBA/BGRA
        marker only affects readback/writeToFile, not the fill."""
        self.width, self.height = int(width), int(height)
        self.format = self.kByte
        data = bytes(data)
        n = self.width * self.height * self.channels
        if len(data) < n:
            raise RuntimeError("setPixels data too short")
        self._rows = [
            [tuple(data[(y * self.width + x) * 4 + c] for c in range(4)) for x in range(self.width)]
            for y in range(self.height)
        ]
        return self

    def setFloatPixels(self, data, width, height, channels=4):
        self.width, self.height = int(width), int(height)
        self.channels = int(channels)
        self.format = self.kFloat
        data = list(data)
        self._rows = [
            [
                tuple(float(data[(y * self.width + x) * self.channels + c]) for c in range(4))
                for x in range(self.width)
            ]
            for y in range(self.height)
        ]
        return self

    def verticalFlip(self):
        """Physically reverse buffer row order (real MImage.verticalFlip)."""
        if self._rows is not None:
            self._rows = self._rows[::-1]
        return True

    def _fill_from_viewport(self, w, h, rgba=False):
        """GL-truth fill: top-down row order; channels BGRA by default,
        RGBA when readColorBuffer's readRGBA flag was passed (real API)."""
        sc = runtime.scene
        pattern = getattr(sc, "viewport_pattern", None) or _default_pattern
        self._rgba = bool(rgba)
        order = (0, 1, 2, 3) if rgba else (2, 1, 0, 3)
        # vp2_readback_bottom_up models a device whose readback arrives
        # row-flipped (D-082d): the buffer's row 0 is the image BOTTOM.
        ys = range(h - 1, -1, -1) if getattr(sc, "vp2_readback_bottom_up", False) else range(h)
        rows = []
        for y_top in ys:  # buffer row order: top-down unless bottom-up device
            row = []
            for x in range(w):
                ch = pattern(x, y_top, w, h)  # (r, g, b, a) top-down
                out = (ch[order[0]], ch[order[1]], ch[order[2]], ch[order[3]])
                if self.format == self.kFloat:
                    row.append(tuple(float(c) for c in out))
                else:
                    row.append(tuple(max(0, min(255, int(round(c * 255)))) for c in out))
            rows.append(row)
        self._rows = rows

    def writeToFile(self, path, outputType="png"):
        if self._rows is None:
            if self.width == 0:
                raise RuntimeError("MImage has no image data")
            # allocated but never filled — keep old uniform fill behavior
            with open(path, "wb") as fh:
                fh.write(png_bytes(self.width, self.height))
            return True
        # writeToFile emits buffer order to file rows; channels are
        # interpreted via the RGBA marker (a lie here swaps R/B out).
        rows_rgb = []
        for row in self._rows:
            out = bytearray()
            for px in row:
                if self.format == self.kFloat:
                    px = tuple(max(0, min(255, int(round(c * 255)))) for c in px)
                else:
                    px = tuple(max(0, min(255, int(c))) for c in px)
                if self._rgba:
                    r, g, b = px[0], px[1], px[2]
                else:
                    b, g, r = px[0], px[1], px[2]
                out += bytes((r, g, b))
            rows_rgb.append(bytes(out))
        with open(path, "wb") as fh:
            fh.write(png_pixels(self.width, self.height, rows_rgb))
        return True


class _ViewWidget:
    def __init__(self, w, h):
        self._w, self._h = w, h

    def width(self):
        return self._w

    def height(self):
        return self._h


class M3dView:
    kViewport2Renderer = "vp2Renderer"

    def __init__(self, scene):
        self._scene = scene

    @classmethod
    def active3dView(cls):
        if runtime.scene is None:
            raise RuntimeError("maya stub not installed")
        return cls(runtime.scene)

    def getRendererName(self):
        return self.kViewport2Renderer

    def portWidth(self):
        return self._scene.viewport_size[0]

    def portHeight(self):
        return self._scene.viewport_size[1]

    def readColorBuffer(self, img, read_rgba=False):
        # Empty image: real VP1 path sizes it to the viewport.
        if img.width == 0 or img.height == 0:
            img.create(*self._scene.viewport_size, img.channels, img.format)
        img._fill_from_viewport(img.width, img.height, read_rgba)
        return True

    def widget(self):
        return _ViewWidget(*self._scene.viewport_size)
