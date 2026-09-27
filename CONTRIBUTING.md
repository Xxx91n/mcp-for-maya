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

## Pull requests

- One branch per change; keep diffs small and reviewable.
- Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (feat / fix / docs / refactor / test / chore).
- CI gates (`.github/workflows/ci.yml`): `pytest` must be green on ubuntu + windows; the ruff budget
  (`.github/ruff-baseline.json`) is ratchet-only-down — above budget fails, and a lower count may be
  budgeted down in the same PR commit with the reason stated. The `src` count includes
  `aesthetic_engine.py`, a **dormant** module (zero production references; Maya-side inline
  `_score_*` is the live implementation — kept for the T-06 consolidation decision, see the
  ADR-0003 status note and D-038). `mypy` is baseline-gated in CI (`mypy-baseline.txt`; 223 errors in 3 files
  as of the post-audit resync — baseline counts are stub-env sensitive; drift trail
  221→223→212→223 across formatter and stub-environment changes): `python -m mypy src | mypy-baseline filter` fails only on NEW errors.
  After resolving errors, run `python -m mypy src | mypy-baseline sync` and commit
  the refreshed baseline in the same PR. The ruff budget is per-rule
  (`{segment:{rule:count}}`) since T-10b — rules cannot subsidise each other.

## Conduct

This project follows the [Contributor Covenant](https://www.contributor-covenant.org/version/2/1/code_of_conduct/) v2.1. Be respectful, assume good faith, keep discussion technical.
