"""Pins for .github/scripts/run_mypy_gate.py.

The gate's whole job is one sentence: a mypy run whose EXIT CODE, REPORT
SHAPE or CHECKED SCOPE cannot be trusted must be red, and a healthy run
(including the current not-yet-zero baseline) must stay green. The red cases
below inject the exact faults #214 measured: an empty or garbage report on an
EMPTY baseline (which the old pipe happily passed), a crashed checker, a
module that dropped out of the checked set, a weakened strict configuration
and a missing baseline file.

Fake mypy and fake filter verdicts are injected as module functions, so the
verdict matrix runs in milliseconds against disposable trees. Two tests touch
the real seam: the CLI red control (no mypy needed -- configuration faults
fire before mypy starts) and the CLI green control that runs REAL mypy over
this repository, which is the same command CI runs. Every red asserts the
fault tag, not just a nonzero exit.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".github" / "scripts" / "run_mypy_gate.py"


def _load():
    spec = importlib.util.spec_from_file_location("run_mypy_gate", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


# --------------------------------------------------------------------------
# Disposable repo tree
# --------------------------------------------------------------------------


PYPROJECT = """[project]
name = "demo"

[tool.mypy]
python_version = "3.10"
strict = true
warn_unused_ignores = true
warn_unused_configs = true
"""


def _make_repo(
    tmp_path: Path,
    *,
    pyproject: str = PYPROJECT,
    baseline: str = "",
    src_files: tuple[str, ...] = ("pkg/__init__.py", "pkg/app.py"),
) -> Path:
    root = tmp_path / "repo"
    (root / "src" / "pkg").mkdir(parents=True)
    (root / "pyproject.toml").write_text(pyproject, encoding="utf-8")
    if baseline is not None:
        (root / "mypy-baseline.txt").write_text(baseline, encoding="utf-8")
    for rel in src_files:
        (root / "src" / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / "src" / rel).write_text("", encoding="utf-8")
    return root


def _success_report(count: int) -> str:
    return f"Success: no issues found in {count} source files\n"


def _error_report(count: int, *, with_summary: bool = True) -> str:
    lines = [
        "src/pkg/app.py:1: error: Incompatible types  [assignment]",
        "src/pkg/app.py:2: error: Missing type annotation  [no-untyped-def]",
        "src/pkg/app.py:2: note: a helpful note",
    ]
    if with_summary:
        lines.append(f"Found {len(lines) - 1} errors in 1 file (checked {count} source files)")
    return "\n".join(lines) + "\n"


def _run_main(mod, monkeypatch, root: Path, *, mypy=None, filter_output=None):
    """Invoke main() with injected mypy/filter results; return (rc, cap)."""
    if mypy is not None:
        monkeypatch.setattr(mod, "run_mypy", lambda root: mypy)
    if filter_output is not None:
        monkeypatch.setattr(mod, "run_baseline_filter", lambda root, report: filter_output)
    monkeypatch.setattr(sys, "argv", ["run_mypy_gate.py", str(root)])
    return mod.main()


# --------------------------------------------------------------------------
# Green controls
# --------------------------------------------------------------------------


def test_a_clean_run_is_green(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path)  # empty baseline: the exact state #214 broke
    rc = _run_main(
        mod,
        monkeypatch,
        root,
        mypy=(0, _success_report(2), ""),
        filter_output="",
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "mypy exited 0" in out
    assert "scope: 2 .py files" in out


def test_baseline_matched_errors_stay_green(tmp_path, monkeypatch):
    mod = _load()
    root = _make_repo(tmp_path, baseline="stale entries\n")
    rc = _run_main(
        mod,
        monkeypatch,
        root,
        mypy=(1, _error_report(2), ""),
        filter_output="",
    )
    assert rc == 0


def test_a_new_source_module_is_included_automatically(tmp_path, monkeypatch):
    mod = _load()
    files = ("pkg/__init__.py", "pkg/app.py", "pkg/brand_new.py")
    root = _make_repo(tmp_path, baseline="stale\n", src_files=files)
    # mypy reports three checked files with NO gate edit anywhere.
    rc = _run_main(
        mod,
        monkeypatch,
        root,
        mypy=(1, _error_report(3), ""),
        filter_output="",
    )
    assert rc == 0


# --------------------------------------------------------------------------
# Report-shape faults: empty and garbage output can no longer look healthy
# --------------------------------------------------------------------------


def test_empty_report_with_zero_exit_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path)  # EMPTY baseline: the hole from #214
    rc = _run_main(mod, monkeypatch, root, mypy=(0, "", ""))
    assert rc == 1
    assert "execution_fault" in capsys.readouterr().err


def test_empty_report_with_error_exit_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path)  # EMPTY baseline
    rc = _run_main(mod, monkeypatch, root, mypy=(1, "", ""))
    assert rc == 1
    assert "execution_fault" in capsys.readouterr().err


def test_garbage_report_with_zero_exit_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path)  # EMPTY baseline
    rc = _run_main(mod, monkeypatch, root, mypy=(0, "hello world\nnot mypy\n", ""))
    assert rc == 1
    assert "execution_fault" in capsys.readouterr().err


def test_garbage_report_with_error_exit_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path)  # EMPTY baseline
    rc = _run_main(mod, monkeypatch, root, mypy=(1, "hello world\nnot mypy\n", ""))
    assert rc == 1
    assert "execution_fault" in capsys.readouterr().err


def test_error_lines_without_a_summary_are_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, baseline="stale\n")
    rc = _run_main(
        mod,
        monkeypatch,
        root,
        mypy=(1, _error_report(2, with_summary=False), ""),
    )
    assert rc == 1
    assert "execution_fault" in capsys.readouterr().err


def test_garbage_body_with_a_valid_success_summary_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path)  # EMPTY baseline
    report = "not mypy\nSuccess: no issues found in 2 source files\n"
    rc = _run_main(mod, monkeypatch, root, mypy=(0, report, ""))
    assert rc == 1
    assert "execution_fault" in capsys.readouterr().err


def test_an_error_line_under_a_success_verdict_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path)  # EMPTY baseline
    report = (
        "src/pkg/app.py:1: error: Incompatible types  [assignment]\n"
        "Success: no issues found in 2 source files\n"
    )
    rc = _run_main(mod, monkeypatch, root, mypy=(0, report, ""))
    assert rc == 1
    assert "execution_fault" in capsys.readouterr().err


def test_a_summary_disagreeing_with_its_error_lines_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, baseline="stale\n")
    report = _error_report(2).replace("Found 2 errors", "Found 3 errors")
    rc = _run_main(mod, monkeypatch, root, mypy=(1, report, ""), filter_output="")
    assert rc == 1
    assert "counts disagree" in capsys.readouterr().err


def test_an_error_substring_inside_a_note_line_is_not_an_error_report(
    tmp_path, monkeypatch, capsys
):
    mod = _load()
    root = _make_repo(tmp_path, baseline="stale\n")
    # Even with the summary count MATCHING the decoy line, a note line whose
    # message contains ": error: " is not an error diagnostic.
    report = (
        "src/pkg/app.py:2: note: expected signature : error: decoy\n"
        "Found 1 errors in 1 file (checked 2 source files)\n"
    )
    rc = _run_main(mod, monkeypatch, root, mypy=(1, report, ""), filter_output="")
    assert rc == 1
    assert "execution_fault" in capsys.readouterr().err


def test_a_crashed_checker_is_red_with_evidence(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, baseline="stale\n")
    rc = _run_main(mod, monkeypatch, root, mypy=(2, "", "mypy: internal error: boom"))
    assert rc == 1
    err = capsys.readouterr().err
    assert "checker_fault" in err
    assert "internal error: boom" in err


def test_an_exit_code_above_one_is_not_the_only_fault(tmp_path, monkeypatch):
    # The rc==0 and rc==1 fault cases above already prove the gate does not
    # rely on rc>1; this pin keeps the contract named in one place.
    mod = _load()
    root = _make_repo(tmp_path)
    assert _run_main(mod, monkeypatch, root, mypy=(0, "garbage", "")) == 1
    assert _run_main(mod, monkeypatch, root, mypy=(1, "", "")) == 1


# --------------------------------------------------------------------------
# Scope protection
# --------------------------------------------------------------------------


def test_an_excluded_module_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    files = ("pkg/__init__.py", "pkg/app.py", "pkg/dropped.py")
    root = _make_repo(tmp_path, baseline="stale\n", src_files=files)
    # mypy only claims two checked files although src/ holds three.
    rc = _run_main(
        mod,
        monkeypatch,
        root,
        mypy=(1, _error_report(2), ""),
        filter_output="",
    )
    assert rc == 1
    assert "scope_fault" in capsys.readouterr().err


def test_an_excluded_module_is_red_on_a_clean_run_too(tmp_path, monkeypatch, capsys):
    mod = _load()
    files = ("pkg/__init__.py", "pkg/app.py", "pkg/dropped.py")
    root = _make_repo(tmp_path, src_files=files)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "scope_fault" in capsys.readouterr().err


def test_an_empty_scope_fails_closed(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, src_files=())
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(0), ""))
    assert rc == 1
    assert "scope_fault" in capsys.readouterr().err


# --------------------------------------------------------------------------
# Configuration guards
# --------------------------------------------------------------------------


def _without_setting(pyproject_key: str) -> str:
    lines = [line for line in PYPROJECT.splitlines() if not line.startswith(pyproject_key)]
    return "\n".join(lines) + "\n"


def test_removing_strict_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, pyproject=_without_setting("strict"))
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_disabling_strict_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, pyproject=PYPROJECT.replace("strict = true", "strict = false"))
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_removing_warn_unused_ignores_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, pyproject=_without_setting("warn_unused_ignores"))
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_removing_warn_unused_configs_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, pyproject=_without_setting("warn_unused_configs"))
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_missing_baseline_file_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, baseline=None)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_config_guards_fire_before_mypy_runs(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, pyproject=_without_setting("strict"))

    def _explode(root):
        raise AssertionError("mypy must not run when the config is already red")

    monkeypatch.setattr(mod, "run_mypy", _explode)
    rc = _run_main(mod, monkeypatch, root)
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_strict_subflag_override_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    # strict = true stays intact, but the same table explicitly disables a
    # flag strict expands to: mypy would honor the explicit false while the
    # guard still sees strict = true.
    relaxed = PYPROJECT + "disallow_untyped_defs = false\n"
    root = _make_repo(tmp_path, pyproject=relaxed)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_redundant_true_strict_subflag_is_red_too(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, pyproject=PYPROJECT + "check_untyped_defs = true\n")
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_mypy_config_error_on_stderr_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path)  # EMPTY baseline
    # mypy writes a config-parsing error to stderr and then CONTINUES with
    # its default configuration, exiting 0 with a legal success summary.
    stderr = "mypy: error: bad value for 'module' in overrides: 123"
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), stderr))
    assert rc == 1
    err = capsys.readouterr().err
    assert "config_fault" in err
    assert "bad value for 'module'" in err


def test_an_overrides_table_is_refused(tmp_path, monkeypatch, capsys):
    mod = _load()
    # The exact shape CodeRabbit round-3 described: strict intact, but an
    # overrides table silences errors for one module.
    silenced = PYPROJECT + "\n[[tool.mypy.overrides]]\nmodule = 'pkg.app'\nignore_errors = true\n"
    root = _make_repo(tmp_path, pyproject=silenced)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_global_disable_error_code_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    # strict = true does not re-enable globally suppressed error codes.
    suppressed = PYPROJECT + "disable_error_code = ['assignment']\n"
    root = _make_repo(tmp_path, pyproject=suppressed)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_global_ignore_errors_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, pyproject=PYPROJECT + "ignore_errors = true\n")
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_quoted_suppression_key_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    # A TOML quoted key is equivalent to a bare key, and mypy reads it as
    # such; the guard must normalize before matching.
    quoted = PYPROJECT + '"ignore_errors" = true\n'
    root = _make_repo(tmp_path, pyproject=quoted)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_quoted_strict_subflag_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    quoted = PYPROJECT + '"disallow_untyped_defs" = false\n'
    root = _make_repo(tmp_path, pyproject=quoted)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_an_error_line_with_an_empty_message_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path)  # EMPTY baseline
    # mypy-baseline 0.7.4 refuses to match an empty error message, so this
    # line would flow through the filter unbaselined; the gate must not
    # count it as an error report either.
    report = "src/pkg/app.py:1: error: \nFound 1 error in 1 file (checked 2 source files)\n"
    rc = _run_main(mod, monkeypatch, root, mypy=(1, report, ""))
    assert rc == 1
    assert "execution_fault" in capsys.readouterr().err


def test_semantic_analysis_only_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    # mypy 2.3.1 accepts this flag and skips the type-check phase entirely,
    # still printing a legal success summary with a full checked count.
    skipped = PYPROJECT + "semantic_analysis_only = true\n"
    root = _make_repo(tmp_path, pyproject=skipped)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_an_unknown_tool_mypy_key_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    # The allowlist backstop: any key the gate does not explicitly allow is
    # refused, so future weakening flags cannot slip through a blacklist.
    root = _make_repo(tmp_path, pyproject=PYPROJECT + "some_future_flag = true\n")
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_baseline_filter_config_table_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    # mypy-baseline filter reads [tool.mypy-baseline] from pyproject and its
    # ignore list makes the filter skip matching errors.
    filtered = PYPROJECT + '\n[tool.mypy-baseline]\nignore = [".*"]\n'
    root = _make_repo(tmp_path, pyproject=filtered)
    rc = _run_main(mod, monkeypatch, root, mypy=(1, _error_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_the_underscore_baseline_config_table_is_red_too(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, pyproject=PYPROJECT + '\n[tool.mypy_baseline]\nignore = [".*"]\n')
    rc = _run_main(mod, monkeypatch, root, mypy=(1, _error_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_spaced_overrides_header_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    # TOML allows spaces around the dots; mypy's real parser applies the
    # table, so the text guard must normalize before matching.
    spaced = PYPROJECT + "\n[[tool . mypy . overrides]]\nmodule = 'pkg.app'\nignore_errors = true\n"
    root = _make_repo(tmp_path, pyproject=spaced)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_spaced_baseline_config_header_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    spaced = PYPROJECT + '\n[tool . mypy-baseline]\nignore = [".*"]\n'
    root = _make_repo(tmp_path, pyproject=spaced)
    rc = _run_main(mod, monkeypatch, root, mypy=(1, _error_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_quoted_tool_segment_in_an_overrides_header_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    quoted = PYPROJECT + '\n[tool."mypy".overrides]\nmodule = "pkg.app"\nignore_errors = true\n'
    root = _make_repo(tmp_path, pyproject=quoted)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_spaced_tool_mypy_header_still_parses(tmp_path, monkeypatch):
    mod = _load()
    # The main table itself may be written with spaced dots; the guard must
    # still audit it instead of failing closed with a misleading reason.
    root = _make_repo(tmp_path, pyproject=PYPROJECT.replace("[tool.mypy]", "[tool . mypy]"))
    rc = _run_main(
        mod,
        monkeypatch,
        root,
        mypy=(0, _success_report(2), ""),
        filter_output="",
    )
    assert rc == 0


def test_a_quoted_single_key_header_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    # ["tool.mypy"] is ONE top-level key, not the [tool.mypy] table: mypy
    # would run on its default (non-strict) config. The guard must refuse
    # the quoted header instead of normalizing it into the audited table.
    root = _make_repo(tmp_path, pyproject='["tool.mypy"]\nstrict = true\n')
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_fenced_example_config_does_not_satisfy_the_guard(tmp_path, monkeypatch, capsys):
    mod = _load()
    # strict = true lives ONLY inside a multi-line string; the real table
    # disables it. The masked parser must not read the string as config.
    fenced = (
        '[project]\nname = "demo"\ndescription = """\n'
        "[tool.mypy]\nstrict = true\nwarn_unused_ignores = true\n"
        'warn_unused_configs = true\n"""\n\n'
        "[tool.mypy]\nstrict = false\n"
    )
    root = _make_repo(tmp_path, pyproject=fenced)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_harmless_multiline_string_does_not_break_the_guard(tmp_path, monkeypatch):
    mod = _load()
    benign = '[project]\nname = "demo"\ndescription = """\na long\ndescription\n"""\n\n' + PYPROJECT
    root = _make_repo(tmp_path, pyproject=benign)
    rc = _run_main(
        mod,
        monkeypatch,
        root,
        mypy=(0, _success_report(2), ""),
        filter_output="",
    )
    assert rc == 0


