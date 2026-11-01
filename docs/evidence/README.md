# docs/evidence/ — decision-grade evidence

In-repo store for decision-grade artifacts: machine evidence backing
public adjudications and external claims (probe JSON dumps, comparison
reports).

Non-goals: process transcripts, draft reports, and claims without a
live verification record are out of scope here and stay in `.scratch/` —
raw output defaults out; only explicitly frozen evidence enters the repo.

Admission rules:

- **Append-only.** Artifacts are never edited in place — git history is
  the audit trail. A refuted artifact gets a new artifact plus a new
  ledger adjudication; the old file is annotated `superseded`, not
  rewritten.
- **Provenance required.** `meta` carries env / date / versions / PID —
  admission requirements, not redaction targets.
- **claim_boundary required.** Every artifact states the strongest claim
  it supports (example: connected != renders).
- **Forward rule:** a live-verified-grade claim must cite an in-repo
  artifact here or name a mayapy/human_verify tier record.
