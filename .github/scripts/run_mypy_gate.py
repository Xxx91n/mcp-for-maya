#!/usr/bin/env python3
"""Run mypy and fail closed when the check's EXECUTION is not trustworthy.

The old mypy job piped mypy straight into ``mypy-baseline filter`` and only
looked at the exit code of that pipe. Issue #214 measured the holes: with an
empty baseline an EMPTY report and a GARBAGE report both returned success
(fix 0 / new 0 -> exit 0), and a previously clean module could be dropped
from the checked set without anything going red. With a NONempty baseline the
same faults only turned red by accident -- 167 stale entries stopped matching,
not because anything detected the fault.

This gate decides from three independent signals, and a fault on ANY of them
is red:

1. Exit code, classified rather than thresholded. 0 means "claims zero
   errors", 1 means "reports type errors", anything else is a checker or
   configuration fault. An exit code alone is never trusted: the exit code is
   only a claim about the report, and the report is verified next.
2. Report shape. A zero-error run must end in mypy's ``Success: no issues
   found in N source files`` line; an error run must be nonempty, contain at
   least one ``error:`` line, parse line by line as mypy output, and carry the
   ``Found ... (checked N source files)`` summary. Empty or garbage output on
   either branch is an execution fault, so an empty baseline can no longer
   wave it through.
3. Scope. ``src/`` is enumerated live (every ``*.py`` under it) and the
   ``checked N source files`` count must cover that enumeration. Excluding a
   previously clean module shrinks mypy's count below the enumeration and
   fails; a legitimately added module grows both sides together, so nothing
   is pinned to a stale file count.

Before mypy runs at all, two configuration guards fail closed: ``pyproject``
must still carry the strict trio (``strict``, ``warn_unused_ignores``,
``warn_unused_configs`` -- the last two are what force a silently broadened
ignore to surface), and ``mypy-baseline.txt`` must exist and be readable. A
missing baseline is a configuration fault; an EMPTY baseline is legal and is
exactly the state the report-shape checks protect. When the historic errors
are gone and the baseline retires, this guard is the one line to revisit.

Every verdict prints its evidence: mypy's exit code, the stderr, the report
line count, the summary line and the scope count. Faults are printed as
``::error`` and exit 1; a healthy run prints one summary line and exits 0.

Wiring: the mypy CI job calls this script, and ``check_ci_wiring.py`` requires
that call by exact command shape, so the job cannot go back to a bare mypy
invocation. This script itself is a registered gate (``run_mypy_gate`` in
``.github/gate-registry.yaml``), and its pytest pins prove the verdict logic
against injected fake mypy/filter runs.

Usage:
    python .github/scripts/run_mypy_gate.py [repo-root]

Scope honesty, stated so nobody reads more into this than it does:

* The strict-trio guard proves the settings are PRESENT, not that mypy read
  them: it parses the ``[tool.mypy]`` section text of pyproject and stops at
  the next table header. Within that table, an explicit strict-derived
  sub-flag is refused outright (a ``false`` would override the strict
  expansion behind the guard's back), global suppression flags
  (``ignore_errors``, ``disable_error_code``) are refused because strict
  does not re-enable them, a mypy ``mypy: error`` on stderr is a
  config fault even when the exit code looks healthy (mypy can announce a
  config-parsing failure and then continue on defaults), and ANY mypy
  overrides table is refused outright: the guard cannot honestly audit its
  contents (``ignore_errors`` and friends) without re-implementing mypy's
  config semantics, so adding one requires editing this registered, pinned
  gate. Four review rounds found one weakening key after another, so the
  guard ends the whack-a-mole with a whitelist: the top-level table may hold
  only the required trio plus ``python_version``. Any other key -- present
  or future, weakening or not -- is refused, and allowing it requires
  editing this gate.
* A newly added broad ignore that mypy actually USES does not fail anything;
  ``warn_unused_ignores`` only catches ignores that suppress nothing. Whether
  a specific ignore is too wide stays a review decision.
* The scope comparison uses mypy's own ``checked`` count. A fault that fakes
  the report text wholesale (and gets the count right) is not detectable
  here; the guard against that is CI running the pinned tests, not this
  script.
* ``checked`` greater than the enumeration is allowed, because mypy may
  follow imports the enumeration does not know about; only a shortfall is
  treated as lost coverage. Consequence worth naming: the comparison counts
  FILES, not identities, so a fault that excludes one module while another
  file inflates mypy's count could balance out. Related assumption:
  ``src/`` holds no ``.pyi`` stubs today; mypy discovers stubs alongside
  ``.py`` and dedups by directory/stem, so if stubs are ever added, the
  enumeration rule must be aligned with mypy's discovery before the count
  comparison can be trusted. An identity-based guarantee would need the
  checked-file set, which mypy's summary does not expose.
* The baseline filter subprocess is invoked with a fixed argument list; the
  report text it reads is mypy's own output on stdin, never a shell string.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]

# The directory mypy is pointed at. One constant, so narrowing the scope
# requires editing this gate -- which is registered, pinned and reviewed --
# instead of a quiet edit to a workflow line. The command argument and the
# enumeration root are derived from the same string, so they cannot drift.
SCOPE_DIR = "src"
SCOPE_ARGS = (SCOPE_DIR + "/",)

# The settings whose loss would weaken the check itself. All three are
# present today; a negative fixture removes each one and must go red.
REQUIRED_MYPY_SETTINGS = ("strict", "warn_unused_ignores", "warn_unused_configs")

# The flags mypy's ``strict = true`` expands to (mypy 2.3.1). If any of them
# appears in the [tool.mypy] table the gate refuses the run regardless of the
# assigned value: a ``false`` silently overrides the strict expansion, and a
# ``true`` is redundant. Expressing strictness via these sub-flags is a gate
# edit, not a config tweak. SYNCHRONIZATION OBLIGATION: if mypy's strict
# expansion changes, this set must follow in the same commit -- a newly added
# sub-flag this set does not know is a review item, not something the guard
# can prove.
STRICT_DERIVED_FLAGS = frozenset(
    {
        "warn_unused_configs",
        "disallow_any_generics",
        "disallow_subclassing_any",
        "disallow_untyped_calls",
        "disallow_untyped_defs",
        "disallow_incomplete_defs",
        "check_untyped_defs",
        "disallow_untyped_decorators",
        "warn_redundant_casts",
        "warn_unused_ignores",
        "warn_return_any",
        "no_implicit_reexport",
        "strict_equality",
        "extra_checks",
    }
)

# Global error-suppression switches in the top-level table. Neither is
# re-enabled by strict = true, so their presence silences exactly the errors
# this gate exists to surface, regardless of the assigned value. The
# per-module forms of the same switches live in overrides tables, which are
# refused wholesale below.
REFUSED_SUPPRESSION_FLAGS = frozenset({"ignore_errors", "disable_error_code"})

# The WHITELIST that ends the whack-a-mole: four review rounds found one
# weakening key after another (strict sub-flags, ignore_errors,
# disable_error_code, semantic_analysis_only). The top-level [tool.mypy]
# table may hold ONLY the required trio plus python_version; anything else --
# known weakening flags, stage-skipping flags, keys mypy adds in the future
# -- is refused, and adding a legitimate new key requires editing this
# registered, pinned gate. The specialized refusals above stay so their
# error messages name the exact threat; this list is the backstop.
ALLOWED_MYPY_KEYS = frozenset({"python_version", *REQUIRED_MYPY_SETTINGS})

BASELINE_FILENAME = "mypy-baseline.txt"
REPORT_FILENAME = "mypy-report.txt"

# mypy's two verdict lines. The captured group is the checked-source count
# that the scope comparison reads; it is compared live, never stored.
_SUCCESS_LINE = re.compile(r"^Success: no issues found in (\d+) source files?$")
_SUMMARY_LINE = re.compile(r"^Found \d+ errors? in \d+ files? \(checked (\d+) source files?\)$")
# One mypy diagnostic: ``path:line(:col)?: (error|note): text``. Path may be
# POSIX or Windows shaped; everything up to the message is structural. The
# message may begin with spaces -- mypy's overload ``note:`` lines indent the
# signatures -- so no \S is required after the colon. Assumptions worth
# naming: this grammar covers mypy's DEFAULT formatter only (--pretty or
# show_error_context add lines that will be judged malformed, i.e. red), and
# a checkout path containing a space would not match \S+ and false-red. CI
# checkouts have no spaces today; if that changes, this regex and its pins
# change in the same commit.
_DIAGNOSTIC_LINE = re.compile(r"^\S+:\d+(?::\d+)?: (?:error|note): .*$")
# An error diagnostic names ``error`` as its severity token and carries a
# NONEMPTY message on a PYTHON FILE path: mypy-baseline 0.7.4 refuses to
# match an empty message and only parses diagnostics for .py/.pyi paths, so
# a line outside that shape would flow through the filter unbaselined while
# this gate counted it as an error. The path segment excludes colons: a
# Windows ABSOLUTE path (drive-letter colon) is judged malformed, i.e. red,
# which matches CI's relative-path checkout.
_ERROR_DIAGNOSTIC_LINE = re.compile(r"^[^\s:]+\.pyi?:\d+(?::\d+)?: error: \S.*$")


class GateError(Exception):
    """A gate finding. Carries the tag used in the ::error line."""


def _table_key(header: str) -> str:
    """Drop whitespace and quotes so spaced or quoted TOML keys match.

    TOML allows spaces around the dots of a dotted key and quoted key
    segments: ``[[tool . mypy . overrides]]`` is the same table as
    ``[[tool.mypy.overrides]]``, and mypy's real TOML parser will apply it.
    Text matching must normalize the header before comparing prefixes.
    Only apply the result to headers whose segments are ALL bare: a quoted
    segment is a DIFFERENT key from a bare one (``["tool.mypy"]`` is one
    top-level key, not the [tool.mypy] table), so quoted headers must be
    refused, not normalized.
    """
    return re.sub(r"[\s'\"]", "", header)


def _mask_multiline_strings(text: str) -> str:
    """Blank out non-structural text: comments and multi-line strings.

    Both directions matter for honesty:

    * A ``#`` starts a comment only OUTSIDE a string, so ``# \"\"\"`` must
      not open a multi-line string (a fenced ``ignore_errors = true`` behind
      two comment lines would otherwise be masked away from the whitelist).
    * A multi-line string body is not configuration, so ``strict = true``
      inside a \"\"\" description must not satisfy the guard while the real
      table disables it.

    Character-level masking keeps line structure intact. Out of scope for
    this text parser: escaped delimiters inside strings; anything they
    confuse fails closed via mypy's own stderr check or an audit mismatch.
    """
    out: list[str] = []
    triple: str | None = None
    line_quote: str | None = None
    in_comment = False
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if in_comment:
            if ch == "\n":
                in_comment = False
                out.append(ch)
            else:
                out.append(" ")
            i += 1
            continue
        if ch == "\n":
            line_quote = None
            out.append(ch)
            i += 1
            continue
        if triple:
            if text.startswith(triple, i):
                out.append(triple)
                triple = None
                i += 3
            else:
                out.append("\n" if ch == "\n" else " ")
                i += 1
            continue
        if text.startswith('"""', i) or text.startswith("'''", i):
            triple = text[i : i + 3]
            out.append(triple)
            i += 3
            continue
        if ch == "#":
            in_comment = True
            out.append(" ")
            i += 1
            continue
        if line_quote:
            if ch == line_quote:
                line_quote = None
            out.append(ch)
            i += 1
            continue
        if ch in ('"', "'"):
            line_quote = ch
            out.append(ch)
            i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _unquote(value: str) -> str:
    """Strip ONE matching pair of quotes; inner quotes are content.

    ``strip("'\\\"")`` on ``'"true"'`` would read the invalid value
    ``true`` as if it were a boolean; mypy rejects that value and skips the
    setting, so the guard must see the quotes and fail on it.
    """
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def parse_mypy_section(pyproject_text: str) -> dict[str, str]:
    """Read the first ``[tool.mypy]`` table as flat ``key = value`` strings.

    Deliberately a text parse of the section between this header and the next
    ``[`` header: pyproject has no stdlib parser on the minimum Python this
    repo supports, and the guard only needs to know whether three boolean
    keys are present with a truthy value. Quoted values and trailing comments
    are stripped the same way the wiring checker strips YAML comments.
    """
    section: dict[str, str] = {}
    inside = False
    for raw_line in _mask_multiline_strings(pyproject_text).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("["):
            if inside:
                break  # the next table ends the [tool.mypy] section
            # A quoted segment is a different key from a bare one, so a
            # header carrying quotes is never treated as the audited table.
            inside = '"' not in line and _table_key(line) == "[tool.mypy]"
            continue
        if not inside or "=" not in line:
            continue
        key, _, value = line.partition("=")
        # TOML quoted keys are equivalent to bare keys, and mypy treats them
        # as such: normalize the key (ONE matching pair) so "ignore_errors"
        # cannot masquerade past the suppression checks.
        key_name = _unquote(key.strip())
        section[key_name] = _unquote(_strip_comment(value).strip())
    return section


