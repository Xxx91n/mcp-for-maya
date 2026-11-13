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
`uv run python -m mypy`, `uv run mypy-baseline filter`,
`uv run python -m pytest`). Comments and echo-only calls do not count.
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
- Report contents and whether mypy really checked files belong to A2 (#226).
  No type-error budget, strictness setting, Maya behavior or baseline changes
  are part of this check.
