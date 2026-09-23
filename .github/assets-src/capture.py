"""T-19c capture pass — runs the whole asset set through the
product MCP tools against a live Maya GUI session.

Usage: python .github/assets-src/capture.py

Emits:
  .scratch/t19/final/hero.png            render_preview CAM_hero1 (no HUD)
  .scratch/t19/final/shot-hero.png       viewport snapshot, persp @ hero pose
  .scratch/t19/final/shot-alt.png        viewport snapshot, persp @ alt pose
  .scratch/t19/final/orbit.gif           48f CAM_orbit playblast -> gif
  .scratch/t19/final/social-preview.png  1280x640 CAM_alt1 frame
  .scratch/t19/final/row1..row4*.png     prompt-table example images
  .scratch/t19/dogfood-transcript.json   per-step evidence
"""

import asyncio
import base64
import json
import sys
import time
from pathlib import Path


REPO = Path("D:/Aworker/maya/maya-mcp-server")
FINAL = REPO / ".scratch" / "t19" / "final"
FRAMES = REPO / ".scratch" / "t19" / "frames"
TRANS = REPO / ".scratch" / "t19" / "dogfood-transcript.json"

_BUFS = {}


async def read_msg(proc, timeout=240.0):
    buf = _BUFS.setdefault(proc, bytearray())

    async def _one():
        while True:
            nl = buf.find(b"\n")
            if nl >= 0:
                line = bytes(buf[:nl])
                del buf[: nl + 1]
                return line
            ch = await proc.stdout.read(65536)
            if not ch:
                return None
            buf.extend(ch)

    line = await asyncio.wait_for(_one(), timeout)
    return json.loads(line.decode("utf-8", "replace").strip()) if line else None


async def send(proc, obj):
    proc.stdin.write((json.dumps(obj) + "\n").encode())
    await proc.stdin.drain()


class S:
    def __init__(self, p):
        self.p = p
        self.rid = 0

    async def call(self, name, args, timeout=240):
        self.rid += 1
        await send(
            self.p,
            {
                "jsonrpc": "2.0",
                "id": self.rid,
                "method": "tools/call",
                "params": {"name": name, "arguments": args},
            },
        )
        return await read_msg(self.p, timeout)


def _c(r):
    if not r or "result" not in r:
        raise RuntimeError("no result: " + str(r)[:300])
    return r["result"].get("content", [])


def txt(r):
    return "\n".join(c.get("text", "") for c in _c(r) if c.get("type") == "text")


def img(r):
    for c in _c(r):
        if c.get("type") == "image":
            return base64.b64decode(c["data"])
    raise RuntimeError("no image in response: " + str([c.get("type") for c in _c(r)]))


def err(r):
    return bool(r and r.get("result", {}).get("isError"))


POSE = """
import maya.cmds as cmds
eye = __EYE__
tgt = __TGT__
cmds.move(eye[0], eye[1], eye[2], 'persp')
a = cmds.aimConstraint(tgt, 'persp', aimVector=(0,0,-1), upVector=(0,1,0),
                       worldUpType='vector', worldUpVector=(0,1,0))[0]
cmds.delete(a)
cmds.select(clear=True)
{'posed': eye}
"""


def pose(eye, tgt):
    return POSE.replace("__EYE__", eye).replace("__TGT__", tgt)


LOCATORS = """
import maya.cmds as cmds
for name, pos in [('LOC_teapot', (-250, 85, 30)), ('LOC_camera', (250, 70, 30))]:
    if not cmds.objExists(name):
        t = cmds.spaceLocator(name=name)[0]
        cmds.move(pos[0], pos[1], pos[2], t)
        cmds.hide(t)
{'locators': 'ok'}
"""

VIOLATE = """
import maya.cmds as cmds
# deliberate audit violations: default name, orphan, overlap
b = cmds.polyCube(w=60, h=60, d=60)[0]          # pCubeN default name
cmds.move(40, 30, 30, b)
bad2 = cmds.polySphere(r=25)[0]                  # pSphereN default name
cmds.move(55, 30, 30, bad2)                      # overlaps the cube
grp = cmds.group(em=True)                        # unnamed empty group
{'violations': 'injected'}
"""

FIX = """
import maya.cmds as cmds
# fix: rename + group + separate the overlap
if cmds.objExists('pCube1'):
    cmds.rename('pCube1', 'GEO_marker_block')
if cmds.objExists('pSphere1'):
    cmds.rename('pSphere1', 'GEO_marker_sphere')
if cmds.objExists('GEO_marker_sphere'):
    cmds.move(140, 30, 30, 'GEO_marker_sphere')
if cmds.objExists('group1'):
    cmds.delete('group1')
for n in ['GEO_marker_block', 'GEO_marker_sphere']:
    if cmds.objExists(n):
        cmds.parent(n, 'GRP_env')
cmds.select(clear=True)
{'fixed': True}
"""


async def snap_to(s, out, max_size=1400):
    r = await s.call("scene_viewport_snapshot", {"max_size": max_size, "format": "png"}, 300)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(img(r))
    return {"file": out.name, "bytes": out.stat().st_size, "isError": err(r)}


