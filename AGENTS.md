# AGENTS.md — Maya MCP Server

## Project Overview

This is an MCP (Model Context Protocol) server for Autodesk Maya. It enables LLM agents to interact with Maya sessions through structured tools for spatial awareness, camera planning, aesthetic analysis, and scene auditing.

## Repository Structure

```
src/maya_mcp_server/
├── server.py              # FastMCP server entry point, tool registration
├── client.py              # Maya connection client (native + Qt)
├── session_manager.py     # Multi-session management
├── maya_mcp_helper.py     # Maya-side helper (executed inside Maya)
├── maya_bootstrap.py      # Maya bootstrap code (create_module)
├── scene_tools.py         # 13 MCP scene tool definitions
├── visual_tools.py        # 2 GUI-only visual tools (D-023..D-026)
├── scene_cache.py         # TTL + dirty-detection cache
├── cos_formatter.py       # Chain-of-Symbol notation formatter
├── maya_scene_module.py   # Maya-side module (injected via write_module)
├── visual_module.py       # Maya-side _mcp_visual (lazy inject, GUI only)
├── asset_tools.py         # asset_search/asset_import MCP tools (D-074/D-075)
├── asset_module.py        # Maya-side _mcp_asset importer (lazy inject)
├── polyhaven.py           # Poly Haven host client: whitelist/md5/cache (D-075)
├── spatial_types.py       # Data type definitions
├── connection_guide.py    # Connection bootstrap; userSetup.py managed marker-block (D-017)
├── security.py            # Validation, token-bucket rate limits, pattern scan, JSONL audit
├── pipeline.py            # FastMCP middleware: all 22 tools -> validate/rate-limit/scan/audit
├── types.py               # Core types (ResultType, ClientType, SessionInfo)
├── bootstrap.py           # Server bootstrap
├── utils.py               # Utility functions (cross-platform process detection)
└── __main__.py            # Entry point

tests/
├── maya_stub/             # stub maya.cmds + OpenMaya + Scene graph (D-004/D-005)
├── conftest.py            # maya_env fixture installs stub, binds maya_scene_module
├── test_checkpoint_rollback.py  # T-03 checkpoint/rollback regression (ADR-0004/D-015)
├── test_pipeline.py             # T-04 unified pipeline + audit JSONL + annotations (D-018/D-019)
├── test_client.py             # typed errors, write_module, bootstrap fallback
├── test_qt_channel.py         # T-05 framed codec/dispatch/ClientChannel/Qt roundtrip (D-013)
├── test_connection_guide.py
├── test_cos_formatter.py
├── test_maya_scene_module.py    # module-level regressions on the stub
├── test_maya_stub.py            # stub self-verification (math must stay honest)
├── test_mayapy_smoke.py         # real-Maya tier, manual local only (-m mayapy)
├── test_gui_session.py          # live-GUI tier, real asserts (-m gui; MAYA_MCP_GUI_ADDR probe) (D-049a)
├── test_human_verify.py         # versioned manual checklist (-m human_verify; prints steps, always skips)
├── test_prepare_code.py
├── test_scene_cache.py
├── test_scene_tools.py
├── test_scene_tools_json.py     # tool-layer JSON arg passing + error passthrough
├── test_visual_tools.py         # T-08 visual loop contract tests (D-023..D-027)
├── test_security.py
├── test_session_manager.py
├── test_module_teardown.py   # T-16a overwrite teardown protocol + Qt signal semantics (D-058, upstream #4)
├── test_version_unification.py # T-16e serverInfo=product version (D-060③)
├── test_aesthetic_engine.py     # dormant-engine unit coverage (D-038; not a production-path claim)
├── test_polyhaven.py        # T-19a host client: whitelist/md5/cache/domain errors (D-075)
├── test_asset_module.py     # T-19a _mcp_asset importer on the stub scene
├── test_asset_tools.py      # T-19a tool layer: dedup/domain errors/audit detail
├── test_check_ruff_budget.py    # ruff-budget comparator guard (per-rule ratchet, D-044/T-10b)
└── test_presence_baseline.py    # presence-baseline auto-diff vs real Maya (D-049b/D-056①)

docs/
├── adr/                   # ADR-0001..0024 architecture decision records
├── decision-ledger.md     # grill decision ledger — canonical path since T-11a (D-041)
├── handoffs/              # round handoffs — canonical (next-round.md standing task book)
├── testing.md             # real-Maya manual tier checklist
└── threat-model.md        # threat model + security boundaries

.github/
├── workflows/ci.yml       # lint (ruff budget gate) + README skeleton check + test matrix ubuntu/windows x 3.10/3.x
├── workflows/release.yml  # tag v* -> test -> build -> publish (trusted publisher; env: pypi)
├── dependabot.yml         # weekly github-actions bumps, minor+patch grouped
├── ruff-baseline.json     # frozen lint budget {"src":{"RULE":N},"tests":{...}} — per-rule ratchet down only (T-10b/D-044)
├── scripts/check_ruff_budget.py  # budget comparator used by the lint job
├── scripts/check_readme_skeleton.py  # README/zh-CN title-skeleton parity check (D-072)
├── assets-src/            # reproducible capture scripts for README imagery (scene_build.py + capture.py; T-19c)
└── assets/                # published README imagery (populated only after sign-off)
```

