# Testing Tiers

Two test tiers exist. They are deliberately separate.

## Environment floor

| Side | Requirement |
|------|-------------|
| Host (this package) | Python >= 3.10 (`requires-python`) |
| Injected helper (inside Maya) | Maya >= 2023 i.e. Python >= 3.9 — the `ast.unparse` floor is enforced with a friendly refusal at injection time |
| Empirically verified | Maya 2024 GUI (Tier 3) |

Multi-instance note (D-060): each Maya instance binds its own `commandPort` on a distinct port — a second instance on the same port fails to bind. The scanner probes all listening ports; a port that answers the port-type `eval("1/2")` probe as non-Python goes on this session's do-not-probe list and is not probed again while it keeps LISTENing (upstream issue #1). Bound or exclude probe targets via `MAYA_MCP_INCLUDE_PORTS` / `MAYA_MCP_EXCLUDE_PORTS` (comma-separated ports or `a-b` ranges).

## Tier 1 — fake Maya tests (CI-safe, no Maya needed)

```bash
python -m pytest tests/ -q
```

`tests/maya_stub/` provides semantic fakes for `maya.cmds` and
`maya.api.OpenMaya`: a real DAG scene graph, row-major matrix math,
and correct 8-corner world-bbox transforms. The `maya_env` fixture
(conftest.py) installs the fake into `sys.modules` and imports
`maya_scene_module` bound to it.

The fake is NOT a Maya replacement — it models only the cmds/OpenMaya
surface the scene module uses. Its math is self-verified in
`test_maya_stub.py`; if the fake lies, product tests lie, so keep
`math3d.py` honest (row-vector convention, translation in M[12..14]).

## Tier 2 — real Maya through mayapy (manual, local-only, NEVER in CI)

Run the scene module inside a real Maya interpreter to catch drift
between the fake and real API:

```bash
# Point mayapy at the repo so maya_mcp_server + tests import cleanly
set PYTHONPATH=D:\Aworker\maya\maya-mcp-server\src;D:\Aworker\maya\maya-mcp-server\tests
"D:\maya2024\Maya2024\bin\mayapy.exe" -m pytest tests/ -q -m mayapy
```

The install path differs per machine (`<MayaInstallDir>\bin\mayapy.exe`);
on the box that last tried it the interpreter lived under
`D:\maya2024\Maya2024`, not under `C:\Program Files\Autodesk`.

Tests marked `@pytest.mark.mayapy` exercise real `maya.cmds`/
`maya.api.OpenMaya` against `maya_scene_module` — they are skipped
unless the `mayapy` marker is explicitly selected. They are the
reference tier: if a fake-Maya test and a real-Maya test disagree, the
fake is wrong.

The tier auto-initializes `maya.standalone` once per session
(`tests/test_mayapy_smoke.py::_maya_standalone_init`) — bare mayapy
crashes hard on `import maya.api.OpenMaya` without it.

**Prerequisite**: `maya.standalone` must import cleanly under mayapy.
Verified blocked on at least one dev box (Maya 2024, Windows):
`import maya.standalone` raises a native access violation
(0xC0000005) inside module creation and `maya.exe -batch` hangs — the
whole tier is unrunnable there. The Maya 2024 box measured on
2026-11-15 fails earlier and differently: plain `mayapy.exe` starts
fine, but `import maya.standalone` ends in
`ImportError: DLL load failed while importing standalone: 动态链接库(DLL)初始化例程失败。`
(exit 1). Neither box was repaired: no DLL was swapped and
`MAYA_APP_DIR` was left alone. On such a box, run the real-Maya checks
(checkpoint/read-back roundtrip, reference-edit case, signature
collection, the six call forms below) through a live GUI session
instead — see `docs/reference/gui_verify.py` and
`docs/reference/six_callform_gui_driver.py` for reference
implementations. Launch mayapy from PowerShell/cmd, never Git Bash
(MSYS environment makes mayapy SIGSEGV at startup).

If `mayapy` hits `0xC0000005` on Windows, inspect Maya's `bin\`
directory with PowerShell to surface any unsigned DLLs (such as
`mayaLib0.dll` or `OpenEXRCore-3_1-maya.dll` reporting `NotSigned`):

```powershell
Get-AuthenticodeSignature "<MayaInstallDir>\bin\*.dll" |
  Where-Object Status -ne Valid |
  Select-Object Status, Path
```

