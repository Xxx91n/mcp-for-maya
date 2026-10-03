"""D-212 tier-2 sensitivity track for the liveness probe.

An INSTRUMENT has no veto power: nothing it produces can turn a PR red, which
is exactly why the ruling does not hand it a per-PR pin. It gets the weaker
obligation instead -- prove it still reacts to a KNOWN FAULT. A counterfactual
pin asks "does this input produce red?". A sensitivity experiment asks the
complementary and harder question: "when reality breaks, does the instrument
notice at all?" An instrument that silently stopped reporting has no red to
look for, so nothing else in CI would notice either.

WHY THIS FILE IS ABOUT ONE INSTRUMENT. The R46 task book named
evidence_anchors / readme_skeleton / version_unification / liveness_probe /
notify_drift_canary as the *suspected* zero-pin gates and required a per-gate
re-check before backfilling. Re-checking found the suspicion was right for
liveness_probe (no test file existed) and WRONG for notify_drift_canary, which
already carries 12 tests in tests/test_notify_drift_canary.py. Seven tests
written here for notify were therefore duplicates and were deleted rather than
committed alongside the real ones -- a registry entry claiming a pin file "does
not exist" is a false record, and the fix is to correct the record, not to leave
a redundant test file looking like corroboration.

FORM (D-212 tier 2 / D-215 5):
  fault injection -> the instrument must produce a NON-ZERO verdict.
  Silence is the failure this lane exists to catch, so every case below asserts
  the instrument REACTED.

CADENCE: this logic is a pytest module, so it runs in the CI matrix on every PR
on both platforms. What is deliberately NOT automated is the live half --
pointing the real probe at a real Maya session. That needs a human with the
environment, so it stays a manual step recorded in the release checklist, not
something to fake here (D-205 3: unreproducible is recorded as unverified, never
guessed).

SCOPE, stated honestly: these tests exercise the probe's REACTION LOGIC with an
injected collaborator, not its real subprocess spawn against a live server. They
establish that the verdict wiring is intact. They do NOT establish that a Maya
session is reachable, and nothing here should be read as claiming that. The
real spawn is covered separately by running the probe itself, which is a
manual preflight step.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / ".github" / "scripts"

ALL_TOOLS = {"scene_snapshot", "scene_review", "execute_code", "write_module"}
UMBRELLAS_GONE = {"execute_code", "maya_setup_guide", "write_module"}


def _load(name: str):
    path = SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# liveness_probe
# ---------------------------------------------------------------------------


def _fixed_probe(mod, unguarded: set[str], guarded: set[str]):
    """Replace the subprocess spawn with a scripted pair of answers."""
    answers = [(("0.5.0"), unguarded), (("0.5.0"), guarded)]

    def fake(_env_extra):
        return answers.pop(0)

    mod.probe = fake


def test_a_dead_server_is_not_reported_as_a_pass():
    """Fault: the server answers nothing (empty tool list). A probe that treated
    an empty list as 'nothing to check' would print PASS and exit 0 -- the exact
    silence this lane hunts."""
    mod = _load("liveness_probe")
    _fixed_probe(mod, set(), set())
    assert mod.main(["--policy-flag", "MAYA_MCP_DISABLE_ARBITRARY"]) == 1


def test_a_policy_flag_that_removes_nothing_is_red():
    """Fault: the strict-policy escape hatch stops removing anything. That is the
    exact regression D-207 1 legislated against, and it is invisible to every
    other gate because the tool list still looks healthy."""
    mod = _load("liveness_probe")
    _fixed_probe(mod, ALL_TOOLS, ALL_TOOLS)
    assert mod.main(["--policy-flag", "MAYA_MCP_DISABLE_ARBITRARY"]) == 1


def test_a_policy_flag_that_leaks_a_forbidden_tool_is_red():
    mod = _load("liveness_probe")
    _fixed_probe(mod, ALL_TOOLS, ALL_TOOLS - {"write_module"})
    assert mod.main(["--policy-flag", "MAYA_MCP_DISABLE_ARBITRARY"]) == 1


def test_a_policy_flag_that_removes_a_read_only_tool_is_red():
    """Fault in the other direction: collateral damage. A flag that took the
    read-class surface with it would still 'pass' a leak-only check."""
    mod = _load("liveness_probe")
    _fixed_probe(mod, ALL_TOOLS, (ALL_TOOLS - UMBRELLAS_GONE) - {"scene_snapshot"})
    assert mod.main(["--policy-flag", "MAYA_MCP_DISABLE_ARBITRARY"]) == 1


def test_a_policy_flag_that_removes_every_tool_is_red():
    mod = _load("liveness_probe")
    _fixed_probe(mod, ALL_TOOLS, set())
    assert mod.main(["--policy-flag", "MAYA_MCP_DISABLE_ARBITRARY"]) == 1


def test_healthy_probe_run_is_green():
    """The live-green control for the four reds above."""
    mod = _load("liveness_probe")
    _fixed_probe(mod, ALL_TOOLS, ALL_TOOLS - UMBRELLAS_GONE)
    assert mod.main(["--policy-flag", "MAYA_MCP_DISABLE_ARBITRARY"]) == 0


def test_the_umbrella_flag_expectation_matches_the_code_not_a_restated_copy():
    """D-214: the flag table is object-derivable, so it is read from
    pipeline.POLICY_ENV_FLAGS. A probe asserting a second hand-written copy of
    that table is how a probe ends up checking the wrong thing and reporting
    PASS."""
    mod = _load("liveness_probe")
    assert mod.expected_removed("MAYA_MCP_DISABLE_ARBITRARY") == UMBRELLAS_GONE
    assert mod.expected_removed("MAYA_MCP_DISABLE_EXECUTE") == {"execute_code"}


def test_the_protocol_revision_comes_from_the_spec_file():
    """D-214: PROTOCOL is a governance constant, so its source is
    .github/liveness-probe-spec.yaml, not a literal in this script."""
    mod = _load("liveness_probe")
    import json

    spec = json.loads((REPO / ".github" / "liveness-probe-spec.yaml").read_text(encoding="utf-8"))
    assert mod.PROTOCOL == spec["PROTOCOL"]
