#!/usr/bin/env python3
"""Check that the key CI jobs are still wired in .github/workflows/ci.yml.

The lint, mypy and pytest jobs do the real work, and the ``ci`` job sums
their results. This check fails when one of those jobs is gone, is skipped,
swallows its failure, only names the tool in a comment, or is cut from the
summary. It reads the workflow job/step structure and checks the ``run:`` lines,
so a tool name in a comment does not count as running the tool.

The rules, each finding carries one tag:

  missing_job         a protected job (lint, mypy, test) or the ``ci``
                      summary job is not in the workflow
  job_skipped         a protected job carries an ``if:`` that can skip it;
                      the summary must carry ``if: always()`` so it runs
                      even when a needed job failed
  step_skipped        the step that runs the tool carries an ``if:`` that
                      can skip it
  failure_swallowed   a protected job or its tool step sets
                      a non-false ``continue-on-error``, or the run text hides a
                      failure with ``|| true`` or the same shape
  tool_not_executed   the job has no ``run:`` line that actually calls its
                      tool (comments are stripped first)
  aggregate_broken    the ``ci`` summary does not need all three jobs, or
                      its final command does not test all three results for success
  workflow_unreadable the workflow file is missing or has no jobs to read;
                      the check fails closed instead of passing silently

Posture: hard gate. Findings are printed as ``::error`` and the process
exits 1; a clean workflow prints OK and exits 0. There is no warning mode.

Scope honesty, stated so nobody reads more into this than it does:

* This check runs inside the lint job. Deleting the lint job itself kills
  this check too, so that case is not covered here. Branch protection is
  the separate check for it.
* The parser handles the plain shape this repo uses: jobs at one indent,
  steps as ``- `` items, ``run:`` inline or as a ``|`` block. Anchors,
  flow mappings and other exotic YAML are out of scope; if no jobs can be
  read the check fails closed.
* Only the listed swallow shapes are flagged: ``continue-on-error: true``
  and ``|| true`` / ``|| :`` / ``|| echo`` / ``|| exit 0``. Shell tricks
  beyond those (for example ``set +e`` with a later ``; true``) are not
  detected.
* ``if: always()`` and ``if: success()`` are allowed on a tool step. Any
  other ``if:`` on the tool step is flagged, because this check cannot
  prove it still runs on an ordinary pull request. Move the tool call to
  an unconditional step instead of gating it.
* The ruff report step uses ``--exit-zero`` on purpose: it only writes the
  report, and the next step enforces the budget. That flag alone is not
  flagged; the budget step itself must exist and be fatal.

Usage:
    python .github/scripts/check_ci_wiring.py
    python .github/scripts/check_ci_wiring.py [path-to-ci.yml]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DEFAULT_WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

# The jobs whose loss must stop a merge, plus the summary that sums them.
PROTECTED_JOBS = ("lint", "mypy", "test")
SUMMARY_JOB = "ci"

# ``if:`` values that still mean "run on the ordinary path". Anything else
# on a tool step is treated as a skip risk.
_ALLOWED_IF = ("always()", "success()")

# Swallow shapes in shell run text. ``|| rc=$?`` (capture the code and check
# it) and ``|| cat ...; exit`` (print and re-raise) do not match these.
_SWALLOW = re.compile(r"\|\|\s*(true\b|:\s*(;|$)|\bexit\s+0\b|\becho\b)")

_JOB_NAME = re.compile(r"^([A-Za-z0-9_-]+):\s*(#.*)?$")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_yaml_comment(value: str) -> str:
    """Drop a trailing `` #...`` from a structural YAML line.

    A ``#`` inside quotes is kept. This is only for ``needs:`` / ``if:`` /
    ``continue-on-error:`` values, which never need a ``#`` of their own.
    """
    in_single = False
    in_double = False
    for i, ch in enumerate(value):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if i == 0 or value[i - 1] in " \t":
                return value[:i].rstrip()
    return value.strip()


def _strip_shell_comment(line: str) -> str:
    """Drop the shell comment from one run-text line.

    A full-line comment becomes empty, so a tool name that only appears in
    a comment never counts as an execution. A ``#`` inside quotes is kept.
    """
    in_single = False
    in_double = False
    for i, ch in enumerate(line):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if i == 0 or line[i - 1] in " \t":
                return line[:i].rstrip()
    return line.rstrip()


def _clean_if(value: str) -> str:
    """Normalise an ``if:`` value for the allowlist check."""
    text = _strip_yaml_comment(value).strip().strip("'\"")
    text = text.replace("${{", "").replace("}}", "").strip()
    return text.lower()


def _clean_bool(value: str) -> bool:
    return _strip_yaml_comment(value).strip().strip("'\"").lower() != "false"


def _parse_needs_inline(value: str) -> list[str]:
    """Parse ``needs: [a, b]`` or ``needs: a``."""
    text = _strip_yaml_comment(value).strip()
    if text.startswith("[") and text.endswith("]"):
        inner = text[1:-1]
        return [part.strip().strip("'\"") for part in inner.split(",") if part.strip()]
    if text:
        return [text.strip("'\"")]
    return []


def _parse_workflow(text: str) -> dict[str, dict]:
    """Read jobs, their needs/if flags, and their steps from workflow text.

    Returns ``{job: {"needs": [...], "if": str|None, "continue_on_error":
    bool, "steps": [{"run": str, "if": str|None, "continue_on_error": bool}]}}``.
    Only the plain shape this repo uses is handled; anything else yields
    fewer jobs, and the caller fails closed on a missing job.
    """
    lines = text.splitlines()
    jobs: dict[str, dict] = {}

    jobs_at: int | None = None
    for i, line in enumerate(lines):
        if _strip_yaml_comment(line).strip() == "jobs:":
            jobs_at = i
            break
    if jobs_at is None:
        return jobs

    job_indent: int | None = None
    current_job: str | None = None
    current_step: dict | None = None
    in_steps = False
    steps_indent: int | None = None
    step_indent: int | None = None
    needs_block = False
    needs_indent = 0
    run_block = False
    run_indent = 0
    run_lines: list[str] = []

    def flush_run() -> None:
        nonlocal run_block, run_lines, current_step
        if run_block and current_step is not None:
            current_step["run"] = "\n".join(run_lines)
        run_block = False
        run_lines = []

    i = jobs_at + 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        indent = _indent(line)

        if run_block:
            if stripped == "" or indent > run_indent:
                run_lines.append(line)
                i += 1
                continue
            flush_run()
            # Fall through: this line ends the block and is read again.

        if stripped == "":
            i += 1
            continue

        if needs_block:
            if stripped.startswith("- ") and indent > needs_indent:
                item = _strip_yaml_comment(stripped[2:]).strip().strip("'\"")
                if item and current_job is not None:
                    jobs[current_job]["needs"].append(item)
                i += 1
                continue
            needs_block = False

        # A job name: one level under ``jobs:``, nothing after the colon.
        if job_indent is None or indent == job_indent:
            m = _JOB_NAME.match(stripped)
            if m and indent > _indent(lines[jobs_at]):
                if job_indent is None:
                    job_indent = indent
                current_job = m.group(1)
                jobs[current_job] = {
                    "needs": [],
                    "if": None,
                    "continue_on_error": False,
                    "steps": [],
                }
                current_step = None
                in_steps = False
                steps_indent = None
                step_indent = None
                i += 1
                continue

        if current_job is None or job_indent is None or indent <= job_indent:
            # A top-level key (name:, on:, ...) ends the jobs section.
            if indent <= _indent(lines[jobs_at]):
                break
            i += 1
            continue

        if _strip_yaml_comment(stripped) == "steps:" and not in_steps:
            in_steps = True
            steps_indent = indent
            i += 1
            continue

        if in_steps and stripped.startswith("- ") and indent > (steps_indent or 0):
            if step_indent is None:
                step_indent = indent
            current_step = {"run": "", "if": None, "continue_on_error": False}
            jobs[current_job]["steps"].append(current_step)
            # A ``- run: ...`` step carries its key on the dash line.
            rest = stripped[2:].strip()
            if rest.startswith("run:"):
                value = rest[len("run:") :].strip()
                if value in ("|", "|-", "|+", ">", ">-", ">+"):
                    run_block = True
                    run_indent = indent
                    run_lines = []
                elif value:
                    current_step["run"] = _strip_yaml_comment(value)
            elif rest.startswith("if:"):
                current_step["if"] = rest[len("if:") :].strip()
            elif rest.startswith("continue-on-error:"):
                current_step["continue_on_error"] = _clean_bool(rest[len("continue-on-error:") :])
            i += 1
            continue

        if in_steps and current_step is not None and indent > (step_indent or 0):
            if stripped.startswith("run:"):
                value = stripped[len("run:") :].strip()
                if value in ("|", "|-", "|+", ">", ">-", ">+"):
                    run_block = True
                    run_indent = indent
                    run_lines = []
                elif value:
                    current_step["run"] = _strip_yaml_comment(value)
            elif stripped.startswith("if:"):
                current_step["if"] = stripped[len("if:") :].strip()
            elif stripped.startswith("continue-on-error:"):
                current_step["continue_on_error"] = _clean_bool(
                    stripped[len("continue-on-error:") :]
                )
            i += 1
            continue

        if indent == (steps_indent or -2):
            in_steps = False

        if not in_steps:
            if stripped.startswith("needs:"):
                value = stripped[len("needs:") :].strip()
                if value:
                    jobs[current_job]["needs"] = _parse_needs_inline(value)
                else:
                    needs_block = True
                    needs_indent = indent
            elif stripped.startswith("if:"):
                jobs[current_job]["if"] = stripped[len("if:") :].strip()
            elif stripped.startswith("continue-on-error:"):
                jobs[current_job]["continue_on_error"] = _clean_bool(
                    stripped[len("continue-on-error:") :]
                )
            i += 1
            continue

        i += 1

    flush_run()
    return jobs


def _run_text(job: dict) -> str:
    """All run text of a job with shell comments stripped."""
    parts = []
    for step in job["steps"]:
        for line in step["run"].splitlines():
            parts.append(_strip_shell_comment(line))
    return "\n".join(parts)


def _if_can_skip(value: str | None) -> bool:
    """True when an ``if:`` value can skip the job or step."""
    if value is None:
        return False
    text = _clean_if(value)
    if not text:
        return False
    return text not in _ALLOWED_IF


# Deliberately small command grammar, not arbitrary shell evaluation. A token in
# echo/printf, an assignment or a step name cannot satisfy these patterns.
_TOOL_CALLS = {
    "lint": (r"uvx ruff@[^ ]+ check .+", r"python \.github/scripts/check_ruff_budget\.py .+"),
    "mypy": (r"uv run python -m mypy .+", r"uv run mypy-baseline filter .+"),
    "test": (r"uv run python -m pytest .+",),
}


def _tool_missing(job_name: str, run_text: str) -> str | None:
    for pattern in _TOOL_CALLS.get(job_name, ()):
        if not any(re.fullmatch(pattern, line.strip()) for line in run_text.splitlines()):
            return pattern
    return None


def check(root: Path, workflow_path: Path | None = None) -> list[str]:
    """Return findings, one string per violation. Empty list == wired."""
    path = workflow_path or (root / ".github" / "workflows" / "ci.yml")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:
        return [f"workflow_unreadable -- cannot read the workflow file: {e}"]

    jobs = _parse_workflow(text)
    if not jobs:
        return ["workflow_unreadable -- no jobs could be read from the workflow file"]

    findings: list[str] = []

    for job_name in (*PROTECTED_JOBS, SUMMARY_JOB):
        if job_name not in jobs:
            findings.append(
                f"{job_name}: missing_job -- the {job_name} job is not in the "
                "workflow; a key check must stay in the merge path"
            )

    for job_name in PROTECTED_JOBS:
        job = jobs.get(job_name)
        if job is None:
            continue
        if _if_can_skip(job["if"]):
            findings.append(
                f"{job_name}: job_skipped -- the job carries an if: that can "
                "skip it; remove the condition so it runs on every pull request"
            )
        if job["continue_on_error"]:
            findings.append(
                f"{job_name}: failure_swallowed -- the job sets "
                "continue-on-error: true; a failing check must fail the job"
            )
        run_text = _run_text(job)
        missing = _tool_missing(job_name, run_text)
        if missing is not None:
            findings.append(
                f"{job_name}: tool_not_executed -- no run line actually calls "
                f"{missing}; a name in a comment does not count"
            )
        for step in job["steps"]:
            if _if_can_skip(step["if"]):
                findings.append(
                    f"{job_name}: step_skipped -- a step carries an if: that "
                    "can skip the tool call; move the call to an unconditional step"
                )
            if step["continue_on_error"]:
                findings.append(
                    f"{job_name}: failure_swallowed -- a step sets "
                    "continue-on-error: true; a failing check must fail the job"
                )
            for line in step["run"].splitlines():
                code = _strip_shell_comment(line)
                if _SWALLOW.search(code):
                    findings.append(
                        f"{job_name}: failure_swallowed -- the run text hides a "
                        "failure with || true or the same shape; let it fail"
                    )
                    break

    summary = jobs.get(SUMMARY_JOB)
    if summary is not None:
        if _clean_if(summary["if"] or "") != "always()":
            findings.append(
                "ci: job_skipped -- the summary must carry if: always() so it "
                "runs even when a needed job failed; without it a skipped "
                "summary can look green"
            )
        if summary["continue_on_error"]:
            findings.append(
                "ci: failure_swallowed -- the summary sets continue-on-error: "
                "true; a failing summary must fail the run"
            )
        for step in summary["steps"]:
            if step["continue_on_error"]:
                findings.append(
                    "ci: failure_swallowed -- a summary step sets "
                    "continue-on-error: true; a failing summary must fail the run"
                )
            for line in step["run"].splitlines():
                code = _strip_shell_comment(line)
                if _SWALLOW.search(code):
                    findings.append(
                        "ci: failure_swallowed -- the summary run text hides a "
                        "failure with || true or the same shape; let it fail"
                    )
                    break
        needs = summary["needs"]
        for job_name in PROTECTED_JOBS:
            if job_name not in needs:
                findings.append(
                    f"ci: aggregate_broken -- the summary does not need {job_name}; "
                    "every key check must stay in the summary"
                )
        for step in summary["steps"]:
            if _if_can_skip(step["if"]):
                findings.append("ci: step_skipped -- summary step can be skipped")
        summary_lines = _run_text(summary).splitlines()
        expected = " && ".join(
            'test "${{ needs.' + name + '.result }}" = "success"' for name in PROTECTED_JOBS
        )
        # This must be the last command: a later echo would mask its exit code.
        nonempty = [line.strip() for line in summary_lines if line.strip()]
        if not nonempty or nonempty[-1] != expected:
            findings.append("ci: aggregate_broken -- final command must test all three results")
        for job_name in PROTECTED_JOBS:
            needle = f"needs.{job_name}.result"
            checked = any(needle in line and "success" in line for line in summary_lines)
            if not checked:
                findings.append(
                    f"ci: aggregate_broken -- the summary run text does not check "
                    f"{needle} for success on one line; a failed job must fail "
                    "the summary"
                )

    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("workflow", nargs="?", default=str(DEFAULT_WORKFLOW))
    args = ap.parse_args()

    workflow_path = Path(args.workflow)
    if not workflow_path.is_absolute():
        workflow_path = REPO / workflow_path

    findings = check(REPO, workflow_path)
    for finding in findings:
        print(f"::error file=.github/workflows/ci.yml::{finding}")
    if findings:
        print(
            f"ci-wiring: {len(findings)} finding(s). Fix the workflow so the "
            "lint, mypy and pytest jobs run their tools, are not skipped, do "
            "not swallow failures, and stay in the ci summary."
        )
        return 1
    print(
        "ci-wiring OK: lint, mypy and pytest jobs run their tools, are not "
        "skipped, do not swallow failures, and stay in the ci summary"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
