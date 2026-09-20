"""Rasterize SVG files to PNG via Playwright/Chromium (deterministic, local).

Usage: python rasterize.py <in.svg> <out.png> [--size N] [--bg dark|light|none]
Renders the SVG centered in a viewport sized to the SVG viewBox (or --size),
optionally on a dark/light backdrop for transparency inspection.
"""
import argparse
import pathlib
import re
import sys

from playwright.sync_api import sync_playwright


def viewbox_size(svg_text: str) -> tuple[int, int]:
    m = re.search(r'viewBox="([\d.\s-]+)"', svg_text)
    if m:
        parts = m.group(1).split()
        return int(float(parts[2])), int(float(parts[3]))
    m2 = re.search(r'width="(\d+)"[^>]*height="(\d+)"', svg_text)
    if m2:
        return int(m2.group(1)), int(m2.group(2))
    return 800, 600


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--size", type=int, default=0, help="max side px for output")
    ap.add_argument("--dpr", type=float, default=2.0, help="device scale factor")
    ap.add_argument("--bg", default="none", choices=["dark", "light", "none"])
    args = ap.parse_args()

    src = pathlib.Path(args.src).resolve()
    out = pathlib.Path(args.out).resolve()
    svg_text = src.read_text(encoding="utf-8")
    w, h = viewbox_size(svg_text)
    if args.size:
        scale = args.size / max(w, h)
        w, h = max(1, round(w * scale)), max(1, round(h * scale))

    bg_css = {"dark": "#0d1117", "light": "#ffffff", "none": "transparent"}[args.bg]
    inline = re.sub(
        r"<svg ", f'<svg style="display:block;width:{w}px;height:{h}px;" ',
        svg_text, count=1,
    )
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<style>html,body{margin:0;padding:0;background:" + bg_css + ";}</style>"
        "</head><body>" + inline + "</body></html>"
    )

    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(
            viewport={"width": w, "height": h}, device_scale_factor=args.dpr
        )
        pg.set_content(html, wait_until="load")
        pg.wait_for_timeout(150)
        out.parent.mkdir(parents=True, exist_ok=True)
        pg.screenshot(path=str(out), omit_background=(args.bg == "none"))
        b.close()
    print(f"{src.name} -> {out.name}  {w}x{h} (dpr{args.dpr:g}) bg={args.bg}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