def check_no_overrides_table(pyproject_text: str) -> None:
    """Red when any mypy overrides table exists.

    This gate audits the top-level ``[tool.mypy]`` table as text; an
    ``[[tool.mypy.overrides]]`` entry can silence errors per module
    (``ignore_errors = true`` and friends) and the guard cannot honestly
    audit its contents without re-implementing mypy's config semantics. So
    overrides are refused outright: repo-wide they are unnecessary today,
    and if one is ever genuinely needed, that requires editing this
    registered, pinned gate -- the same rule the scope constant follows.
    """
    for raw_line in _mask_multiline_strings(pyproject_text).splitlines():
        stripped = raw_line.strip()
        if not stripped.startswith("["):
            continue
        key = _table_key(stripped)
        if '"' in stripped and "tool" in key and "mypy" in key:
            # A quoted key segment is a different key from a bare one, so
            # this text parser cannot tell what mypy will read; refuse
            # rather than normalize (covers ["tool.mypy"] posing as a table).
            raise GateError(
                "config_fault -- a quoted TOML header cannot be audited by "
                f"this text parser ({stripped}); mypy may read it as a table "
                "or as a single key. Use bare dotted keys."
            )
        if key.startswith("[[tool.mypy") or key.startswith("[tool.mypy."):
            raise GateError(
                "config_fault -- a mypy overrides table was found "
                f"({stripped}); this gate does not audit per-module overrides, "
                "which can silence errors (ignore_errors and friends). Adding "
                "one requires editing this gate."
            )


