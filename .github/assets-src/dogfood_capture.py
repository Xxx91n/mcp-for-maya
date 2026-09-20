"""T-15b dogfood capture: spawn a fresh MCP server (repo HEAD) over stdio,
attach to the live Maya GUI session, build a demo showcase scene, then
capture 2 real viewport snapshots + an orbit frame sequence.

Outputs:
  .github/assets/shot-hero.png, shot-alt.png        (viewport snapshots, HUD incl.)
  .scratch/facade/frames/orbit-*.png                (playblast frames for GIF)
  .scratch/facade/dogfood-transcript.json           (liveness + capture evidence)
"""
import asyncio
import base64
import json
import sys
from pathlib import Path


REPO = Path(r"D:\Aworker\maya\maya-mcp-server")
ASSETS = REPO / ".github" / "assets"
FRAMES = REPO / ".scratch" / "facade" / "frames"
TRANS = REPO / ".scratch" / "facade" / "dogfood-transcript.json"

SCENE_BUILD = r"""
import maya.cmds as cmds

for n in ["GRP_demo", "GRP_lighting", "CAM_hero", "CAM_alt",
          "CAM_orbit", "LOC_aim", "orbit_cam", "LOC_CAM_orbit_target"]:
    if cmds.objExists(n):
        try: cmds.delete(n)
        except Exception: pass
for pat in ["MAT_*", "LOC_*", "CAM_*"]:
    for n in cmds.ls(pat) or []:
        try: cmds.delete(n)
        except Exception: pass

def _mat(name, rgb, spec=0.18):
    m = cmds.shadingNode("blinn", asShader=True, name=name)
    cmds.setAttr(m+".color", rgb[0], rgb[1], rgb[2], type="double3")
    cmds.setAttr(m+".specularColor", spec, spec, spec, type="double3")
    sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=name+"SG")
    cmds.connectAttr(m+".outColor", sg+".surfaceShader", f=True)
    return sg

def _assign(obj, sg):
    cmds.sets(obj, e=True, forceElement=sg)

demo = cmds.group(em=True, name="GRP_demo")

fl = cmds.polyCylinder(r=560, h=8, sx=48, name="GEO_stage_floor")[0]
cmds.move(0, -4, 0, fl); cmds.parent(fl, demo)
_assign(fl, _mat("MAT_stage", (0.13, 0.14, 0.17)))

ring = cmds.polyTorus(r=560, sr=8, sx=48, name="GEO_ring_accent")[0]
cmds.move(0, 2, 0, ring); cmds.parent(ring, demo)
_assign(ring, _mat("MAT_ring", (0.18, 0.38, 0.60)))

sg_ped = _mat("MAT_pedestal", (0.20, 0.22, 0.26))
for i, x in enumerate([-240, 0, 240]):
    p = cmds.polyCube(w=110, h=40, d=110, name="GEO_pedestal_%d" % (i + 1))[0]
    cmds.move(x, 20, 0, p); cmds.parent(p, demo); _assign(p, sg_ped)

t = cmds.polyTorus(r=46, sr=18, name="GEO_hero_torus")[0]
cmds.move(-240, 100, 0, t); cmds.rotate(0, 0, 35, t); cmds.parent(t, demo)
_assign(t, _mat("MAT_red", (0.80, 0.25, 0.20)))

c = cmds.polyCube(w=78, h=78, d=78, name="GEO_hero_cube")[0]
cmds.move(0, 84, 0, c); cmds.rotate(0, 38, 0, c); cmds.parent(c, demo)
_assign(c, _mat("MAT_green", (0.22, 0.66, 0.40)))

k = cmds.polyCone(r=44, h=96, name="GEO_hero_cone")[0]
cmds.move(240, 88, 0, k); cmds.parent(k, demo)
_assign(k, _mat("MAT_blue", (0.25, 0.48, 0.92)))

lg = cmds.group(em=True, name="GRP_lighting")
key = cmds.directionalLight(intensity=1.25, name="LGT_key_main")
cmds.rotate(-38, -45, 0, key); cmds.parent(key, lg)
fill = cmds.directionalLight(intensity=0.5, name="LGT_fill_ambient")
cmds.setAttr(fill + ".color", 0.62, 0.72, 1.0, type="double3")
cmds.rotate(-18, 55, 0, fill); cmds.parent(fill, lg)
rim = cmds.directionalLight(intensity=0.9, name="LGT_rim_back")
cmds.setAttr(rim + ".color", 1.0, 0.85, 0.7, type="double3")
cmds.rotate(-30, 178, 0, rim); cmds.parent(rim, lg)
amb = cmds.ambientLight(intensity=0.3, name="LGT_ambient"); cmds.parent(amb, lg)

tgt = cmds.spaceLocator(name="LOC_aim")[0]
cmds.move(0, 80, 0, tgt)

def _cam(name, eye):
    ct, cs = cmds.camera(name=name)
    cmds.move(eye[0], eye[1], eye[2], ct)
    a = cmds.aimConstraint(tgt, ct, aimVector=(0, 0, -1),
                           upVector=(0, 1, 0), worldUpType="vector",
                           worldUpVector=(0, 1, 0))[0]
    cmds.delete(a)
    return ct

_cam("CAM_hero", (640, 380, 780))
_cam("CAM_alt", (-560, 220, 640))
cmds.hide(tgt)
result = {"ok": True, "objects": len(cmds.ls(dag=True, long=False) or [])}
"""

