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
  admission requirements, not redaction targets. Artifacts frozen before
  this rule (e.g. `probes/probe-signature-baseline-maya2024.json`, which
  has no `versions`/`PID` fields) are grandfathered and stay as-is —
  append-only applies to them too.
- **claim_boundary required.** Every artifact states the strongest claim
  it supports (example: connected != renders).
- **Forward rule:** a live-verified-grade claim must cite an in-repo
  artifact here or name a mayapy/human_verify tier record **with a
  recorded outcome** — the `human_verify` marker only prints manual steps
  and always skips, so naming the marker alone does not satisfy this rule.
