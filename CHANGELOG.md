# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.1] - 2026-09-24

### Fixed

- **Poly Haven single-asset texture wiring** — `split_texture_key()`
  only recognised compound `<part>_<suffix>` keys, so single-piece
  assets (e.g. `vintage_pocket_watch`, `metal_tool_chest`) silently
  downloaded zero textures and imported as untextured shells. Bare
  keys (`Diffuse`, `nor_gl`, `Metal`, `Rough`, `AO`, `ARM`, ...) now
  map to the asset's single unnamed part; compound matching is
  case-insensitive (`Body_Diff` no longer drops). Regression tests
  cover the bare-key and case-variant forms in `select_files()`
  (`tests/test_polyhaven.py::TestSelectFiles`).
- **Temp-file injection hygiene (D-082a)** — the native-channel
  fallback in `asset_tools.py::_ensure_asset_injected` and
  `scene_tools.py::_ensure_module_injected` staged module source at a
  predictable shared temp path with default perms and no cleanup; it
  now uses `mkstemp` under `platformdirs.user_cache_dir("mcp-for-maya")
  /inject`, chmod `0600`, try/finally unlink on success and failure
  (`tests/test_scene_tools.py::TestInjectionHygiene`,
  `tests/test_asset_tools.py::TestInjectionHygiene`,
  `tests/test_qt_channel.py::test_native_client_keeps_tempfile_fallback`).
- **Displacement wiring cleanup (D-082b)** — a `connectAttr` failure
  mid-wiring left a half-created `displacementShader` node orphaned in
  the scene; `_wire_map` now deletes it on every failure path
  (`src/maya_mcp_server/asset_module.py::_wire_map`,
  `tests/test_asset_module.py::TestDisplacement` — positive +
  negative + orphan-cleanup cases). Note: the R3 audit's "connection
  impossible" claim was refuted by a live Maya 2024 probe
  (`disp.displacement -> sg.displacementShader` connects —
  `.scratch/t21/probe-displacement.json`); "connected" is still not
  "renders correctly" — visual proof stays on the gui/human_verify tier.
- **Poly Haven surface hardening (D-082f)** — bare `int()` on
  API/HTTP-controlled fields could escape the `AssetError` domain as a
  raw `ValueError`; now `_as_int` maps them to `bad_response`
  (`src/maya_mcp_server/polyhaven.py`). The multi-MB `/assets` index
  carries a 300 s TTL cache (`SEARCH_INDEX_TTL_S`) so repeated
  `asset_search` calls don't re-pull the listing — unrelated to the
  download path's fresh-metadata revalidation rule. The supplementary
  `asset_import` audit row now records real download+import wall time
  instead of the `duration_ms: 0.0` placeholder
  (`src/maya_mcp_server/asset_tools.py::_audit_asset_download`,
  `tests/test_polyhaven.py::test_index_ttl_cache_bounds_calls`,
  `test_dirty_content_length_is_domain_error`,
  `test_dirty_size_in_payload_is_domain_error`,
  `tests/test_asset_tools.py::test_audit_duration_ms_is_measured`).
- **VP2 readback direction probed at runtime (D-082d)** —
  `_VP2_READBACK_BOTTOM_UP` was a compile-time constant arbitrating a
  runtime variable (cross-GPU differences were a known blind spot);
  `visual_module._vp2_direction` now resolves it per-session on first
  capture via an asymmetric pure-color probe — disposable ortho camera
  + red `surfaceShader` cube, net-zero (undo recording suspended
  without flushing, selection / panel camera / scene-dirty flag
  restored, every node deleted on every path). The constant is demoted
  to fallback default; `MAYA_MCP_VP2_BOTTOM_UP=0|1` is the documented
  override (`src/maya_mcp_server/visual_module.py::_probe_vp2_direction`,
  `tests/test_visual_tools.py::TestVp2DirectionProbe`).
- **0.2.0 changelog wording correction (D-082c)** — the cache
  mechanism was described as "manifest-based"; the actual mechanism is
  fresh-metadata revalidation + per-file size/md5 re-verification
  (`src/maya_mcp_server/polyhaven.py::_verify_local`), with
  `manifest.json` a write-only audit artifact.

### Changed