def test_a_comment_fenced_string_is_not_a_string_boundary(tmp_path, monkeypatch, capsys):
    mod = _load()
    # Two comment lines whose # """ would trick a naive masker: TOML reads
    # them as comments, so ignore_errors between them is REAL configuration
    # and the guard must see it.
    fenced = PYPROJECT + '# """\nignore_errors = true\n# """\n'
    root = _make_repo(tmp_path, pyproject=fenced)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_a_quoted_non_boolean_strict_fails_the_guard(tmp_path, monkeypatch, capsys):
    mod = _load()
    # strip-all-quotes would read '"true"' as true; mypy rejects the value
    # and SKIPS strict. The guard must see the quotes and fail here.
    quoted = PYPROJECT.replace("strict = true", "strict = '\"true\"'")
    root = _make_repo(tmp_path, pyproject=quoted)
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), ""))
    assert rc == 1
    assert "config_fault" in capsys.readouterr().err


def test_any_stderr_on_a_healthy_exit_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path)  # EMPTY baseline
    # mypy's stderr is empty on every healthy run; a config error WITHOUT
    # the "mypy: error" prefix (e.g. strict: Not a boolean) also lands here
    # and can make mypy skip the audited config while exiting 0.
    stderr = 'pyproject.toml: strict: Not a boolean: "true"'
    rc = _run_main(mod, monkeypatch, root, mypy=(0, _success_report(2), stderr))
    assert rc == 1
    err = capsys.readouterr().err
    assert "config_fault" in err
    assert "Not a boolean" in err


