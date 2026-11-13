"""Pins for .github/scripts/check_ci_wiring.py.

The checker's whole job is one sentence: the lint, mypy and pytest jobs
must stay in the workflow, must run their tools, must not be skipped or
swallow failures, and must stay in the ``ci`` summary. Each broken shape
below is a small edit to a valid workflow, and each test asserts the
check fails for the right reason -- a named tag, not just "some finding".

Every red is paired with the live-green control
(``test_the_real_workflow_is_clean``) so a check that fires on everything
is as visible as one that fires on nothing. The valid fixture also carries
the three shapes that must NOT fail: a non-protected job with
``continue-on-error: true``, the ruff ``--exit-zero`` report step whose
budget step enforces the verdict, and the mypy ``|| rc=$?`` exit-code
capture.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".github" / "scripts" / "check_ci_wiring.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_ci_wiring", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


VALID = (
    """name: CI

on:
  pull_request:

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - name: ruff check (JSON report)
        run: uvx ruff@0.17.1 check . --output-format=json --exit-zero > ruff-report.json
      - name: compare against the ruff error budget
        run: python .github/scripts/check_ruff_budget.py ruff-report.json .github/ruff-baseline.json

  mypy:
    runs-on: ubuntu-latest
    steps:
      - name: mypy | mypy-baseline filter
        run: |
          rc=0
          uv run python -m mypy src/ > mypy-report.txt || rc=$?
          if [ "$rc" -gt 1 ]; then cat mypy-report.txt; exit "$rc"; fi
          uv run mypy-baseline filter < mypy-report.txt

  test:
    runs-on: ubuntu-latest
    steps:
      - name: pytest
        run: uv run python -m pytest -q

  drift-notify:
    runs-on: ubuntu-latest
    continue-on-error: true
    steps:
      - name: notify
        run: echo notify

  ci:
    needs: [lint, mypy, test]
    if: always()
    runs-on: ubuntu-latest
    steps:
      - name: aggregate results
        run: |
          echo "lint=${{ needs.lint.result }} mypy=${{ needs.mypy.result }}"
"""
    + "          "
    + " && ".join(
        'test "${{ needs.' + name + '.result }}" = "success"' for name in ("lint", "mypy", "test")
    )
    + "\n"
    + """
"""
)

MYPY_JOB = """  mypy:
    runs-on: ubuntu-latest
    steps:
      - name: mypy | mypy-baseline filter
        run: |
          rc=0
          uv run python -m mypy src/ > mypy-report.txt || rc=$?
          if [ "$rc" -gt 1 ]; then cat mypy-report.txt; exit "$rc"; fi
          uv run mypy-baseline filter < mypy-report.txt