- **Camera default names use the `CAM_` prefix (D-082f)** —
  `create_camera_shot`/`create_orbit_camera` and their `camera_create`/
  `camera_orbit` tool wrappers default to `CAM_shot`/`CAM_orbit`
  instead of `shot_cam`/`orbit_cam`, matching the project's own naming
  audit (`maya_scene_module.py::_MAYA_STANDARDS`,
  `src/maya_mcp_server/scene_tools.py:685`). Externally visible:
  unnamed camera calls now produce `CAM_*` nodes.
- **Generated materials are `standardSurface` (D-082e)** —
  `_new_material` emits Maya's PBR default instead of `blinn`; the
  texture wiring table is attribute-aware: color -> `color|baseColor`,
  roughness -> `specularRoughness|roughness`, metalness ->
  `metalness|metallic` (the old `reflectivity` fallback is dropped —
  specular strength is not metalness), normal -> `normalCamera`,
  AO -> `base|diffuse` (`src/maya_mcp_server/asset_module.py`,
  `tests/test_asset_module.py::TestStandardSurface`). The stub material
  attribute model was re-pinned to live-probe evidence: blinn carries
  `reflectivity`/`specularRollOff` but no `specularRoughness`;
  standardSurface has no `color`/`diffuse`/`ambientColor` and gains
  `base` (`tests/maya_stub/scene.py`).
- **README facade rework (T-20, D-078~D-081)** — design banner restored
  at top (`hero.svg` embeds a real `scene_viewport_snapshot` HUD capture
  in its viewport slot); all demo imagery consolidated into one
  `Prompt | Result` showcase table (involute watch movement, low-poly
  L-system bonsai, Poly Haven workbench, low-poly street block,
  Utah teapot recreation, `scene_review` before/after pair at 53.7→64.2)
  plus a full-width 20-frame orbit GIF; every image reference is an
  absolute `raw.githubusercontent.com` URL on `main` so assets render
  on PyPI (a living-branch reference by design — `.github/assets/` is
  append-only so historical release pages keep rendering); generation
  scripts checked in under
  `.github/assets-src/t20/`; `README.zh-CN.md` mirrored (anchor
  `f8e6869`). Retired: `hero.png`, `row1-4`, `shot-hero`, `shot-alt`.

## [0.2.0] - 2026-09-23

### Added

- **Poly Haven asset library (T-19a, D-074/D-075)** — two new tools
  bringing the count to 22:
  - `asset_search` — host-side Poly Haven index query
    (`api.polyhaven.com/assets`); read-only, needs no Maya session.
  - `asset_import` — downloads the model (FBX + textures) via
    HTTPS into a platformdirs cache, then imports into Maya.
  - Host-side guardrails in `polyhaven.py`: HTTPS + host whitelist
    (`api.polyhaven.com`, `dl.polyhaven.org`, `dl.polyhaven.com`),
    mandatory User-Agent, timeout, per-file 256 MiB / per-call 512 MiB
    caps, official per-file md5 verification + sha256 audit records,
    cache reuse gated on fresh /files metadata revalidation plus
    per-file size and md5 re-verification (`manifest.json` is a
    write-only audit artifact, never a cache-validity source —
    no silent stale-cache serving; offline yields the structured
    `network_unavailable` error).
  - Maya-side `_mcp_asset` (lazy-injected, zero network by design):
    fbxmaya plug-in gate, `FBXImportConvertUnitString=m` unit lock,
    `GRP_asset_<asset_id>` grouping with same-name dedup (repeat
    imports report the existing group; `force=True` opts out),
    default 100k-face polycount gate (`allow_high_polycount`
    override, audited), post-import dims sanity warnings, texture
    auto-wiring by filename suffix (`diff/rough/metal/nor_gl/ao/disp/
    arm`) with sRGB/Raw color spaces and bump2d normal maps.
  - Both tools carry audit rows incl. download URL/size/hash detail,
    and are the first tools annotated `openWorldHint=True`
    (threat-model §4/§5 updated accordingly).
- **README restructure (T-19b, D-072)** — `README.md` is now the
  English source-of-truth; the Chinese text moved to
  `README.zh-CN.md` (convenience mirror carrying a `synced-with`
  commit anchor); `README_en.md` deleted. Language selectors sit
  above all content, and CI now runs a heading-skeleton parity check
  (.github/scripts/check_readme_skeleton.py) in the lint job.

