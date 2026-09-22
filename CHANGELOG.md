# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-09-20

> First real-Maya verification round: everything below was found by
> running the shipped 0.1.1 code against a live Maya 2024 GUI session.
> The stub suite was green on all of it — each fix ships with the stub
> modeling the real semantic that was missing.

### Fixed

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
  kFloat readback is normalized in-process — `floatPixels()` →
  BGRA→RGBA swizzle per `isRGBA()` → `setPixels` → `setRGBA(True)` —
  and flips only under the assertion-pinned `_VP2_READBACK_BOTTOM_UP`
  condition (D-056⑤); `convertPixelFormat` is a C++-only API and is
  never called. When neither module provides `MImage`, tools return a
  structured `capture_unsupported` error instead of `AttributeError`.
- Runtime `__version__` matches `pyproject.toml` (was 0.1.0 vs 0.1.1).

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