PANEL_TO = r"""
import maya.cmds as cmds
eye = __EYE__
if not cmds.objExists("LOC_aim"):
    t = cmds.spaceLocator(name="LOC_aim")[0]
    cmds.move(0, 80, 0, t)
    cmds.hide(t)
cmds.move(eye[0], eye[1], eye[2], "persp")
a = cmds.aimConstraint("LOC_aim", "persp", aimVector=(0, 0, -1),
                       upVector=(0, 1, 0), worldUpType="vector",
                       worldUpVector=(0, 1, 0))[0]
cmds.delete(a)
"""

SET_TIME = "import maya.cmds as cmds; cmds.currentTime({f}, edit=True)"


_BUFS: dict = {}


async def read_msg(proc, timeout=120.0):
    buf = _BUFS.setdefault(proc, bytearray())

    async def _one_line():
        while True:
            nl = buf.find(b"\n")
            if nl >= 0:
                line = bytes(buf[:nl])
                del buf[: nl + 1]
                return line
            chunk = await proc.stdout.read(65536)
            if not chunk:
                return None
            buf.extend(chunk)

    line = await asyncio.wait_for(_one_line(), timeout)
    if not line:
        return None
    return json.loads(line.decode("utf-8", "replace").strip())


async def send(proc, obj):
    proc.stdin.write((json.dumps(obj) + "\n").encode())
    await proc.stdin.drain()