def check_no_baseline_config(pyproject_text: str) -> None:
    """Red when the baseline filter's own config section exists.

    ``mypy-baseline filter`` reads ``[tool.mypy-baseline]`` (or
    ``[tool.mypy_baseline]``) from pyproject by default, and an ``ignore``
    list there makes it skip matching errors -- a silent pass that none of
    the report checks can see. The filter is unconfigured in this repo; if a
    configuration is ever genuinely needed, that requires editing this
    registered, pinned gate.
    """
    for raw_line in _mask_multiline_strings(pyproject_text).splitlines():
        stripped = raw_line.strip()
        key = _table_key(stripped)
        if (
            stripped.startswith("[")
            and key.startswith("[tool.")
            and ("mypy-baseline" in key or "mypy_baseline" in key)
        ):
            raise GateError(
                "config_fault -- a mypy-baseline config table was found "
                f"({stripped}); its ignore list makes the baseline filter "
                "skip matching errors. Adding one requires editing this gate."
            )


def _strip_comment(value: str) -> str:
    in_single = False
    in_double = False
    for i, ch in enumerate(value):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return value[:i]
    return value


def check_strict_trio(pyproject_path: Path) -> None:
    """Red when a strict-trio setting is missing or not truthy."""
    try:
        text = pyproject_path.read_text(encoding="utf-8")
    except OSError as e:
        raise GateError(f"config_fault -- cannot read pyproject.toml: {e}") from e
    check_no_overrides_table(text)
    check_no_baseline_config(text)
    section = parse_mypy_section(text)
    if not section and "[tool.mypy]" not in text:
        raise GateError("config_fault -- pyproject.toml has no [tool.mypy] section")
    for key in REQUIRED_MYPY_SETTINGS:
        value = section.get(key, "").lower()
        if value not in ("true", "yes", "1"):
            raise GateError(
                f"config_fault -- [tool.mypy] {key} is missing or not enabled; "
                "weakening the strict configuration must not look green"
            )
    overridden = sorted(
        key for key in section if key in STRICT_DERIVED_FLAGS and key not in REQUIRED_MYPY_SETTINGS
    )
    if overridden:
        raise GateError(
            "config_fault -- [tool.mypy] explicitly sets strict sub-flag(s) "
            f"{', '.join(overridden)}; a false value would override the strict "
            "expansion while the guard still sees strict = true. Keep the "
            "strict intent on the single strict flag."
        )
    suppressing = sorted(key for key in section if key in REFUSED_SUPPRESSION_FLAGS)
    if suppressing:
        raise GateError(
            "config_fault -- [tool.mypy] sets global error-suppression "
            f"flag(s) {', '.join(suppressing)}; strict = true does not "
            "re-enable them, so they can silence exactly the errors this "
            "gate surfaces. Remove them."
        )
    outside_whitelist = sorted(
        key
        for key in section
        if key not in ALLOWED_MYPY_KEYS and key not in REFUSED_SUPPRESSION_FLAGS
    )
    if outside_whitelist:
        raise GateError(
            "config_fault -- [tool.mypy] holds key(s) outside this gate's "
            f"allowlist ({', '.join(outside_whitelist)}); mypy accepts "
            "options that skip or weaken the type check here (measured: "
            "semantic_analysis_only), and a blacklist cannot keep up. A new "
            "key requires editing this gate."
        )


