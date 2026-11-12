# T-18c release prep — v0.1.2 (D-068)

The v0.1.2 section below is PREPARED ONLY: every step past the "prepared"
line was a human gate, and nothing in that section was pushed, published,
yanked, or posted by the agent. The Registry section near the top is a
different kind of record — it lists publishes the maintainer already ran, with
the check that confirmed each one. Read the header of each section before
trusting it.

## MCP Registry listing — publish records and the standing rule

These records were kept in `docs/distribution-surfaces.md` until that file
was deleted in the plain-language cleanup (#192). They live here now, next
to the other release records. The rule they carry: every new version gets
re-published, and the published `version` string must match PyPI exactly.

| Date (UTC) | Version | Result |
|---|---|---|
| 2026-09-30 | 0.5.0 | First listing (`io.github.Xxx91n/mcp-for-maya`) |
| 2026-10-25 17:29:14 | 0.6.0 | Re-published; `status=active`, `isLatest=true` |
| 2026-10-28 09:57:46 | 0.7.0 | Re-published; `status=active`, `isLatest=true` |

How each publish was checked:

- v0.6.0: offline `mcp-publisher validate` (exit 0), then `mcp-publisher
  login github` and `mcp-publisher publish` (exit 0). The 1.8.4 `status`
  subcommand only writes, so the record was confirmed with the authenticated
  Registry API: `GET /v0.1/servers/io.github.Xxx91n%2Fmcp-for-maya/versions/0.6.0`
  returned HTTP 200 with `version=0.6.0`, `status=active`, `isLatest=true`,
  `publishedAt=2026-10-25T17:29:14Z`, matching PyPI 0.6.0 exactly.
- v0.7.0: same sequence (offline `validate`, then login and publish, both
  exit 0). Confirmed with the public endpoint (no auth):
  `GET /v0.1/servers/io.github.Xxx91n%2Fmcp-for-maya/versions/0.7.0`
  returned HTTP 200 with `version=0.7.0`, `status=active`, `isLatest=true`,
  `publishedAt=2026-10-28T09:57:46Z`, matching PyPI 0.7.0 exactly (artifacts
  uploaded 08:55:37Z wheel and 08:55:39Z sdist).
- A public HTTP 200 is evidence the listing is there. An anonymous 404 is
  not evidence that it is gone.

The 30-day re-check window starts at the publish date, not the release date.
The current window started 2026-10-28, the v0.7.0 publish date, and it
replaced the 2026-10-25 window. Removing or renaming a listing goes through
the publish side's `status` field (`active`/`deprecated`/`deleted`), not by
deleting the record.

What the 30-day check actually involves — the ledger carried these steps and
they are easy to lose otherwise:

1. Look at four channels: mcp.so, PulseMCP, the VS Code MCP gallery, and the
   Cline marketplace. These are the ones still in passive observation; the
   rest are either listed already or structurally rejected.
2. Ask one question per channel: did the latest Registry publish show up
   there, or not. The VS Code gallery has no API, so that one is a manual
   search.
3. Record the answer per channel as a plain "synced" or "not synced" fact,
   then re-decide that channel's state: no listing and no signal means stay
   passive or drop the debt; listed means it goes quiet, no further action.

Cline carries the least urgency of the four: it stays on hold until its
catalogue shows a DCC/Maya entry, and its check rides this same window at no
extra cost.

### Other listing surfaces — the facts that outlived the ledger

`docs/distribution-surfaces.md` also carried a per-channel table. These facts
still govern what this repo does at each channel, so they are kept here.
The rest of that table is recoverable with
`git show bf06a54:docs/distribution-surfaces.md`.

- **Glama** — listed and claimed 2026-09-30 (OAuth claim by the maintainer;
  the auto-index page answered HTTP 200). Glama's build surface needs a
  Dockerfile, and this repo has none. That is the normal state: do not turn
  on a Docker build or health-check surface for it, because a Maya GUI host
  cannot build in a container and a red health check hurts the listing.
- **awesome-mcp-servers** — listed. The PR
  ([punkpeye/awesome-mcp-servers#15382](https://github.com/punkpeye/awesome-mcp-servers/pull/15382))
  added this repo to the Art & Culture section and was merged 2026-10-23.
- **mcp.so** — rejected, and the reason matters: the decision rests on the
  manual GitHub-issue submission path plus low audience quality. It is not
  the "aggregators sync automatically" assumption, which was never checked.
- **Cline marketplace** — held back on purpose. Its one-click install
  promise clashes with the Maya-on-the-same-host precondition: the install
  appears to work, then the server cannot connect. Revisit only when its
  catalogue shows a DCC/Maya entry.
- **Structural rejections** — Claude Connectors Directory (its docs stop
  taking local MCPB servers and accept remote HTTPS only), Docker MCP
  Catalog (containers only), Cursor directory (code-editing workflows only),
  Windsurf/Zed (no third-party submission path), Smithery (stdio plus Maya
  host does not fit its hosted scanning). Each is a one-way "no" until that
  channel changes its rules.

One rule from that table has no home yet: when the repo's own description
changes, check that the listing descriptions still match it, so a stale
listing does not become a second source of wrong claims. This branch changed
the README tagline, so that check is due — the Registry 0.7.0 record and the
Glama page still carry the older wording. Nothing in the tree enforces this
today; it stays a manual step, recorded here rather than dropped.

## Per-version defect audit (git show on release tags)

### v0.1.0

- `result_type` raw-string crash: `result_type.value` at client.py:347
  on the tag → any caller passing `"JSON"` (the documented JSON path
  on the real transport) dies with AttributeError. scene_* and visual
  tools affected. (D-046 class)
- VP2 snapshot path calls `img.convertPixelFormat(MImage.kByte)` — a
  C++-only symbol absent from the Python API → viewport_snapshot
  crashes on Maya 2024; `_omui.MImage` resolution also wrong on ≤2024.
- `1+1` probe → MEL commandPort Script-Editor error spam (upstream #1).
- No `_mcp_teardown` in helper → create_module(overwrite) orphans the
  Qt listener on every reconnect (upstream #4).
- `module_create_failed` swallowed on the hot-update path (N7).
- serverInfo leaked the FastMCP framework version (D-060③).
- scene_rollback used `file(rename+prompt)` combos + MItDag accepted
  non-DAG nodes (crash modes fixed only in 0.1.2).
- lookThru ambiguity bug (later fixed in 0.1.1).

### v0.1.1

- Same transport/VP2/teardown/MEL-probe defect set as 0.1.0 (verified:
  `1+1` probe still at client.py:532; `convertPixelFormat` still at
  visual_module.py:257; no `_mcp_teardown` in helper).
- PLUS a packaging defect: `__version__` reports `0.1.0` while
  pyproject ships `0.1.1`.

### v0.1.2 (candidate)

- All of the above fixed + T-18a real-Maya gui tier green (7/7).

## Yank procedure + reasons (run only after 0.1.2 confirmed on PyPI)

**twine has no yank command** (audit F2 — twine only ships
register/check/upload). Yank via the PyPI web UI:

1. https://pypi.org/manage/project/mcp-for-maya/releases/ →
   open the release (0.1.0, then 0.1.1) → **Options → Yank**
2. Paste the per-version reason below.

- 0.1.0 reason:
  `Superseded by 0.1.2: execute_code JSON result_type crashes on str, viewport_snapshot calls C++-only convertPixelFormat (crashes on Maya 2024), reconnect leaks the Qt listener, MEL-port probing spams the Script Editor.`
- 0.1.1 reason:
  `Superseded by 0.1.2: same defect set as 0.1.0 plus __version__ reports 0.1.0.`

(Programmatic alternative: PyPI's REST API POST .../release/<ver>/yank —
unverified here; web UI is the verified path.)

## Tag + release sequence (human gate)

```bash
but tag v0.1.2            # or: git tag -a v0.1.2 -m <tag description below>
but push v0.1.2           # triggers release.yml -> build -> publish (trusted publisher)
# watch: gh run watch / release workflow
# verify: https://pypi.org/project/mcp-for-maya/ shows 0.1.2
# then yank per above, then post upstream comments #1/#3/#4/#5 (approved drafts)
```

Tag description draft:

> v0.1.2 — real-Maya-verified reliability round: Qt bootstrap build-marker
> (kills the connect flake), module_create_failed surfacing, orphan-listener
> cleanup on fallback + dedicated-port close, VP2 RGBA readback without
> MScriptUtil + top-down orientation pin, MEL/Python bilingual port probe,
> multi-instance docs, upstream #1/#3/#4/#5 dispositions.

## Release notes draft (from CHANGELOG [0.1.2], verbatim)

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
  the injected module's `__build__` marker is compared first and the
  hot-update write is skipped when it matches. The big write is what
  tripped the commandPort stale-response quirk and intermittently
  stranded the just-started Qt server (connect refused on a live bind);
  skipping it removes the flake. A bounded connect+ping retry still
  covers genuinely slow Qt servers (T-18a, live-verified).
- Fallback hygiene: when the Qt channel is unavailable, the bootstrap
  now stops the orphaned Qt listener before opening the fallback
  commandPort, and the dedicated fallback port is closed on
  `disconnect()` instead of leaking (T-18a).


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
