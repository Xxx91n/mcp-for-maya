**English** | [简体中文](showcase_cn.md)

<img src="https://raw.githubusercontent.com/Xxx91n/mcp-for-maya/main/.github/assets/section-live-demo.svg" width="100%" alt="Live Demo — captured by the product itself"/>

All media below were genuinely captured with the toolchain itself (no mockups): scenes were generated via `execute_code` / `write_module` (plus a real `asset_import`), preview frames were rendered through `scene_render_preview`, audit comparisons were captured using `scene_review` + `scene_viewport_snapshot`, and the orbit sequence was recorded frame by frame with `playblast` in a Maya 2024 GUI session.

| Prompt | Result |
|---|---|
| `write_module` → `t20_movement.build()` — "parametric involute gear caliber: true involute gear profile, Geneva stripes, heat-blued screws, ruby jewel bearings, spiral hairspring" | <img src="https://raw.githubusercontent.com/Xxx91n/mcp-for-maya/main/.github/assets/showcase-movement.png" width="440" alt="Parametric watch caliber: involute gears, Geneva stripes, balance wheel and hairspring"/> |
| `write_module` → `t20_bonsai.build()` — "low-poly L-system bonsai tree: recursive branching, faceted leaf clusters, pot + moss + rocks" | <img src="https://raw.githubusercontent.com/Xxx91n/mcp-for-maya/main/.github/assets/showcase-bonsai.png" width="440" alt="Low-poly L-system bonsai: recursive branches, foliage clusters, pot with moss and rocks"/> |
| `asset_import("vintage_pocket_watch")` + `asset_import("metal_tool_chest")` → `t20_workbench.build()` — "watchmaker workbench: imported assets with wired textures + procedural involute watch parts" | <img src="https://raw.githubusercontent.com/Xxx91n/mcp-for-maya/main/.github/assets/showcase-workbench.png" width="440" alt="Watchmaker workbench: imported pocket watch and tool chest, procedural gear parts"/> |
| `write_module` → `t20_street.build()` — "low-poly street corner block: 11 parametric buildings, gable roofs, awnings, street furniture, parked vehicles" | <img src="https://raw.githubusercontent.com/Xxx91n/mcp-for-maya/main/.github/assets/showcase-street.png" width="440" alt="Low-poly street block: 11 parametric buildings, awnings, street furniture"/> |
| `write_module` → `t20_teapot.build()` — "Utah teapot reproduction: lathe body profile, Bezier tapered spout, loop handle, checkerboard floor" | <img src="https://raw.githubusercontent.com/Xxx91n/mcp-for-maya/main/.github/assets/showcase-teapot.png" width="440" alt="Utah teapot reproduction: revolve body, Bezier tapered spout, checkerboard floor"/> |
| Running `scene_review()` on a cluttered workbench → `scene_plan(auto_fix=True)` + cleanup → re-running `scene_review()` — score jumped from **53.7 → 64.2** | <img src="https://raw.githubusercontent.com/Xxx91n/mcp-for-maya/main/.github/assets/audit-before.png" width="215" alt="scene_review before: cluttered workbench with default object names"/><img src="https://raw.githubusercontent.com/Xxx91n/mcp-for-maya/main/.github/assets/audit-after.png" width="215" alt="scene_review after: issues resolved, clean workbench"/> |

<p align="center"><img src="https://raw.githubusercontent.com/Xxx91n/mcp-for-maya/main/.github/assets/orbit.gif" width="100%" alt="Caliber orbit — 20 real playblast frames, 120° sweep"/></p>

Every frame can be reproduced using the scripts under [`.github/assets-src/`](https://github.com/Xxx91n/mcp-for-maya/tree/main/.github/assets-src).
