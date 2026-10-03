# S2 post-hoc review — polarity corpus track-3 promotion samples

- **Date of this review:** 2026-10-03
- **Round:** R46 (execution lane)
- **Ledger:** D-221 ③ (S2), D-198 ② (track-3 → track-2 promotion channel), D-205 ③
- **Status:** **post-hoc review** — performed AFTER the samples were already in
  the corpus. This is explicitly NOT a pre-registered verification and carries
  no pre-tense of one. D-221 ③ ③ forbids back-dating it.

## What D-221 ③ asked for

The ruling records that the pre-verification record for track-3 → track-2
promotion returned **zero hits**, and that the five samples are checkable in the
repo. S2 is therefore an execution-window task, not a lane: adjudicate the five
now, record the result honestly as post-hoc.

## How to re-derive the cohort

```
uv run python .github/scripts/polarity_corpus_probe.py
```

Track-2 arithmetic at the time of this review:

| quantity                                   | value                                    |
| ------------------------------------------ | ---------------------------------------- |
| labelled samples                           | 14                                       |
| `true_negative`                            | 7                                        |
| `forgiven`                                 | 5                                        |
| `known_limitation`                         | 2                                        |
| adjudicable (TN + forgiven, D-203 caliber) | **12**                                   |
| `MIN_ADJUDICABLE`                          | 12                                       |
| guarded elements                           | 1 (`camera_orbit/mutation_side_effects`) |
| per-element true negatives                 | 7 (floor is 3)                           |
| label/guard disagreements                  | **0**                                    |

The five samples adjudicated here are exactly the `forgiven` cohort: corpus
indices 4, 5, 6, 12 and 13 of `LABLED_CORPUS` in
`.github/scripts/polarity_corpus_probe.py`.

## Adjudication

D-198 ④ defines the `forgiven` label as _"a correct negation-FORM disclosure
('not idempotent') that the exemption list must forgive"_. So the question per
sample is not "is this sentence negative?" but "is this the tool honestly
declaring its non-idempotence, in a form the exemption list is supposed to
forgive?"

| #   | sample text                                                                           | guard verdict | agrees with label | adjudication                                                                                                                                                                             |
| --- | ------------------------------------------------------------------------------------- | ------------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 4   | `Not idempotent — each call creates a new camera.`                                    | `forgiven`    | yes               | **confirmed.** `camera_orbit` does create a fresh camera per call, so "Not idempotent" is the truthful disclosure, in the canonical form. Forgiving the later positive claim is correct. |
| 5   | `This tool is non-idempotent: it creates a new camera every time.`                    | `forgiven`    | yes               | **confirmed.** Same claim, `non-idempotent` surface form, also listed in `positive_exemptions`.                                                                                          |
| 6   | `Not idempotent, so it creates a new camera on every invocation.`                     | `forgiven`    | yes               | **confirmed.** Phrase-scoped exemption behaves as legislated: the exempt phrase does not swallow the positive claim that follows it.                                                     |
| 12  | `Non-idempotent by design; each call creates a new camera and animation curves.`      | `forgiven`    | yes               | **confirmed.** Positive claim sits after a `; ` split and is still counted; forgiveness applied to the sentence, not to the clause boundary.                                             |
| 13  | `Not idempotent - calling this twice creates a new camera and marks the scene dirty.` | `forgiven`    | yes               | **confirmed.** Two positive matches follow one exempt phrase; both were forgiven rather than only the first.                                                                             |

**Result: 5 of 5 confirmed.** Each is a defensible one-sentence label
(`why` field present on all five, satisfying D-198 ①), and each states the tool's
real behaviour truthfully.

## What is NOT established here — recorded as unverified, not guessed

D-205 ③: anything not reproducible is recorded as unverified; an invalid
experiment is not evidence.

1. **Provenance as track-3 promotions is NOT verified.** D-221 ③ refers to five
   samples promoted from the programmatic mutation track. Track 3
   (`mutation_track` in the same script) generates sentences shaped
   `"<cue> <clause>"` for cues `does not / never / without / cannot`, and
   `"does not <clause><split>and <clause>"` for splits `. ; , and  but `. **None
   of the five samples above has that shape** — they are hand-written
   disclosures. No promotion record exists anywhere in the repo (D-221 ③
   records zero hits for it). So this review confirms the five samples are
   _correctly labelled_; it does **not** confirm they arrived via the track-3
   channel. Possible readings, none chosen: the ruling counted a cohort that was
   in fact hand-authored, or an unrecorded promotion happened. **No cause is
   guessed.** If the distinction matters, the fix is a promotion log, not a
   reinterpretation of this file.
2. **No real-Maya or live-tool verification.** These are text fixtures. Nothing
   here observed `camera_orbit` running.
3. **The floor has zero headroom.** Adjudicable = 12 against
   `MIN_ADJUDICABLE` = 12. Removing or re-labelling any single verdict-carrying
   sample returns the run to "not yet adjudicable". One guarded element carries
   the entire corpus. Both facts are properties of the current corpus, recorded
   here so a future reader does not mistake a cleared floor for margin.
4. **D-198 ⑤ second precondition still open.** This review speaks only to the
   track-2 floor. Promotion of the TDQS gate from warn to hard additionally
   requires the primary track's zero-false-rejection verdict, and the FN-rate
   threshold D-198 ⑤ deferred is still unlegislated. Neither is established
   here.

## Reproduction

| claim                               | command                                                          | observed                                                                                                           |
| ----------------------------------- | ---------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| the five-sample cohort + arithmetic | `uv run python .github/scripts/polarity_corpus_probe.py`         | `samples=14`, `true_negative=7`, `forgiven=5`, `known_limitation=2`, `adjudicable (true_negative + forgiven) = 12` |
| guard agrees with every hand label  | same command, TRACK2 block                                       | `disagreements with the hand labels = 0`                                                                           |
| this record stays labelled post-hoc | `uv run python -m pytest tests/test_polarity_corpus_probe.py -q` | includes `test_s2_post_hoc_record_is_labelled_as_post_hoc`                                                         |
