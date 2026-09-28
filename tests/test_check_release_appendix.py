"""Regression tests for .github/scripts/check_release_appendix.py.

D-142beta weak assertions: disclosure-appendix section exists, is
non-empty, and the release body references the gate-tracker issue —
asserted only while that issue is open (a closed tracker discharges
the obligation). gh infrastructure failures are fail-loud (exit 2),
never silently absorbed.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "check_release_appendix.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_release_appendix", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


BODY_OK = (
    "# v0.4.0\n\nRelease notes.\n\n## Disclosure appendix\n\n"
    "Ship-time snapshot: see #7 for the real-Maya verification "
    "checklist state.\n\n## Install\n\npip install mcp-for-maya\n"
)


class FakeGh:
    """Serves canned release body / issue state; can raise on any call."""

    def __init__(self, body=BODY_OK, state="OPEN", exc=None):
        self.body = body
        self.state = state
        self.exc = exc
        self.calls = []

    def __call__(self, argv):
        self.calls.append(argv)
        if self.exc is not None:
            raise self.exc
        if "release" in argv:
            return self.body
        if "issue" in argv:
            return self.state
        return ""


def test_pass_when_appendix_present_and_issue_open():
    mod = _load()
    assert mod.check("v0.4.0", 7, FakeGh()) == 0


def test_appendix_may_sit_anywhere_in_body():
    mod = _load()
    body = "# v0.4.0\n\n## Known-unverified\n\n- item referencing #7\n"
    assert mod.check("v0.4.0", 7, FakeGh(body=body)) == 0


def test_missing_appendix_section_fails():
    mod = _load()
    body = "# v0.4.0\n\nAll good. See #7.\n"
    assert mod.check("v0.4.0", 7, FakeGh(body=body)) == 1


def test_empty_appendix_fails():
    mod = _load()
    body = "# v0.4.0\n\n## Disclosure appendix\n\n## Install\n\nref #7\n"
    assert mod.check("v0.4.0", 7, FakeGh(body=body)) == 1


def test_missing_issue_reference_fails():
    mod = _load()
    body = "# v0.4.0\n\n## Disclosure appendix\n\nsnapshot text\n"
    assert mod.check("v0.4.0", 7, FakeGh(body=body)) == 1


def test_issue_url_counts_as_reference():
    mod = _load()
    body = "## Disclosure appendix\n\ntracker: https://github.com/o/r/issues/7 remains open\n"
    assert mod.violations(body, 7) == []


def test_closed_tracker_discharges_obligation():
    mod = _load()
    bare = "# v0.4.0\n\nNothing to disclose.\n"
    assert mod.check("v0.4.0", 7, FakeGh(body=bare, state="CLOSED")) == 0


def test_gh_unavailable_is_fail_loud():
    mod = _load()
    rc = mod.check("v0.4.0", 7, FakeGh(exc=FileNotFoundError("gh")))
    assert rc == 2


def test_rate_limit_is_fail_loud():
    mod = _load()
    exc = subprocess.CalledProcessError(1, ["gh"], stderr="gh: HTTP 403: API rate limit exceeded")
    assert mod.check("v0.4.0", 7, FakeGh(exc=exc)) == 2


def test_other_gh_failure_is_fail_loud():
    mod = _load()
    exc = subprocess.CalledProcessError(1, ["gh"], stderr="HTTP 404: Not Found")
    assert mod.check("v0.4.0", 7, FakeGh(exc=exc)) == 2


def test_appendix_section_helper_boundaries():
    mod = _load()
    sec = mod.appendix_section(BODY_OK)
    assert sec is not None
    line, text = sec
    assert "Ship-time snapshot" in text
    assert "pip install" not in text  # next heading closes the section
    assert mod.appendix_section("no headings here") is None