## Key Architecture Decisions

1. **No Maya client modification** — everything works through existing `execute_code` + `write_module` channels
2. **Maya-side module injection** — `_mcp_scene` is injected once via `write_module` on first scene tool call
3. **Large module handling** — GUI/Qt sessions inject modules of any size directly via the framed channel (16 MiB cap, D-013); temp-file injection is retained only for headless/native commandPort sessions
4. **Response alignment** — `execute_code` handles both `str` and `dict` results to prevent `json.loads` errors
5. **CoS notation** — Chain-of-Symbol format compacts scene tokens (the CoS paper reports ~65% savings vs JSON on its demo scenes, arXiv 2305.10276 — a paper figure, not a local benchmark)

## ICEV Workflow

Every scene modification must follow:
1. **INSPECT**: `scene_snapshot()` — understand current state
2. **COMPUTE**: Use spatial data to calculate changes
3. **EXECUTE**: `execute_code()` — apply changes
4. **VERIFY**: `scene_assert()` + `scene_review()` — confirm results

## scene_review Dimensions (Universal)

The audit tool is generic — works for ANY Maya project:

| Dimension | Score | What it checks |
|-----------|-------|----------------|
| spatial | 10 | Object count, cameras, lights |
| overlaps | 10 | BBox collision (excludes parent-child) |
| conflicts | 10 | Penetration detection (excludes env objects like SUN) |
| zones | 5 | Naming-rule zone coverage |
| naming | 5 | Maya production naming convention |
| components | 10 | GRP_ grouping + nesting depth ≤ 4 |
| orphans | 5 | Empty groups, default names |
| aesthetics | 15 | 5-dim score: color/composition/scale/lighting/flow |
| lighting | 10 | Three-point setup, fill ratio, decay |
| organization | 10 | Hierarchy health |
| constraints | 5 | Max objects, custom rules |

## Maya Connection Setup Guide

When `list_sessions` returns empty, use `maya_setup_guide()` to diagnose and fix.

### Workflow

1. **Diagnose**: `maya_setup_guide(action="diagnose")` — checks Maya process, port, userSetup.py
2. **Install**: `maya_setup_guide(action="install")` — auto-generates userSetup.py in Maya scripts dirs
3. **Guide**: `maya_setup_guide(action="guide")` — full step-by-step fallback instructions for user
4. **Uninstall**: `maya_setup_guide(action="uninstall")` — removes installed userSetup.py

### Auto-Setup (userSetup.py)

The generated `userSetup.py` opens Maya command port on startup using `evalDeferred` for safety.

**Platform-specific paths:**
- **Windows**: `%MAYA_APP_DIR%\<version>\scripts\userSetup.py`
- **Linux**: `~/maya/<version>/scripts/userSetup.py`
- **macOS**: `~/Library/Preferences/Autodesk/maya/<version>/scripts/userSetup.py`

### Fallback (Manual Setup)

If userSetup.py does not work, guide the user to:
1. Open Maya Script Editor (Windows > General Editors > Script Editor)
2. Switch to **Python** mode (not MEL)
3. Execute: `import maya.cmds as cmds; cmds.commandPort(name=":7001", sourceType="python")`

### Cross-Platform Notes

- Process detection (`utils.py`) handles Windows/Linux/macOS Maya process names
- `connection_guide.py` auto-detects platform and Maya installation paths
- Linux: Maya may appear as `maya`, `MayaBin`, or `maya-bin`
- All file paths use `pathlib.Path` for cross-platform compatibility

## Maya Naming Convention

- `GRP_` for groups, `GEO_` for geometry, `MAT_` for materials
- `CAM_` for cameras, `LGT_` for lights, `LOC_` for locators
- NEVER use default Maya names (pCube1, group1, etc.)

## Development Commands