def check_baseline(baseline_path: Path) -> None:
    """Red when the baseline file is gone; an empty file is legal."""
    if not baseline_path.is_file():
        raise GateError(
            "config_fault -- mypy-baseline.txt is missing; the filter would "
            "silently pass everything. Retiring the baseline means editing "
            "this gate, not deleting the file."
        )
    try:
        baseline_path.read_text(encoding="utf-8")
    except OSError as e:
        raise GateError(f"config_fault -- cannot read mypy-baseline.txt: {e}") from e


def enumerate_scope(root: Path) -> int:
    """Count the live ``*.py`` files under src/. Zero files fails closed."""
    scope_dir = root / SCOPE_DIR
    if not scope_dir.is_dir():
        raise GateError(f"scope_fault -- {SCOPE_DIR}/ does not exist; nothing to check")
    count = len(list(scope_dir.rglob("*.py")))
    if count == 0:
        raise GateError(f"scope_fault -- no .py files under {SCOPE_DIR}/; scope read failed")
    return count


def run_mypy(root: Path) -> tuple[int, str, str]:
    """Run mypy over the scope; return (exit code, stdout, stderr).

    The config file is passed explicitly so mypy reads the SAME file the
    strict-trio guard checked: mypy's own lookup order prefers mypy.ini and
    .mypy.ini over pyproject.toml, so a future ini file could otherwise
    silently change the rules while the guard kept auditing pyproject.
    """
    command = [sys.executable, "-m", "mypy", "--config-file", "pyproject.toml", *SCOPE_ARGS]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as e:
        raise GateError(f"checker_fault -- could not start mypy ({command}): {e}") from e
    return completed.returncode, completed.stdout, completed.stderr


