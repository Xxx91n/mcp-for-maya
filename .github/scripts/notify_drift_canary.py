"""D-123 drift-canary notify bridge.

Turns the weekly resolution-drift job's conclusion into a persistent
work item (a GitHub issue), because a scheduled-job red only emails
the person who last touched the cron line — a structural blind spot
on a single-maintainer repo.

Semantics:

- drift red (failure/cancelled): open one dedup issue per
  workflow+branch, or COMMENT on the existing open issue — never
  spam a new issue per red.
- drift green (success): if a canary issue is open, comment the
  recovery and auto-close it.
- drift skipped / other results: no-op.

Dedup key: the open issue whose title carries the marker
``[drift-canary]`` plus the workflow name and branch — one live
issue per canary lane.

Invocation: notify_drift_canary.py (no args; env-driven).
  DRIFT_RESULT        — needs.drift.result (success|failure|cancelled|skipped)
  DRIFT_WORKFLOW      — github.workflow name (part of the dedup key)
  BRANCH              — github.ref_name (part of the dedup key)
  REPO                — owner/name for `gh` commands (default GITHUB_REPOSITORY)
  RUN_URL             — the run's URL, embedded for provenance
  RUN_ATTEMPT         — github.run_attempt
  GITHUB_SHA          — head sha
  GH_TOKEN            — auth token for gh (required on CI)
  DRY_RUN=1           — resolve the action but only print it (local debug)

The notify job wraps this with job-level continue-on-error: the
script may fail loudly (non-zero exit) without ever masking the
drift job's own red (D-123).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable


MARKER = "[drift-canary]"
RED = {"failure", "cancelled"}

Runner = Callable[[list[str]], str]


def _subprocess_runner(argv: list[str]) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout


def _gh(args: list[str], runner: Runner) -> str:
    return runner(["gh", *args])


def title_for(workflow: str, branch: str) -> str:
    return f"{MARKER} resolution-drift red — {workflow} on {branch}"


def find_open_issue(repo: str, workflow: str, branch: str, runner: Runner) -> int | None:
    """Issue number of the open canary issue for this lane, if any."""
    out = _gh(
        [
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--search",
            MARKER,
            "--json",
            "number,title",
            "--limit",
            "50",
        ],
        runner,
    )
    want = title_for(workflow, branch)
    for item in json.loads(out):
        if item.get("title") == want:
            return int(item["number"])
    return None


def _issue_body(env: dict[str, str]) -> str:
    return (
        "Weekly resolution-drift canary (uv lock --upgrade + pytest on the "
        "floating resolution) went red.\n\n"
        f"- workflow: {env.get('DRIFT_WORKFLOW', '?')}\n"
        f"- branch: {env.get('BRANCH', '?')}\n"
        f"- run: {env.get('RUN_URL', '?')} (attempt {env.get('RUN_ATTEMPT', '?')})\n"
        f"- sha: {env.get('GITHUB_SHA', '?')}\n\n"
        "A red here means upstream dependency drift first broke us — "
        "the D-100 trigger-debt is armed by this signal. Repeated reds "
        "comment on this issue instead of opening new ones; the issue "
        "auto-closes on the next green run.\n\n"
        "Obligation: at least one human review record (result + "
        "attribution in the decision ledger) is required before the "
        "v1.0.0 release checklist can pass — red or green counts "
        "(ADR-0023 / D-127)."
    )


def notify(env: dict[str, str], runner: Runner = _subprocess_runner) -> int:
    """Drive gh for one drift conclusion. Returns a process exit code."""
    result = env.get("DRIFT_RESULT", "").strip().lower()
    repo = env.get("REPO") or env.get("GITHUB_REPOSITORY", "")
    workflow = env.get("DRIFT_WORKFLOW", "CI")
    branch = env.get("BRANCH", "main")
    dry = env.get("DRY_RUN") == "1"
    if result not in RED | {"success"}:
        print(f"drift-notify: result={result!r} — nothing to do")
        return 0
    if not repo:
        print("::error::drift-notify: REPO/GITHUB_REPOSITORY unset")
        return 2

    number = find_open_issue(repo, workflow, branch, runner)
    title = title_for(workflow, branch)

    if result == "success":
        if number is None:
            print("drift-notify: green, no open canary issue — clean")
            return 0
        body = (
            f"Recovered on {env.get('RUN_URL', '?')} "
            f"(attempt {env.get('RUN_ATTEMPT', '?')}, sha {env.get('GITHUB_SHA', '?')}). "
            "Auto-closing — reopen via a fresh failure."
        )
        print(f"drift-notify: green — closing #{number}")
        if not dry:
            _gh(["issue", "comment", str(number), "--repo", repo, "--body", body], runner)
            _gh(["issue", "close", str(number), "--repo", repo], runner)
        return 0

    # red path
    if number is None:
        print(f"drift-notify: {result} — creating canary issue {title!r}")
        if not dry:
            _gh(
                [
                    "issue",
                    "create",
                    "--repo",
                    repo,
                    "--title",
                    title,
                    "--body",
                    _issue_body(env),
                ],
                runner,
            )
        return 0
    body = (
        f"Still red: {env.get('RUN_URL', '?')} "
        f"(attempt {env.get('RUN_ATTEMPT', '?')}, sha {env.get('GITHUB_SHA', '?')})."
    )
    print(f"drift-notify: {result} — commenting on #{number}")
    if not dry:
        _gh(["issue", "comment", str(number), "--repo", repo, "--body", body], runner)
    return 0


def main() -> int:
    return notify(dict(os.environ))


if __name__ == "__main__":
    sys.exit(main())
