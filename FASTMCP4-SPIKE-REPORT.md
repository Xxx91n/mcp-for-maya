# fastmcp-4.x exploration-window spike — report draft (probe branch)

> Canonical full report: `.scratch/t25/reports/2026-09-26-fastmcp4-spike.md`
> (gitignored process artifact). This draft is committed on the DISCARDABLE
> probe branch for PR review context (allowed commit class ②, D-097).

- Round: T-25a | Spec: docs/decision-ledger.md D-096..D-100
- Probed version: fastmcp 4.0.10 (resolves mcp 2.2.0 / mcp-types 2.2.0,
  pydantic 2.13.5, starlette 1.7.0, httpx2 2.13.1, fastmcp-slim 4.0.10)
- Host env: Windows 11 + CPython 3.11.9, uv 0.11.7
- CI corroboration: pending (this PR's matrix run)

## 1. Objective

Decide the fastmcp pin's next move: keep `>=2.14.0,<3.0.0`, tighten to
`>=4.x,<5.0.0`, or register per-item migration debts. Output = information,
not code (probe branch carries only: pin change, this draft, dependabot
comment sync — main already carries the 4.x narrative, verified identical).

## 2. Red-history root-cause correction (MANDATORY per D-100③)

The ledger's earlier camelCase->snake_case attribution is corrected:

| PR | bump target | red legs | PRECISE breakpoint |
|----|-------------|----------|--------------------|
| #36 | >=2.14,<4 (3.x era) | 4/4 pytest legs; ruff+mypy GREEN | `@mcp.tool` returns the plain function in 3.x (v2 returned FunctionTool) -> 3 tests calling `server.X.fn` fail: AttributeError 'function' object has no attribute 'fn'. camelCase NOT implicated (mypy green). |
| #18 | >=2.14,<5 (4.x era) | 4/4 pytest legs + mypy + aggregate | pytest: collection-killer ImportError `from fastmcp.tools.tool import ToolResult` (module removed; new path `fastmcp.tools.ToolResult`) — masks the same 3 .fn failures. mypy: camelCase kwargs on SDK v2 — `readOnlyHint->read_only_hint` etc. in pipeline.py (5 ctor sites + 1 attr read) and `mimeType->mime_type` in visual_tools.py. camelCase IS implicated — on 4.x only. |

Net correction: camelCase breakage belongs to the 4.x jump (MCP SDK v2),
not to 3.x. #36's red was purely the decorator return-value change.

## 3. Breaking-surface x repo call-surface matrix

| Upstream change (4.x) | Our call surface | Verdict |
|-----------------------|------------------|---------|
| `fastmcp.tools.tool` module removed (ToolResult -> fastmcp.tools.base) | tests/test_pipeline.py:14 only | RED (tests only, 1-line fix) |
| `@mcp.tool` returns function (no .fn/.name attrs) | tests: qt_channel:635, scene_tools_json:256,268 | RED (tests only, trivial fix) |
| SDK v2 field rename camelCase->snake_case + compat bridge ON by default | pipeline.py:43-72 (5 ToolAnnotations ctors), :178 (.readOnlyHint read); visual_tools.py:164 (mimeType=) | runtime GREEN (FastMCPDeprecationWarning), mypy RED — mechanical rename |
| meta key _fastmcp->fastmcp (observed _meta.fastmcp on call results) | zero consumers (grep ⓪) | immune |
| include_fastmcp_meta removed / FASTMCP_DECORATOR_MODE deprecated | zero env-var use | immune |
| FastMCP() ctor kwargs | FastMCP(name, version=, instructions=) all in 4.x sig | GREEN |
| Middleware hooks (on_call_tool(context, call_next)->ToolResult) | pipeline.py:154 same shape; CallNext/MiddlewareContext exports intact; context.message.name/.arguments + .fastmcp_context survive | GREEN |
| Sync handler moved to worker thread | all our hooks async def | immune (structural) |
| requires-python floor | fastmcp 4.x requires >=3.10; ours >=3.10 | GREEN |
| Dependency floor pydantic>=2.12 / starlette>=1.0.1 / httpx2 / mcp>=2,<3 | resolved 94 pkgs clean: pydantic 2.13.5 / starlette 1.7.0 / httpx2 2.13.1 / mcp 2.2.0; no conflict with dev pins (mypy 2.3.1, PySide6) | GREEN |
| elicit sessionless raise / sampling / roots / OAuth | unused in repo | immune |
| fastmcp.__version__ removed | we use importlib.metadata | immune |
| fastmcp-slim split (fastmcp = thin extras wrapper) | install resolves both | noted, GREEN |

## 4. Local evidence (venv .venv-fm4, fastmcp 4.0.10)

- pytest tests/ -q: 1 collection error (test_pipeline ImportError) +
  --ignore run: 3 failed (.fn), 732 passed, 26 skipped.
- stdio probe: initialize -> serverInfo {Maya MCP Server, 0.3.0};
  tools/list -> 25 tools; ping -> {}; tools/call list_sessions and
  maya_setup_guide diagnose both execute THROUGH SecurityPipeline
  (deprecation warning at pipeline.py:178 proves the hook ran).
- mypy (expected, mirrors #18): camelCase kwargs/attrs ~14 sites
  (pipeline.py 11, visual_tools.py 1, tests assert reads ~5).

## 5. Findings

1. ZERO production-code hard breaks. Runtime fully functional via the
   camelCase compat bridge (default on; emits FastMCPDeprecationWarning).
2. All reds sit in the test/type layer and are mechanical:
   R1 test_pipeline.py import path (ToolResult moved to fastmcp.tools);
   R2 three .fn call sites (call the function directly);
   R3 camelCase->snake_case renames (pipeline.py x6 incl. :178,
   visual_tools.py x1, test asserts x5) — required by mypy, optional at
   runtime until upstream removes the bridge;
   R4 dependabot ignore stays semver-major (5.0 still major) — comment
   refresh rides the real narrowing PR, not this spike.
3. Deprecation bridge is a countdown: silent today, removal later —
   the renames should ride the SAME minor window as the pin change so
   no deprecation debt survives the bump.

## 6. Recommendation

Partial-red verdict (anticipated): register per-item migration debts
(R1-R3, each with precise breakpoint + tiny fix estimate + trigger =
next minor window 0.4.0) and keep pin >=2.14,<3 on main until the
migration PR lands. No blocker found — 4.x runtime is compatible end-
to-end including the middleware choke point; the spike justifies
scheduling the mechanical rename + pin move together in 0.4.0 rather
than closing the window.

## 7. CI corroboration (PR #41, run 36225673230 — AUTHORITATIVE)

Matches the local first-screen exactly:

| leg | result | breakpoint |
|-----|--------|------------|
| pytest ubuntu 3.10 / 3.x, windows 3.10 / 3.x | 4x FAIL | collection-killer ModuleNotFoundError 'fastmcp.tools.tool' (test_pipeline.py:14); run aborts at collection so the 3 .fn failures stay masked |
| mypy baseline gate | FAIL | camelCase kwargs on SDK v2 — pipeline.py:43/49/55/62/68 (readOnlyHint/destructiveHint/idempotentHint/openWorldHint), attr read :178, visual_tools.py:164 mimeType |
| ruff budget gate | PASS | no new violations |

VERDICT: partial red, zero blockers. All reds are test/type-layer
mechanical items with one-line-class fixes; runtime on 4.0.10 is fully
functional (stdio initialize/tools-list-25/ping/tools-call all green).
Per D-097④ the outcome is per-item migration debts (R1-R3 below),
trigger = next minor window (0.4.0); pin stays >=2.14,<3 on main.

- R1 test_pipeline.py import: fastmcp.tools.tool -> fastmcp.tools.ToolResult
- R2 three .fn call sites -> invoke the function object directly
- R3 camelCase->snake_case: pipeline.py x6 sites + visual_tools.py x1 +
  test asserts (test_export_tools.py:201-204, test_visual_tools.py:245)