"""


def _check(tmp_path: Path, text: str) -> list[str]:
    mod = _load()
    path = tmp_path / "ci.yml"
    path.write_text(text, encoding="utf-8")
    return mod.check(tmp_path, path)


# --- live-green controls ---------------------------------------------------


def test_the_real_workflow_is_clean():
    """The positive control every red below is measured against."""
    mod = _load()
    findings = mod.check(REPO)
    assert findings == [], findings


def test_a_minimal_valid_workflow_is_clean(tmp_path):
    """The fixture itself must pass, or every red below is meaningless."""
    assert _check(tmp_path, VALID) == []


def test_block_style_needs_still_passes(tmp_path):
    """``needs:`` as a block list is the same wiring as the inline list."""
    text = VALID.replace(
        "    needs: [lint, mypy, test]\n",
        "    needs:\n      - lint\n      - mypy\n      - test\n",
    )
    assert _check(tmp_path, text) == []


def test_a_non_protected_job_may_be_skipped(tmp_path):
    """Only the protected jobs are held to the no-skip rule."""
    text = VALID.replace(
        "  drift-notify:\n    runs-on:",
        "  drift-notify:\n    if: false\n    runs-on:",
    )
    assert _check(tmp_path, text) == []


def test_main_is_zero_on_the_real_workflow(monkeypatch):
    mod = _load()
    monkeypatch.setattr(sys, "argv", ["check_ci_wiring.py"])
    assert mod.main() == 0


# --- missing jobs ----------------------------------------------------------


def test_a_missing_mypy_job_is_red(tmp_path):
    findings = _check(tmp_path, VALID.replace(MYPY_JOB, ""))
    assert findings, "a deleted mypy job must be reported"
    assert any("mypy" in f and "missing_job" in f for f in findings), findings


def test_a_missing_mypy_and_its_aggregate_need_is_red(tmp_path):
    """The coordinated edit: job and summary reference go together."""
    text = VALID.replace(MYPY_JOB, "").replace("needs: [lint, mypy, test]", "needs: [lint, test]")
    findings = _check(tmp_path, text)
    assert any("missing_job" in f for f in findings), findings
    assert any("aggregate_broken" in f for f in findings), findings


# --- skipped jobs and steps ------------------------------------------------


def test_a_skipped_mypy_job_is_red(tmp_path):
    text = VALID.replace("  mypy:\n    runs-on:", "  mypy:\n    if: false\n    runs-on:")
    findings = _check(tmp_path, text)
    assert any("job_skipped" in f for f in findings), findings


def test_a_skipped_mypy_step_is_red(tmp_path):
    text = VALID.replace(
        "      - name: mypy | mypy-baseline filter\n        run: |",
        "      - name: mypy | mypy-baseline filter\n        if: false\n        run: |",
    )
    findings = _check(tmp_path, text)
    assert any("step_skipped" in f for f in findings), findings


def test_an_aggregate_without_always_is_red(tmp_path):
    text = VALID.replace(
        "    if: always()\n    runs-on: ubuntu-latest\n    steps:\n      - name: aggregate",
        "    runs-on: ubuntu-latest\n    steps:\n      - name: aggregate",
    )
    findings = _check(tmp_path, text)
    assert any("job_skipped" in f for f in findings), findings


# --- aggregate wiring ------------------------------------------------------


def test_a_lint_need_removed_from_aggregate_is_red(tmp_path):
    text = VALID.replace("needs: [lint, mypy, test]", "needs: [mypy, test]")
    findings = _check(tmp_path, text)
    assert any("aggregate_broken" in f for f in findings), findings


def test_a_test_need_removed_from_aggregate_is_red(tmp_path):
    text = VALID.replace("needs: [lint, mypy, test]", "needs: [lint, mypy]")
    findings = _check(tmp_path, text)
    assert any("aggregate_broken" in f for f in findings), findings


def test_an_aggregate_that_no_longer_checks_mypy_is_red(tmp_path):
    text = VALID.replace('test "${{ needs.mypy.result }}" = "success" && ', "")
    findings = _check(tmp_path, text)
    assert any("aggregate_broken" in f for f in findings), findings


# --- tool calls that only appear in comments -------------------------------


def test_a_comment_only_tool_call_is_red(tmp_path):
    text = VALID.replace(
        "          uv run python -m mypy src/ > mypy-report.txt || rc=$?\n",
        "          # uv run python -m mypy src/\n",
    ).replace(
        "          uv run mypy-baseline filter < mypy-report.txt\n",
        "          # uv run mypy-baseline filter\n",
    )
    findings = _check(tmp_path, text)
    assert findings, "a tool named only in comments must be reported"
    assert any("tool_not_executed" in f for f in findings), findings


# --- swallowed failures ----------------------------------------------------


def test_continue_on_error_on_the_mypy_job_is_red(tmp_path):
    text = VALID.replace(
        "  mypy:\n    runs-on: ubuntu-latest\n",
        "  mypy:\n    runs-on: ubuntu-latest\n    continue-on-error: true\n",
    )
    findings = _check(tmp_path, text)
    assert any("failure_swallowed" in f for f in findings), findings


def test_continue_on_error_on_the_mypy_step_is_red(tmp_path):
    text = VALID.replace(
        "      - name: mypy | mypy-baseline filter\n        run: |",
        "      - name: mypy | mypy-baseline filter\n"
        "        continue-on-error: true\n        run: |",
    )
    findings = _check(tmp_path, text)
    assert any("failure_swallowed" in f for f in findings), findings


def test_or_true_in_the_mypy_run_is_red(tmp_path):
    text = VALID.replace(
        "          uv run mypy-baseline filter < mypy-report.txt\n",
        "          uv run mypy-baseline filter < mypy-report.txt || true\n",
    )
    findings = _check(tmp_path, text)
    assert any("failure_swallowed" in f for f in findings), findings


# --- unreadable workflow ---------------------------------------------------


def test_a_missing_workflow_file_is_red_not_a_traceback(tmp_path):
    mod = _load()
    findings = mod.check(tmp_path, tmp_path / "no-such-ci.yml")
    assert findings, "a missing workflow file must be reported, not raise"
    assert any("workflow_unreadable" in f for f in findings), findings


def test_an_empty_workflow_file_is_red_not_a_silent_pass(tmp_path):
    findings = _check(tmp_path, "name: CI\n")
    assert findings, "a workflow with no jobs must not pass silently"
    assert any("workflow_unreadable" in f for f in findings), findings


# --- every finding names its rule ------------------------------------------

RULE_TAGS = (
    "missing_job",
    "job_skipped",
    "step_skipped",
    "failure_swallowed",
    "tool_not_executed",
    "aggregate_broken",
    "workflow_unreadable",
)


def test_every_finding_names_the_rule_it_fired(tmp_path):
    """A finding with no tag is unmappable, so each case pins its tag."""
    cases = [
        ("missing", "missing_job", VALID.replace(MYPY_JOB, "")),
        (
            "job-skip",
            "job_skipped",
            VALID.replace("  mypy:\n    runs-on:", "  mypy:\n    if: false\n    runs-on:"),
        ),
        (
            "step-skip",
            "step_skipped",
            VALID.replace(
                "      - name: mypy | mypy-baseline filter\n        run: |",
                "      - name: mypy | mypy-baseline filter\n        if: false\n        run: |",
            ),
        ),
        (
            "swallow",
            "failure_swallowed",
            VALID.replace(
                "          uv run mypy-baseline filter < mypy-report.txt\n",
                "          uv run mypy-baseline filter < mypy-report.txt || true\n",
            ),
        ),
        (
            "comment",
            "tool_not_executed",
            VALID.replace(
                "          uv run python -m mypy src/ > mypy-report.txt || rc=$?\n",
                "          # uv run python -m mypy src/\n",
            ).replace(
                "          uv run mypy-baseline filter < mypy-report.txt\n",
                "          # uv run mypy-baseline filter\n",
            ),
        ),
        (
            "aggregate",
            "aggregate_broken",
            VALID.replace("needs: [lint, mypy, test]", "needs: [mypy, test]"),
        ),
    ]
    for case_id, expected, text in cases:
        root = tmp_path / case_id
        root.mkdir()
        findings = _check(root, text)
        assert findings, f"{case_id}: the fixture must produce at least one finding"
        untagged = [f for f in findings if not any(tag in f for tag in RULE_TAGS)]
        assert untagged == [], f"{case_id} produced an unmappable finding: {untagged}"
        assert any(expected in f for f in findings), (
            f"{case_id}: expected {expected!r}, got {findings}"
        )


# --- blocking posture ------------------------------------------------------


def test_findings_are_blocking_with_no_opt_out(tmp_path):
    """A broken workflow must exit 1 with ::error lines, never a warning."""
    broken = tmp_path / "ci.yml"
    broken.write_text(VALID.replace(MYPY_JOB, ""), encoding="utf-8")
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), str(broken)],
        capture_output=True,
        text=True,
        cwd=REPO,
    )
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "::error" in proc.stdout, proc.stdout
    assert "::warning" not in proc.stdout, proc.stdout


def test_echo_is_not_a_tool_call(tmp_path):
    text = VALID.replace("run: uv run python -m pytest -q", "run: echo uv run python -m pytest -q")
    assert any("tool_not_executed" in f for f in _check(tmp_path, text))


def test_summary_echo_after_tests_is_red(tmp_path):
    assert any("aggregate_broken" in f for f in _check(tmp_path, VALID + "          echo done\n"))


def test_summary_skipped_step_is_red(tmp_path):
    text = VALID.replace(
        "- name: aggregate results", "- name: aggregate results\n        if: false"
    )
    assert any("step_skipped" in f for f in _check(tmp_path, text))


def test_job_flag_after_steps_is_red(tmp_path):
    text = VALID.replace("  drift-notify:", "    continue-on-error: true\n\n  drift-notify:")
    assert any("failure_swallowed" in f for f in _check(tmp_path, text))


def test_each_required_fault_exits_one(tmp_path):
    """Exercise the real process exit, not just the check() helper's findings."""
    faults = [
        VALID.replace(MYPY_JOB, "").replace("[lint, mypy, test]", "[lint, test]"),
        VALID.replace("  mypy:\n", "  mypy:\n    if: false\n"),
        VALID.replace(
            "- name: mypy | mypy-baseline filter",
            "- name: mypy | mypy-baseline filter\n        if: false",
        ),
        VALID.replace("[lint, mypy, test]", "[mypy, test]"),
        VALID.replace("[lint, mypy, test]", "[lint, mypy]"),
        VALID.replace("uv run python -m mypy src/", "# uv run python -m mypy src/"),
        VALID.replace(
            "uv run mypy-baseline filter < mypy-report.txt",
            "uv run mypy-baseline filter < mypy-report.txt || true",
        ),
    ]
    for number, text in enumerate(faults):
        path = tmp_path / f"fault-{number}.yml"
        path.write_text(text, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(path)], capture_output=True, text=True
        )
        assert proc.returncode == 1, (number, proc.stdout, proc.stderr)
        assert "::error" in proc.stdout
