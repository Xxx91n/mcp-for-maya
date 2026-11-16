# Parent closeout check (#259)

**Verdict: the owner resolved the blocking condition on 2026-11-16 by choosing
退役 — keep the baseline retired and waive #222's exit rule.** The independent
CI guard still does not exist, and this record does not pretend it does. The
matrix is closable: no condition blocks it, and the missing guard sits in the
owner-accepted-boundary column. The close actions were completed on 2026-11-16:
the final comments were posted and #222 and #259 were closed. The #221 comment
was posted without reopening it, since #221 was already closed `not planned`.

**What this file is:** the one place that maps each acceptance condition of
#221 and #222 to its current evidence, its owner-accepted boundary, or the
reason it is not done. It is a point-in-time read, not a promise about future
CI or type-checker behaviour.

**What it is not:** a claim that the type gate cannot be bypassed, that branch
protection cannot change, or that Maya 2025/2026 and the batch lane are
verified. Those limits stay listed at the end.

## Measurement point

- Baseline commit at ticket start: `6b5a84e2fc215f43de3357658d96869becdd7113`
  (`origin/main`, the merge of PR #286). The work ran in a separate worktree at
  that commit, so the shared GitButler workspace did not decide the result.
- Evidence re-read on 2026-11-16 (UTC). The branch-protection read is stamped
  `2026-11-16T03:48:50Z` (PID 30248). It was run as
  `gh api repos/Xxx91n/mcp-for-maya/branches/main/protection` from this host,
  in the owner's `Xxx91n` GitHub session, by the agent working ticket #259. The
  response is frozen in `docs/evidence/branch-protection-main-2026-11-16.json`;
  `gh api repos/Xxx91n/mcp-for-maya/rulesets` returned `[]` in the same pass.
  A first read at `03:04:36Z` returned the same values; the artifact keeps the
  later read because it also captured a PID.
- Remote CI numbers come from the GitHub Actions runs linked under each row.
  Nothing here was re-run locally: this ticket audits records and reads the
  current configuration. The Maya evidence is #253's recorded run, not a new
  Maya session.
- Owner decision recorded on 2026-11-16 during this ticket's implementation:
  **退役** — keep the baseline retired and waive #222's exit rule. The final
  #222 comment will make the decision durable on GitHub.

## Status key

- **已通过** — measured evidence exists and matches the condition.
- **owner 已接受边界** — the condition is not met as written, and the owner has
  recorded a decision to accept the remaining risk. This is not a pass.
- **未完成** — not done: the condition has no evidence yet, the owner decision
  it needs is absent, or the ticket's own rule keeps the item open.

## #221 and its #256 sub-ticket — the conditions and where each one stands

#221 was closed `not planned` by the owner on 2026-11-15T06:07:58Z. Rows 20–21
come from #256, the owner-decision ticket under #221; the rest come from #221's
own acceptance list. The status below is the factual review the owner's closing
comment already describes.

| # | Condition | Status | Evidence |
| --- | --- | --- | --- |
| 1 | A real new mypy error fails the expected merge check | 已通过 | Throwaway PR #287 added `INJECTED: int = "not an int"`. `mypy baseline gate` failed with `type_fault -- mypy exited 1 with 1 type error(s)` naming `src/maya_mcp_server/_injected_258.py:1`; the PR was `mergeStateStatus: BLOCKED` and was closed unmerged. https://github.com/Xxx91n/mcp-for-maya/actions/runs/43750680182/job/132923715156 |
| 2 | Invalid mypy output or a checker failure fails closed | 已通过 | `run_mypy_gate.py` rejects empty and garbage reports on both exit branches, treats any exit other than 0/1 as a checker fault, and refuses a weakened strict trio or a suppression key. Pins: `tests/test_run_mypy_gate.py` (11 registered pin nodes in `.github/gate-registry.yaml`). |
| 3 | A missing or empty historical baseline is handled explicitly | 已通过 | This row checks the gate's behaviour, not who authorized the deletion. The gate treats any well-formed error report as red with no filter between the checker and the verdict. This state came from #258 under #222; #221 itself did not authorize the deletion, and the owner's 2026-11-16 waiver covers the removal. A `[tool.mypy-baseline]` table is still refused as a reintroduction tripwire. |
| 4 | The intended source tree is still checked; new modules are included automatically | 已通过 | `src/` is enumerated live (34 `.py` files today), and mypy's checked count must cover it. The gate refuses a shortfall and does not pin a file count. Main run log: `Success: no issues found in 34 source files (scope: 34 .py files); type errors: 0`. |
| 5 | Strict settings are retained | 已通过 | `pyproject.toml` still has `strict`, `warn_unused_ignores`, `warn_unused_configs` and `python_version`. The gate whitelist refuses any other key, any overrides table and the known suppression flags. |
| 6 | Removing mypy and its aggregate dependency together is detected | 已通过 | `check_ci_wiring.py` reads the job graph and requires lint, mypy, test and the `ci` summary to stay connected. Negative fixture: missing mypy plus its aggregate need. Pins: `tests/test_check_ci_wiring.py::test_a_missing_mypy_and_its_aggregate_need_is_red`. |
| 7 | Skipping the whole mypy job or only its check step is detected | 已通过 | The wiring checker rejects skip-capable conditions in all steps of the four protected jobs, including transitive `needs` chains. Negative fixtures cover whole-job and step-level skips. |
| 8 | `continue-on-error` and failure-swallowing shell forms are rejected | 已通过 | The wiring checker rejects unknown `continue-on-error` values and the measured shell forms (`\|\| true`, `\|\| :`, `\|\| echo`, `\|\| exit 0`) in protected jobs. |
| 9 | Lint and pytest stay in the mandatory aggregate | 已通过 | `ci.yml` keeps `needs: [lint, mypy, test]` and the three `test ... = "success"` commands. The wiring checker fails when a dependency is removed. |
| 10 | The registry distinguishes executed commands from comments | 已通过 | `check_ci_wiring.py` requires a real run-text line per registered gate; comment-only and echo-only forms do not count. Negative fixtures cover this. |
| 11 | The registry check itself stays protected | 已通过 | `check_gate_registry` registers itself and is wired in CI; `tests/test_check_gate_registry.py` pins the clean-registry and unregistered-object cases. Its own scope limit is disclosed in the script. |
| 12 | The actual GitHub required-check configuration is known | 已通过 | Read at `2026-11-16T03:48:50Z`: required contexts `ci`, `ruff budget gate`, `mypy baseline gate`, all from GitHub Actions `app_id 15368`; `strict: false`; `enforce_admins: false`; `required_conversation_resolution: true`; force pushes and deletions disabled; `rulesets: []`. Frozen in `docs/evidence/branch-protection-main-2026-11-16.json`. |
| 13 | Missing admin access is recorded instead of guessed | 已通过 | #256 recorded the 2026-11-15 403. The 2026-11-16 read succeeded and is recorded here with its time and account, so it is a point-in-time fact, not a permanent assumption. |
| 14 | A clean ordinary PR stays green | 已通过 | PR #286 at final head `8ed81334`: every check-run that is meant to run on a pull request is green, including `ci`, `mypy baseline gate`, `ruff budget gate`, the four pytest legs, coverage (separate workflow run) and the Semgrep app scan. The two scheduled drift canaries are `skipped` by their trigger condition, as designed. Actions run: https://github.com/Xxx91n/mcp-for-maya/actions/runs/43751203949 ; coverage: https://github.com/Xxx91n/mcp-for-maya/actions/runs/43751203951 ; Semgrep: https://github.com/Xxx91n/mcp-for-maya/runs/132925320352 |
| 15 | CI failures name which check was lost or bypassed | 已通过 | The gate prints a tagged `::error` (`config_fault`, `checker_fault`, `execution_fault`, `scope_fault`, `type_fault`). The wiring checker prints its own finding tag and path. |
| 16 | The negative test suite is repeatable | 已通过 | The gate and wiring pins are registered and run in CI. The disposable PRs (#242, #246, #261, #287) were closed without merging; #287's remote branch was deleted. |
| 17 | No branch-protection change without approval | owner 已接受边界 | The 2026-11-14 A3 (#228) work under #221 added `ruff budget gate` and `mypy baseline gate` to the required contexts. `docs/ci-wiring.md` records the `PATCH` and the read-back, but the immutable record does not quote a prior explicit approval. The owner later closed #228 and #221 with that setting in place, and the 2026-11-16 read confirms it; that is an accepted boundary, not proof of prior approval. #256, #258 and #259 made no further edits; the job name stayed `mypy baseline gate`. |
| 18 | No Maya runtime change from the governance work | 已通过 | The #258 diff touches the gate, its tests, docs, CI config, dependency metadata and two small references; no file under `src/maya_mcp_server/` changed. |
| 19 | Existing vocabulary and test conventions are respected | 已通过 | The work extends the existing gate registry, wiring checker and pytest seams; it does not add a second registry or a parallel checker framework. |
| 20 | An independent merge anchor exists, so the check cannot silently disappear | owner 已接受边界 | Not implemented. #250/PR #261 showed that keeping the three required names while replacing the real tool with an unconditional success still produced a green, mergeable PR. #254 and #256 were closed `not planned`; the owner accepted the risk in the #256 closeout comment (https://github.com/Xxx91n/mcp-for-maya/issues/256#issuecomment-6890139942). |
| 21 | The owner separately decides `strict` and `enforce_admins` | owner 已接受边界 | Not separately decided. The #256 closeout explicitly accepted the risk of leaving both unknown, made no change, and said that accepting the risk is not the same as choosing. The fresh read shows both `false`. That is the recorded boundary, not a choice. |

### #256's four independent-merge constraints, side by side

| Constraint | Status | Evidence |
| --- | --- | --- |
| A required check is missing | 已通过（historical） | PR #246 deleted the whole CI workflow; the required contexts never reported and GitHub returned `mergeStateStatus: BLOCKED`. The PR was closed unmerged. Recorded in #221's 2026-11-14 comment; not re-run because #259 says not to repeat closed tasks. |
| A required check is skipped | owner 已接受边界 | PR #242 made the required `ci` job `SKIPPED`; after the other blockers were cleared, GitHub reported `UNSTABLE` / `MERGEABLE`. The in-repo wiring check rejects parseable skip edits, but the skip itself is not a hard block at the GitHub layer. #221's closeout comment records this as a known gap and accepts it. |
| A check name is kept and the tool is replaced with a fake success | owner 已接受边界 | #250/PR #261 kept all three required names and made the tool step succeed unconditionally; the checks stayed green and the PR was mergeable. #254/#256 stopped this work and the owner accepted the risk. |
| A real new type error | 已通过（fresh） | PR #287: `mypy baseline gate` red with the injected error named, PR `BLOCKED`, closed unmerged. |

Known skip behaviour is part of the boundary, not a separate pass: the in-repo
wiring check runs inside the lint job, so a coordinated workflow deletion can
remove both the check and its protector.

## #222 — the conditions and where each one stands

#222 is still open. The type cleanup is done, the strict gate is retained, and
the owner waived its exit condition on 2026-11-16. The table below records both
the finished work and that waiver.

#222's per-batch conditions (each batch removes its intended errors, adds no
unreviewed errors, keeps strictness and scope, and passes tests/CI) were closed
by the tickets below. This ticket does not re-run those batches, per #259's
rule not to repeat closed tasks; it records where each one landed.

| Batch | PR | Merge commit | What it closed |
| --- | --- | --- | --- |
| #225 (B1) | #233 | `426c6a89` | Five aesthetic colour helpers annotated |
| #224 (B1) | #230 | `d0831cae` | Scene tool registration and token budget typed |
| #227 (B2) | #236 | `1ece725e` | Scene JSON containers typed |
| #229 (B3) | #238 | `e0199547` | Maya stub-disagreement errors settled with evidence |
| #252 | #264 | `a7f6c294` | Scene-plan organisation chain annotated |
| #251 | #267 | `95a95a58` | Aesthetic scoring chain annotated, baseline shrunk |
| #255 | #270 | `554e1c87` | Scene standards container pinned, 10 findings dropped |
| #253 (evidence) | — | `983c4961` | Six call forms measured on Maya 2024 |
| #257 | #274 | `96ffd83a` | Last untyped calls typed, raw mypy to zero |
| #258 (decision) | #286 | `6b5a84e2` | Baseline retired, strict gate retained |

Story 5 (duplicate messages must not hide a replacement error) and story 8
(baseline regeneration only from a valid full report) were handled in the batch
records as they ran; this ticket does not re-verify each batch. The final state
makes them moot for the gate: the baseline is empty and then removed, so no
duplicate message is hidden by it. No dependency upgrade was made during the
cleanup (story 18), and no exception growth was accepted (story 19).

The table after this one re-checks the final conditions only.

| # | Condition (from #222 and #258) | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Full unfiltered strict mypy is re-run on locked dependencies, with SHA, versions, exit code, error set and checked scope recorded | 已通过 | #258 record: `mypy==2.3.1` (compiled), `types-maya-strict==2025.0.6`, target Python 3.10, 34 of 34 files, exit 0, stderr empty. Main re-run confirms it: `mypy gate OK: mypy exited 0; report: 1 lines; Success: no issues found in 34 source files (scope: 34 .py files); type errors: 0` (run 43754350484). |
| 2 | Strict config, source scope and the precision of `Any` / `ignore` are checked; zero errors is not bought by a weaker config | 已通过 | The strict trio, whitelist, overrides refusal and live scope enumeration are unchanged. `docs/reference/type-precision-inventory-257.md` lists the remaining weak spots as review concerns, not hidden errors. |
| 3 | A new type error is stopped under real protection | 已通过 | See #221 row 1: PR #287 red and `BLOCKED`. |
| 4 | Branch one: a separate PR deletes the baseline and its dependency, and the gate fails closed without a filter | 已通过 | PR #286 (merged as `6b5a84e2`). `mypy-baseline.txt` deleted, `mypy-baseline==0.7.4` removed, `run_mypy_gate.py` no longer reads or filters a baseline. |
| 5 | Normal CI and the negative injection both pass | 已通过 | PR #286 green at `8ed81334`; PR #287 red only on the injected type error, then closed unmerged. |
| 6 | Behaviour tests and real-Maya evidence are present, with skips not counted as passes | 已通过 | Four pytest legs on 3.10/3.13 × ubuntu/windows: ubuntu 3.13 1599 passed / 28 skipped; ubuntu 3.10 1598 / 29; windows 3.13 1599 / 28; windows 3.10 1598 / 29. The skips are reported as skips in every leg. #253's Maya 2024 GUI run: 6/6 call forms pass (xform, rename, keyTangent, playbackOptions, aimConstraint, MFnMesh.getPoint). Artifact: `docs/evidence/probes/probe-253-six-callforms-gui-maya2024-v2.json`. The mayapy/standalone lane is recorded as blocked by a DLL initialisation failure, not as a skip-pass. |
| 7 | The final result is one of the two named outcomes, with a check against #222's close criteria | 已通过 | Result: `baseline retired, strict gate retained`. #258's record lists the close criteria and marks the CI-guard row as unmet; the owner waived that row on 2026-11-16 (next row). |
| 8 | No branch-protection edit in this ticket | 已通过 | No ruleset or protection change was made by #258 or #259. |
| 9 | #222's exit rule: a separate CI guard proves the check cannot silently disappear before the baseline is retired | owner 已接受边界 | Owner decision 2026-11-16: 退役 — keep the baseline retired and waive this exit rule, with the residual risks below accepted. The guard is still absent, and #258's table still says `Not met`; this is a waiver, not a pass. The final #222 comment records the decision. |

Why row 9 blocked the closeout before 2026-11-16: #221's closing comment says
its administrative closure must not be read as permission to delete the
baseline, and that removing it later needs a separate decision on whether to
accept or adjust that precondition
(https://github.com/Xxx91n/mcp-for-maya/issues/221#issuecomment-6890140857).
The owner accepted the risk of not building the guard (#256) and merged the
retirement (#286), but neither text was an explicit waiver of #222's exit rule.
On 2026-11-16 the owner supplied that waiver: the baseline stays retired, the
guard stays missing, and the risk is accepted. The guard is not created by this
decision and must not be cited as existing.

## What was checked for stray blockers

- Open issues at read time: #222, #259, and unrelated records/roadmaps (#178,
  #80, #53, #7, #6, #4, #3). No blocking fix ticket was created for #221 or
  #222.
- Open pull requests: none. PR #287 was closed unmerged; its branch is deleted.
- #212 is closed `completed` (2026-11-13). #223–#229 are all closed `completed`
  with their work in `main`; #212's follow-up split is intact.
- #253 is closed with its Maya evidence in the tree. #257 is closed with its
  inventory in the tree. #258 is closed; #286 is merged as `6b5a84e2`.
- #178 is untouched: still open, `updatedAt 2026-11-13T15:15:51Z`, and its
  historical content was not rewritten.
- The #257 inventory listed candidate typing follow-ups. Both were resolved
  before this record: #275 (`b3823cb4`) typed the aesthetic merge result, and
  #276 (`96a91119`) removed the duplicated light-payload builders. No open
  typing follow-up blocks #222's exit.

## Final status table

| Area | 已通过 | owner 已接受边界 | 未完成 |
| --- | --- | --- | --- |
| #221 execution effect (run, fail closed, scope, strictness) | Rows 1–11, 14–16, 18–19 | Row 17 | — |
| #221 live configuration | Row 12 (read 2026-11-16T03:48:50Z), row 13 | Rows 20–21 | — |
| #222 type cleanup and retirement | Rows 1–8 | Row 9 (CI guard waived 2026-11-16) | — |
| #259 audit itself | Items 1–7 of its acceptance list | — | — |

### Ticket #259 acceptance list, item by item

| # | Criterion | Status | Where handled |
| --- | --- | --- | --- |
| 1 | Verify every original #221/#222 condition with evidence, an accepted boundary, or a blocked reason | 已通过 | #221 table, #222 table, batch trail |
| 2 | Re-check #256's four merge constraints and the latest protection config; record the time and the responsible party | 已通过 | #256 four-case table; row 12; frozen artifact |
| 3 | Re-check #258's conclusion, strict scope, negative test, full test results and #253's Maya evidence; do not count skip as pass | 已通过 | #222 rows 1–8; #253 artifact; pytest leg counts |
| 4 | Check for extra blocking fix tickets or unmerged required PRs | 已通过 | "What was checked for stray blockers" |
| 5 | Post final comments and close the parents once every key constraint is met; otherwise keep them open with the next action | 已通过 | Comments posted: [#221](https://github.com/Xxx91n/mcp-for-maya/issues/221#issuecomment-6907054225), [#222](https://github.com/Xxx91n/mcp-for-maya/issues/222#issuecomment-6907055030), [#259](https://github.com/Xxx91n/mcp-for-maya/issues/259#issuecomment-6907056041). #222 and #259 closed `completed`; #221 stayed closed `not planned`. |
| 6 | Record #212, #223–#229 and #178; do not claim permanent immunity | 已通过 | "What was checked for stray blockers"; residual risk |
| 7 | Deliver the status table with PR, merge SHA, tests, real-Maya and settings-read links | 已通过 | This table, the evidence index and the artifact list below |

### Closeout artifacts

| Artifact | Value |
| --- | --- |
| Parent main SHA | `6b5a84e2fc215f43de3357658d96869becdd7113` |
| Baseline-retirement PR | #286 |
| This record's PR | #288 — https://github.com/Xxx91n/mcp-for-maya/pull/288 ; squash merge `4db5a556111bdc07c3146db163039c93e98368bc` |
| Normal CI on main | run 43754350484 |
| Post-closeout main CI | run 43802336391 — `ci` aggregate `lint=success mypy=success test=success`, four pytest legs, mypy and ruff pass |
| Normal CI on the retirement PR | run 43751203949 |
| Negative injection | PR #287, run 43750680182 |
| Automated tests | Four pytest legs: 1598–1599 passed, 28–29 skipped |
| Real Maya | #253, 6/6 on Maya 2024 GUI, probe v2 |
| Settings read | `docs/evidence/branch-protection-main-2026-11-16.json`, `2026-11-16T03:48:50Z` |

## Residual risk, stated so a later reader cannot mistake it for a pass

- A PR can keep the three required-check names and replace the real tool with
  a fake success. This was measured (#250 / PR #261) and is not fixed.
- A skipped required `ci` job can still look mergeable (#242). The in-repo
  wiring check catches parseable skip edits, but it can be deleted together
  with the workflow it protects.
- `strict: false` means a PR does not have to be up to date with `main` before
  merging. `enforce_admins: false` means an admin can merge without the
  required checks. An admin can also change the rules themselves. None of these
  is a defect in the repo checks; they are the external boundary.
- The mypy gate compares file counts, not file identities. A wholesale faked
  report with a consistent checked count is not detectable at that layer. A
  broad ignore that mypy actually uses remains a review decision.
- Real-Maya evidence covers Maya 2024 GUI and six call forms. Maya 2025/2026
  and the batch/standalone lane are not verified. The other booked call-form
  rows (camera, ls, file, selection, about(batch)) are not measured.
- No future CI run, type error or Maya version is permanently covered. This
  file records one point in time.

## Recorded decision and closeout steps

On 2026-11-16 the owner chose **退役**: keep the baseline retired, waive the
#222 exit rule, and accept the risks above. This is a waiver, not a guard. It
must not be cited as proof that the check cannot silently disappear.

Source: the owner's direction in the #259 implementation session on
2026-11-16. The pull request body, this file and the final #222 comment record
it on GitHub.

Closeout steps, completed on 2026-11-16:

1. Landed this record: PR #288, squash merge `4db5a556`.
2. Posted the final comments to #221, #222 and #259. Each repeats the verdict,
   the evidence links, the accepted boundary and the reason for closing.
   Neither parent comment claims the independent guard exists.
3. Closed #222 and #259. #222 was already `closed / completed` right after the
   merge; #259 was closed by the closeout run. #221 stayed
   `closed / not planned`.

## Evidence index

- Main commit: `6b5a84e2fc215f43de3357658d96869becdd7113` (PR #286).
- Main CI: https://github.com/Xxx91n/mcp-for-maya/actions/runs/43754350484
  (mypy job 132935050646; coverage 43754350415).
- PR #286 final head `8ed81334`:
  https://github.com/Xxx91n/mcp-for-maya/actions/runs/43751203949 ; coverage
  43751203951; Semgrep run 132925320352.
- PR #287 negative injection:
  https://github.com/Xxx91n/mcp-for-maya/actions/runs/43750680182/job/132923715156
- Branch-protection read: `docs/evidence/branch-protection-main-2026-11-16.json`
  (command and account in its `meta`).
- #250 fake-green measurement:
  https://github.com/Xxx91n/mcp-for-maya/issues/250#issuecomment-6879037895
- #256 owner risk acceptance:
  https://github.com/Xxx91n/mcp-for-maya/issues/256#issuecomment-6890139942
- #258 closing record: `docs/reference/mypy-baseline-retirement-258.md`
- #257 inventory: `docs/reference/type-precision-inventory-257.md`
- #253 Maya run: `docs/evidence/probes/probe-253-six-callforms-gui-maya2024-v2.json`
  and `docs/testing.md`
- CI wiring rules and limits: `docs/ci-wiring.md`
- Gate registry: `.github/gate-registry.yaml`
