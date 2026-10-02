"""D-191(1)c two-track polarity corpus measurement (D-190 / T-R42-02).

Manual measurement instrument, NOT a CI gate -- same shape as
check_release_appendix.py (release-preflight item, human-run). It measures;
check_tdqs_disclosure.py is what gates. Run it to reproduce the corpus
evidence quoted in check_tdqs_disclosure.py, and at the 0.6.0 preflight
when D-190(4)/D-189 decide whether negated_only may be promoted warn->hard.

Two tracks, always reported separately (D-191(1)c):

  PRIMARY  the real validation surface, and the only denominator the
           zero-false-rejection judgement uses (D-190 4): each tool declared
           in docs/adr/0028-elements.yaml against its OWN docstring,
           checking only its OWN elements.
  STRESS   diagnostic only: every docstring-bearing function in
           src/maya_mcp_server x every element pattern (cartesian).

Caliber (pinned because the pre-hardening evidence did not pin it, D-191 1c):
the stress corpus is every function/async-function carrying a docstring,
counted per OCCURRENCE -- methods and nested defs included, nothing
de-duplicated. The 264 figure in the 2026-09-30 evidence was a probe
artifact: that probe keyed docstrings by bare function name into a single
dict and silently collapsed 23 same-named functions. Compare like with
like; this script prints the reconciled counts on every run.

Usage:  python .github/scripts/polarity_corpus_probe.py
Exit code is always 0 -- read the numbers, do not gate on it.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent.parent
ELEMENTS = REPO / "docs" / "adr" / "0028-elements.yaml"
CHECKER = REPO / ".github" / "scripts" / "check_tdqs_disclosure.py"
NAIVE_WINDOW = 80  # the retired fixed-window form, kept only for comparison


def load_checker():
    spec = importlib.util.spec_from_file_location("tdqs", CHECKER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def corpus(src_dir):
    """(file::function, docstring) per OCCURRENCE -- no de-duplication."""
    out = []
    for path in sorted(src_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                doc = ast.get_docstring(node)
                if doc:
                    out.append((path.name + "::" + node.name, doc))
    return out


def naive_negated(checker, doc, start):
    """The retired 80-char window, kept only for before/after comparison."""
    head = doc[max(0, start - NAIVE_WINDOW) : start]
    return bool(checker.NEGATION_CUES.search(head))


def primary_track(checker, tools, by_name):
    checked = guarded = negated_only = 0
    exemption_flips = 0
    for tool, cfg in sorted(tools.items()):
        doc = by_name.get(Path(cfg["file"]).name + "::" + tool)
        if doc is None:
            print(f"  [primary] MISSING docstring: {tool}")
            continue
        for elem in cfg.get("required_elements", []):
            checked += 1
            if not elem.get("polarity_aware"):
                continue
            guarded += 1
            exempt = tuple(elem.get("positive_exemptions", ()))
            pos = neg = 0
            for pat in elem.get("any", []):
                for m in re.finditer(pat, doc):
                    scoped = checker._negated(doc, m.start(), exempt)
                    # how many verdicts the exemption list alone changes:
                    # same clause, but forgiven without the list
                    bare = checker._negated(doc, m.start(), ())
                    if bare != scoped:
                        exemption_flips += 1
                    if scoped:
                        neg += 1
                    else:
                        pos += 1
            if neg and not pos:
                negated_only += 1
                print(f"  [primary] NEGATED-ONLY {tool}/{elem['id']}")
    print(f"PRIMARY: elements={checked} guarded={guarded} negated_only={negated_only}")
    print(
        f"  exemption_list_changed_verdicts={exemption_flips}"
        " (0 = the list is a forward guard, no verdict depends on it today)"
    )
    verdict = "PASS" if negated_only == 0 else "REVIEW"
    print(f"  D-190(4) zero-false-rejection verdict: {verdict}")


def stress_track(checker, tools, docs):
    pos = neg = naive_neg = forgiven = 0
    shapes = {}
    for _key, doc in docs:
        for cfg in tools.values():
            for elem in cfg.get("required_elements", []):
                exempt = tuple(elem.get("positive_exemptions", ()))
                for pat in elem.get("any", []):
                    for m in re.finditer(pat, doc):
                        naive_neg += int(naive_negated(checker, doc, m.start()))
                        if checker._negated(doc, m.start(), exempt):
                            neg += 1
                            clause = doc[checker._clause_start(doc, m.start()) : m.end()]
                            key = (elem["id"], clause[:90])
                            shapes[key] = shapes.get(key, 0) + 1
                        else:
                            pos += 1
                            forgiven += int(naive_negated(checker, doc, m.start()))
    print(
        f"STRESS: matches={pos + neg} clause_scope_negated={neg} "
        f"naive80_negated={naive_neg} naive_FP_forgiven={forgiven}"
    )
    for (eid, clause), n in sorted(shapes.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  surviving negated clause: {n} x {eid}: {clause!r}")


# ---------------------------------------------------------------------------
# D-198 track 2 -- hand-labelled criteria corpus. The ONLY false-negative
# denominator (D-191 1c): every sample carries a label and a one-sentence
# defensible reason, so a disagreement is a conversation, not a number.
#
# Three labels, and the third is NOT a false negative:
#   true_negative       the sentence really does negate the claim, so the
#                       guard must answer negated_only
#   forgiven            a correct negation-FORM disclosure ("not idempotent")
#                       that the exemption list must forgive
#   known_limitation    a real negation the clause-scope rule deliberately
#                       forgives because the cue sits in an EARLIER clause.
#                       This is the traded-away false-positive class from
#                       D-190 1, counted as a design limitation, never as an FN.
# ---------------------------------------------------------------------------

TRUE_NEGATIVE = "true_negative"
FORGIVEN = "forgiven"
KNOWN_LIMITATION = "known_limitation"

LABELLED_CORPUS = [
    {
        "label": TRUE_NEGATIVE,
        "text": "This tool does not create a new camera.",
        "why": "the claim is genuinely denied in the same clause, so a positive "
               "match would be a fake green",
    },
    {
        "label": TRUE_NEGATIVE,
        "text": "It never adds animation curves to the scene.",
        "why": "'never' is a cue and the match follows it inside one clause",
    },
    {
        "label": TRUE_NEGATIVE,
        "text": "Calling this twice will not create a new camera.",
        "why": "the cue precedes the match with no clause terminator between them",
    },
    {
        "label": TRUE_NEGATIVE,
        "text": "This call does not mark the scene dirty.",
        "why": "exercises the scene-dirty pattern, not only the camera one",
    },
    {
        "label": FORGIVEN,
        "text": "Not idempotent \u2014 each call creates a new camera.",
        "why": "'not idempotent' is the canonical disclosure of the property, "
               "listed in positive_exemptions",
    },
    {
        "label": FORGIVEN,
        "text": "This tool is non-idempotent: it creates a new camera every time.",
        "why": "the non-idempotent form is listed too, and must be forgiven the same way",
    },
    {
        "label": FORGIVEN,
        "text": "Not idempotent, so it creates a new camera on every invocation.",
        "why": "the exemption is scoped to the phrase, not the clause, so a "
               "later true claim still counts",
    },
    {
        "label": KNOWN_LIMITATION,
        "text": "It does not delete anything. The tool creates a new camera.",
        "why": "the cue sits in an earlier clause; clause scope forgives it by design (D-190 1)",
    },
    {
        "label": KNOWN_LIMITATION,
        "text": "No geometry is removed; instead a camera is created and animated.",
        "why": "semicolon splits the clause, so the guard sees only the positive second half",
    },
]

# Below this many labelled samples the corpus is a smoke test, not evidence.
# The ruling keeps such a run at "not yet adjudicable" rather than promoting
# a verdict off a handful of samples.
MIN_ADJUDICABLE = 12


def labelled_track(checker, tools):
    """Track 2. Prints the FN denominator; never combines with track 3."""
    guarded = _guarded_elements(tools)
    if not guarded:
        print("TRACK2 (labelled): no polarity_aware element to exercise")
        return
    counts = {TRUE_NEGATIVE: 0, FORGIVEN: 0, KNOWN_LIMITATION: 0}
    unexpected = []
    for tool, elem in guarded:
        patterns = elem.get("any", [])
        exempt = tuple(elem.get("positive_exemptions", ()))
        for sample in LABELLED_CORPUS:
            pos = neg = 0
            for pat in patterns:
                for m in re.finditer(pat, sample["text"]):
                    if checker._negated(sample["text"], m.start(), exempt):
                        neg += 1
                    else:
                        pos += 1
            if neg and not pos:
                verdict = TRUE_NEGATIVE
            elif pos:
                verdict = FORGIVEN if sample["label"] == FORGIVEN else "saw-positive"
            else:
                verdict = "no-match"
            counts[sample["label"]] += 1
            if sample["label"] in (TRUE_NEGATIVE, FORGIVEN) and verdict != sample["label"]:
                unexpected.append(
                (tool, elem["id"], sample["label"], verdict, sample["text"])
            )
    print(f"TRACK2 (labelled): samples={len(LABELLED_CORPUS)} per guarded element={len(guarded)}")
    print(f"  labels: true_negative={counts[TRUE_NEGATIVE]} forgiven={counts[FORGIVEN]} "
          f"known_limitation={counts[KNOWN_LIMITATION]}")
    print(f"  FN denominator (true_negative only) = {counts[TRUE_NEGATIVE]}")
    print(f"  disagreements with the hand labels = {len(unexpected)}")
    for row in unexpected:
        print(
            f"    MISMATCH {row[0]}/{row[1]}: labelled {row[2]}, "
            f"guard said {row[3]} -- {row[4]!r}"
        )
    if len(LABELLED_CORPUS) < MIN_ADJUDICABLE:
        print(
            f"  NOT YET ADJUDICABLE: {len(LABELLED_CORPUS)} < "
            f"MIN_ADJUDICABLE={MIN_ADJUDICABLE}; verdict stays warn, "
            "no promotion off this sample"
        )
    elif unexpected:
        print("  REGRESSION: a labelled expectation did not hold")
    else:
        print("  labels hold; still not a promotion signal on its own")


# ---------------------------------------------------------------------------
# D-198 track 3 -- programmatic mutation surface. Reports absolute counts and
# construction coverage ONLY. It is never a denominator: a generated sentence
# has no ground truth, so any ratio computed over it would be a made-up
# number. Promotion into track 2 requires a human confirming a true negative.
# ---------------------------------------------------------------------------

MUTATION_CUES = ["does not", "never", "without", "cannot"]
MUTATION_SPLITS = [". ", "; ", ", and ", " but "]


def mutation_track(checker, tools):
    docs = corpus(REPO / "src" / "maya_mcp_server")
    guarded = _guarded_elements(tools)
    total = 0
    flipped = 0
    shapes: dict[tuple[str, str], int] = {}
    for _key, doc in docs:
        for _tool, elem in guarded:
            exempt = tuple(elem.get("positive_exemptions", ()))
            for pat in elem.get("any", []):
                for m in re.finditer(pat, doc):
                    total += 1
                    clause = doc[checker._clause_start(doc, m.start()) : m.end()]
                    for cue in MUTATION_CUES:
                        mutated = f"{cue} {clause}"
                        if checker._negated(mutated, len(cue) + 1, exempt):
                            flipped += 1
                            shapes[(cue, "prefix")] = shapes.get((cue, "prefix"), 0) + 1
                    for split in MUTATION_SPLITS:
                        mutated = f"{MUTATION_CUES[0]} {clause}{split}and {clause}"
                        first = mutated.find(clause)
                        second = mutated.find(clause, first + 1)
                        if second < 0:
                            continue
                        key = (split.strip(), "split")
                        shapes[key] = shapes.get(key, 0) + 1
                        if not checker._negated(mutated, second, exempt):
                            flipped += 1
    print(f"TRACK3 (mutation): seed_matches={total} negated_after_mutation={flipped}")
    print(f"  constructions exercised={len(shapes)} (cue-prefix and clause-split)")
    for (shape, kind), n in sorted(shapes.items()):
        print(f"    {kind}: {shape!r} -> {n}")
    print("  absolute counts only -- track 3 is NEVER a denominator (D-198)")


def _guarded_elements(tools):
    out = []
    for tool, cfg in sorted(tools.items()):
        for elem in cfg.get("required_elements", []):
            if elem.get("polarity_aware"):
                out.append((tool, elem))
    return out



def main():
    checker = load_checker()
    tools = json.loads(ELEMENTS.read_text(encoding="utf-8")).get("tools", {})
    docs = corpus(REPO / "src" / "maya_mcp_server")
    by_name = {key: doc for key, doc in docs}
    elements = sum(len(c.get("required_elements", [])) for c in tools.values())
    legacy = len({key.split("::")[1] for key in by_name})
    print(f"corpus: {len(docs)} docstring-bearing function occurrences")
    print(f"  distinct file::name pairs: {len(by_name)}")
    print(f"  name-keyed dict (legacy probe caliber): {legacy}")
    print(f"elements: {elements} across {len(tools)} tools")
    primary_track(checker, tools, by_name)
    stress_track(checker, tools, docs)
    labelled_track(checker, tools)
    mutation_track(checker, tools)
    return 0


if __name__ == "__main__":
    sys.exit(main())
