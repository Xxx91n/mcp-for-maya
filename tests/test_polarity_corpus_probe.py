"""D-203 regression tests: the sample floor counts verdict-bearing labels.

The probe itself is a manual instrument that always exits 0 (see its
docstring), so its arithmetic is pinned HERE instead - otherwise "the floor
holds" is a claim nobody can fail.

What D-203 changed and what would regress if it silently reverted:

  * MIN_ADJUDICABLE is measured over true_negative + forgiven only. Counting
    known_limitation as well would let the corpus reach the floor with
    sentences that cannot move a verdict, since those samples record a
    clause-scope trade the design made on purpose.
  * every guarded element independently needs MIN_TN_PER_ELEMENT true
    negatives, so one element carrying the whole corpus cannot pass.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / ".github" / "scripts" / "polarity_corpus_probe.py"
ELEMENTS = REPO / "docs" / "adr" / "0028-elements.yaml"


def _load():
    spec = importlib.util.spec_from_file_location("polarity_corpus_probe", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _tools(mod) -> dict:
    return json.loads(ELEMENTS.read_text(encoding="utf-8")).get("tools", {})


class TestD203FloorCaliber:
    def test_adjudicable_labels_exclude_known_limitation(self):
        mod = _load()
        assert mod.ADJUDICABLE_LABELS == (mod.TRUE_NEGATIVE, mod.FORGIVEN)
        assert mod.KNOWN_LIMITATION not in mod.ADJUDICABLE_LABELS, (
            "known_limitation records a deliberate trade (D-190 1); it can never "
            "move a verdict, so counting it would let the floor be met with "
            "samples that adjudicate nothing"
        )

    def test_every_sample_carries_a_label_a_reason_and_a_text(self):
        mod = _load()
        known = {mod.TRUE_NEGATIVE, mod.FORGIVEN, mod.KNOWN_LIMITATION}
        for sample in mod.LABELLED_CORPUS:
            assert sample["label"] in known, sample
            assert sample["text"].strip(), sample
            # A sample without a defensible reason cannot be adjudicated later.
            assert len(sample["why"]) > 20, sample

    def test_corpus_texts_are_unique(self):
        mod = _load()
        texts = [s["text"] for s in mod.LABELLED_CORPUS]
        assert len(texts) == len(set(texts)), "a duplicated sample inflates the floor"

    def test_floor_is_cleared_on_the_live_corpus(self):
        mod = _load()
        guarded = mod._guarded_elements(_tools(mod))
        counts, _per_element, unexpected = mod.adjudicate(mod.load_checker(), guarded)
        adjudicated = sum(counts[label] for label in mod.ADJUDICABLE_LABELS)
        assert not unexpected, f"labelled expectations broke: {unexpected}"
        assert adjudicated >= mod.MIN_ADJUDICABLE, (
            f"{adjudicated} adjudicable < MIN_ADJUDICABLE={mod.MIN_ADJUDICABLE}; "
            f"the verdict must stay 'not yet adjudicable'"
        )

    def test_the_old_basis_would_have_been_met_earlier(self):
        """Why the basis change mattered: at the pre-D-203 corpus size the
        total row count cleared nothing useful, and TN+F alone is the number
        that decides."""
        mod = _load()
        guarded = mod._guarded_elements(_tools(mod))
        counts, _pe, _u = mod.adjudicate(mod.load_checker(), guarded)
        assert sum(counts.values()) >= counts[mod.KNOWN_LIMITATION], "sanity"
        assert counts[mod.KNOWN_LIMITATION] > 0, (
            "if this is 0 the two bases coincide and the test above no longer "
            "proves the basis is actually applied"
        )

    def test_every_guarded_element_clears_the_per_element_floor(self):
        mod = _load()
        guarded = mod._guarded_elements(_tools(mod))
        assert guarded, "no polarity_aware element - the assertion would be vacuous"
        _counts, per_element_tn, _u = mod.adjudicate(mod.load_checker(), guarded)
        for tool, elem in guarded:
            key = (tool, elem["id"])
            assert per_element_tn.get(key, 0) >= mod.MIN_TN_PER_ELEMENT, (
                f"{key} carries {per_element_tn.get(key, 0)} true negatives, "
                f"needs {mod.MIN_TN_PER_ELEMENT} (D-203)"
            )

    def test_per_element_counter_ignores_forgiven_samples(self):
        """A forgiven sample proves the exemption list works; it is not evidence
        that the element was adjudicated as a true negative."""
        mod = _load()
        guarded = mod._guarded_elements(_tools(mod))
        _counts, per_element_tn, _u = mod.adjudicate(mod.load_checker(), guarded)
        assert sum(per_element_tn.values()) == _counts[mod.TRUE_NEGATIVE]

    def test_adding_a_known_limitation_sample_cannot_reach_the_floor(self):
        """The whole point: a verdict-free sample must not move the gate."""
        mod = _load()
        guarded = mod._guarded_elements(_tools(mod))
        before, _pe, _u = mod.adjudicate(mod.load_checker(), guarded)
        before_n = sum(before[label] for label in mod.ADJUDICABLE_LABELS)
        mod.LABELLED_CORPUS.append(
            {
                "label": mod.KNOWN_LIMITATION,
                "text": "It does not create a new camera. Instead a camera is created.",
                "why": "temporary probe sample used to prove the floor ignores it",
            }
        )
        try:
            after, _pe2, _u2 = mod.adjudicate(mod.load_checker(), guarded)
            assert sum(after.values()) == sum(before.values()) + 1
            assert sum(after[label] for label in mod.ADJUDICABLE_LABELS) == before_n
        finally:
            mod.LABELLED_CORPUS.pop()

    def test_min_adjudicable_has_a_provenance_note(self):
        """D-205: a bare number with no stated basis is how the R44 audit found
        MIN_ADJUDICABLE=12 in the first place."""
        source = SCRIPT.read_text(encoding="utf-8")
        block = source.split("MIN_ADJUDICABLE = 12", 1)
        assert len(block) == 2
        preceding = source[: source.index("MIN_ADJUDICABLE = 12")]
        assert "D-203" in preceding, "the floor must cite the ruling that set its basis"
        assert "circular" in preceding, (
            "the comment must say why 12 was carried over rather than "
            "recomputed from the corpus it gates"
        )

    def test_probe_still_exits_zero(self):
        """Its documented contract is exit 0 with no gating; a change here would
        silently turn a manual instrument into a CI gate."""
        import subprocess
        import sys

        out = subprocess.run(
            [sys.executable, str(SCRIPT)], capture_output=True, text=True, cwd=REPO
        )
        assert out.returncode == 0, out.stdout[-2000:] + out.stderr[-2000:]
        assert "TRACK3 (mutation)" in out.stdout

    def test_element_with_zero_true_negatives_is_reported_not_passed(self, capsys):
        """D-204 regression: the thin-element list iterated the TN dict instead
        of the guarded elements, so an element with NO true negatives had no
        key, was skipped, and fell through to the branch that announces every
        element clears the floor - a false green on exactly the failing case."""
        mod = _load()
        checker = mod.load_checker()
        # a guarded element whose pattern no labelled sample can match
        # labelled_track takes the tools MAP; a guarded element whose pattern
        # no labelled sample can match
        synthetic = {
            "ghost_tool": {
                "file": "src/maya_mcp_server/pipeline.py",
                "required_elements": [
                    {
                        "id": "never_matched_element",
                        "polarity_aware": True,
                        "any": [r"(?i)zzzzz_no_sample_matches_this"],
                    }
                ],
            }
        }
        mod.labelled_track(checker, synthetic)
        out = capsys.readouterr().out
        assert "PER-ELEMENT TN ghost_tool/never_matched_element" in out, out
        assert "carries >= 3 true negatives" not in out, (
            "must not claim the floor is met while an element has zero"
        )
        assert "PER-ELEMENT FLOOR NOT MET" in out, out
