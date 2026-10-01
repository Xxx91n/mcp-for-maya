"""Regression tests for .github/scripts/check_tdqs_disclosure.py.

D-175: static ratchet asserting that tool docstrings disclose required
elements legislated by ADR-0028 and cataloged in docs/adr/0028-elements.yaml.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / ".github" / "scripts"
SCRIPT = SCRIPTS_DIR / "check_tdqs_disclosure.py"
REPO = Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("check_tdqs_disclosure", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_missing_element_fails(tmp_path):
    mod = _load()
    src_file = tmp_path / "src" / "tool.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text('def demo_tool():\n    """A simple tool."""\n    pass\n', encoding="utf-8")

    elements_file = tmp_path / "elements.yaml"
    elements_file.write_text(
        json.dumps(
            {
                "tools": {
                    "demo_tool": {
                        "file": "src/tool.py",
                        "required_elements": [
                            {"id": "must_have_foo", "why": "needs foo", "any": ["foo"]},
                            {"id": "must_have_bar", "why": "needs bar", "all": ["bar"]},
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    ok, errors, _warnings, count = mod.check(tmp_path, elements_file)
    assert not ok
    assert count == 2
    assert any("must_have_foo" in err for err in errors)
    assert any("must_have_bar" in err for err in errors)


def test_satisfied_element_passes(tmp_path):
    mod = _load()
    src_file = tmp_path / "src" / "tool.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text(
        'def demo_tool():\n    """A simple tool with foo and bar."""\n    pass\n', encoding="utf-8"
    )

    elements_file = tmp_path / "elements.yaml"
    elements_file.write_text(
        json.dumps(
            {
                "tools": {
                    "demo_tool": {
                        "file": "src/tool.py",
                        "required_elements": [
                            {"id": "must_have_foo", "why": "needs foo", "any": ["foo"]},
                            {"id": "must_have_bar", "why": "needs bar", "all": ["bar"]},
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    ok, errors, _warnings, count = mod.check(tmp_path, elements_file)
    assert ok
    assert errors == []
    assert count == 2


def test_missing_file_reports_error(tmp_path):
    mod = _load()
    elements_file = tmp_path / "elements.yaml"
    elements_file.write_text(
        json.dumps(
            {
                "tools": {
                    "ghost_tool": {
                        "file": "src/ghost.py",
                        "required_elements": [{"id": "elem", "any": ["x"]}],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    ok, errors, _warnings, _ = mod.check(tmp_path, elements_file)
    assert not ok
    assert any("file not found" in err for err in errors)


def test_missing_function_or_docstring_reports_error(tmp_path):
    mod = _load()
    src_file = tmp_path / "src" / "tool.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text("def other_fn():\n    pass\n", encoding="utf-8")

    elements_file = tmp_path / "elements.yaml"
    elements_file.write_text(
        json.dumps(
            {
                "tools": {
                    "target_tool": {
                        "file": "src/tool.py",
                        "required_elements": [{"id": "elem", "any": ["x"]}],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    ok, errors, _warnings, _ = mod.check(tmp_path, elements_file)
    assert not ok
    assert any("tool function 'target_tool' or docstring not found" in err for err in errors)


def test_main_cli_entrypoint(tmp_path, monkeypatch, capsys):
    mod = _load()
    src_file = tmp_path / "src" / "tool.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text('def demo():\n    """hello world"""\n', encoding="utf-8")

    elements_file = tmp_path / "elements.yaml"
    elements_file.write_text(
        json.dumps(
            {
                "tools": {
                    "demo": {
                        "file": "src/tool.py",
                        "required_elements": [{"id": "hello", "all": ["hello"]}],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(mod, "REPO", tmp_path)
    monkeypatch.setattr(mod, "DEFAULT_ELEMENTS", elements_file)
    monkeypatch.setattr("sys.argv", ["check_tdqs_disclosure.py"])
    assert mod.main() == 0
    captured = capsys.readouterr().out
    assert "TDQS disclosure check OK" in captured


def test_polarity_negated_only_match_warns_not_fails(tmp_path):
    """D-180: a mutation assertion satisfied only by a negated statement
    produces a warning during the observation period, never an error."""
    mod = _load()
    src_file = tmp_path / "src" / "tool.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text(
        "def demo_tool():\n"
        '    """A check without auto_fix mutations \u2014 it does not modify."""\n'
        "    pass\n",
        encoding="utf-8",
    )

    elements_file = tmp_path / "elements.yaml"
    elements_file.write_text(
        json.dumps(
            {
                "tools": {
                    "demo_tool": {
                        "file": "src/tool.py",
                        "required_elements": [
                            {
                                "id": "mutates_scene",
                                "why": "mutation disclosure",
                                "polarity_aware": True,
                                "any": [r"(?i)auto_fix\s+mutations"],
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    ok, errors, warnings, _ = mod.check(tmp_path, elements_file)
    assert ok
    assert errors == []
    assert len(warnings) == 1
    assert "negated" in warnings[0]
    assert "mutates_scene" in warnings[0]


def test_polarity_positive_match_satisfies(tmp_path):
    mod = _load()
    src_file = tmp_path / "src" / "tool.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text(
        'def demo_tool():\n    """Mutates the scene: creates a camera in the scene."""\n    pass\n',
        encoding="utf-8",
    )

    elements_file = tmp_path / "elements.yaml"
    elements_file.write_text(
        json.dumps(
            {
                "tools": {
                    "demo_tool": {
                        "file": "src/tool.py",
                        "required_elements": [
                            {
                                "id": "mutates_scene",
                                "why": "mutation disclosure",
                                "polarity_aware": True,
                                "any": [r"(?i)creates?\s+a\s+camera"],
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    ok, errors, warnings, _ = mod.check(tmp_path, elements_file)
    assert ok
    assert errors == []
    assert warnings == []


def test_polarity_no_match_at_all_still_errors(tmp_path):
    mod = _load()
    src_file = tmp_path / "src" / "tool.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text('def demo_tool():\n    """A simple tool."""\n    pass\n', encoding="utf-8")

    elements_file = tmp_path / "elements.yaml"
    elements_file.write_text(
        json.dumps(
            {
                "tools": {
                    "demo_tool": {
                        "file": "src/tool.py",
                        "required_elements": [
                            {
                                "id": "mutates_scene",
                                "why": "mutation disclosure",
                                "polarity_aware": True,
                                "any": [r"(?i)creates?\s+a\s+camera"],
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    ok, errors, warnings, _ = mod.check(tmp_path, elements_file)
    assert not ok
    assert any("mutates_scene" in err for err in errors)
    assert warnings == []


def test_polarity_all_branch_negated_literal_warns(tmp_path):
    """D-180: 'all' elements are polarity-aware too \u2014 a literal surviving
    only inside a negation window warns instead of silently passing."""
    mod = _load()
    src_file = tmp_path / "src" / "tool.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text(
        'def demo_tool():\n    """Does not modify the scene at all."""\n    pass\n',
        encoding="utf-8",
    )
    elements_file = tmp_path / "elements.yaml"
    elements_file.write_text(
        json.dumps(
            {
                "tools": {
                    "demo_tool": {
                        "file": "src/tool.py",
                        "required_elements": [
                            {
                                "id": "mutation_targets",
                                "why": "mutation targets disclosed",
                                "polarity_aware": True,
                                "all": ["modify", "the scene"],
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    ok, errors, warnings, _ = mod.check(tmp_path, elements_file)
    assert ok
    assert errors == []
    assert len(warnings) == 1
    assert "mutation_targets" in warnings[0]


def test_polarity_all_branch_positive_literals_satisfy(tmp_path):
    mod = _load()
    src_file = tmp_path / "src" / "tool.py"
    src_file.parent.mkdir(parents=True)
    src_file.write_text(
        'def demo_tool():\n    """May modify the scene. It does not modify config."""\n    pass\n',
        encoding="utf-8",
    )
    elements_file = tmp_path / "elements.yaml"
    elements_file.write_text(
        json.dumps(
            {
                "tools": {
                    "demo_tool": {
                        "file": "src/tool.py",
                        "required_elements": [
                            {
                                "id": "mutation_targets",
                                "why": "mutation targets disclosed",
                                "polarity_aware": True,
                                "all": ["modify", "the scene"],
                            }
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    ok, errors, warnings, _ = mod.check(tmp_path, elements_file)
    assert ok
    assert errors == []
    assert warnings == []


# --- D-190 polarity hardening (clause-scope window + positive_exemptions) ---

_REPEAT_CALLS = r"(?i)each\s+(call|invocation)\s+(adds|creates|produces)"

# D-190(3): the polarity guard is legislated for purely-positive pattern sets
# only, with camera_orbit/mutation_side_effects as the sole sanctioned instance.
# Widening it is a decision, not an edit — so the set is pinned here.
LEGISLATED_GUARDED = ["camera_orbit/mutation_side_effects"]


def _polarity_case(tmp_path, docstring, element):
    """Write a one-tool fixture; return (module, elements_file)."""
    mod = _load()
    src_file = tmp_path / "src" / "tool.py"
    src_file.parent.mkdir(parents=True, exist_ok=True)
    src_file.write_text(
        'def demo_tool():\n    """' + docstring + '"""\n    pass\n', encoding="utf-8"
    )
    elements_file = tmp_path / "elements.yaml"
    elements_file.write_text(
        json.dumps(
            {
                "tools": {
                    "demo_tool": {
                        "file": "src/tool.py",
                        "required_elements": [element],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    return mod, elements_file


def test_polarity_cross_clause_cue_does_not_negate(tmp_path):
    """D-190(1): a cue separated from the match by a clause boundary does not
    negate it. 'not idempotent - each call adds' discloses multiplicity, it is
    not a negated mutation claim -- the 80-char fixed window mis-flagged it."""
    mod, elements = _polarity_case(
        tmp_path,
        "Creates a camera. Not idempotent \u2014 each call adds another one.",
        {
            "id": "mutates_scene",
            "why": "mutation disclosure",
            "polarity_aware": True,
            "any": [_REPEAT_CALLS],
        },
    )
    ok, errors, warnings, _ = mod.check(tmp_path, elements)
    assert (ok, errors, warnings) == (True, [], [])


def test_polarity_same_clause_exemption_forgives_cue(tmp_path):
    """D-190(2): positive_exemptions names the legitimate negation-form
    phrases; a cue belonging to one of them is forgiven even in the same
    clause as the match."""
    mod, elements = _polarity_case(
        tmp_path,
        "Creates a camera; it is not idempotent, each call adds another one.",
        {
            "id": "mutates_scene",
            "why": "mutation disclosure",
            "polarity_aware": True,
            "any": [_REPEAT_CALLS],
            "positive_exemptions": ["not idempotent"],
        },
    )
    ok, errors, warnings, _ = mod.check(tmp_path, elements)
    assert (ok, errors, warnings) == (True, [], [])


def test_polarity_same_clause_cue_without_exemption_still_warns(tmp_path):
    """Exemptions are opt-in per element: the same clause minus the exemption
    list still reads as negated-only (warn, never error, observation period)."""
    mod, elements = _polarity_case(
        tmp_path,
        "Creates a camera; it is not idempotent, each call adds another one.",
        {
            "id": "mutates_scene",
            "why": "mutation disclosure",
            "polarity_aware": True,
            "any": [_REPEAT_CALLS],
        },
    )
    ok, errors, warnings, _ = mod.check(tmp_path, elements)
    assert ok
    assert errors == []
    assert len(warnings) == 1
    assert "mutates_scene" in warnings[0]


def test_polarity_exemption_does_not_forgive_other_cues_in_clause(tmp_path):
    """D-190(2): the exemption is cue-scoped. A listed phrase forgives the
    cue that belongs to it, not every cue in the same clause —
    otherwise one listed phrase would silently excuse a real negation
    sitting next to it."""
    mod, elements = _polarity_case(
        tmp_path,
        "Not idempotent, and it does not create a camera.",
        {
            "id": "mutates_scene",
            "why": "mutation disclosure",
            "polarity_aware": True,
            "any": [r"(?i)create\s+a\s+camera"],
            "positive_exemptions": ["not idempotent"],
        },
    )
    ok, errors, warnings, _ = mod.check(tmp_path, elements)
    assert ok
    assert errors == []
    assert len(warnings) == 1
    assert "mutates_scene" in warnings[0]


def test_polarity_empty_exemption_cannot_disable_the_guard(tmp_path):
    """A blank entry in positive_exemptions must not erase the window and
    switch the guard off; it is skipped instead."""
    mod, elements = _polarity_case(
        tmp_path,
        "A check without auto_fix mutations.",
        {
            "id": "mutates_scene",
            "why": "mutation disclosure",
            "polarity_aware": True,
            "any": [r"(?i)auto_fix\s+mutations"],
            "positive_exemptions": ["", "   "],
        },
    )
    ok, errors, warnings, _ = mod.check(tmp_path, elements)
    assert ok
    assert errors == []
    assert len(warnings) == 1
    assert "mutates_scene" in warnings[0]


def test_polarity_negation_across_line_wrap_still_detected(tmp_path):
    """D-190(1): the boundary set is clause terminators only. A line wrap is
    not a clause boundary, so the D-180 fake-green lesion (a negated sentence
    satisfying a mutation assertion) stays detectable."""
    mod, elements = _polarity_case(
        tmp_path,
        "A check without\n    auto_fix mutations.",
        {
            "id": "mutates_scene",
            "why": "mutation disclosure",
            "polarity_aware": True,
            "any": [r"(?i)auto_fix\s+mutations"],
        },
    )
    ok, errors, warnings, _ = mod.check(tmp_path, elements)
    assert ok
    assert errors == []
    assert len(warnings) == 1
    assert "mutates_scene" in warnings[0]


def test_live_corpus_has_no_polarity_warnings():
    """D-190(4): zero false rejections on the live corpus is the landing
    precondition — asserted here so it cannot silently regress.
    Also pins the guarded set to the instance D-190(3) legislates. Pinning is
    the whole enforcement: a negation-form element usually has BOTH a positive
    and a negated hit, so mounting the guard on one yields matched=True and
    zero warnings " + EM + " the assertions themselves cannot detect it."""
    mod = _load()
    data = json.loads(mod.DEFAULT_ELEMENTS.read_text(encoding="utf-8"))
    guarded = sorted(
        tool + "/" + elem["id"]
        for tool, cfg in data["tools"].items()
        for elem in cfg.get("required_elements", [])
        if elem.get("polarity_aware")
    )
    assert guarded == LEGISLATED_GUARDED, (
        f"guarded set drifted from the D-190(3) legislated instance: {guarded}"
    )

    ok, errors, warnings, checked = mod.check(mod.REPO, mod.DEFAULT_ELEMENTS)
    assert ok
    assert errors == []
    assert warnings == []
    assert checked == sum(len(cfg.get("required_elements", [])) for cfg in data["tools"].values())
