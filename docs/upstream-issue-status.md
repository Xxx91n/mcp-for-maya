# Upstream issue status — chadrik/maya-mcp-server

This page maps each open issue on the upstream repository
([chadrik/maya-mcp-server](https://github.com/chadrik/maya-mcp-server)) to its
disposition in this fork ([Xxx91n/mcp-for-maya](https://pypi.org/project/mcp-for-maya/),
dist name `mcp-for-maya`). It exists so that issue comments can point at a
stable, honest anchor instead of re-stating per-release details inline.

Source of truth: `docs/decision-ledger.md` (D-057..D-065) and `CHANGELOG.md`
— this table is regenerated from the same facts, never ahead of them.

Version pointers are **durable claims**: `>= X.Y.Z` names the first release
that contains the change, which stays true even if later releases supersede it
or an intermediate release is yanked.

| Issue | Symptom (upstream title) | Disposition in this fork | Ships in | Verification status |
|-------|--------------------------|--------------------------|----------|---------------------|
| [#1](https://github.com/chadrik/maya-mcp-server/issues/1) | `_scan_for_sessions` repeatedly probes MEL commandPorts -> Script Editor error spam | **Fixed**: bilingual `eval("1/2")` probe (MEL integer-divides to `0`, Python 3 answers `0.5` — legal and silent on both sides); non-Python ports join a session-level permanent exemption set (lifted only when the port leaves LISTEN); `MAYA_MCP_INCLUDE_PORTS` / `MAYA_MCP_EXCLUDE_PORTS` env + ctor filters | >= 0.1.2 (pending release — gated on real-Maya verification) | Stub tier green (15 probe/exemption/filter tests); **real-Maya confirmation pending** — the MEL-side socket reply shape of `eval("1/2")` is verified on the stub, not yet on a live Maya (T-16f). If it regresses there, the exemption set alone bounds the symptom to one probe per port per session |
| [#2](https://github.com/chadrik/maya-mcp-server/issues/2) | `ImportError` on startup: `FakeConnection` removed in newer fakeredis | **Already resolved** — this fork's dependency surface contains no `fakeredis` at all (the test suite runs against an in-repo Maya stub, not a fakeredis-backed fake) | >= 0.1.0 (true of every released version, yank-independent) | Verified by inspecting released package metadata (`requires_dist` of 0.1.0/0.1.1) — no code change was needed |
| [#3](https://github.com/chadrik/maya-mcp-server/issues/3) | `prepare_code_for_result_capture` fails on Python 3.7 (Maya 2022) due to `ast.unparse` | **Boundary declaration, not a fix** — dual-runtime support floor: host Python >= 3.10; injected helper requires Maya >= 2023 (Python >= 3.9, the `ast.unparse` boundary). Maya <= 2022 is now refused at injection time with an actionable message instead of a bare `AttributeError`; a `hasattr(ast, 'unparse')` fallback degrades result capture instead of crashing on patched interpreters | >= 0.1.2 | Stub tier green (floor-guard tests); behavior verified against the Maya stub — support matrix documented in README + `docs/testing.md` |
| [#4](https://github.com/chadrik/maya-mcp-server/issues/4) | `create_module(overwrite=True)` discards running `_qt_server`, leaking orphan listeners | **Fixed**: `create_module` invokes the evicted module's `_mcp_teardown` hook before replacing the `sys.modules` entry; the helper ships an idempotent teardown (per-item try/except, `deleteLater`, disconnects `newConnection` so a reloaded helper does not double-fire). A failing teardown surfaces as a `warning` field instead of blocking the reload | >= 0.1.2 (pending release) | Stub tier green (9 teardown-protocol tests incl. Qt signal semantics); **real-Maya reconnect evidence pending** (T-16f — live Qt listener teardown + port rebind) |
| [#5](https://github.com/chadrik/maya-mcp-server/issues/5) | README should explain commandPort setup for multiple Maya instances | **Documented**: bilingual README section + `docs/testing.md` — the mechanics (commandPort = one bound host:port listener, second instance on the same port fails to bind), per-instance port topology, auto-scan as the primary path with `add_session` as manual fallback, symptom-based troubleshooting, and why commandPort does not persist across sessions (`userSetup.py` is the recommended persistence mechanism) | >= 0.1.2 (docs already on `main`) | Docs landed; content reviewed in T-16 audit (PASS-WITH-NITS) |
| [#7](https://github.com/chadrik/maya-mcp-server/issues/7) | `execute_code` silently swallows exceptions: returns `result.result`, drops `result.error` | **Already resolved** — `server.py` calls `raise_for_error` on the execution response and raises `MayaExecutionError` with the remote traceback; true of every released version | >= 0.1.0 | Verified by `git show` on release tags (0.1.0/0.1.1 both contain the raise path). Wider transport-path hardening (call-form handling etc.) ships with 0.1.2 |

## Response plan (human gate)

Each issue gets exactly one technical comment (root cause -> fix path ->
durable version pointer -> fork disclosure -> offer to upstream the fix).
Posting is a human-gated external action: drafts live in
`docs/upstream-issue-response-drafts.md`; #2/#7 are publishable now, the
rest wait for the 0.1.2 release so every claim points at a public artifact.
