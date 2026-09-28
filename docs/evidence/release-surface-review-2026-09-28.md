# Release-surface review — 2026-09-28 (T-28a commit ④, D-131 one-time gate row)

```yaml
meta:
  env: Windows (Git Bash), node v24, uv, twine via uvx
  date: 2026-09-28 ~04:00 UTC
  repo_state: branch grill/round28-v1-gate on base 8bef528 (main); version 0.4.0 (unreleased)
  scope: 48 markdown files (README.md, README.zh-CN.md, CHANGELOG.md,
    CONTRIBUTING.md, SECURITY.md, AGENTS.md, CONTEXT.md, docs/**)
claim_boundary: >
  This artifact supports "the release-facing surface passed a one-time
  hygiene review on 2026-09-28" — link resolution, stale-claim sweep,
  experimental-wording check, CVE-2026-66004 applicability on the
  asset_import path, and twine check of the 0.4.0 artifacts. It does NOT
  claim runtime correctness, real-Maya behavior (gated by #7), or that
  external links stay alive after this date.
```

## 1. Dead-link full scan — PASS (1 false positive, 1 fixed)

Method: scripted markdown scan (`](...)` links + `<img src>`), fenced code
stripped; internal links resolved against the working tree; self-repo
`github.com|raw.githubusercontent.com/Xxx91n/mcp-for-maya/(blob|tree)/main/...`
paths verified against the tree (they go live at merge — absolute URLs are
the PyPI convention, D-080⑤); all other externals probed HEAD→GET fallback,
15 s timeout, `Mozilla/5.0` UA.

| Class | Count | Result |
|-------|-------|--------|
| Internal relative links | 5 | 1 flagged — `docs/decision-ledger.md` → `README.zh-CN.md`: **false positive**, it is quoted selector markup inside the D-072 ledger row, not a navigation link |
| Self-repo blob/tree paths | 26 occurrences | all targets exist in tree (0 missing) |
| `<img src>` self-repo assets | 14 | all files present under `.github/assets/` |
| External (non-self) | 27 unique | 26 × 200; **1 × 404 fixed** |

**Fixed:** threat-model.md cited `github.com/ahujasid/blender-mcp/issues/257`,
which 404s — the upstream repo was renamed to `ahujasid/mcp-for-blender`
(repo root and `/pull/258` redirect; `/issues/257` under the old name does
not). Canonical URL now used: `github.com/ahujasid/mcp-for-blender/issues/257`
(verified 200).

## 2. Stale-claim inventory — PASS after repair

Swept `0.x.y` version literals, "current"-claims, alpha/beta/stable/
experimental wording across the release-facing docs.

- **Fixed (commit ②):** README/Versioning bullet claimed "current 0.2.0,
  Alpha" — stale on two axes (0.3.0 is the latest release; the in-flight
  0.4.0 carries the `4 - Beta` classifier per D-131). Now reads
  "0.x (through 0.3.x, Alpha)" + "Beta (0.4.0)"; zh-CN mirror in sync.
- Historical version mentions are narrative facts and exempt per D-121
  ("shipped in 0.2.0", CHANGELOG release sections, upstream-issue-status).
- Tool-count claims: CI gate `check_tool_count_claims.py` covers the four
  live files + newest CHANGELOG section; new prose carries no absolute
  count claim (D-121④ forward discipline).

## 3. Experimental-wording check — PASS

- `skills/` cards labeled **Experimental** with an explicit disclosure line
  ("Evaluated on Claude Code only; untested on Codex/Gemini CLI/Cursor.
  Cross-model evaluation is tracked in issue #3") — calibrated, not a lazy
  blanket claim. Per D-132 the removal of experimental framing belongs to
  the 1.0.0 tag commit batch, not this round.
- No project-level alpha/beta banner exists outside the Versioning
  section; the section now matches the shipped classifier.

## 4. CVE-2026-66004 applicability on `asset_import` — NOT APPLICABLE as designed

Reference (double-sourced in D-132): BlenderMCP < commit `30a3308`,
`download_polyhaven_asset` joined API-response `include` dict keys directly
into filesystem paths — no containment check — so MITM/prompt injection
could supply `../../.bashrc` for arbitrary file write (CWE-22, CVSS 6.0).
VulnCheck advisory + upstream report mcp-for-blender#257.

The same disease requires attacker-controlled path components. On this
repo's path every component is constrained in code (`polyhaven.py`):

| Disease leg | This project's control | Where |
|---|---|---|
| API keys used as paths | Never — no response key becomes a path; names derive from the whitelisted download URL's last segment | `download_asset` → `_sanitize_filename` |
| `..` / separators in filename | Charset whitelist `[A-Za-z0-9_.-]`; dot-prefixed or empty names replaced by `file_<md5>` | `_sanitize_filename` (L399–405) |
| Traversal via cache subdirs | `asset_id` matches `^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$` (no dots → `..` impossible); `resolution` ∈ {1k,2k,4k,8k} | `validate_asset_id`, `download_asset` |
| Caller-chosen destination | `cache_root` is not a tool-surface param — `asset_tools` calls `download_asset(asset_id, resolution=…)`; dest is fixed under `platformdirs.user_cache_dir("mcp-for-maya")/polyhaven` | `asset_tools.py:201`, `cache_dir_for` |
| Malicious redirect host | https-only + host allowlist re-validated on every 30x hop | `_check_url`, `_WhitelistRedirectHandler` |
| Corrupted/tampered payload | API-declared size + per-file md5 verified post-download | `_verify_local`, `download_asset` L494–502 |
| Tool-param traversal | pipeline pattern scan blocks `../` in filename params (defense-in-depth; `asset_import` takes no filename param anyway) | `security.py` |

Residual honesty note: safety derives from charset-whitelisting every path
component; there is no explicit `resolve().startswith(cache_root)`
containment assertion as a final belt. That is a hardening candidate, not
a live hole — no injection surface exists today. Registered for the gate
reviewer to decide whether it becomes a debt row.

Conclusion: the CVE is cited in docs/threat-model.md §4 as attack-class
evidence only; the applicability precondition (verify our controls cover
the disease before citing) is satisfied.

## 5. twine check (D-080⑤) — PASSED

```
uv build → dist/mcp_for_maya-0.4.0.tar.gz + mcp_for_maya-0.4.0-py3-none-any.whl
uvx twine check dist/*
  Checking dist/mcp_for_maya-0.4.0-py3-none-any.whl: PASSED
  Checking dist/mcp_for_maya-0.4.0.tar.gz: PASSED
```

PKG-INFO inside the sdist reports `Version: 0.4.0` and
`Classifier: Development Status :: 4 - Beta` — the commit ② bump
propagates into the shipped metadata.