def test_an_error_line_on_a_non_python_file_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path)  # EMPTY baseline
    # mypy-baseline 0.7.4 only parses diagnostics for .py/.pyi paths and
    # passes anything else through unbaselined; the gate must reject it too.
    report = (
        "src/pkg/app.txt:1: error: broken report\n"
        "Found 1 error in 1 file (checked 2 source files)\n"
    )
    rc = _run_main(mod, monkeypatch, root, mypy=(1, report, ""))
    assert rc == 1
    assert "execution_fault" in capsys.readouterr().err


def test_a_summary_before_the_error_lines_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, baseline="stale\n")
    report = _error_report(2)
    summary = report.splitlines()[-1]
    moved = summary + "\n" + report[: report.rindex(summary)]
    rc = _run_main(mod, monkeypatch, root, mypy=(1, moved, ""), filter_output="")
    assert rc == 1
    assert "execution_fault" in capsys.readouterr().err


def test_a_duplicated_summary_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, baseline="stale\n")
    report = _error_report(2) + "Found 2 errors in 1 file (checked 2 source files)\n"
    rc = _run_main(mod, monkeypatch, root, mypy=(1, report, ""), filter_output="")
    assert rc == 1
    assert "execution_fault" in capsys.readouterr().err


# --------------------------------------------------------------------------
# Baseline filter faults
# --------------------------------------------------------------------------