When headless `mayapy` is blocked, you can also run one-shot
verification through the GUI host instead of attaching interactively:

```powershell
# Keep the host's existing MAYA_APP_DIR intact; do not clear or overwrite
# it (observed to stall GUI initialization on the blocked Maya 2024 box
# above; exact root cause across other hosts is unverified).
& "<MayaInstallDir>\bin\maya.exe" -script "<verify.mel>"
```

Inside `<verify.mel>`, call your Python check via `python("...")`. For
unattended runs, wrap the check in Python `try`/`except` (writing the
pass/fail status or traceback to a log file) or MEL `catch(...)` before
`quit -f;` — otherwise an uncaught Python exception aborts the MEL
script early and leaves the Maya GUI open.

Pending: the mayapy/batch run must also cover the `gui_session_required`
headless gate (visual tools must return the structured error, not
crash) — queued until a healthy headless Maya env exists.

### Six call forms measured on Maya 2024 (2026-11-15, issue #253)

`docs/reference/six_callform_gui_driver.py` runs `#229`'s six
stub-disagreement call forms inside a real GUI session, and reports one
pass/fail row per form. It is the honest substitute for the mayapy lane
on a box where that lane cannot start. Run it in a throwaway instance:

```mel
int $rc = catch(python("exec(open(r'<repo>/docs/reference/six_callform_gui_driver.py', encoding='utf-8').read())"));
if ($rc != 0) { print "six-form driver raised; read its JSON for the traceback\n"; }
evalDeferred "quit -f";
```

launched as `"<MayaInstallDir>\bin\maya.exe" -script "<the mel file above>"`.
The driver forces a new empty scene, writes one JSON file (path in
`MAYA253_OUT`), and refuses to replace a scene that has a file on disk
unless `MAYA253_FORCE=1` is set on purpose. Every node it makes is
deleted in a `finally`, playback is restored, and a deliberate raising
probe checks that the failure path cleans up too.

Measured on Maya 2024 (24.0.0.4640), Windows 11, Maya-side Python
3.10.8: all six forms pass (xform `q/ws/t/ro`, `rename` returning the
new name, `keyTangent itt/ott`, `playbackOptions min/max`,
`aimConstraint` with three-number lists, `MFnMesh.getPoint` with
`MSpace.kWorld`), the shipped
`tests/test_mayapy_smoke.py::test_callform_stub_disagreement_forms`
passes against real `maya.cmds`, and the scene returns to its starting
node count and playback range. Artifact:
`docs/evidence/probes/probe-253-six-callforms-gui-maya2024.json`.

What this does not prove: Maya 2025/2026, and anything batch-only
(`cmds.about(batch=True)` needs a real batch session, not a GUI one).

### Call-form items booked to the real interpreter

Viewport-independent call forms whose real-return shape must be
asserted on a healthy real Maya interpreter (the tests in
`tests/test_mayapy_smoke.py` run when one is available and skip honestly
otherwise). Evidence table:
`docs/visual-callform-matrix.md`. Stub-versus-call disagreements are a
separate record: `docs/reference/maya-stub-mismatches.md`.

Status 2026-11-15: the `rename`, `xform`, `keyTangent`,
`playbackOptions`, `aimConstraint` and `getPoint` rows are measured on
Maya 2024 (section above). The `camera`, `ls`, `file`, selection and
`about(batch=)` rows are still booked only — none of them has a live
result yet.

- `cmds.camera(name=X)` -> `[transform, shape]` list (X1 rename authority)
- `cmds.ls(type='camera')` -> list including `perspShape` shape nodes
- `cmds.file(rename=X)` + `sceneName` query — the rename+prompt form
  (the 0.1.1 hang came from a positional form hitting the prompt dialog)
- `MSelectionList.add('*')` includes non-DAG nodes -> `getDagPath`
  raises `TypeError('item is not a DAG path')` on them
- `cmds.about(batch=True)` -> True under mayapy (the batch gate trigger)
- `cmds.rename(node, name)` -> the new name string (the stub says `None`)
- `cmds.xform(node, q=True, ws=True, t=True/ro=True)` -> world-space
  translation and rotation (the stub lists the long flag names only)
- `cmds.keyTangent(edit=True, itt=..., ott=...)` and
  `cmds.playbackOptions(min=..., max=...)` -> accepted (same stub gap)