```bash
# Run tests
python -m pytest tests/ -q

# Lint vs frozen per-rule budget (.github/ruff-baseline.json — ratchet down only)
ruff check .

# Typecheck vs frozen baseline (mypy-baseline.txt — fails only on NEW errors)
python -m mypy src/ | mypy-baseline filter

# Run with debug logging (-v=INFO, -vv=DEBUG)
python -m maya_mcp_server -vv

# Security audit
semgrep scan --config auto src/
```

## Known Quirks

- Maya command port produces stale responses when large modules (>10K chars) are written. Qt sessions use the framed channel directly; the temp-file fallback is retained only for headless/native sessions (D-013).
- `execute_code` with `result_type="JSON"` may receive `dict` directly (not `str`). The client handles both.
- Stream capture auto-installs on first `get_client()` call.
- `import X; X.func()` pattern can fail with `prepare_code_for_result_capture`. Pre-import with `execute_code("import X", NONE)` then use expression-only calls.


## Cross-Module Dependency Rules (联动规范)

When modifying any module, the following files MUST be updated together.
Failure to update dependent files will cause integration failures.

### Module Dependency Map

| Module Modified | Must Also Update | Reason |
|----------------|------------------|--------|
| `maya_scene_module.py` (scene_plan) | `scene_tools.py`, `server.py`, `README.md`, `README.zh-CN.md` | Scene planning tool needs MCP tool + docs |
| `maya_scene_module.py` (aesthetic functions) | `aesthetic_engine.py`, `scene_tools.py`, `tests/test_aesthetic_engine.py` | Aesthetic engine is dual-implemented (standalone + Maya-side); tool descriptions must match; tests must cover |
| `maya_scene_module.py` (lighting functions) | `scene_tools.py`, `tests/test_aesthetic_engine.py` | Lighting data fields must match tool expectations |
| `maya_scene_module.py` (scene_review) | `scene_tools.py` (scene_review docstring), `server.py` (instructions) | Review check names must match tool args; instructions must list all checks |
| `maya_scene_module.py` (new function) | `scene_tools.py` (new tool), `server.py` (instructions), `README.md`, `README.zh-CN.md`, `tests/` | Every new Maya function needs a corresponding MCP tool, docs, and tests |
| `visual_module.py` (capture paths) | `visual_tools.py`, `server.py` (instructions), `docs/adr/0013-visual-loop-architecture.md`, `tests/test_visual_tools.py` | Capture contract, annotations, and ADR must stay in sync |
| `visual_tools.py` (tool surface) | `pipeline.py` (TOOL_ANNOTATIONS), `server.py` (instructions), `docs/threat-model.md` (§5 matrix), `README.md`, `README.zh-CN.md` | Tool surface changes require annotation + docs sync |
| `asset_tools.py` / `polyhaven.py` / `asset_module.py` (asset surface) | `pipeline.py` (TOOL_ANNOTATIONS), `server.py` (instructions + shared audit), `docs/threat-model.md` (§4/§5), `tests/test_polyhaven.py`, `tests/test_asset_module.py`, `tests/test_asset_tools.py`, `tests/maya_stub/` (new cmds surface), `README.md`, `README.zh-CN.md`, `AGENTS.md` | Asset tools split host (download/cache) vs Maya-side (import/wire); every piece must stay in sync |
| `scene_tools.py` (new tool) | `server.py` (instructions), `README.md`, `README.zh-CN.md`, `AGENTS.md` | Tool surface changes require documentation sync |
| `aesthetic_engine.py` | `maya_scene_module.py` (mirror functions), `tests/test_aesthetic_engine.py` | **DORMANT** (T-11b/D-038, ADR-0003 status note): zero production refs - Maya-side inline `_score_*` is the live implementation; kept for the T-06 consolidation decision |
| `scene_cache.py` | `scene_tools.py` (cache invalidation), `session_manager.py` (mark_dirty) | Cache behavior must be consistent |
| `security.py` | `pipeline.py` (enforcement point), `tests/test_security.py`, `tests/test_pipeline.py` | Security rules enforced by the middleware pipeline, not per-tool |
| `pipeline.py` | `server.py` (middleware registration + annotations), `scene_tools.py` (annotations), `docs/threat-model.md` | Pipeline/threat-model must stay in sync |
| `connection_guide.py` | `server.py` (maya_setup_guide params), `tests/test_connection_guide.py` | Marker-block semantics + confirm/dry_run/remove_empty_file flags |
| `cos_formatter.py` | `scene_tools.py` (COS format output) | Formatter changes affect all tool COS outputs |
| `maya_scene_module.py` (scene_review check names/semantics) | `skills/scene-review-playbook/SKILL.md` | Card documents the 11 checks + findings→actions; check renames/semantics changes must sync it |