def test_a_new_error_outside_the_baseline_is_red_and_named(tmp_path, monkeypatch, capsys):
    mod = _load()
    # A parseable baseline that covers NEITHER of the report's two errors, so
    # the real filter sees both as new and names them in its output.
    root = _make_repo(tmp_path, baseline="src/pkg/app.py:0: error: an old error  [old-code]\n")
    rc = _run_main(mod, monkeypatch, root, mypy=(1, _error_report(2), ""))
    assert rc == 1
    err = capsys.readouterr().err
    assert "filter_fault" in err
    assert "Incompatible types" in err


def test_a_failing_filter_exit_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, baseline="stale\n")
    completed = SimpleNamespace(returncode=100, stdout="new violations", stderr="")
    calls = iter([completed])

    def fake_run(*args, **kwargs):
        return next(calls)

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    rc = _run_main(mod, monkeypatch, root, mypy=(1, _error_report(2), ""))
    assert rc == 1
    assert "filter_fault" in capsys.readouterr().err


def test_a_missing_filter_command_is_red(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path, baseline="stale\n")
    completed = SimpleNamespace(returncode=1, stdout=_error_report(2), stderr="")
    calls = iter([completed, FileNotFoundError("no mypy_baseline")])

    def fake_run(*args, **kwargs):
        step = next(calls)
        if isinstance(step, Exception):
            raise step
        return step

    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    rc = _run_main(mod, monkeypatch, root)
    assert rc == 1
    assert "filter_fault" in capsys.readouterr().err


