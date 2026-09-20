# Testing Tiers

Two test tiers exist. They are deliberately separate.

## Tier 1 — stub tests (CI-safe, no Maya needed)

```bash
python -m pytest tests/ -q
```

`tests/maya_stub/` provides semantic fakes for `maya.cmds` and
`maya.api.OpenMaya`: a real DAG scene graph, row-major matrix math,
and correct 8-corner world-bbox transforms. The `maya_env` fixture
(conftest.py) installs the stub into `sys.modules` and imports
`maya_scene_module` bound to it.

The stub is NOT a Maya replacement — it models only the cmds/OpenMaya
surface the scene module uses. Its math is self-verified in
`test_maya_stub.py`; if the stub lies, product tests lie, so keep
`math3d.py` honest (row-vector convention, translation in M[12..14]).

## Tier 2 — real Maya via mayapy (manual, local-only, NEVER in CI)

Run the scene module inside a real Maya interpreter to catch stub drift
and real API behavior differences:

```bash
# Point mayapy at the repo so maya_mcp_server + tests import cleanly
set PYTHONPATH=D:\Aworker\maya\maya-mcp-server\src;D:\Aworker\maya\maya-mcp-server\tests
"C:\Program Files\Autodesk\Maya2024\bin\mayapy.exe" -m pytest tests/ -q -m mayapy
```

Tests marked `@pytest.mark.mayapy` exercise real `maya.cmds`/
`maya.api.OpenMaya` against `maya_scene_module` — they are skipped
unless the `mayapy` marker is explicitly selected. They are the
reference tier: if a stub test and a mayapy test disagree, the stub is
wrong.

For a quick smoke test of the module inside Maya's Script Editor:

```python
import sys; sys.path.insert(0, r"D:\Aworker\maya\maya-mcp-server\src")
import maya_mcp_server.maya_scene_module as _mcp_scene
_mcp_scene.get_scene_graph()
```

## Tier 3 — live Maya GUI session (`gui` + `human_verify` markers, D-049a)

Two markers split the live-GUI tier by assertability — the HIL layer of
the SIL(stub)/PIL(mayapy)/HIL(live GUI) mapping:

```bash
# machine-checkable items — real asserts against a live session
# (probes MAYA_MCP_GUI_ADDR=host:port, default 127.0.0.1:7001 bootstrap
# commandPort; skips cleanly when no session is up)
python -m pytest tests/ -m gui

# human-eye checklist — tests exist, print manual steps, always skip
# (never fake a green on viewport state)
python -m pytest tests/ -m human_verify -s
```

`gui` covers: framed-channel bootstrap (PySide2/Qt real session),
str `result_type` over the real wire (D-046), viewport_snapshot PNG
contract, render_preview net-zero side effects (panel camera +
currentTime restored) and the camera_not_found domain error.

`human_verify` versioned checklist (was a docs-only list): snapshot
orientation (verticalFlip), WYSIWYG HUD/selection match, VP2 non-black
(2025/2026 = partial), render_preview framing vs requested camera,
multi-client ImageContent rendering (non-Devin seats blocked on user
env), modelPanel -camera call form on 2025/2026 (partial — only 2024
verified locally).

For ad-hoc Script Editor checks inside Maya:

```python
import sys; sys.path.insert(0, r"D:\Aworker\maya\maya-mcp-server\src")
import maya_mcp_server.visual_module as _mcp_visual
```
