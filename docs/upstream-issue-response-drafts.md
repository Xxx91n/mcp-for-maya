# Upstream issue response drafts (D-063/D-064)

Status: **DRAFT — human gate**. Posting to chadrik/maya-mcp-server is an
external side effect; these drafts are prepared by the agent and published by
the user (or under explicit authorization). One comment per issue, no
follow-up comments.

Shared template: root cause -> fix path -> durable version pointer -> fork
disclosure -> offer to contribute the fix back.

Timing (D-064): **#2 and #7 are publishable now** — the claims hold for every
released version and survive the planned 0.1.1 yank. **#1/#3/#4/#5 wait for
the 0.1.2 release** so the version pointer resolves to a public artifact
(with real-Maya verification landed by then).

---

## Issue #2 — publishable now

> Root cause: upstream pinned/instantiated `FakeConnection` from fakeredis,
> which was removed in newer fakeredis releases — the import itself fails at
> startup.
>
> In our fork ([Xxx91n/mcp-for-maya](https://pypi.org/project/mcp-for-maya/))
> this failure mode does not exist: the dependency surface contains no
> `fakeredis` at all — the test suite runs against an in-repo Maya stub
> instead. This holds for **every released version (>= 0.1.0)**, verified from
> the published `requires_dist` metadata, not from memory.
>
> Full status mapping: https://github.com/Xxx91n/mcp-for-maya/blob/main/docs/upstream-issue-status.md
>
> Disclosure: we maintain a fork of this project (upstream MIT license
> retained). If the maintainers want it, we are happy to contribute the
> approach back.

## Issue #7 — publishable now

> Root cause: `execute_code` returned `result.result` and dropped
> `result.error`, so exceptions raised inside Maya were silently swallowed.
>
> In our fork ([Xxx91n/mcp-for-maya](https://pypi.org/project/mcp-for-maya/))
> this is already fixed: `server.py` passes the execution response through
> `raise_for_error`, which raises `MayaExecutionError` carrying the remote
> traceback — true of **every released version (>= 0.1.0)** (verified via
> `git show` on the release tags).
>
> Related transport-path hardening (call-form handling and friends) ships
> with 0.1.2 — the core symptom you reported is already covered today.
>
> Full status mapping: https://github.com/Xxx91n/mcp-for-maya/blob/main/docs/upstream-issue-status.md
>
> Disclosure: we maintain a fork of this project (upstream MIT license
> retained). If the maintainers want it, we are happy to contribute the
> approach back.

---

## Issue #1 — post after 0.1.2

> Root cause: the session scanner probes every listening commandPort with a
> Python payload; a MEL commandPort cannot evaluate it, so each scan cycle
> drops an error into the Script Editor.
>
> Fixed in our fork ([Xxx91n/mcp-for-maya](https://pypi.org/project/mcp-for-maya/),
> **>= 0.1.2**): the probe payload is now the bilingual `eval("1/2")` —
> Python 3 answers `0.5`; on a live Maya 2024 MEL port it returns a
> syntax-error body (verified on a real session — MEL's `eval` expects
> a command string, not an expression), which still classifies the port as
> MEL. Ports detected as non-Python join a session-level permanent
> exemption set (re-enabled only if the port leaves LISTEN), so the probe
> costs at most one Script Editor error line per port per session — then
> the re-probe spam ends entirely. On top of that,
> `MAYA_MCP_INCLUDE_PORTS` / `MAYA_MCP_EXCLUDE_PORTS` (or the matching
> `SessionManager` ctor args) bound which ports get probed at all —
> productizing the workaround reported in this thread.
>
> Verified on a live Maya 2024 session: the MEL-port reply shape is pinned
> in our test suite, and the exemption set bounds residual Script Editor
> noise to one line per port.
>
> Full status mapping: https://github.com/Xxx91n/mcp-for-maya/blob/main/docs/upstream-issue-status.md
>
> Disclosure: we maintain a fork of this project (upstream MIT license
> retained). If the maintainers want it, we are happy to contribute the
> approach back.

## Issue #3 — post after 0.1.2 (boundary statement, not a fix announcement)

> This is a declared-boundary note rather than a fix: the injected helper
> genuinely requires `ast.unparse` (added in Python 3.9), and our fork is a
> dual-runtime package — the host env needs Python >= 3.10 while the
> *injected* side declares its own floor at **Maya >= 2023 (Python >= 3.9)**.
>
> What changed in >= 0.1.2 ([Xxx91n/mcp-for-maya](https://pypi.org/project/mcp-for-maya/)):
> Maya <= 2022 is now refused at injection time with an actionable message
> naming the floor, instead of dying on a bare `AttributeError`; a
> `hasattr(ast, 'unparse')` fallback additionally degrades result capture on
> patched/forked interpreters. The support matrix is documented in the
> README and `docs/testing.md`.
>
> We deliberately do not ship a Python-3.7 compatibility shim — a declared
> floor with an explicit capability error beats a partial emulation layer
> for an EOL runtime.
>
> Full status mapping: https://github.com/Xxx91n/mcp-for-maya/blob/main/docs/upstream-issue-status.md
>
> Disclosure: we maintain a fork of this project (upstream MIT license
> retained). If the maintainers want it, we are happy to contribute the
> approach back.

## Issue #4 — post after 0.1.2

> Root cause: `create_module(overwrite=True)` builds a new `ModuleType`
> and replaces the `sys.modules` entry outright — the old module's globals
> keep a *listening* `QtCommandServer` alive, orphaned: the port stays bound
> and the replacement server fails to rebind. Every reconnect of an
> already-bootstrapped session hits this.
>
> Fixed in our fork ([Xxx91n/mcp-for-maya](https://pypi.org/project/mcp-for-maya/),
> **>= 0.1.2**): `create_module` now invokes the evicted module's
> `_mcp_teardown` hook *before* replacing the `sys.modules` entry. The
> injected helper implements an idempotent teardown — per-item try/except
> so one failing resource cannot block the rest, `deleteLater` semantics
> for Qt objects, and `stop()` disconnects the `newConnection` signal
> rather than only closing the socket (prevents double-firing after a
> reload). A failing teardown surfaces as a `warning` field instead of
> blocking the replacement.
>
> Verification status: covered by stub-tier tests including the Qt signal
> semantics, and verified on a live Maya 2024 session — the teardown
> hook fired exactly once across a reconnect, the old listener port was
> released, and the replacement server bound cleanly.
>
> Full status mapping: https://github.com/Xxx91n/mcp-for-maya/blob/main/docs/upstream-issue-status.md
>
> Disclosure: we maintain a fork of this project (upstream MIT license
> retained). If the maintainers want it, we are happy to contribute the
> approach back.

## Issue #5 — post after 0.1.2

> Root cause: the README never documented multi-instance commandPort
> topology — one bound host:port listener per port — so running a
> second Maya instance on the same port silently failed to bind.
>
> Covered in our fork's docs ([Xxx91n/mcp-for-maya](https://pypi.org/project/mcp-for-maya/),
> >= 0.1.2): the README (both languages) and `docs/testing.md` now carry a
> multi-instance section — the mechanics (a commandPort is one bound
> host:port listener, so a second Maya instance on the same port fails to
> bind), a per-instance port topology example, auto-scan as the primary
> discovery path with `add_session` as the manual fallback, symptom-based
> troubleshooting, and the persistence caveat: commandPort does not survive
> a restart, so `userSetup.py` is the recommended mechanism.
>
> Full status mapping: https://github.com/Xxx91n/mcp-for-maya/blob/main/docs/upstream-issue-status.md
>
> Disclosure: we maintain a fork of this project (upstream MIT license
> retained). If the maintainers want it, we are happy to contribute the
> approach back.