### Aesthetic Module Change Checklist

When modifying ANY aesthetic-related code, update ALL of these:

1. **`maya_scene_module.py`** — Maya-side `analyze_aesthetics()` + `_score_*()` functions
2. **`aesthetic_engine.py`** — **dormant** module (zero production refs; sync optional until the T-06 consolidation — Maya-side inline `_score_*` is the live implementation)
3. **`scene_tools.py`** — `scene_aesthetics` tool docstring + COS format output
4. **`maya_scene_module.py`** — `scene_review()` aesthetics section (must read new format)
5. **`server.py`** — MCP instructions (aesthetic dimension descriptions)
6. **`tests/test_aesthetic_engine.py`** — Unit tests for all dimensions
7. **`README.md`** + **`README.zh-CN.md`** — Feature descriptions
8. **`AGENTS.md`** — This checklist (if new dimensions added)

### Lighting Module Change Checklist

When modifying lighting analysis:

1. **`maya_scene_module.py`** — Light data collection in `analyze_aesthetics()` + `_score_lighting_quality()`
2. **`aesthetic_engine.py`** — `compute_lighting_quality_score()` (**dormant** — optional sync; Maya-side inline is authoritative)
3. **`scene_tools.py`** — `scene_aesthetics` and `scene_review` tool docs
4. **`maya_scene_module.py`** — `scene_review()` lighting section
5. **`tests/test_aesthetic_engine.py`** — Lighting tests

### Scene Review Change Checklist

When modifying `scene_review()`:

1. **`maya_scene_module.py`** — `scene_review()` function
2. **`scene_tools.py`** — `scene_review` tool docstring (check names must match)
3. **`server.py`** — Instructions (list all review checks)
4. **`README.md`** + **`README.zh-CN.md`** — Review capabilities description
5. **`tests/`** — Review tests

### Naming Convention Rules

- Groups: `GRP_` prefix (e.g., `GRP_store_shell`, `GRP_display_main`)
- Geometry: `GEO_` prefix (e.g., `GEO_wall_north`)
- Materials: `MAT_` prefix (e.g., `MAT_dark_wood`)
- Cameras: `CAM_` prefix (e.g., `CAM_entrance_wide`)
- Lights: `LGT_` prefix with role (e.g., `LGT_key_main`, `LGT_fill_ambient`, `LGT_accent_spot`)
- Locators: `LOC_` prefix
- Root groups must use `GRP_` prefix
- No default Maya names (`pCube`, `pSphere`, `group1`, etc.)
- Max nesting depth: 4 levels
- All meshes must be under a `GRP_` parent

### Group-Based Layout Rules

Every object in the scene MUST belong to a GRP_ group. The scene_plan tool provides:

1. **Intelligent Auto-Fix**: Automatically categorizes orphan objects into 9 zone groups:
   - GRP_shell: walls, floors, ceilings, structure
   - GRP_entrance: doors, gates, lobby
   - GRP_display: shelves, counters, kiosks
   - GRP_ip_core: characters, figures, mascots
   - GRP_furniture: tables, chairs, benches
   - GRP_lighting: lights, spots, LEDs
   - GRP_path: aisles, corridors, walkways
   - GRP_decor: signs, banners, decorations
   - GRP_service: checkout, storage, staff areas

2. **Group-Level Layout**: Analyzes group positions for overlaps, spacing, and zone compliance
3. **Natural Language Planning**: Parses user objectives into structured execution plans
4. **Zone Compliance**: Maps groups to functional zones (entrance → display → circulation → service)

### ICEV Workflow (Mandatory)

Every scene modification MUST follow:

1. **INSPECT** — `scene_snapshot()` to get current state
2. **COMPUTE** — Calculate changes based on spatial data
3. **EXECUTE** — `execute_code()` to apply changes
4. **VERIFY** — `scene_assert()` or `scene_review()` to confirm

### Error Detection Rules

The `scene_review()` function now detects:

- **Orphan objects**: Root-level meshes not under `GRP_` groups
- **Empty groups**: `GRP_` groups with no children
- **Inconsistent naming**: Too many single-use naming prefixes
- **Excessive depth**: Hierarchy deeper than 4 levels
- **Spatial conflicts**: Objects penetrating non-parent objects
- **Aesthetic weaknesses**: Dimensions scoring below 40/100
- **Lighting issues**: Missing three-point setup, poor fill ratio, non-physical decay