# --------------------------------------------------------------------------
# Annotation surface
# --------------------------------------------------------------------------


def test_red_prints_a_single_line_annotation(tmp_path, monkeypatch, capsys):
    mod = _load()
    root = _make_repo(tmp_path)
    _run_main(mod, monkeypatch, root, mypy=(2, "", "boom"))
    err = capsys.readouterr().err
    annotation = [line for line in err.splitlines() if line.startswith("::error")]
    assert len(annotation) == 1
    assert "\n" not in annotation[0]


# --------------------------------------------------------------------------
# Config section parser
# --------------------------------------------------------------------------


def test_parser_reads_the_first_tool_mypy_table_only():
    mod = _load()
    text = "[tool.mypy]\nstrict = true # the good one\n\n[tool.other]\nstrict = true\n"
    section = mod.parse_mypy_section(text)
    assert section["strict"] == "true"
    assert "other" not in str(section)


def test_parser_strips_comments_and_quotes():
    mod = _load()
    text = '[tool.mypy]\nstrict = true  # keep\nwarn_unused_ignores = "true"\n'
    section = mod.parse_mypy_section(text)
    assert section["strict"] == "true"
    assert section["warn_unused_ignores"] == "true"


def test_parser_strips_a_comment_after_a_quoted_value():
    mod = _load()
    text = '[tool.mypy]\nwarn_unused_ignores = "true" # force on\n'
    section = mod.parse_mypy_section(text)
    assert section["warn_unused_ignores"] == "true"


# --------------------------------------------------------------------------
# CLI level: the real seam
# --------------------------------------------------------------------------


def test_cli_red_control_exits_one_with_annotation(tmp_path):
    # A tree with no pyproject fails on the config guard before mypy starts,
    # so the CLI verdict is red without installing anything.
    root = tmp_path / "empty-repo"
    root.mkdir()
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), str(root)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    assert completed.returncode == 1
    assert "::error file=.github/scripts/run_mypy_gate.py::" in completed.stderr


def test_cli_green_control_runs_real_mypy_over_this_repo():
    # Same command as the CI mypy job, on the real tree: the not-yet-zero
    # baseline must stay green, and the checked count must cover src/.
    completed = subprocess.run(
        [sys.executable, str(SCRIPT)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=600,
    )
    assert completed.returncode == 0, completed.stderr
    assert "mypy gate OK" in completed.stdout
