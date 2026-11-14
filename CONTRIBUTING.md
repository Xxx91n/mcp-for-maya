# Contributing

## Development setup

```bash
uv sync --frozen                   # installs project + dev group from uv.lock (D-112)
# alternatives: uv sync (re-resolve) | pip install -e . --group dev (pip >=25.1)
uv run pre-commit install            # one-time: wire git hooks (.pre-commit-config.yaml)
uv run pre-commit run --all-files    # hook sweep — CI's lint fallback. doc-claims is language: system,
                                     # so it runs the PATH `python`: `.venv/Scripts/pre-commit.exe run
                                     # doc-claims --all-files` exits 1 with `SRE module mismatch` at
                                     # python 3.11.9 against the uv 3.13 venv; `uv run` of it exits 0
python -m pytest tests/ -q         # fake-Maya test layer (contract tests against the maya.cmds fake)
uvx ruff@0.17.1 check . --output-format=json --exit-zero > ruff-report.json          # lint pass 1: report only, red findings must not fail the shell
python .github/scripts/check_ruff_budget.py ruff-report.json .github/ruff-baseline.json   # lint pass 2: per-rule budget that only goes down
rc=0; uv run python -m mypy src/ > mypy-report.txt || rc=$?; if [ "$rc" -gt 1 ]; then cat mypy-report.txt; false; else uv run mypy-baseline filter < mypy-report.txt; fi   # type-check gate: the raw exit is non-zero on the baselined errors; `false` rather than `exit` keeps a pasted line from closing the shell, so a crash lands at exit 1 here and CI's 2
python -m maya_mcp_server -vv      # run with DEBUG logs (-v=INFO, -vv=DEBUG)
```

House rules:

- Every fix ships with a regression test on the fake Maya test layer.
- Real-Maya tests are a separate local manual tier (`pytest -m mayapy`, see docs/testing.md) — never mixed with the fake Maya test layer.
- If your change makes a doc line stale, fix that line in the same commit — the [cross-module dependency rules](#cross-module-dependency-rules-联动规范) table below is the propagation matrix: it names, per module, the files that must move with it.
- When folding `[Unreleased]` into a release section, rewrite each Fixed entry's
  `fixed version: [Unreleased]` literal to that release's version number by hand
  (D-230 fold-time rule; human step).

## Cross-module dependency rules (联动规范)

When modifying a module, the dependent files below MUST be updated together —
stale companions cause integration failures and gate reds.

| Module modified | Must also update | Reason |
|-----------------|------------------|--------|
| `maya_scene_module.py` (scene_plan) | `scene_tools.py`, `server.py`, `README.md`, `README.zh-CN.md` | Scene planning tool needs MCP tool + docs |
| `maya_scene_module.py` (aesthetic/lighting/scene_review functions) | `scene_tools.py`, `tests/test_maya_scene_module.py` | Inline `_score_*` functions are the sole implementation; tool descriptions + fake-Maya-layer coverage must match |
| `maya_scene_module.py` (new function) | `scene_tools.py`, `server.py`, `README.md`, `README.zh-CN.md`, `tests/` | Every new Maya function needs an MCP tool, docs, and tests |
| `maya_scene_module.py` (line-count growth) | `.github/monolith-budget.json` | Only down: growth past the cap fails lint; legitimate additions need a reasoned budget edit in the same PR; new capability goes in a separate file injected together with it, never appended to `maya_scene_module.py` |
| `visual_module.py` / `visual_tools.py` | `server.py` instructions, `pipeline.py` annotations, `tests/test_visual_tools.py`, READMEs, `docs/threat-model.md` | Capture contract, annotations, and docs must stay in sync |
| `asset_tools.py` / `polyhaven.py` / `asset_module.py` | `pipeline.py`, `server.py`, `docs/threat-model.md`, asset tests, `tests/maya_stub/` (new cmds surface), READMEs | Host-side download/cache vs Maya-side import — every piece in sync |
| `export_tools.py` / `export_module.py` | `pipeline.py`, `server.py`, `docs/threat-model.md`, export tests, `tests/maya_stub/` (export surface), READMEs | Host validation/registration vs Maya-side export contract |
| `introspect_tools.py` / `introspect_module.py` | `pipeline.py`, `server.py`, `docs/threat-model.md`, `docs/visual-callform-matrix.md`, introspect tests, `tests/maya_stub/`, READMEs | Its source is concatenated into the `_mcp_scene` payload (a separate file of the same module); the D-110 response budget (`limit`, `*_truncated`, `total_*` fields) is part of the contract |
| `validator_module.py` | `scene_tools.py` (`extra_source_paths` + the `scene_review` tool), `tests/maya_stub/__init__.py`, `tests/test_mayapy_smoke.py`, `tests/test_validator_module.py` (whose `TestCardPinsTheShippedApi` goes red when the card and the code drift), `skills/scene-review-playbook/SKILL.md`, `GLOSSARY.md`, `docs/threat-model.md` §5 | Its source is concatenated into the `_mcp_scene` payload after `introspect_module.py`; both fake-Maya-layer assemblers must list it or they stop matching the shipped bytes. The session-scoped registry composes `scene_review_with_validators` Maya-side. #79 deliberately ships no registration MCP tool — calls go through `execute_code` — which is the exception the `maya_scene_module.py (new function)` row above does not cover, and nothing persists host-side |
| `zone_geometry_module.py` | `scene_tools.py` (`extra_source_paths` + the internal `get_zone_geometry` host helper, wired to `scene_plan`'s opt-in `recommend_assets`), `tests/maya_stub/__init__.py`, `tests/test_mayapy_smoke.py`, `tests/test_zone_geometry_module.py`, `tests/test_scene_tools_json.py` | Its source is concatenated into the `_mcp_scene` payload after `validator_module.py` (order: `maya_scene_module.py` → introspect → validator → zone geometry → scene state); both fake-Maya-layer assemblers must list it and the assembled bytes must match the host write. Wired by #217: `scene_plan` reads it only with `recommend_assets=True`, so default `scene_plan` output stays unchanged |
| `asset_recommendation.py` | `scene_tools.py` (`scene_plan` `recommend_assets` wiring + the CoS `RECOMMEND` block), `pipeline.py` (`scene_plan` openWorld annotation), `tests/test_asset_recommendation.py`, `tests/test_scene_tools_json.py` (`TestRecommendAssets`), READMEs, `docs/threat-model.md` | Pure host-side composition: 7-zone → query table, normalized word-level check, cross-keyword dedup, rank-band + size-difference ordering, 3-per-zone / 12-per-scene caps, Maya-unit-to-metres conversion, zone-envelope size screen, and the `recommendations` shape. No new MCP tool; the default `scene_plan` output must stay byte-identical, and a search or geometry failure may never fail the plan |
| `scene_tools.py` (new tool) | `server.py` instructions, READMEs, `AGENTS.md` | Tool surface changes require documentation sync |
| `scene_state_module.py` | `scene_tools.py` (`extra_source_paths` + the `scene_snapshot` and `scene_rollback` tools, and their shared `_read_scene_modified` host helper), `cos_formatter.py` (the `MODIFIED=` marker in the header), `tests/maya_stub/__init__.py`, `tests/test_mayapy_smoke.py`, `tests/test_scene_tools_json.py` (the flag's tool contract), `tests/test_checkpoint_rollback.py` (read-back ignores the flag), `tests/test_cos_formatter.py` + `tests/test_scene_tools.py` (formatter call sites), `tests/test_zone_geometry_module.py` (assembly order), READMEs | Its source is concatenated into the `_mcp_scene` payload after `zone_geometry_module.py` (order: `maya_scene_module.py` → introspect → validator → zone geometry → scene state); both fake-Maya-layer assemblers must list it and the assembled bytes must match the host write. It only reads Maya's unsaved-changes flag: no tool refuses to run because of its value. `scene_rollback` reads the flag on the host side, before the call that swaps the scene, because `maya_scene_module.py` is line-capped, and a call from that file to a function in another file of the same injected module is invisible to mypy, which type-checks each file on its own (it would add a `name-defined` error to the baseline) |
| `scene_cache.py` | `scene_tools.py`, `session_manager.py` | Cache invalidation consistency |
| `security.py` | `pipeline.py`, `tests/test_security.py`, `tests/test_pipeline.py` | Rules enforced by the middleware pipeline |
| `security.py` (`safe_mode` rule table: `SAFE_IMPORT_ROOTS`/`SAFE_NODE_TYPES`/denied builtins) | `docs/threat-model.md` §2/§3, `GLOSSARY.md`, `README.md` + `README.zh-CN.md`, `server.py` docstrings, `tests/test_security.py::TestScanSafeModeCode`, `tests/test_pipeline.py::TestSafeModeGate`, the error-code registry under `docs/guide/` | The v1 deny-by-default matrix is the single source — docs, tool docstrings, and pin tests restate it; every rule change propagates |
| `pipeline.py` strict policy flags (`MAYA_MCP_DISABLE_*`) | `docs/threat-model.md` §2/§3, `llms.txt`, `tests/test_pipeline.py::TestStrictPolicyMode` | Every tool call passes through one place; uncovered dangerous tools fail their gates |
| `connection_guide.py` | `server.py` (maya_setup_guide params), `tests/test_connection_guide.py` | Managed-block semantics + flags |
| `cos_formatter.py` | `scene_tools.py`, `tests/test_cos_formatter.py`, `tests/test_scene_tools.py` (call sites when a formatter signature changes) | Formatter changes affect all tool COS outputs |
| Derived surfaces | — | `llms.txt` (from TOOL_ANNOTATIONS) and the version list (pyproject/`__init__`/server.json/CHANGELOG/llms.txt) are derived and gated — never hand-edit; `docs/guide/session-lifecycle.md` is prose, NOT derived; the eight `path::symbol` bullets under its Anchors heading are hand-maintained, no gate resolves them, and all eight currently resolve |
| `.github/gate-registry.yaml` / `check_gate_registry.py` / `*-spec.yaml` | `tests/`, `ci.yml`, `AGENTS.md`, `CHANGELOG.md` | Gates register pins (human-authored, never generated); exemptions carry `expires\|issue`; governance constants live in per-domain spec files, not code; spec files must not mirror object state (second source of truth) |

### When a new Maya-side module is allowed

New Maya-side capability defaults to a NEW per-domain injected module — never
into `maya_scene_module.py`. A new module is allowed only when all three
thresholds hold: (1) its own injection timing — the capability is needed in
session shapes of its own; (2) its own Maya-side API; (3) its own failure
domain — if it breaks, nothing else breaks with it. If any of them fails and
the destination is `maya_scene_module.py`,
land the code as a separate host-side file injected together with that module
(first case: introspection → `_mcp_scene`). Cross-module calls must be declared
explicitly — injected modules are self-contained by architecture.

Host-side calls into injected modules go through `client.py` primitives:
`module_call(module, fn, *args, **kw)` (JSON-payload builder — user input never
becomes executable source) and `exec_module_code(client, code)`. Per-domain
`_ensure_X_injected` binders pin module_name/source_path/session-set = domain
config, not duplication.

### Changelog evidence rule

Every `Added`/`Fixed`/`Changed` bullet in CHANGELOG.md's `[Unreleased]` lane
MUST carry an executable evidence pointer: a pytest node ID, `path::symbol`, or
`sha:path:line`. "Run this command and here is its output" is not one of them —
it cannot be resolved after the fact, so it asserts nothing a checker can test.
Released sections are point-in-time records and are never re-checked. Enforced by
`.github/scripts/check_doc_claims.py`, which also fails a pointer that no longer
resolves and a test count that no longer matches the suite it cites. Every
`Fixed` entry records `Broken version:` → `fixed version:` fields.

### Assertion & evidence discipline

- Enumeration/count assertions declare their domain; recompute before restating a count.
- A PR body and a changelog bullet are assertion surfaces too: recompute their counts and capability claims against the tip you push or merge.
- A mechanism claim travels with its reproduction: the condition that triggers it, the command that showed it, and the exit code that came back. Write the sentence no wider than that measurement — the `SRE module mismatch` note in Development setup above is that shape.
- Anything not reproducible is recorded "unverified" — never guess a cause.

### Asset directory discipline

`.github/assets/` only grows: files are added, never deleted, renamed, or
edited in place. README imagery is referenced by absolute `main` URLs, and
published PyPI pages render `main` forever — a delete, rename, or in-place
edit of a published asset permanently changes what historical release pages
show. The guard checks `--diff-filter=DMRT`, so a modified file fails the job
just like a deleted one. New captures get NEW filenames. The guard does have
a stated escape hatch: a maintainer-aware merge that names the removal in the
PR body, which is how the three asset fixes before this cleanup landed.

## Pull requests

- One branch per change; keep diffs small and reviewable.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (feat / fix / docs / refactor / test / chore).
- CI gates (`.github/workflows/ci.yml`): `pytest` must be green on ubuntu + windows; the ruff budget
  (`.github/ruff-baseline.json`) may only go down — above budget fails, and a lower count may be
  budgeted down in the same PR commit with the reason stated. `mypy` is baseline-gated in CI
  (`mypy-baseline.txt`; 67 errors in 1 file as of the Maya-stub-mismatch batch (#229),
  down from 184 after three added-annotation batches (#225, #230, #227) and this
  stub-mismatch batch; every remaining entry is an annotation or
  container-inference gap, not a stub dispute —
  baseline counts are sensitive to the fake Maya environment;
  drift trail 221→223→212→223→184→168→152→85→67 across formatter, fake-Maya-environment changes,
  D-124's removal of the code that was not wired up, and the annotation/stub batches):
  the type-check row in
  Development setup above is that gate — the filter fails only on NEW errors,
  and the wrapper keeps a mypy crash (raw exit above 1) red.
  After resolving errors, regenerate the baseline from the same guarded report —
  `uv run mypy-baseline sync < mypy-report.txt`, once the wrapper above has
  stopped reporting errors — and commit the refreshed baseline in the same PR.
  The ruff budget is per-rule
  (`{segment:{rule:count}}`) since T-10b — rules cannot subsidise each other.
  Budget gates are judged on the checked commit's tip (the PR's end state); a
  mid-PR commit that transiently exceeds a budget does not constitute a gate
  failure.

## Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) v2.1. Be respectful, assume good faith, keep discussion technical.
