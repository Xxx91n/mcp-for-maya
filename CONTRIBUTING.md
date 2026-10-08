# Contributing

## Development setup

```bash
uv sync --frozen                   # installs project + dev group from uv.lock (D-112)
# alternatives: uv sync (re-resolve) | pip install -e . --group dev (pip >=25.1)
pre-commit install                  # one-time: wire git hooks (.pre-commit-config.yaml)
pre-commit run --all-files          # hook sweep — CI runs this identical step as its lint fallback
python -m pytest tests/ -q         # stub-layer suite (contract tests vs the maya.cmds stub)
ruff check .                        # lint — frozen budget gate (.github/ruff-baseline.json), ratchet only goes down
python -m mypy src | mypy-baseline filter   # typecheck gate — fails only on NEW errors vs mypy-baseline.txt
python -m maya_mcp_server -vv      # run with DEBUG logs (-v=INFO, -vv=DEBUG)
```

House rules:

- Every fix ships with a regression test on the maya stub layer.
- Real-Maya tests are a separate local manual tier (`pytest -m mayapy`, see docs/testing.md) — never mixed with the stub tier.
- If your change makes a doc line stale, fix that line in the same commit (propagation matrix in AGENTS.md).
- When folding `[Unreleased]` into a release section, rewrite each Fixed entry's
  `fixed version: [Unreleased]` literal to that release's version number by hand.
  The `check_changelog_fixed.py` gate only checks field existence/non-emptiness —
  it does not police this rewrite (D-230 fold-time rule; human step).

## Pull requests

- One branch per change; keep diffs small and reviewable.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (feat / fix / docs / refactor / test / chore).
- CI gates (`.github/workflows/ci.yml`): `pytest` must be green on ubuntu + windows; the ruff budget
  (`.github/ruff-baseline.json`) is ratchet-only-down — above budget fails, and a lower count may be
  budgeted down in the same PR commit with the reason stated. `mypy` is baseline-gated in CI
  (`mypy-baseline.txt`; 184 errors in 2 files as of the D-124 dormant-module deletion —
  baseline counts are stub-env sensitive; drift trail 221→223→212→223→184 across formatter,
  stub-environment changes and dormant-code removal): `python -m mypy src | mypy-baseline filter`
  fails only on NEW errors.
  After resolving errors, run `python -m mypy src | mypy-baseline sync` and commit
  the refreshed baseline in the same PR. The ruff budget is per-rule
  (`{segment:{rule:count}}`) since T-10b — rules cannot subsidise each other.
  Budget gates are judged on the checked commit's tip (the PR's end state); a
  mid-PR commit that transiently exceeds a budget does not constitute a gate
  failure.

## Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) v2.1. Be respectful, assume good faith, keep discussion technical.
