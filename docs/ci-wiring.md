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
  A3's verification of the real merge path is recorded in the
  "A3 (#228): GitHub merge-path verification" section below.
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

## A3 (#228): GitHub merge-path verification

Recorded 2026-11-14 against baseline `6d1896e`. Every finding below names how
it was obtained: `API` means a fresh REST read whose command is listed, so a
maintainer can re-run the audit; `doc` means GitHub's documented behavior that
was NOT measured on this repository. Nothing here changes any branch setting.

### Access status (what changed since #215/#216)

The token used now holds `admin: maintain` on this repository, so the 403 that
#215/#216 recorded no longer applies; the full protection config was readable.
This is itself a fact to re-check over time — access that was missing once can
be granted, and granted access can be revoked.

### Recorded settings (API, 2026-11-14)

| Setting | Value | Source |
| --- | --- | --- |
| Protected branches | `main` is protected; one sampled non-`main` branch (`ticket-220-scene-plan-recs`) is not; dependabot branches not individually queried | `gh api repos/Xxx91n/mcp-for-maya/branches/ticket-220-scene-plan-recs/protection` → 404 "Branch not protected"; `gh api repos/Xxx91n/mcp-for-maya/branches/main/protection` → 200 |
| Required status checks | exactly one: context `ci`, app_id 15368, `strict: false` | `gh api repos/Xxx91n/mcp-for-maya/branches/main/protection` |
| Required check app pin | 15368 = slug `github-actions` | `gh api /apps/github-actions` |
| `enforce_admins` | `false` — administrators can bypass protection | same protection read |
| Required conversation resolution | `true` | same protection read |
| Required signatures / linear history | `false` / `false` | same protection read |
| Force push / deletion of `main` | blocked (`false` / `false`) | same protection read |
| Rulesets applying to `main` | none — `[]` | `gh api repos/Xxx91n/mcp-for-maya/rules/branches/main` |

Real-PR cross-check (API, head of PR #237, `fa3160d`; command
`gh api repos/Xxx91n/mcp-for-maya/commits/fa3160d/check-runs`): the required
context `ci` reported `success` from app 15368; the sibling check runs on the
same commit include `ruff budget gate`, `mypy baseline gate`, four
`pytest (…)` legs and `ci` (all app 15368), plus `coverage`, `CodeRabbit`
(app 347564) and `semgrep-cloud-platform/scan` (app 5541447). Non-Actions
apps demonstrably report check runs on this repository's PRs and cannot
satisfy the app-pinned required check.

Mapping to the workflow: the required context `ci` is the display name of the
aggregate job, which `needs: [lint, mypy, test]` and ends on
`test "${{ needs.X.result }}" = "success"` for all three. The three real
jobs' display names (`ruff budget gate`, `mypy baseline gate`, the four
`pytest (…)` matrix legs) are **not** individually required; nothing outside
the workflow pins them. The scheduled `drift` / `drift-notify` jobs are
outside the aggregate (their skip conditions and `continue-on-error` are
legal precisely because they carry no merge veto).

### 已保护 / 未保护 / 未验证 matrix (protected / unprotected / unverified)

已保护 (verified on this repository, API evidence above; the enforcement
hold behind items 1 and 3 is documented-not-measured — see 未验证 item 1):

1. A PR into `main` cannot merge without a `ci` check run reporting success,
   and only the GitHub Actions app (15368) can produce one. One documented
   exception cuts against this: a skipped job reports `Success` and does
   not block a merge even as a required check (未保护 item 4).
2. Force push to and deletion of `main` are blocked.
3. PR conversations must be resolved before merge.

未保护 (structural gaps, stated so nobody over-reads the protection):

1. **Content swap.** The only required check is a name. A rewritten ci.yml
   holding one trivially-green job named `ci` satisfies it, and every
   in-repo guard (this checker, the registry, the mypy gate) lives inside
   the same deletable workflow — the coordinated-edit bypass #215 measured
   against the registry text test extends to the whole merge path. Closing
   it needs extra required checks that point at jobs that actually run the
   tools (see the recommendation below) or a maintainer-side ruleset.