async def frame_to(s, cam, out, w, h):
    r = await s.call(
        "scene_render_preview",
        {"camera": cam, "width": w, "height": h, "format": "png", "max_size": 1600},
        300,
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(img(r))
    return {"file": out.name, "bytes": out.stat().st_size, "isError": err(r)}


async def exec_code(s, code, timeout=240):
    r = await s.call("execute_code", {"code": code, "result_type": "JSON"}, timeout)
    return {"isError": err(r), "text": txt(r)[:600]}


async def main():
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "maya_mcp_server",
        cwd=str(REPO),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={
            "PATH": "D:/DevTools/Python/runtimes/pythoncore-3.11-64",
            "PYTHONPATH": str(REPO / "src"),
            "SYSTEMROOT": "C:/Windows",
        },
    )
    tr = {"steps": {}, "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        s = S(proc)
        await send(
            proc,
            {
                "jsonrpc": "2.0",
                "id": 0,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "dogfood-t19c", "version": "0.2"},
                },
            },
        )
        init = await read_msg(proc)
        await send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        tr["steps"]["initialize"] = {"server": (init or {}).get("result", {}).get("serverInfo")}

        # 1) hero render (no HUD)
        tr["steps"]["hero"] = await frame_to(s, "CAM_hero1", FINAL / "hero.png", 1280, 720)

        # 2) HUD snapshots at two poses
        await exec_code(s, POSE.replace("__EYE__", "(60,165,355)").replace("__TGT__", "'LOC_iris'"))
        tr["steps"]["shot_hero"] = await snap_to(s, FINAL / "shot-hero.png")
        await exec_code(
            s, POSE.replace("__EYE__", "(-480,210,560)").replace("__TGT__", "'LOC_wide'")
        )
        tr["steps"]["shot_alt"] = await snap_to(s, FINAL / "shot-alt.png")

        # 3) social preview 1280x640 real frame
        tr["steps"]["social"] = await frame_to(
            s, "CAM_alt1", FINAL / "social-preview.png", 1280, 640
        )

        # 4) orbit gif frames
        FRAMES.mkdir(parents=True, exist_ok=True)
        frames = []
        for f in range(1, 49):
            await exec_code(s, f"import maya.cmds as cmds; cmds.currentTime({f}, edit=True)")
            fp = FRAMES / f"orbit-{f:02d}.png"
            res = await frame_to(s, "CAM_orbit", fp, 640, 360)
            frames.append(res)
        tr["steps"]["orbit_frames"] = {
            "count": len(frames),
            "bytes": sum(f["bytes"] for f in frames),
        }
        try:
            from PIL import Image

            ims = [Image.open(FRAMES / f"orbit-{f:02d}.png") for f in range(1, 49)]
            ims[0].save(
                FINAL / "orbit.gif",
                save_all=True,
                append_images=ims[1:],
                duration=130,
                loop=0,
            )
            tr["steps"]["orbit_gif"] = {
                "file": "orbit.gif",
                "bytes": (FINAL / "orbit.gif").stat().st_size,
                "seconds": round(48 * 0.13, 1),
            }
        except Exception as e:
            tr["steps"]["orbit_gif"] = {"error": str(e)}

        # 5) prompt-table example images
        tr["steps"]["row1"] = await frame_to(s, "CAM_hero1", FINAL / "row1-showroom.png", 960, 540)
        await exec_code(s, LOCATORS)
        # row2: teapot closeup via persp pose + snapshot
        await exec_code(
            s, POSE.replace("__EYE__", "(-120,150,270)").replace("__TGT__", "'LOC_teapot'")
        )
        tr["steps"]["row2"] = await snap_to(s, FINAL / "row2-teapot.png")
        # row3: imported camera closeup
        await exec_code(
            s, POSE.replace("__EYE__", "(380,140,300)").replace("__TGT__", "'LOC_camera'")
        )
        tr["steps"]["row3"] = await snap_to(s, FINAL / "row3-camera.png")

        # 6) audit before/after dual frame
        await exec_code(s, POSE.replace("__EYE__", "(30,120,300)").replace("__TGT__", "'LOC_aim'"))
        await exec_code(s, VIOLATE)
        tr["steps"]["row4_before"] = await snap_to(s, FINAL / "row4-audit-before.png")
        rev = await s.call("scene_review", {"detail": "compact"}, 240)
        tr["steps"]["row4_review"] = {"isError": err(rev), "text": txt(rev)[:800]}
        await exec_code(s, FIX)
        tr["steps"]["row4_after"] = await snap_to(s, FINAL / "row4-audit-after.png")
        rev2 = await s.call("scene_review", {"detail": "compact"}, 240)
        tr["steps"]["row4_review_after"] = {"isError": err(rev2), "text": txt(rev2)[:800]}

        # restore hero framing in the live viewport
        await exec_code(s, POSE.replace("__EYE__", "(60,165,355)").replace("__TGT__", "'LOC_iris'"))
        await exec_code(s, "import maya.cmds as cmds; cmds.currentTime(1, edit=True)")

        tr["verdict"] = (
            "PASS"
            if all(
                not v.get("isError")
                for v in tr["steps"].values()
                if isinstance(v, dict) and "isError" in v
            )
            else "CHECK"
        )
    finally:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), 8)
        except asyncio.TimeoutError:
            proc.kill()

    TRANS.write_text(json.dumps(tr, indent=2, default=str), encoding="utf-8")
    print(json.dumps(tr, indent=2, default=str)[:5000])
    return 0 if tr.get("verdict") == "PASS" else 1


sys.exit(asyncio.run(main()))
