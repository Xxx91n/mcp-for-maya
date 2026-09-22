<!-- D-056③ evidence layer: independent call-form comparison table for
     visual_module. The presence-allowlist holds verdicts + anchors
     pointing here; this table is the single source of truth.
     Every row verified against official Maya docs via atomcode
     research on 2026-09-22 (see source list at bottom). -->

# visual_module call-form matrix

Scope: every cmds.* / maya.api call site in `src/maya_mcp_server/visual_module.py`.

Verdicts:
- `match` — call form + return shape match the official contract
- `absent-in-python` — method exists in C++ only; never callable from Python
- `deprecated-available` — officially deprecated but still functional

## maya.cmds call sites

| # | Call site | Official signature / return | Verdict | URL | Version | Date |
|---|---|---|---|---|---|---|
| 1 | `cmds.about(batch=True)` | `about(batch=boolean)` -> bool | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/about.html | 2024 | 2026-09-22 |
| 2 | `cmds.getPanel(type="modelPanel")` | `getPanel(type=string)` -> string[] | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/getPanel.html | 2024 | 2026-09-22 |
| 3 | `cmds.getPanel(withFocus=True)` | `getPanel(withFocus=boolean)` -> string | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/getPanel.html | 2024 | 2026-09-22 |
| 4 | `cmds.objectTypeUI(panel)` | `objectTypeUI(string)` -> string | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/objectTypeUI.html | 2024 | 2026-09-22 |
| 5 | `cmds.lsUI(editors=True)` | `lsUI(editors=boolean)` -> string[] | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/lsUI.html | 2024 | 2026-09-22 |
| 6 | `cmds.modelEditor(ed, query=True, activeView=True)` | `modelEditor(editorName, activeView=boolean)` query -> bool | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/modelEditor.html | 2024 | 2026-09-22 |
| 7 | `cmds.modelEditor(panel, query=True, camera=True)` | `modelEditor(editorName, camera=string)` query -> string | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/modelEditor.html | 2024 | 2026-09-22 |
| 8 | `cmds.modelPanel(panel, query=True, camera=True)` | `modelPanel(panelName, camera=string)` query -> string | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/modelPanel.html | 2024 | 2026-09-22 |
| 9 | `cmds.modelPanel(panel, edit=True, camera=cam)` | `modelPanel(panelName, camera=string)` edit -> None | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/modelPanel.html | 2024 | 2026-09-22 |
| 10 | `cmds.modelPanel(panel, exists=True)` | `modelPanel(panelName, exists=boolean)` -> bool | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/modelPanel.html | 2024 | 2026-09-22 |
| 11 | `cmds.objExists(name)` | `objExists(string)` -> bool | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/objExists.html | 2024 | 2026-09-22 |
| 12 | `cmds.currentTime(query=True)` | `currentTime([time], update=boolean)` query -> float | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/currentTime.html | 2024 | 2026-09-22 |
| 13 | `cmds.currentTime(t, edit=True)` | `currentTime(time, edit=boolean)` -> None | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/currentTime.html | 2024 | 2026-09-22 |
| 14 | `cmds.refresh(force=True)` | `refresh(force=boolean)` -> None | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/refresh.html | 2024 | 2026-09-22 |
| 15 | `cmds.playblast(...)` | `playblast` -> string; flags used: format string ("image"), compression string ("png"), offScreen bool, viewer bool, showOrnaments bool, percent int 10-100 (clamped), forceOverwrite bool, completeFilename string (exact name; exclusive vs filename), frame time-list, widthHeight [int,int] (clamped; %4 on Windows non-fcheck), editorPanelName string | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/CommandsPython/playblast.html | 2024 | 2026-09-22 |

## maya.api.OpenMayaUI / OpenMaya call sites

