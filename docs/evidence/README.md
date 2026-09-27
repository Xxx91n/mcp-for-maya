# docs/evidence/ — decision-grade evidence (D-109)

In-repo store for decision-grade artifacts: machine evidence backing
public adjudications and external claims (probe JSON dumps, comparison
reports). Process transcripts and draft reports stay in `.scratch/`
and never land here (KORA selective-freeze: raw output defaults out,
only explicitly frozen evidence enters the repo).

Discipline:

- **Append-only.** Artifacts are never edited in place — git history is
  the audit trail. A refuted artifact gets a NEW artifact + a new ledger
  adjudication, and the old file is annotated `superseded`, not
  rewritten.
- **Provenance required.** `meta` carries env / date / versions / PID —
  these are admission requirements, not redaction targets.
- **claim_boundary required.** Every artifact states the strongest claim
  it supports (example: connected != renders).
- Forward rule (D-109): any live-verified-grade claim must cite an
  in-repo artifact here or name a mayapy/human_verify tier record.
