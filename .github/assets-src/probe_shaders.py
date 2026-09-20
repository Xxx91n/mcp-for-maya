import socket
import time


OUT = r"D:\Aworker\maya\maya-mcp-server\.scratch\facade\shader_probe.json"

CODE = r"""import maya.cmds as cmds, json, traceback
res = {}
try:
    for sg in ["MAT_redSG","MAT_greenSG","MAT_blueSG","MAT_ringSG","MAT_stageSG","MAT_pedestalSG"]:
        if cmds.objExists(sg):
            res[sg+"_surf"] = cmds.listConnections(sg+".surfaceShader") or []
    res["isg_members"] = cmds.sets("initialShadingGroup", q=True) or []
    res["isg_surf"] = cmds.listConnections("initialShadingGroup.surfaceShader") or []
except Exception:
    res["trace"] = traceback.format_exc()
open(r"OUTPATH","w").write(json.dumps(res))
""".replace("OUTPATH", OUT.replace("\\", "/"))

s = socket.create_connection(("127.0.0.1", 7001), 5)
s.sendall(CODE.encode())
time.sleep(3)
try:
    reply = s.recv(65535).decode("utf-8", "replace")
    if reply.strip() and reply.strip() != "None":
        print("REPLY:", reply[:500])
except TimeoutError:
    pass
s.close()
print(open(OUT, encoding="utf-8").read())
