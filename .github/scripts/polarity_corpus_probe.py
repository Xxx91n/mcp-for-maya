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
    return 0


if __name__ == "__main__":
    sys.exit(main())