class Session:
    def __init__(self, proc):
        self.proc = proc
        self.rid = 0

    async def call(self, name, arguments, timeout=180.0):
        self.rid += 1
        await send(self.proc, {
            "jsonrpc": "2.0", "id": self.rid, "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        })
        resp = await read_msg(self.proc, timeout=timeout)
        return resp

    async def exec(self, code, result_type="NONE", timeout=120.0):
        return await self.call("execute_code", {"code": code, "result_type": result_type}, timeout)

    async def snap(self, path, max_size=1400):
        r = await self.call("scene_viewport_snapshot",
                            {"max_size": max_size, "format": "png"}, timeout=180)
        img = _image_bytes(r)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(img)
        meta = _text_payload(r)
        return {"file": str(path), "bytes": len(img), "meta": meta[:300]}

    async def frame(self, camera, path, w=640, h=360):
        r = await self.call("scene_render_preview",
                            {"camera": camera, "width": w, "height": h,
                             "format": "png", "max_size": 800}, timeout=180)
        img = _image_bytes(r)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(img)
        return {"file": path.name, "bytes": len(img)}


def _contents(resp):
    if not resp or "result" not in resp:
        raise RuntimeError(f"no result in response: {str(resp)[:300]}")
    return resp["result"].get("content", [])


def _image_bytes(resp):
    for c in _contents(resp):
        if c.get("type") == "image":
            return base64.b64decode(c["data"])
    texts = [c.get("text", "")[:300] for c in _contents(resp)]
    raise RuntimeError(f"no image content: {texts}")


def _text_payload(resp):
    out = []
    for c in _contents(resp):
        if c.get("type") == "text":
            out.append(c["text"])
    return "\n".join(out)


def _is_err(resp):
    return bool(resp and resp.get("result", {}).get("isError"))


async def main() -> int:
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "maya_mcp_server",
        cwd=str(REPO),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={
            "PATH": r"D:\DevTools\Python\runtimes\pythoncore-3.11-64",
            "PYTHONPATH": str(REPO / "src"),
            "SYSTEMROOT": r"C:\Windows",
        },
    )
    tr = {"steps": {}}
    try:
        s = Session(proc)
        await send(proc, {
            "jsonrpc": "2.0", "id": 0, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "dogfood-t15b", "version": "0.1"}},
        })
        init = await read_msg(proc)
        tr["steps"]["initialize"] = {
            "ok": bool(init and "result" in init),
            "server": (init or {}).get("result", {}).get("serverInfo"),
        }
        await send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})

        s.rid += 1
        await send(proc, {"jsonrpc": "2.0", "id": s.rid, "method": "tools/list", "params": {}})
        tools = await read_msg(proc)
        names = [t["name"] for t in tools["result"]["tools"]] if tools and "result" in tools else []
        tr["steps"]["tools_list"] = {"count": len(names)}

        sess = await s.call("list_sessions", {})
        stext = _text_payload(sess)
        tr["steps"]["list_sessions"] = {"isError": _is_err(sess), "text": stext[:400]}

        snap = await s.call("scene_snapshot", {"format": "json", "detail": "compact"}, timeout=240)
        tr["steps"]["scene_snapshot_pre"] = {"isError": _is_err(snap),
                                             "text": _text_payload(snap)[:300]}

        build = await s.exec(SCENE_BUILD, timeout=240)
        tr["steps"]["scene_build"] = {"isError": _is_err(build),
                                      "text": _text_payload(build)[:400]}

        ver = await s.call("scene_snapshot", {"format": "json", "detail": "compact"}, timeout=240)
        tr["steps"]["scene_snapshot_post"] = {"isError": _is_err(ver),
                                              "text": _text_payload(ver)[:300]}

        for tag, eye, fname in [
            ("hero", (640, 380, 780), "shot-hero.png"),
            ("alt", (-560, 220, 640), "shot-alt.png"),
        ]:
            r = await s.exec(PANEL_TO.replace("__EYE__", repr(list(eye))))
            tr["steps"][f"pose_{tag}"] = {"isError": _is_err(r), "text": _text_payload(r)[:200]}
            shot = await s.snap(ASSETS / fname)
            tr["steps"][f"snap_{tag}"] = shot

        orb = await s.call("camera_orbit",
                           {"center": "[0,80,0]", "radius": 560, "frames": 36,
                            "name": "CAM_orbit"}, timeout=240)
        tr["steps"]["camera_orbit"] = {"isError": _is_err(orb),
                                       "text": _text_payload(orb)[:300]}

        frames_out = []
        for f in range(1, 37, 2):
            await s.exec(SET_TIME.format(f=f))
            fr = await s.frame("CAM_orbit", FRAMES / f"orbit-{f:02d}.png")
            frames_out.append(fr)
        tr["steps"]["orbit_frames"] = frames_out

        await s.exec(PANEL_TO.replace("__EYE__", repr([640, 380, 780])))
        await s.exec("import maya.cmds as cmds; cmds.currentTime(1, edit=True)")
        tr["verdict"] = "PASS" if all(
            not v.get("isError") for v in tr["steps"].values() if isinstance(v, dict)
        ) else "CHECK"
    finally:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), 10)
        except asyncio.TimeoutError:
            proc.kill()

    TRANS.write_text(json.dumps(tr, indent=2, default=str), encoding="utf-8")
    print(json.dumps(tr, indent=2, default=str)[:6000])
    return 0 if tr.get("verdict") == "PASS" else 1


sys.exit(asyncio.run(main()))