- `cmds.aimConstraint(..., aimVector=[...], upVector=[...])` -> constraint
  name from three-number lists (the stub takes tuples only)
- `MFnMesh.getPoint(i, om2.MSpace.kWorld)` -> world-space point (the stub
  types the constant `int`)

For a quick smoke test of the module inside Maya's Script Editor:

```python
import sys

sys.path.insert(0, r"D:\Aworker\maya\maya-mcp-server\src")
import maya_mcp_server.maya_scene_module as _mcp_scene

_mcp_scene.get_scene_graph()
```

## Tier 3 — live Maya GUI session (`gui` + `human_verify` markers, D-049a)

Two markers split the live-GUI tier by assertability — the third layer of
the fake(CI) / real-interpreter / live-GUI split:

```bash
# machine-checkable items — real asserts against a live session
# (probes MAYA_MCP_GUI_ADDR=host:port, default 127.0.0.1:7001 entry
# port; skips cleanly when no session is up)
python -m pytest tests/ -m gui

# human-eye checklist — tests exist, print manual steps, always skip
# (never fake a green on viewport state)
python -m pytest tests/ -m human_verify -s
```

`gui` covers: the framed-channel setup after injection (PySide2/Qt real session),
str `result_type` over the real wire (D-046), viewport_snapshot PNG
contract, render_preview leaving the viewport as it found it (panel camera +
currentTime restored), returned-metadata `width/height` matching
reality, and the camera_not_found domain error.

`human_verify` versioned checklist (was a docs-only list): snapshot
orientation (verticalFlip), WYSIWYG HUD/selection match, VP2 non-black
(2025/2026 = partial), render_preview framing vs requested camera,
multi-client ImageContent rendering (non-Devin seats blocked on user
env), modelPanel -camera call form on 2025/2026 (partial — only 2024
verified locally).

### Call-form checklist (D-056②)

Every call form below is verified against its official signature —
the evidence layer is `docs/visual-callform-matrix.md` (single source
of truth); this list is the tier assignment. `pytest -m gui`
machine-asserts the first group on the live wire
(`test_callform_surface_probe`); the asymmetric pure-color pin has its
own test (`test_vp2_pure_color_orientation_and_channels`).

Machine-assertable (gui):

- `cmds.getPanel(withFocus=True)` -> `str|None`; may return a
  non-modelPanel — `objectTypeUI` must confirm `modelEditor` first
- `cmds.getPanel(type='modelPanel')` -> `string[]`
- `cmds.modelPanel(p, q=True, camera=True)` -> `str` camera name;
  `modelPanel(p, e=True, camera=X)` -> None; `modelPanel(p, ex=True)`
  -> bool (D-039)
- `cmds.modelEditor(ed, q=True, camera=True)` -> `str`;
  `modelEditor(ed, q=True, activeView=True)` -> bool
- `cmds.lsUI(editors=True)` -> `string[]`; `objectTypeUI(name)` -> `str`
- `cmds.currentTime(q=True)` -> float; `currentTime(v, edit=True)` -> None
- `cmds.refresh(force=True)` -> None
- `omui.M3dView.active3dView().getRendererName()` -> `'vp2Renderer'`
  under VP2
- `view.readColorBuffer(img, readRGBA=True)` -> RGBA-ordered float
  MImage on 2024 (`isRGBA()` -> True); `writeToFile` does the
  float->byte conversion — no Python pointer read (`MScriptUtil` is
  gone in Maya 2024, `floatPixels()` returns a bare `int` address)
- `hasattr(om.MImage, 'convertPixelFormat')` -> False on 2024 Python
  (C++-only API — evidence print in the VP2 gui test, not a gate)

Human-eye (human_verify manual checklist):

- asymmetric pure-color probe (top-left red block) lands top-left AND
  red — the flip + channel-order pin on real VP2; also machine-asserted
  by `test_vp2_pure_color_orientation_and_channels`
- `cmds.playblast(completeFilename=F, frame=[t])` writes F verbatim —
  no frame suffix, no extension rewriting

For ad-hoc Script Editor checks inside Maya:

```python
import sys

sys.path.insert(0, r"D:\Aworker\maya\maya-mcp-server\src")
import maya_mcp_server.visual_module as _mcp_visual
```
