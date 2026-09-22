<p align="center">
  <img src=".github/assets/hero.png" width="100%" alt="mcp-for-maya — Give AI agents eyes inside Autodesk Maya"/>
</p>

# mcp-for-maya

> MCP server giving AI agents spatial awareness of Autodesk Maya scenes

English | [中文](README.md)

[![CI](https://github.com/Xxx91n/mcp-for-maya/actions/workflows/ci.yml/badge.svg)](https://github.com/Xxx91n/mcp-for-maya/actions/workflows/ci.yml) [![PyPI](https://img.shields.io/pypi/v/mcp-for-maya?cacheSeconds=300)](https://pypi.org/project/mcp-for-maya/) [![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![Python](https://img.shields.io/pypi/pyversions/mcp-for-maya)](https://pypi.org/project/mcp-for-maya/)

## What Is This

`mcp-for-maya` is a [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that lets LLM agents (Codex, Claude, etc.) directly drive Autodesk Maya for 3D modeling, scene planning, and engineering-grade delivery.

Forked from [chadrik/maya-mcp-server](https://github.com/chadrik/maya-mcp-server), it adds a scene-intelligence layer on top of the upstream connection stack: spatial awareness, deterministic auditing, transactional safety, and a visual loop.

**Key capability:** the agent stops "writing blind" — it can perceive spatial state, materials, and object relationships, then verify changes against engineering rules.

> [!WARNING]
> This server executes arbitrary Python inside Maya — that is a designed capability, not a bug. The built-in validation / rate-limit / audit pipeline is a **safety net for accidents and injected instructions, not a boundary against a malicious client**; the connected agent is trusted. See [docs/threat-model.md](docs/threat-model.md).

<img src=".github/assets/section-live-demo.svg" width="100%" alt="Live Demo — captured by the product itself"/>

Every asset below is a real capture produced by this project's own tool chain — no mockups: the demo scene was built via `execute_code`, the viewport stills come from `scene_viewport_snapshot`, and the orbit sequence comes from `camera_orbit` + `scene_render_preview` (Maya 2024 GUI session; the scene's RGB trio echoes the logo's gizmo tripod).

<p align="center"><img src=".github/assets/orbit.gif" width="640" alt="camera_orbit sequence — real playblast frames"/></p>

<p align="center">
<img src=".github/assets/shot-hero.png" width="49%" alt="scene_viewport_snapshot: persp viewport capture (HUD included)"/>
<img src=".github/assets/shot-alt.png" width="49%" alt="scene_viewport_snapshot: side angle (HUD included)"/>
</p>

## vs blender-mcp

An honest three-tier comparison with [ahujasid/blender-mcp](https://github.com/ahujasid/blender-mcp) (measured 2026-09):

| Tier | Contents |
|------|----------|
| **Unique to this project** | ICEV enforced workflow (in server instructions), CoS notation output, checkpoint/rollback transactional safety, scene_plan holistic planning (zone mapping + layout suggestions), multi-session management, 11 deterministic audit checks, playblast render preview with metadata |
| **Unique to blender-mcp** | Asset ecosystem (Poly Haven/Sketchfab/Hyper3D/Hunyuan3D), first-class object CRUD tools, AI-generated-model integrations, community scale |
| **Shared** | MCP tool surface, viewport screenshot feedback, arbitrary Python execution, local socket connection |

Asset integration is on our roadmap (Poly Haven thin slice, issue #2); AI generation and first-class object CRUD are explicitly out of scope — the latter is already covered by `execute_code`.

<img src=".github/assets/section-capability-matrix.svg" width="100%" alt="Capability Matrix"/>

| Capability | Tools | Notes |
|------------|-------|-------|
| 🧊 **Spatial awareness** | `scene_snapshot` `scene_inspect` `scene_measure` | One-call full-scene spatial model; precise distance/overlap/gap measurement |
| 🎨 **Aesthetic analysis** | `scene_aesthetics` | 5 dimensions: color theory (60-30-10), spatial composition (golden ratio / rule of thirds), proportion & scale (ergonomics), lighting quality (three-point / fill ratio / temperature / decay), visual flow |
| 🎬 **Camera planning** | `camera_create` `camera_orbit` | 8 industry-standard shot types + orbit animation |
| 🛡️ **Disaster recovery** | `scene_checkpoint` `scene_rollback` `scene_checkpoint_list` | exportAll in-memory snapshots; rollback explicitly rebinds the original path |
| 🧠 **Scene planning** | `scene_plan` | Organization health, zone balance, layout suggestions, conflict prevention, natural-language planning |
| 📋 **Engineering audit** | `scene_review` `scene_validate` `scene_assert` | 11 deterministic checks (0-100 score) + custom constraint validation + state assertions |
| ⚡ **Code execution** | `execute_code` `write_module` | Run arbitrary Python in Maya / inject reusable modules |
| 👁️ **Visual loop** | `scene_viewport_snapshot` `scene_render_preview` | WYSIWYG viewport capture + single-frame playblast preview (GUI sessions only) |
| 🔌 **Session management** | `list_sessions` `add_session` `maya_setup_guide` | Multi-session discovery/attach + connection diagnosis/install/fallback guidance |

20 MCP tools in total.

<img src=".github/assets/section-quick-start.svg" width="100%" alt="Quick Start"/>

### 1. Install

```bash
# Install from PyPI (recommended)
pip install mcp-for-maya

# or run straight away with uvx
uvx mcp-for-maya

# alternative: install from git with uv
uv tool install git+https://github.com/Xxx91n/mcp-for-maya.git

# or clone the source
git clone https://github.com/Xxx91n/mcp-for-maya.git
cd mcp-for-maya
pip install -e .
```

> [!NOTE]
> **Three-layer naming**: dist name `mcp-for-maya` (PyPI shelf name) → installs import package `maya_mcp_server` (kept from upstream); script name `mcp-for-maya` (old name `maya-mcp-server` remains as a compat alias). `uvx mcp-for-maya` resolves precisely because the command name matches the dist name.

### 2. Connect Maya

#### Option A: automatic (recommended)

With the MCP server running, the agent calls `maya_setup_guide` to walk the connection:

1. Make sure Maya is running
2. Give the agent any instruction (e.g. "look at my Maya scene")
3. If unconnected, the agent runs diagnostics and can install `userSetup.py` (idempotent marker-block merge, timestamped backup before writing)
4. After restarting Maya, the command port opens automatically

#### Option B: manual

In Maya's Script Editor (Python mode, not MEL):

```python
import maya.cmds as cmds
cmds.commandPort(name=':7001', sourceType='python')
```

#### Option C: persistent auto-connect

Save this as `userSetup.py` in your Maya scripts directory:

| Platform | Path |
|----------|------|
| Windows | `%MAYA_APP_DIR%\<version>\scripts\` |
| Linux | `~/maya/<version>/scripts/` |
| macOS | `~/Library/Preferences/Autodesk/maya/<version>/scripts/` |

```python
import maya.cmds as cmds
cmds.evalDeferred('cmds.commandPort(name=":7001", sourceType="python")', lowestPriority=True)
```

#### Multiple Maya instances

A `commandPort` is a single listening socket bound to one `host:port` — a second instance fails to bind the same port, so **each Maya instance needs its own port**. Typical topology:

| Maya instance | commandPort | Notes |
|---------------|-------------|-------|
| Instance A | `:7001` python | primary |
| Instance B | `:7002` python | second instance |
| Instance A | `:7011` mel | MEL port (auto-detected and exempted — no error spam) |

Run `cmds.commandPort(name=":<port>", sourceType="python")` inside each instance (its Script Editor or its own `userSetup.py`). **Auto-scan** is the primary path — the server periodically enumerates listening Maya ports and bootstraps them; if a session is missed, `add_session(host, port)` is the manual fallback. If scanning probes a non-Maya TCP service on the box, bound the probe set with `MAYA_MCP_INCLUDE_PORTS=7001,7002` (comma-separated, `7005-7010` ranges allowed) or exclude offenders via `MAYA_MCP_EXCLUDE_PORTS=<port>`.

Note: a `commandPort` does **not** persist across sessions — it dies with Maya; for persistence write it into `userSetup.py` (Option C).

#### Troubleshooting

| Problem | Fix |
|---------|-----|
| `list_sessions` returns empty | call `maya_setup_guide(action="diagnose")` |
| Port in use | close other Maya instances or pick another port |
| userSetup.py not loading | check it sits in the right scripts dir, restart Maya |
| Firewall blocks | ensure localhost:7001 is reachable |
| Second Maya instance not listed | each instance needs its own `commandPort` (same port = bind conflict); if scanning still misses it, call `add_session(host, port)` |
| Script Editor spams syntax errors | legacy symptom of probing a MEL port — current versions auto-exempt non-Python ports; if it persists, exclude the port via `MAYA_MCP_EXCLUDE_PORTS` |

### 3. Configure the MCP client

Codex `~/.codex/config.toml`:

```toml
[mcp_servers.maya]
command = "uvx"
args = ["mcp-for-maya"]
tool_timeout_sec = 120
```

For the git source use `args = ["--from", "git+https://github.com/Xxx91n/mcp-for-maya.git", "mcp-for-maya"]`; for a source checkout use `command = "python"`, `args = ["-m", "maya_mcp_server"]`, and point `PYTHONPATH` at `<repo>/src` under `env`.

### 4. Use it

Talk naturally:

> "Look at what's in my Maya scene, then create a display shelf at the entrance"

The agent calls `scene_snapshot()` → understands the scene → models → `scene_review()` audits the result.

<img src=".github/assets/section-icev-workflow.svg" width="100%" alt="ICEV Workflow"/>

Every scene modification follows the **ICEV** loop (also shipped as an agent process card, see `skills/icev-workflow`):

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ INSPECT  │ ──→ │ COMPUTE  │ ──→ │ EXECUTE  │ ──→ │ VERIFY   │
│ snapshot │     │  plan    │     │  apply   │     │  audit   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

1. **INSPECT**: `scene_snapshot()` for full-scene spatial data
2. **COMPUTE**: plan positions, sizes, clearances from that data
3. **EXECUTE**: `execute_code()` applies Maya Python
4. **VERIFY**: `scene_assert()` + `scene_review()` confirm the result; on GUI sessions the visual tools give pixel-level confirmation

## Tools Reference

### Spatial

```python
scene_snapshot(detail="compact", format="cos")   # full scene in one call
scene_inspect(target="wall_entrance", include_neighbors=True)
scene_measure(obj_a="wall_north", obj_b="counter_A", mode="clearance")
scene_assert(expectations='{"wall": {"exists": true, "position": [0,0,500]}}')
```

### Audit

```python
scene_review()   # 11 deterministic checks, 0-100 score
scene_validate(rules='[{"type": "min_clearance", "value": 180}]')
```

### Cameras

```python
camera_create(target="product_display", shot_type="medium", azimuth=30, elevation=15)
# extreme_wide / wide / medium / close / extreme_close / bird_eye / low_angle / over_shoulder
camera_orbit(center=[0, 100, 0], radius=500, frames=120)
```

### Disaster recovery

```python
scene_checkpoint(name="before_renovation")   # exportAll in-memory snapshot; no undo history
scene_checkpoint_list()
scene_rollback(filename="cp_before_renovation.ma")
# auto safety snapshot first, then rebinds the scene name to the original path
# call scene_snapshot() after a rollback — snapshots carry no undo history
# self-contained: references are flattened (no write-back); one scene file per session assumed
```

### Visual loop (GUI sessions only)

```python
scene_viewport_snapshot(max_size=800, format="jpeg")   # HUD/selection included — what the artist sees
scene_render_preview(camera="CAM_hero", width=640, height=360)   # clean single-frame playblast
# both return [image, JSON metadata]; headless sessions get a gui_session_required error
# prefer format="png" for wireframe/line-art review; trust returned metadata for actual size
```

## CoS Notation

Default output uses **Chain-of-Symbol** notation to compress scene data. The format's paper reports ~65% token savings vs JSON on its demo scenes (arXiv:2305.10276, −65.8%) — this project implements the notation; that figure is the paper's measurement, not a benchmark of this project.

```
SCENE[164obj, 5zones] UNIT=cm UP=y
shell (23obj) @(-11.8,178.8,145.7)
  GRP_floor[mesh]@(0,0,0) 1121.5x20x1530.5
```

## Agent Skills

Two **Experimental** process cards ship in `skills/`:

| Skill | Purpose |
|-------|---------|
| `skills/icev-workflow` | ICEV discipline: every scene mutation goes through Inspect→Compute→Execute→Verify |
| `skills/scene-review-playbook` | Audit playbook: what the 11 checks weigh and how to map findings to fixes |

> Evaluated on Claude Code only; untested on Codex/Gemini CLI/Cursor. Cross-model evaluation is tracked in issue #3.

<img src=".github/assets/section-audit-trust.svg" width="100%" alt="Audit & Trust"/>

`scene_review()` provides 11 universal checks (score normalized to 0-100):

| Check | Max pts | What it looks at |
|-------|---------|------------------|
| spatial | 10 | object/camera/light presence |
| overlaps | 10 | bbox collisions (parent-child excluded) |
| conflicts | 10 | penetration between unrelated objects |
| zones | 5 | naming-rule zone coverage |
| naming | 5 | production naming convention |
| components | 10 | GRP_ grouping + nesting depth ≤ 4 |
| orphans | 5 | empty groups / default names |
| aesthetics | 15 | 5-dimension aesthetics (color/composition/scale/lighting/flow) |
| lighting | 10 | three-point setup, fill ratio, decay |
| organization | 10 | overall hierarchy health |
| constraints | 5 | custom rule violations |

## Trust & Privacy

- **Zero telemetry**: no phone-home — the project ships no telemetry or outbound reporting code; verify in source.
- **Local, single-user**: the command port binds localhost only; the connected MCP client is trusted.
- **Safety net**: a unified pipeline validates arguments + token-bucket rate limits (~100/60s reads, ~20/60s writes, per session) + pattern scan (warn-only by default) + an independent JSONL audit log across all 20 tools. It catches accidents, not malicious clients — full model in [docs/threat-model.md](docs/threat-model.md).
- **Transactional safety**: `scene_checkpoint`/`scene_rollback` give in-memory snapshots and explicit rollback (no undo history; references flattened).
- Vulnerability reporting: [SECURITY.md](SECURITY.md).

## Versioning

This project follows [Semantic Versioning](https://semver.org/):

- **0.x (current 0.1.0, Alpha)**: the tool surface may still change; minor bumps carry features, no compatibility freeze.
- **Beta**: promoted once feature-complete and external testing begins (classifier moves to `4 - Beta`).
- **1.0.0**: public-API freeze commitment, promoted together with the `5 - Production/Stable` classifier in one commit.

Releases are milestone-driven — no fixed cadence promised. Roadmap lives in GitHub issues: #2 Poly Haven thin integration (v1.1), #3 Skills program (v1.x), #4 security & permission model (v1.x), #5 export_scene + scene-graph introspection (v1.x), #6 more asset sources (exploratory), #7 real-machine checklist + v1.0 feedback (pinned).

## Requirements

| Environment | Requirement |
|-------------|-------------|
| Host (runs the MCP server) | Python **>= 3.10** (`requires-python`); Windows / Linux / macOS |
| Injected helper (runs inside Maya) | Maya **>= 2023** (bundled Python >= 3.9; relies on `ast.unparse` — older versions get an explicit refusal at injection) |
| Verified against | Maya **2024** GUI |

The two visual-loop tools need a **GUI session** (headless/mayapy returns a structured capability error).

## Development

```bash
pip install -e ".[dev]"          # or: uv pip install -e ".[dev]"
python -m pytest tests/ -q       # tests
ruff check src tests             # lint
mypy src                         # typecheck
python -m maya_mcp_server -vv    # run with DEBUG logs (-v=INFO, -vv=DEBUG)
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the PR flow and [CHANGELOG.md](CHANGELOG.md) for the change log.

## Credits

Forked from [chadrik/maya-mcp-server](https://github.com/chadrik/maya-mcp-server) — upstream MIT copyright retained (see LICENSE); this project adds the scene-intelligence layer on top of its connection stack.

How each upstream open issue maps to a disposition and release version in this fork: [docs/upstream-issue-status.md](docs/upstream-issue-status.md).