def run_baseline_filter(root: Path, report_text: str) -> str:
    """Feed the report to mypy-baseline filter; return its stdout.

    Anything other than exit 0 is red: the filter exits nonzero both for new
    errors and for the "resolved violations" notice, and this gate must not
    second-guess it into a pass.
    """
    command = [sys.executable, "-m", "mypy_baseline", "filter"]
    try:
        completed = subprocess.run(
            command,
            cwd=root,
            input=report_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as e:
        raise GateError(f"filter_fault -- could not start mypy-baseline filter: {e}") from e
    if completed.returncode != 0:
        detail = (completed.stdout + completed.stderr).strip()
        raise GateError(
            f"filter_fault -- mypy-baseline filter exited {completed.returncode}; "
            "the report carries errors the baseline does not cover "
            f"(or the tool refused the input). Filter output:\n{detail}"
        )
    return completed.stdout


def verify_report(rc: int, report_text: str, stderr: str, scope_count: int) -> tuple[str, int]:
    """Judge the mypy report against the exit code's claim.

    Returns ``(summary line, checked count)``; raises ``GateError`` when the
    output does not support the claim. This is where an empty or garbage
    report dies even though the exit code looks survivable. ``stderr`` rides
    along so every fault message carries the checker's own evidence.
    """
    lines = [line for line in report_text.splitlines() if line.strip()]
    summary_matches = [
        _SUMMARY_LINE.match(line) for line in lines if _SUMMARY_LINE.match(line) is not None
    ]
    stderr_note = f"mypy stderr:\n{stderr.strip()}" if stderr.strip() else "mypy stderr: (empty)"

    if rc not in (0, 1):
        raise GateError(
            f"checker_fault -- mypy exited {rc}; this is not a type-error "
            "verdict, it is a crash or configuration failure. "
            f"stdout:\n{report_text.strip() or '(empty)'}\n{stderr_note}"
        )
    if stderr.strip():
        # mypy's stderr is EMPTY on every healthy run (this script invokes
        # it directly, so there is no wrapper noise). Any stderr at all
        # means trouble this text parser cannot fully anticipate: mypy can
        # log a configuration error -- with or without the ``mypy: error``
        # prefix -- and then CONTINUE on its default configuration, exiting
        # 0/1 as if nothing happened. Such a run is a configuration fault,
        # not a verdict: the audited config was never applied.
        raise GateError(
            "config_fault -- mypy wrote to stderr; a healthy run never "
            "does, and a configuration error may have made mypy skip the "
            f"audited config entirely. stderr:\n{stderr.strip()}"
        )

    if rc == 0:
        if not lines:
            raise GateError(
                "execution_fault -- mypy exited 0 but the report is EMPTY; a "
                f"zero-error run must name the files it checked. {stderr_note}"
            )
        success = _SUCCESS_LINE.match(lines[-1])
        if success is None:
            raise GateError(
                "execution_fault -- mypy exited 0 but the report does not end "
                "with a 'Success: no issues found in N source files' line; "
                f"last line: {lines[-1]!r}. {stderr_note}"
            )
        # Same standard as the error branch: the body before the summary may
        # carry note lines, but a garbage line or an error line under a
        # success verdict is not evidence of a clean run.
        stray = [
            line
            for line in lines[:-1]
            if _DIAGNOSTIC_LINE.match(line) is None or _ERROR_DIAGNOSTIC_LINE.match(line)
        ]
        if stray:
            raise GateError(
                "execution_fault -- mypy exited 0 but the report body before "
                "the success summary is not note diagnostics: "
                + "; ".join(repr(line) for line in stray[:3])
                + f". {stderr_note}"
            )
        checked = int(success.group(1))
        verdict = lines[-1]
    if rc == 1:
        if not lines:
            raise GateError(
                "execution_fault -- mypy exited 1 (type errors claimed) but "
                "the report is EMPTY; nothing can be reviewed or baselined. "
                f"{stderr_note}"
            )
        if len(summary_matches) != 1 or summary_matches[0].group(0) != lines[-1]:
            raise GateError(
                "execution_fault -- mypy exited 1 but the 'Found ... (checked N "
                "source files)' summary must appear exactly once, as the last "
                "non-empty line; found "
                f"{len(summary_matches)} summary lines. {stderr_note}"
            )
        # An error line must be a well-formed diagnostic with ``error`` as
        # its severity token; a note line whose MESSAGE contains ": error: "
        # does not make this an error report.
        error_lines = [line for line in lines if _ERROR_DIAGNOSTIC_LINE.match(line)]
        if not error_lines:
            raise GateError(
                "execution_fault -- mypy exited 1 but the report carries no "
                f"'error:' line; the output is not a mypy error report. {stderr_note}"
            )
        malformed = [
            line
            for line in lines
            if _DIAGNOSTIC_LINE.match(line) is None and _SUMMARY_LINE.match(line) is None
        ]
        if malformed:
            raise GateError(
                "execution_fault -- report lines are not mypy diagnostics: "
                + "; ".join(repr(line) for line in malformed[:3])
                + f". {stderr_note}"
            )
        # Cross-check the summary's own count against the error lines it
        # summarizes; a summary that disagrees with the body is not evidence.
        found_match = re.search(r"^Found (\d+) errors?", summary_matches[-1].group(0))
        if found_match and int(found_match.group(1)) != len(error_lines):
            raise GateError(
                f"execution_fault -- the summary claims {found_match.group(1)} "
                f"errors but the report carries {len(error_lines)} 'error:' "
                f"lines; the counts disagree. {stderr_note}"
            )
        checked = int(summary_matches[-1].group(1))
        verdict = summary_matches[-1].group(0)

    if checked < scope_count:
        raise GateError(
            f"scope_fault -- mypy checked {checked} source files but src/ "
            f"holds {scope_count}; a module dropped out of the checked set. "
            "Narrowing the checked scope must not look green."
        )
    return verdict, checked


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("root", nargs="?", default=str(REPO), help="repository root")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    try:
        # Configuration guards run before mypy: a weakened config must fail
        # even when mypy itself would still exit 0.
        check_strict_trio(root / "pyproject.toml")
        check_baseline(root / BASELINE_FILENAME)
        scope_count = enumerate_scope(root)

        rc, stdout, stderr = run_mypy(root)
        try:
            (root / REPORT_FILENAME).write_text(stdout, encoding="utf-8")
        except OSError as e:
            raise GateError(f"execution_fault -- cannot write {REPORT_FILENAME}: {e}") from e

        verdict, checked = verify_report(rc, stdout, stderr, scope_count)
        # Evidence discipline, on green too: the exit code, the report size
        # and anything the checker said on stderr stay visible, so a future
        # reader does not have to trust the word OK.
        if stderr.strip():
            print(f"mypy stderr: {stderr.strip()}")

        # The filter runs on BOTH branches, as the old pipeline did: besides
        # catching new errors, its nonzero "resolved violations" exit is what
        # forces a baseline sync once the historic errors are actually fixed.
        # Skipping it on a clean run would silently retire that signal.
        filter_output = run_baseline_filter(root, stdout)
        sys.stdout.write(filter_output)
        print(
            f"mypy gate OK: mypy exited {rc}; report: {len(stdout.splitlines())} "
            f"lines; {verdict} (scope: {scope_count} .py files); "
            "new errors after baseline: 0"
        )
        return 0
    except GateError as fault:
        # The evidence block is the contract: every red names the tag, the
        # exit code when one exists, and the raw output that justifies it.
        # A GitHub annotation must be a single line, so the annotation
        # carries the first line and the full evidence follows unannotated.
        text = str(fault)
        head = text.splitlines()[0]
        print(f"::error file=.github/scripts/run_mypy_gate.py::{head}", file=sys.stderr)
        if len(text.splitlines()) > 1:
            sys.stderr.write(text + "\n")
        print(f"mypy gate: RED ({head.split(' -- ')[0]})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
