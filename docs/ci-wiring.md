# Keeping key CI checks connected (#223)

Run locally (same entry point as the lint job):

```sh
uv sync --frozen
uv run python .github/scripts/check_ci_wiring.py
uv run pytest tests/test_check_ci_wiring.py -q
```

To try a broken copy without editing the real workflow:

```sh
cp .github/workflows/ci.yml /tmp/broken-ci.yml
sed -i 's/needs: \[lint, mypy, test\]/needs: [lint, test]/' /tmp/broken-ci.yml
uv run python .github/scripts/check_ci_wiring.py /tmp/broken-ci.yml
```

That exits 1 and prints `ci: aggregate_broken`. Tests also delete mypy and its
summary dependency together, skip jobs/steps, remove lint/test dependencies,
leave commands only in comments, and add failure-swallowing flags or `|| true`.
Each copy is checked without touching the real workflow; the real file and an
unchanged fixture must both pass.

## Where the rules come from

Issue #223, under #221, requires lint, mypy, pytest and the `ci` summary to
remain connected. Their existing job IDs are `lint`, `mypy`, `test`, `ci`.
The checker records those IDs once and reads their steps and dependencies from
ci.yml; it does not copy the governance-script inventory. The existing gate
registry still owns that inventory, including this new checker.

This is a deliberately narrow check of this repository's workflow shape, not a
YAML validator or a shell interpreter. Tool commands must start a run-text line
in the current form (`uvx ruff@… check`, `python …check_ruff_budget.py`,
`uv run python .github/scripts/run_mypy_gate.py`,
`uv run python -m pytest`). Comments and echo-only calls do not count.
The mypy job runs its tool through the registered `run_mypy_gate` gate, so the
workflow text cannot show a mypy invocation; that the gate really runs mypy is
pinned by `tests/test_run_mypy_gate.py`, not by this grammar.
The summary must end with the existing three `test … = "success"` commands
joined by `&&`. If those command forms change, update this checker and its
positive and negative tests in the same change, rather than bypassing it.

All steps in a protected job are checked for skip conditions and swallowed
failures, not just the tool step. This intentionally also protects setup and
budget enforcement. Unrelated jobs such as drift-notify are not constrained.
Only absent conditions, `success()` and `always()` are accepted; the summary
job requires `always()`. Unknown continue-on-error values fail closed.

## Limits and hand-off to A3 (#228)

- Deleting the workflow or lint job together with this check removes the check.
  Nothing inside that deleted job can prevent this. A3 must verify required
  checks and rulesets outside the workflow. This change does not configure them.
- Trigger/path filters, permissions, fork behavior, required-check names and
  whether GitHub actually runs the workflow need outside verification.
- The parser accepts this repo's indented jobs/steps and inline/block needs.
  YAML anchors, aliases, flow mappings, duplicate keys, folded shell semantics,
  custom shell settings, reusable workflows and composite actions are not
  evaluated. Review such changes manually; passing here is not proof for them.
- This is not protection against someone deliberately rewriting the checker or
  its tests. CODEOWNERS/review permissions remain external concerns for A3.
- Shell checks catch `|| true`, `|| :`, `|| echo`, `|| exit 0` and
  continue-on-error. They do not prove arbitrary shell behavior: `set +e`,
  conditional execution, command substitution, quoted commands, indirect calls,
  redirection tricks and later successful commands in tool steps need review.
- Report contents and whether mypy really checked files are A2's job and now
  live in `run_mypy_gate.py` (see below). No type-error budget, strictness
  setting, Maya behavior or baseline changes are part of this check.

## The mypy execution-effect gate (A2, issue #226)

The mypy job no longer pipes mypy straight into `mypy-baseline filter`; it
runs `.github/scripts/run_mypy_gate.py`, which decides from three signals and
fails closed when any of them cannot be trusted:

1. **Exit code, classified.** 0 means "claims zero errors", 1 means "reports
   type errors", anything else is a checker/configuration fault. The exit
   code is never trusted alone.
