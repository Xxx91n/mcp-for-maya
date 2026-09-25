# T-19 + T-20 demo assets — reproduction

Frozen-session captures for README/social assets. Every image was
produced by the product MCP tools (no mocks, no post-editing).

## T-20 showcase set (current README)

`t20/` holds the six scene generators plus the shared kit:

| Script | Scene root | Hero camera | Subject |
|--------|-----------|-------------|---------|
| `t20kit.py` | — | — | shared helpers (mats, prism, ring, tube, cam, kill) |
| `movement.py` | `GRP_t20_movement` | `CAM_t20mv_hero` | involute watch movement |
| `bonsai.py` | `GRP_t20_bonsai` | `CAM_t20bn_hero` | L-system bonsai |
| `workbench.py` | `GRP_t20_workbench` | `CAM_t20wb_hero` | Poly Haven import + assembly |
| `streetblock.py` | `GRP_t20_street` | `CAM_t20st_hero` | low-poly corner block |
| `teapot.py` | `GRP_t20_teapot` | `CAM_t20tp_hero` | Utah teapot recreation |
| `auditbench.py` | `GRP_t20_audit` | `CAM_t20au_hero` | metrology bench |

Run order inside a Maya 2024 GUI session (via `write_module` then
`execute_code`):

```python
import t20kit, t20_movement  # modules are injected by write_module

t20_movement.build()  # -> scene_render_preview("CAM_t20mv_hero")
```

Notes: `workbench.py` requires the Poly Haven cache populated by
`asset_import("vintage_pocket_watch")` + `asset_import("metal_tool_chest")`
first. `cmds.scale`/`cmds.rotate` are absolute-set in Maya — the scripts
compute absolute targets, and second rotations use `relative=True`.
`playblast` frame grabs must `lookThru` the intended camera.

## T-19 set (superseded showcase, kept for reference)

## Environment

- Maya 2024 GUI session, en_US UI (`MAYA_UI_LANGUAGE=en_US` env,
  not Maya.env), clean untitled scene
- Repo HEAD `python -m maya_mcp_server` over stdio; Qt framed channel
- Capture host: this repo, Windows

## Build

1. Start Maya (GUI, en_US), commandPort :7001 via userSetup.py managed
   block (see maya_setup_guide).
2. Ensure the Maya window is **visible** (not minimized) —
   `scene_viewport_snapshot` reads the live VP2 buffer and freezes
   while minimized. Dismiss the Home Screen if it shows
   (`mel.eval('appHome -visible false')`).
3. `execute_code` with `.github/assets-src/scene_build.py`
   → builds GRP_env/GRP_exhibits/GRP_lighting, CAM_*, LOC_*.
4. Panel setup (viewport defaults need nudging):
   - `modelEditor -e -dl all` (scene lights, not the headlamp)
   - `modelEditor -e -shadows 1` (depth-map shadows)
   - `modelEditor -e -displayTextures 1`
5. VP2 globals: multiSampleEnable=1, multiSampleCount=8, ssaoEnable=1,
   ssaoAmount=0.65, ssaoRadius=18, ssaoFilterRadius=8,
   transparentShadow=1, lineAAEnable=1 (`hardwareRenderingGlobals`).
6. `asset_import(asset_id="Camera_01", resolution="1k")`
   → GRP_asset_Camera_01, 26,987 faces; scale 351x onto
   GEO_ped_camera at (250, 52, 30), rotate -15° Y, parent GRP_exhibits.
7. `camera_orbit(center=[0,115,-10], radius=660, frames=48, name=CAM_orbit)`;
   parent `LGT_rim_back` transform under CAM_orbit for stable orbit rim.

## Capture

```bash
python .github/assets-src/capture.py
```

Outputs to `.scratch/t19/final/` + `frames/`; transcript at
`.scratch/t19/dogfood-transcript.json`.

| Asset | Tool | Camera | Spec |
|-------|------|--------|------|
| hero.png | scene_render_preview | CAM_hero1 | 1280x720, no HUD |
| shot-hero.png | scene_viewport_snapshot | persp@hero | HUD incl. |
| shot-alt.png | scene_viewport_snapshot | persp@alt | HUD incl. |
| orbit.gif | camera_orbit + preview x48 | CAM_orbit | 640x360, ~6s |
| social-preview.png | scene_render_preview | CAM_alt1 | 1280x640 <1MB |
| row*.png | scene_render_preview | CAM_row*/CAM_audit1 | 960x540 |

## Notes

- `scene_render_preview` (playblast) works regardless of window state;
  `scene_viewport_snapshot` (readback) does not — the window must be
  visible and repainted.
- AO packed maps drive `material.diffuse` (multiplier), not
  ambientColor (adds light). Normal maps wire file.outAlpha ->
  bump2d.bumpValue with bumpInterp=1 (canonical fbxmaya network).
- Poly Haven asset: Camera_01 (CC0), 1k pack.
