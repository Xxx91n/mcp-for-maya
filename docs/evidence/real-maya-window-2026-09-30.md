# Real-Maya verification window — ten-frame results (2026-09-30)

**Authority**: this table is the single source of truth for the window's
per-frame outcomes (D-153① layer-2). Scratch transcripts are process
material, not evidence (docs/evidence/README.md).

**Environment**: Windows 11, Maya 2024 (build 202302170737 / 24.0.0.4640),
en_US GUI lane; published artifact `uvx mcp-for-maya@0.4.1` (FastMCP
4.0.10). Two GUI sessions observed: PID 14284 (exited cleanly mid-window,
no crash events — none of our probes had connected) and PID 7104
(relaunched en_US for box-5).

| # | Issue #7 item | Result | Evidence | Boundary / debt |
|---|---|---|---|---|
| 1 | mayapy Tier-2 suite (checkpoint/rollback + ref-edit) | **conditional** | mayapy AV 0xC0000005 reproduced (D-138⑦ env-broken) | Not a code regression; AC-01 debt row → D-159 |
| 2 | GUI Tier-3 (2024) | **split: 5/7 green, 2 deterministic red** — green: bootstrap framed-Qt, execute_code str coercion, render_preview net-zero + missing-camera domain error (playblast path re-verified live 2026-09-30: render-cube.jpg), callform surface probe (frame 9); red: viewport_snapshot returns image + VP2 pure-color orientation/channels (incl. verticalFlip check) | probe-box02-vp2-red.json + render-cube.jpg | `capture_failed kFailure` → Issue #53 (conditional, owner @Xxx91n); 2025/2026 lanes not-verified (rows 2b/2c) |
| 2b/2c | same on Maya 2025 / 2026 | **not-verified** | — | host has 2024 only; explicit unverified per D-149② |
| 3 | PySide2 real-session compat (framed Qt channel) | **green** | GUI suite passed; box5 live calls on :7001 today | single-station Windows |
| 4 | headless temp-file injection fallback on mayapy | **conditional** | mayapy env-broken (same root as frame 1) | AC-01 debt → D-159 |
| 5 | Inspector + Claude Code + Codex multi-block render of the two visual tools | **conditional (partial)** | probe-box05-client-multiblock.json + render-persp-empty.jpg + render-cube.jpg | Inspector --cli: full chain incl. real multi-block image. Pixel render in a client UI: pending (Inspector web open). claude -p: client model-layer block (kimi-k3 SDK). codex: provider-proxy 502 before MCP layer. Escape-hatch bar (Inspector+Codex native render) not yet met |
| 6 | Windows Qt RST/FIN + Linux CI recheck | **Win: green / Linux: 专项未测** | probe-qt-rst-fin.json (RST+FIN reconnect verified on framed channel) | Linux lane = AC-06 debt → D-158 (event-conditioned expiry) |
| 7 | cmds.* static signature audit vs official docs | **green** | probe-box07-cmds-audit.json | 48 distinct functions, 0 illegal flags, 0 deprecated, lookThru=0; type-value correctness out of scope by design |
| 8 | signature collection → stub contract guardrail | **green at presence tier** | probe-box08-signature-diff.json | presence-baseline + allowlist + guard test 5/5 (in-repo durable mechanism); signature tier structurally unavailable (Maya builtins lack inspect.signature) + mayapy lane env-broken |
| 9 | modelPanel call-form smoke | **green** | inside the 5 passed GUI suite items | — |
| 10 | no-trailing-newline command + 500ms read on real commandPort | **green** | probe-box07-box10.json | :7001 live round-trip 2024/True at ~500ms |

## S2 retained-artifact triage (D-115 debt discharge)

Archived (meta-wrapped per D-109): probe-stdio-0.4.0, probe-stdio-2.14.2,
probe-stdio-2.14.7, probe-qt-rst-fin, probe-signature-baseline-maya2024,
probe-gui-verify-results, probe-shipped-0.1.1-failures,
probe-post-fix-direct-harness, probe-shader-bindings (+ scene snapshot
.ma referenced by probe-s5-guard).

Not archived: probe-stdio.mjs,
probe_shaders.py, live-export-smoke.js, harness/*.py — generator
scripts are methodology, not evidence-form (D-109 admits artifacts
with provenance+claim_boundary; scripts are cited as archived_from
paths where they generated an artifact). t14a/mcp_stdio_probe.json —
byte-identical duplicate of the grill-era copy.

## R6 critique reconciliation

- ⑤ live-window evidence backfill: RESOLVED — S0–S6 audited + this table
  + 19 artifacts in docs/evidence/probes/.
- P1 v0.4.0 appendix: RESOLVED — Known-unverified block appended to the
  v0.4.0 release body 2026-09-30 (D-138③ body-form note now stale).
- D-139 PyPI index: already carried timestamped recovery note; 0.4.1
  installable via uvx verified again today.

## Registered debts created this window

- D-158: AC-06 Linux lane (event-conditioned expiry).
- D-159: AC-01 runbook defect (gui suite lacked a Tier-2 mayapy carrier).
- Frame-5 conditional tracked inside probe-box05 artifact (owner: user,
  expiry: first client-UI image render witnessed OR v1.0.0 gate review).

## D-151③ accounting note

This window executed under the subagent+audit-loop form (LOOP-1/2/3) with
the main stack closing S7 after the audit merge — the execution-form
divergence is recorded here per D-151③ (window outcomes are the landing,
the runner composition is process detail).