2. **Report shape.** A zero-error run must end with `Success: no issues
   found in N source files`; an error run must be non-empty, carry at least
   one `error:` line, parse line by line as mypy output, carry the
   `Found … (checked N source files)` summary, and the summary's error count
   must agree with the number of `error:` lines in the body. Empty or garbage
   output is red on BOTH branches — including with an EMPTY baseline, which
   the old pipe passed silently (`fix 0 / new 0` → exit 0; reproduced
   2026-11-14 on this tree before the fix).
3. **Scope.** `src/` is enumerated live (every `*.py` under it) and mypy's
   `checked` count must cover it. Excluding a previously clean module is red;
   a legitimately added module grows both sides together, so no file count is
   pinned. `checked` above the enumeration is allowed (imports mypy follows).
   The comparison counts FILES, not identities: a fault that excludes one
   module while another file inflates mypy's count could balance out, so the
   guarantee is "no shortfall", not "exact set". mypy also discovers `.pyi`
   stubs under its own dedup rules (`src/` has none today); if stubs appear,
   align the enumeration with mypy's discovery first. An identity-based
   check would need the checked-file set, which mypy's summary does not
   expose.

Before mypy starts, configuration guards fail closed: the strict trio
(`strict`, `warn_unused_ignores`, `warn_unused_configs`) must still be enabled
in `[tool.mypy]` — which is a WHITELIST: four review rounds found one
weakening key after another (strict sub-flags, `ignore_errors`,
`disable_error_code`, `semantic_analysis_only`), so the table may hold only
the trio plus `python_version` and any other key is refused (allowing a new
one requires editing this gate); any mypy overrides table is refused
outright (the guard cannot audit `ignore_errors`-style per-module silencing
without re-implementing mypy's config semantics); the baseline filter's own
config (`[tool.mypy-baseline]`, whose `ignore` list makes the filter skip
matching errors) is refused too; and `mypy-baseline.txt` must exist and be
readable. mypy is invoked with `--config-file pyproject.toml`, so it reads
the same config the guard audits, and a `mypy: error` on stderr is a config
fault even when the exit code looks healthy (mypy can log a config-parsing
failure and then continue on defaults). An empty baseline stays legal — that
transition is exactly what the report-shape checks protect. Retiring the
baseline later means editing this gate, not deleting the file.

The baseline filter runs on BOTH branches, exactly as the old pipeline did:
besides catching new errors, its nonzero "resolved violations" exit still
forces a baseline sync once the historic errors are actually fixed, so a
clean mypy run cannot quietly retire that signal.

Every verdict records evidence: mypy's exit code, its stderr, the report line
count, the summary line and the live scope count. Faults print as `::error`
with the fault tag (`config_fault`, `checker_fault`, `execution_fault`,
`scope_fault`, `filter_fault`).

Known limits (also in the registry note): the strict guard reads the first
`[tool.mypy]` table as text and stops at the next header — explicit strict
sub-flags there, global suppression flags (`ignore_errors`,
`disable_error_code`) and any mypy overrides table are refused outright (see
the guard section above), so nothing that silences errors can pass in config
text this gate reads; the report grammar covers mypy's
default formatter only and assumes space-free checkout paths (`--pretty` or
a path with a space is judged malformed, i.e. red); a broad ignore mypy
actually uses stays a review decision (`warn_unused_ignores` only catches
ignores that suppress nothing); a wholesale faked report with a consistent
`checked` count is not detectable at this layer — the guard against that is
CI running the pinned tests, plus the A1 wiring grammar that requires this
exact script call.

Local commands:

```sh
uv run python .github/scripts/run_mypy_gate.py
uv run pytest tests/test_run_mypy_gate.py -q
```

Local verification (2026-11-14, locked `.venv`, Windows): the gate's own 30
tests passed, including the CLI green control that runs real mypy over this
tree (`Found 152 errors in 1 file (checked 31 source files)`, zero new after
the baseline). The #214 holes were reproduced on this tree before the fix:
with an EMPTY baseline, an empty report and a garbage report both returned
filter exit 0; with the current nonempty baseline the same faults only turned
red through stale-entry mismatch (filter exit 100). Disposable-workspace
injection: a copy of the tree ran green; appending
`INJECTED: int = "not an int"` to `src/maya_mcp_server/asset_tools.py` turned
the chain red with `filter_fault` and the injected error named in the filter
output (`asset_tools.py:242 … [assignment]`, `new: 1`); deleting the copy
restored the original tree, which was untouched throughout. These are local
results, not a claim that the GitHub Actions matrix has run on this branch.

The checker also reads the existing registry's `bound_class: gate` entries and
requires a real Python script call in parsed run text across workflow files.
This closes the comment-only registration gap without copying its script list.
For a supplied ci.yml copy, that copy replaces ci.yml in this scan; other
workflow files still come from the repository (for example the PyPI check).
This extra presence check does not prove every non-critical workflow's control
flow; skip/failure rules here apply to the four protected CI jobs only.

## Local verification (2026-11-13)

With `uv sync --frozen` on Python 3.11: 28 wiring tests passed; full suite
1293 passed, 27 skipped. Ruff 0.17.1 stayed within the unchanged per-rule
budget. The existing mypy + mypy-baseline command reported zero new errors.
Registry, doc-claims and the other local lint-job scripts passed; the monolith
check only noted its existing spare line. These are local results, not a claim
that the GitHub Actions Linux/Windows matrix has run on this branch.

## PR #232 review follow-up

The review correctly found that a default-success job can be skipped through
its `needs` chain even without its own `if`. The checker now follows direct
and transitive dependencies, reports skip-capable conditions, missing jobs and
cycles, and stops following skip propagation at `if: always()`. Conditions
outside the small existing allowlist remain conservatively rejected; arbitrary
expressions are not evaluated. Tests cover the reported case plus transitive,
unconditional, always(), missing-dependency and cycle cases.

The main-branch changelog conflict was resolved by retaining both additions;
no upstream application changes were rewritten as part of this repair.

After the review repair and merge of main (`b81a29b`): 34 wiring tests passed;
full locked suite 1341 passed, 27 skipped. Ruff budget, mypy baseline (zero new
errors), governance checks and all pre-commit hooks passed locally.

## Second review follow-up

Four findings were accepted in the same PR scope:

- Validate the dependency graph separately from skip propagation. Missing jobs
  and cycles are `dependency_invalid`, even when a protected or intermediate
  job uses `always()`. A valid `always()` job still breaks skip propagation.
- Ignore full-line comments while reading block `needs` lists; a comment after
  `needs:` also leaves the block open. Comments must not remove dependencies.
- Strip shell comments line by line, then check each complete step for the
  documented OR-list swallow forms. Newlines and backslash continuations no
  longer hide `|| true`. This still does not interpret arbitrary shell code.
- CLI fault tests now mutate the real workflow, use a clean CLI positive
  control, and assert each intended rule tag as well as exit 1. Unrelated
  registry errors can no longer stand in for detecting the intended fault.

The review's tool-only command-injection warning is not applicable: the test
passes a fixed interpreter, script path and locally generated fixture path as
an argument list to subprocess without `shell=True`; it runs no request text
as a shell command.

After these fixes: 42 wiring tests passed; full locked suite 1349 passed,
27 skipped. Ruff budget, mypy (zero new errors), governance checks and all
pre-commit hooks passed locally. The monolith's spare-line notice is unchanged.

## Colon boundary regression

The next review found that whole-step matching lost the old detection of
`|| :` at the end of a line when another command followed. This is a valid
finding. The swallow regex now uses multiline boundaries while retaining
cross-line matching. A regression matrix covers all five listed swallow forms
in tool and summary steps, both on one line and after a newline, with a later
successful command. Before the fix this test failed on the colon case;
after the fix all 43 wiring tests and the full suite (1350 passed, 27 skipped)
passed locally. Ruff budget, mypy zero-new-error check, governance scripts and
pre-commit were rerun for the repair.