### Fixed

- Stub/`maya.cmds` surface extended for the asset path
  (`maya.mel.eval`, `pluginInfo`, `loadPlugin`, `shadingNode`,
  `createNode`, `setAttr`, `connectAttr`, `disconnectAttr`,
  `polyEvaluate`, `exactWorldBoundingBox`, `sets` create/edit,
  `objectType isAType=dagNode`, FBX-import fixture via `cmds.file`)
  — all verified present on real Maya 2024 and recorded in
  `presence-baseline.json`.
- `ruff --fix` import-sort cleanups in `scene_tools.py` /
  `aesthetic_engine.py`; frozen budget ratcheted down
  (src E401/I001 -> 0).

## [0.1.2] - 2026-09-22

> First real-Maya verification round: everything below was found by
> running the shipped 0.1.1 code against a live Maya 2024 GUI session.
> The stub suite was green on all of it — each fix ships with the stub
> modeling the real semantic that was missing. A second live pass (T-18a)
> re-verified the whole gui tier on Maya 2024.0.0.4640.

### Fixed

- `create_module(overwrite=True)` now invokes the old module's
  `_mcp_teardown` hook before evicting it from `sys.modules`; the
  injected helper ships an idempotent teardown that disconnects the Qt
  `newConnection` signal, deleteLater's the listener and sockets, and
  restores stream capture. Reconnect-time helper reloads no longer orphan
  a listening `QtCommandServer` (upstream #4, D-058).
- Port-type probing switched from `1+1` to the bilingual
  `eval("1/2")` payload — Python 3 answers `0.5`, anything else
  classifies MEL. Live-verified on Maya 2024: a real MEL port replies
  with a syntax-error body (MEL `eval` wants a command string), which
  still classifies correctly — the Script Editor sees at most one
  error line per probe. Ports that answer as non-Python join a
  session-level permanent exemption set (lifted only when the port
  leaves LISTEN), ending the periodic re-probe spam (upstream #1, D-059).
- Probe filtering productized: `MAYA_MCP_INCLUDE_PORTS` /
  `MAYA_MCP_EXCLUDE_PORTS` env vars (or the `SessionManager`
  `include_ports` / `exclude_ports` ctor args) bound which discovered
  ports are probed at all.
- `maya_mcp_helper` refuses injection on Maya < 2023 (Python < 3.9)
  with an actionable message, and missing `ast.unparse` degrades to
  no-result-capture instead of `AttributeError` (upstream #3, D-060).
- `serverInfo.version` now reports the product version
  (`importlib.metadata.version("mcp-for-maya")` with a `__version__`
  source-tree fallback) instead of leaking the FastMCP framework
  version (D-060).
- The `_bootstrap` hot-update path now logs a failing `_mcp_teardown`
  carried in `create_module`'s `warning` field instead of dropping the
  response on the one path that triggers the hook (D-065/N1).
- `_bootstrap` hot-update now surfaces a failed `create_module` — the
  `module_create_failed` error arrives inside the result payload (the
  native commandPort wrap), and it was swallowed behind a false "module
  updated" log (N7). It now raises `MayaExecutionError` like
  `write_module` does.
- Bootstrap no longer rewrites a >10K helper module on every connect:
  the injected module's `_mcp_source_sha` stamp (a content hash of the
  helper source, self-stamped at inject time — no manual marker to
  forget) is compared first and the hot-update write is skipped when it
  matches. The big write is what tripped the commandPort stale-response
  quirk and intermittently stranded the just-started Qt server (connect
  refused on a live bind); skipping it removes the flake. A bounded
  connect+ping retry still covers genuinely slow Qt servers (T-18a,
  live-verified).
- Fallback hygiene: when the Qt channel is unavailable, the bootstrap
  reaps the orphan Qt listener it just started (a pre-existing listener
  is left alone — it may serve other clients), and the dedicated
  commandPort — on either the explicit native branch or the fallback
  path — is closed on `disconnect()` instead of leaking (T-18a).


- `execute_code` coerces `result_type` to `ResultType` at the client
  entry — bare `"JSON"` strings passed by `scene_tools`/`visual_tools`
  crashed with `'str' object has no attribute 'value'`, taking down the
  entire `scene_*` surface and both visual tools on real transports
  while the stub suite stayed green (D-046). Invalid values now raise
  `InputValidationError` instead of `AttributeError`.
- `scene_snapshot`/`scene_review`: removed a dead MItDag preamble that
  ran `MSelectionList.add("*")` + `getDagPath` — the wildcard matches
  non-DAG nodes on real Maya and `getDagPath` raises
  `TypeError: item is not a DAG path`.
- `scene_rollback`: the S2 scene rebind calls `cmds.file(rename=...)`
  alone — real Maya rejects flag combos with `-rename` ("the -rename
  flag must be used by itself"), which previously left the scene bound
  to `cp_*.ma` with `rebind_failed`.
- Visual capture: `MImage` resolves across Maya API layouts
  (`maya.api.OpenMaya` on ≤2024, `maya.api.OpenMayaUI` on 2025+). The VP2
  kFloat readback now asks for RGBA at the source
  (`readColorBuffer(img, readRGBA=True)`) and lets `writeToFile` do the
  float→byte conversion — the `floatPixels()` pointer-wrap path was
  removed entirely because `MScriptUtil` no longer exists in Maya 2024
  (D-056⑤; `convertPixelFormat` is a C++-only API and is never called).
  Row orientation stays under the assertion-pinned
  `_VP2_READBACK_BOTTOM_UP` constant — re-pinned to `False` on
  2024.0.0.4640, where readColorBuffer hands back top-down rows (T-18a).
  When neither module provides `MImage`, tools return a structured
  `capture_unsupported` error instead of `AttributeError`.
- Runtime `__version__` matches `pyproject.toml` (was 0.1.0 vs 0.1.1).

### Docs

- README (bilingual) + `docs/testing.md`: dual-runtime support matrix
  (host Python >= 3.10; injected helper needs Maya >= 2023 / Python >=
  3.9; verified on Maya 2024) and a multi-instance commandPort section
  covering per-instance topology, auto-scan vs `add_session`, and
  userSetup.py persistence (upstream #5, D-060).
- `docs/upstream-issue-status.md` maps the six upstream open issues to
  this fork's disposition, fix version, and verification status;
  human-gated comment drafts live in
  `docs/upstream-issue-response-drafts.md` (D-064).

### Testing

- New `gui` + `human_verify` markers (`--strict-markers` now enforced):
  the live-GUI tier env-probes for a reachable framed session and skips
  cleanly without one; `human_verify` holds explicit manual-confirmation
  skeletons — agents execute and leave evidence, sign-off is human
  (D-049a).
- Presence-baseline ratchet (D-049b/D-056①): `tests/maya_stub/
  presence-baseline.json` collected on live Maya 2024 + allowlist +
  auto-diff tests — a stub symbol missing from real Maya now fails the
  build unless explicitly allowlisted with a reason. (Renamed from
  signature-baseline: cmds builtins carry no inspectable signature, so
  presence + method lists are the auditable contract.)
- Stub honesty: `ls` string patterns filter by name and `*` never
  crosses the namespace `:`; `cmds.file(rename=...)` enforces the
  standalone-flag constraint; `MSelectionList.add("*")` appends a
  non-DAG sentinel so `getDagPath` raises like real Maya.
- `execute_code` regression tests cross the real transport seam
  (fake reader/writer, wire-payload assertions) on both channels —
  closing the mock-the-transport gap that shipped the 0.1.1 defect.
- The `mayapy` tier initializes `maya.standalone` once per session;
  bare mayapy hard-crashes on `import maya.api.OpenMaya` without it.

### Known issues

- mayapy / `maya -batch` are environment-blocked on at least one dev
  box (native access violation / hang) — Tier-2 substance was verified
  through the live GUI session instead; see docs/testing.md.
- Multi-client rendering verification (Inspector/Claude Code/Codex
  seats) remains pending user environments.
- Maya 2025/2026 coverage absent — the `MImage` dual-layout fix is
  written for them but untested there.

## [0.1.1] - 2026-09-19

### Fixed

- `scene_render_preview`/`scene_viewport_snapshot` camera switching uses the `modelPanel`
  named-argument API instead of `cmds.lookThru`'s ambiguous positional forms; the
  single-argument fallback path is removed (D-039).
- `compute_lighting_quality_score` no longer raises `KeyError` on lights whose names
  match no role keyword (D-038; module stays dormant — zero production references —
  pending the T-06 consolidation decision).
- `scene_review` overlap and conflict checks, and `scene_plan` near-miss: the parent-child
  exclusion now uses a DAG-path prefix test instead of basename substring matching —
  sibling names like `GEO_wall`/`GEO_wall2` are correctly flagged again in all three
  dimensions (D-037).
- Native commandPort client: commands now carry the mandatory `\n` terminator (the
  channel executes on newline — without it a command parked in Maya's buffer until the
  next send); a dropped/closed connection now raises `MayaUnavailableError` instead of an
  execution error or a silent empty result, matching the Qt channel's typed errors (D-041).

### Testing

- Stub GUI surface: `modelPanel` added; `modelEditor`/`modelPanel` camera edits resolve
  node names; `lookThru` rewritten type-disambiguated (both arg orders, like the real
  command) with a warn-by-default / strict-on-demand policy for unclassifiable args
  (D-039).

## [0.1.0] - 2026-09-19

### Added

- Scene-intelligence layer on top of the upstream connection stack: 13 scene tools (snapshot / inspect / measure / assert / validate / checkpoint / rollback / checkpoint_list / camera_create / camera_orbit / aesthetics / review / plan) plus 2 GUI-only visual tools (scene_viewport_snapshot, scene_render_preview) — 20 MCP tools total.
- ICEV (Inspect-Compute-Execute-Verify) workflow enforced in server instructions; two experimental agent process cards under `skills/` (icev-workflow, scene-review-playbook).
- Unified pipeline across all tools: argument validation, per-session token-bucket rate limits, warn-only pattern scan, independent JSONL audit log.
- Transactional safety: exportAll in-memory checkpoints with whitelisted filenames, automatic safety snapshot before rollback, explicit scene rebind.
- Qt framed working channel (length-prefixed frames, up to 16 MiB) with a minimal native commandPort fallback for headless sessions.
- `maya_setup_guide` (diagnose / install / guide / uninstall) with idempotent marker-block merge into userSetup.py and timestamped backups.
- Project docs: CHANGELOG.md, CONTRIBUTING.md, SECURITY.md, docs/threat-model.md, docs/adr/*, docs/testing.md, dual README (中文 + English).
- GitHub Actions CI: a lint job enforcing the frozen ruff budget (`.github/ruff-baseline.json`, ratchet-down-only) and a pytest matrix over ubuntu/windows x CPython 3.10/3.x; a release workflow on `v*` tags (test -> build -> publish via Trusted Publisher, `pypi` environment, PEP 740 attestations); Dependabot for GitHub Actions.

### Changed

- Distribution renamed to `mcp-for-maya` (import package stays `maya_mcp_server`); console scripts are now `mcp-for-maya` plus `maya-mcp-server` as a compatibility alias; project URLs point to Xxx91n/mcp-for-maya.
- README rewritten: honest three-tier blender-mcp comparison, code-sourced numbers (20 tools, 11 audit checks with real weights, CoS figure attributed to its paper), a real `skills/` section, zero-telemetry statement, and a versioning policy.
- Two-layer error contract: host-side failures surface via MCP isError with a code prefix; Maya-side results return `{error:{code,message,suggestion}}`.

### Fixed

- JSON-serialized argument passing across scene tools (closes the string-interpolation injection surface in scene_validate / scene_measure / scene_assert).
- scene_checkpoint now snapshots in-memory state via exportAll instead of copying the last saved file; rollback whitelists basenames and rebinds the scene path explicitly.
- World-bbox math unified on the 8-corner transform for rotated objects.
- scene_review check list, weights, and sampling limits aligned to the implementation.
- add_session now uses the post-bootstrap dedicated-port client; Qt channel rewritten to event-driven reads with per-connection queues.
- Qt working channel maps the whole `ConnectionError` family (RST/FIN/aborted/refused) to `MayaUnavailableError`, fixing the Windows-only `test_connection_closed_raises_unavailable` failure (WinError 64).

### Removed

- Phantom references: LOGLEVEL env var, scripts/secrets.py, scripts/dependency.py, and the "4 Codex Skills" README promise (replaced by the real `skills/` cards).
