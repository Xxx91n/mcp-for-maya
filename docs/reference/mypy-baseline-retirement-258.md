# The mypy baseline retired (#258)

**Decision: `baseline retired, strict gate retained`.**

**What this file is:** the closing record for ticket #258 under the type-checking
spec #222. It states what was measured, which branch of the ticket applied, what
changed, and how the #222 closeout criteria are met. It exists so the decision can
be checked from facts instead of a moving error count.

**What it is not:** a claim that the type checker cannot be cheated. #256 recorded
that a same-named check can be replaced by a fake success and closed by accepting
that risk. The gate and its pytest pins block a genuine type error, and a real
throwaway pull request proved the required check goes red. None of that makes the
check unforgeable.

## Measured environment

- Base commit at ticket start: `2bb371eec0169e0a2c5a883dd802d9e5b8ba1d80`
  (origin/main, merged PR #285).
- `mypy==2.3.1` (compiled), `types-maya-strict==2025.0.6`, target
  `python_version = "3.10"` from `pyproject.toml`.
- Host interpreter: CPython 3.13.13 from the locked `.venv`; `uv 0.11.7` resolved
  the lock. Removing the baseline tool removed only `mypy-baseline==0.7.4` and its
  lock entry; every other pinned version stayed the same.
- Checked scope: `src/` holds 34 `.py` files, and mypy reported 34.

## Branch one applied

The first acceptance branch was "the raw strict mypy run exits 0". It did:

```text
$ python -m mypy --config-file pyproject.toml src/
Success: no issues found in 34 source files
exit code: 0
stderr: (empty)
```

The tracked baseline was already a zero-byte file after #257 (PR #274), so no
historic entry was hiding an error. The strict settings were unchanged:
`strict`, `warn_unused_ignores` and `warn_unused_configs` are all true, the table
holds only those three plus `python_version`, and there is no overrides table and
no suppression flag. The gate script checks all of that before running mypy, so
"zero errors" was not bought by relaxing the configuration.

## How the earlier error categories ended

#213's tentative inventory was 100 missing local annotations, 66 local
container/inference findings, 17 possible third-party Maya stub mismatches and
1 mixed finding (184 total). The counts recorded in CONTRIBUTING at the ticket
start took the raw report down as
184 -> 168 -> 152 -> 85 -> 67 -> 45 -> 20 -> 10 -> 0. The last 10 were
all `no-untyped-def` / `no-untyped-call` annotation gaps, cleared by #257
(PR #274). No category is carried by the baseline because the baseline is empty.
`docs/reference/type-precision-inventory-257.md` lists the remaining weaker
`dict[str, Any]` and local `ignore` uses; those are a review concern, not hidden
errors. #253's record covers the six call forms whose stub disagreed; those
fixes are in the tree, and #258 changes no Maya code.

Local behaviour evidence for this change: `pytest tests/` on the locked
environment gave 1599 passed and 28 skipped. Remote CI is recorded after the
pull request opens.

## What changed

- Deleted the expired `mypy-baseline.txt`.
- Removed `mypy-baseline==0.7.4` from the dev dependencies and from `uv.lock`.
- `run_mypy_gate.py` no longer checks for a baseline file and no longer runs a
  filter. Exit 0 still requires mypy's success line and a checked count that
  covers the live `src/` scope. Exit 1 is a `type_fault` red after the report is
  verified as well-formed, with the first error lines printed as evidence.
- The `[tool.mypy-baseline]` config table is still refused. The filter is gone,
  so the table can only be a reintroduction behind the gate's back.
- The CI job keeps the display name `mypy baseline gate` because the recorded
  branch-protection setting pins that exact required-check context. That read is
  from 2026-11-14; #256 later got a 403 and recorded the current value as
  unverified. Renaming the job would change the required check, which is a
  protection change and not part of this ticket.
- Tests updated: the gate's pytest pins now cover a well-formed error report
  being red, and the old baseline-file and filter-fault pins are gone.

## Negative sensitivity

Two checks show that a new type error cannot pass:

- `tests/test_run_mypy_gate.py::test_a_well_formed_type_error_report_is_red`
  feeds a legal mypy error report to the gate and requires `type_fault` with the
  error named.
- `tests/test_run_mypy_gate.py::test_empty_report_with_zero_exit_is_red` and its
  garbage-report siblings keep the #214 holes closed: a successful exit code
  with no usable report is still red.

A real required-check run was exercised on throwaway pull request #287, which
adds `INJECTED: int = "not an int"` on top of this branch. The
`mypy baseline gate` check failed with
`type_fault -- mypy exited 1 with 1 type error(s)` naming
`src/maya_mcp_server/_injected_258.py:1`, and the PR reported
`mergeStateStatus: BLOCKED`. The PR was closed without merging and its branch was
deleted. Run:
`https://github.com/Xxx91n/mcp-for-maya/actions/runs/43750680182/job/132923715156`.

Normal CI on pull request #286 at `b488e7b3` finished green: the mypy gate, the
ruff budget, `ci`, coverage and all four pytest legs (ubuntu and windows on
3.10 and 3.13). Run:
`https://github.com/Xxx91n/mcp-for-maya/actions/runs/43750629052`.

No Maya code changed in this ticket, so the Maya real-machine evidence is the
existing #253 record: `docs/testing.md` (six call forms measured on Maya 2024)
and `docs/evidence/probes/probe-253-six-callforms-gui-maya2024-v2.json`.

## #222 closeout criteria

| Criterion | Result |
| --- | --- |
| Raw strict mypy over the intended scope exits 0 | Yes: exit 0, 34 of 34 files, commit `2bb371ee` |
| Zero errors is not bought by weaker config or narrower scope | Yes: strict trio unchanged, whitelist guard unchanged, live scope enumeration unchanged |
| A new type error is stopped | Yes: gate pytest pin, plus throwaway PR #287 where the required check failed and the PR was `BLOCKED` |
| Baseline and its dependency removed by a separately reviewed change | Yes: pull request #286; no code cleanup is bundled into it |
| Normal CI and fault injection pass | Yes: PR #286 green at `b488e7b3`; PR #287 red on the mypy gate as designed |
| No branch-protection edits in this ticket | Yes: protection stayed untouched; the job name stayed as it was |
| #222 exit rule: a separate CI guard proves the check cannot silently disappear | Not met: #256 was closed `not planned`; its [closeout comment](https://github.com/Xxx91n/mcp-for-maya/issues/256#issuecomment-6890139942) records the owner accepting the residual risk, not the guard being implemented. Recorded as unmet, not as a pass |
| Remaining risk stated | The required check can still be replaced by a same-named fake success, as #256 accepted |

Result text for the parent spec: **baseline retired, strict gate retained.**