| # | Call site | Official signature / return | Verdict | URL | Version | Date |
|---|---|---|---|---|---|---|
| 16 | `omui.M3dView.active3dView()` | `M3dView.active3dView()` -> M3dView | match | https://help.autodesk.com/cloudhelp/2023/ENU/MAYA-API-REF/py_ref/class_open_maya_u_i_1_1_m3d_view.html | 2023* | 2026-09-22 |
| 17 | `view.getRendererName()` / `view.kViewport2Renderer` | `getRendererName()` -> string; `kViewport2Renderer` class const | match | same as #16 | 2023* | 2026-09-22 |
| 18 | `view.portWidth()` / `view.portHeight()` | `portWidth()`/`portHeight()` -> int | match | same as #16 | 2023* | 2026-09-22 |
| 19 | `view.readColorBuffer(img, True)` | `readColorBuffer(MImage&, readRGBA=False)` — deprecated (MRenderTargetManager recommended), still functional; readRGBA=True yields RGBA order + isRGBA()=True (live-verified 2024.0.0.4640) | match | same as #16 | 2024 | 2026-09-22 |
| 20 | `om.MImage.create(w, h, 4, kFloat)` | `create(width, height, channels=4, type=kByte)` -> self | match | https://help.autodesk.com/cloudhelp/2024/ENU/Maya-Tech-Docs/py_ref/class_open_maya_1_1_m_image.html | 2024 | 2026-09-22 |
| 21 | `img.getSize()` | `getSize()` -> [width, height] | match | same as #20 | 2024 | 2026-09-22 |
| 22 | `img.pixelType()` | `pixelType()` -> int (kUnknown=0 / kByte=1 / kFloat=2) | match | same as #20 | 2024 | 2026-09-22 |
| 23 | `img.isRGBA()` | `isRGBA()` -> bool (RGBA vs BGRA storage order) | match | same as #20 | 2024 | 2026-09-22 |
| 24 | `img.floatPixels()` | `floatPixels()` -> int (raw address; MScriptUtil removed in 2024 so it is unreadable in-process) | superseded — module no longer calls it; RGBA comes from readColorBuffer's readRGBA flag | same as #20 | 2024 | 2026-09-22 |
| 25 | `img.setPixels(bytes, w, h)` | `setPixels(pixels, width, height)` -> self | match | same as #20 | 2024 | 2026-09-22 |
| 26 | `img.setRGBA(True)` | `setRGBA(bool)` -> self — channel-order MARKER, not a rearranger | match | same as #20 | 2024 | 2026-09-22 |
| 27 | `img.verticalFlip()` | `verticalFlip()` -> bool | match | same as #20 | 2024 | 2026-09-22 |
| 28 | `img.writeToFile(path, 'png')` | `writeToFile(pathname, outputFormat=iff)` -> self | match | same as #20 | 2024 | 2026-09-22 |
| 29 | `MImage.convertPixelFormat` | NOT in the Python API 2.0 member list (2023 + 2024 refs checked; C++ API only) | absent-in-python — removed from stub and module (D-056⑤) | same as #20 | 2024 | 2026-09-22 |

\* The Maya 2024 M3dView py_ref page returned 404 during research; the
2023 page was read verbatim and the member list was cross-checked
against the 2025/2027 indexes.

## omui.MImage dual-location

Real `MImage` lives in `maya.api.OpenMaya` on Maya <=2024 and moves to
`OpenMayaUI` in 2025+. The stub deliberately models BOTH locations so
`visual_module._MImage` dual-resolution can be exercised against either
layout (a test deletes `omui.MImage` to simulate 2024).

Verdict: **stub-only dual-location — justified, converged via
dual-resolution.** Anchored here from `presence-allowlist.json`.

## Sources (atomcode research, serialized single run, 2026-09-22)

- Autodesk Maya 2024 CommandsPython pages — about, getPanel,
  objectTypeUI, lsUI, modelEditor, modelPanel, objExists, currentTime,
  refresh, playblast: official, fetched and cross-checked verbatim.
- Autodesk Maya 2024 Python API Reference `MImage` page (py_ref):
  official, member list verified verbatim.
- Autodesk Maya 2023 Python API Reference `M3dView` page: official;
  member list cross-checked against 2025/2027 indexes.
- Autodesk Dev Blog (2016): `readColorBuffer`-in-VP2 kFloat target
  requirement.
- Recorded research gaps: 2024 M3dView page unreachable (404);
  `convertPixelFormat` absence verified verbatim for the 2023/2024
  Python refs and inferred — not re-checked — for 2025/2027.