2. **Stale checks.** `strict: false` means an old green `ci` still counts
   after `main` moves; being up to date with the base branch is not
   enforced.
3. **Administrator bypass.** `enforce_admins: false` lets an admin merge
   past a red or missing check, and every protection setting is editable by
   an admin at any time. Per #221 no claim is made against anyone with that
   authority.
4. **Skip counts as success.** GitHub's documentation states that a skipped
   job reports its status as `Success` and does not prevent a pull request
   from merging, even as a required check. The unchanged workflow cannot
   skip `ci` — the wiring gate requires `if: always()` on the summary — but
   a PR that rewrites ci.yml can, the same content-swap family as item 1.

未验证 (`human_verify`-tagged; doc-inferred; needs a disposable-PR experiment
this ticket was not authorized to run):

1. The merge button's actual verdict when context `ci` never reports
   (whole workflow deleted, the `ci` job renamed, an invalid workflow such
   as a deleted job still referenced by `needs:`, or a fork PR whose
   workflow has not been approved to run): GitHub documents
   "Expected — Waiting for status to be reported" holding the merge; not
   merge-tested here. A rename is fail-closed for the same reason — the old
   context stops reporting — but the untested part is GitHub's hold on an
   ordinary PR.
2. The skipped verdict is documented, not measured on this repository: the
   GitHub documentation behind 未保护 item 4 says a skipped job reports
   `Success` and does not prevent merging as a required check.

Ruleset-scope edge: no ruleset applies today, so there is no ruleset that can
silently narrow. If a maintainer later adds one, its target-pattern change
silently re-scopes every rule it carries — the protection read in the table
above (`rules/branches/main`) is the re-check, and checklist step 1 covers it.

### Minimal reliable protection and the maintainer checklist

Acceptance for #228 is "critical checks cannot be silently skipped or
removed", not one required check per CI sub-job. The smallest change that
narrows the content-swap gap:

- **Add `ruff budget gate` and `mypy baseline gate` as additional required
  status checks** on `main`. A coordinated rewrite that fakes the `ci`
  aggregate then still leaves those two contexts unreported, and the merge
  holds. This is partial mitigation: a PR can keep both names and replace
  their steps with commands that only succeed, so the checks report success
  without running the tools — closing that needs checks that actually run
  the tools or a maintainer-side ruleset (未保护 item 1). The four
  `pytest (…)` leg names are dynamic and churn on Python version bumps;
  leaving them to the aggregate is the deliberate trade-off.

Human checklist (maintainer; no code needed; changing branch settings needs
its own explicit approval per #221):

1. Re-run the API reads in the table above and confirm this section still
   matches reality.
2. Settings → Branches → `main`: confirm the required check list shows
   exactly `ci` (Actions); add `ruff budget gate` and `mypy baseline gate`.
3. Decide on `enforce_admins` (currently `false`); enabling it binds the
   owner too, so it is an owner-only decision.
4. Optional measured tests (disposable branch + PR each, nothing else; one
   phenomenon per experiment): (a) delete the whole workflow file — or just
   the `ci` job — on a test branch, open a PR, confirm the merge button is
   held with "Expected — Waiting for status to be reported"; (b) on another
   test branch make the `ci` job skip outright (for example `if: false`) to
   observe the documented skip-reports-`Success` behavior on this
   repository. Close each PR and delete its branch; confirm no rule was
   left changed. Each phenomenon is measured only by its own experiment —
   deleting the `mypy` job alone tests neither: with `ci`
   still listing `mypy` in `needs`, the workflow is simply invalid.

Per #228's acceptance criteria, the end-to-end "cannot silently disappear"
guarantee is NOT declared accepted while that merge-path experiment remains
unmeasured; this section delivers the investigation and the human checklist
instead.
