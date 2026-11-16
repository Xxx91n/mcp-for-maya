# Issue #80: consolidating the nine `scene_*` tools — what the sources actually say

Research date: 2026-11-16. Research target: `origin/main` at `fc243f9c` (v0.8.0).

Standing legend used throughout:

- **verified at source** — I read the page/file that owns the claim.
- **secondhand** — I only saw the number or statement quoted by someone else.
- **unknown** — not established; no source found, or the claim is my own inference.
- **not opened** — a URL I tried and could not read (listed in Sources).

Method note: external pages were read through a text-extraction fetch tool. Quotes below are what that extraction returned; I did not re-type them from a browser render. That is a small but real caveat on every quoted string in this file.

Headline findings, before the detail:

1. The issue's central number is wrong at the source. The public Glama page reports **Disambiguation 4/5**, not 3/5, and it has reported that since at least the 2026-10-30 scoring run. RQ6.
2. The issue's stated cause is wrong at the source too. The retired ledger records that the deferral was **not** about "a major version plus a migration path". It was about tool heterogeneity. See "The internal record", below.
3. The merge's entire upside on the published rubric is worth about **+0.1 overall** and one band on Tool Count. That is not a breaking release's worth of value on its own.
4. The MCP ecosystem does have a working pattern for this (GitHub's server), and it does not require a major version. It requires a resolution layer and a window.

---

## RQ1. TDQS at the source

The spec lives at <https://tdqs.dev/spec>. Version **1.2, published 2026-09-01**. `verified at source` ([spec](https://tdqs.dev/spec), [changelog](https://tdqs.dev/changelog)).

What it scores (`verified at source`): how well a tool *definition* communicates to an agent. It is explicit that this is the definition, not runtime behaviour. Inputs are `name`, `title`, `description`, `inputSchema`, `outputSchema`, `annotations`, and sibling tool names.

Per-tool: six weighted dimensions scored 1–5 — Purpose Clarity 25%, Usage Guidelines 20%, Behavioral Transparency 20%, Parameter Semantics 15%, Conciseness & Structure 10%, Contextual Completeness 10%. Aggregated with integer half-up rounding (`round1`), not float `Math.round`. `verified at source`.

Server rollup (`verified at source`), quoted:

- `descriptionQualityScore = round1(0.6 × mean(TDQS) + 0.4 × min(TDQS))`
- `coherenceScore = round1((disambiguation + namingConsistency + toolCountAppropriateness + completeness) / 4)`
- `overallScore = round1(0.7 × descriptionQualityScore + 0.3 × coherenceScore)`

### The three ADR claims, tested

**Claim A — `descQuality = 0.6*mean + 0.4*min`, `overall = 0.7*descQuality + 0.3*coherence`.** `verified at source`, exactly as quoted above. The ADR got this one right. The spec also explains the 40% weight on the minimum is deliberate, so a single bad tool drags the server down.

**Claim B — tool-count bands 5 points at 3–15, 3 points at 16–25, 2 points at 26+.** `verified at source`, but with a date caveat the ADR omitted. The v1.2 anchors are: 5 = "well-scoped, each tool earns its place (typically 3-15 tools)"; 4 = "slightly over or under but reasonable"; 3 = "borderline (1-2 tools feels thin, 16-25 feels heavy)"; 2 = "too many (26+) or too few (1) for the apparent scope"; 1 = "extreme mismatch (50+ tools, or a single trivial tool)" ([tool count page](https://tdqs.dev/dimensions/tool-count-appropriateness)).

The caveat matters for this repo. The v1.2 changelog says the bands used to overlap at exactly 25, so a 25-tool server could land in either the 16–25 band or the 25+ band, and v1.2 fixed it: "The upper band now starts at 26." It also says "Only servers with exactly 25 tools are affected." `verified at source` ([changelog](https://tdqs.dev/changelog)). This server had exactly 25 tools. So the band question was genuinely ambiguous until 2026-09-01, and any pre-v1.2 score of `Tool Count` on a 25-tool server is not comparable to a v1.2 score.

**Claim C — a "single-direction enforceable boundary statement" scores full marks on Disambiguation.** `unknown` to `refuted`. The disambiguation rubric never mentions "Boundary:", "enforceable", or single-direction statements. Its anchors are purpose-overlap judgements only ([disambiguation page](https://tdqs.dev/dimensions/disambiguation)):

- 5 = "every tool has a clearly distinct purpose, no ambiguity"
- 4 = "mostly distinct, one or two could be confused"
- 3 = "some overlap exists but descriptions help"
- 2 = "multiple tools have unclear boundaries"
- 1 = "several tools appear to do the same thing"

The page's scoring guidance says a boundary must be *describable*, gives the example "to filter by user, use search_calls_extensive", and says a priority claim like "always call this first" is not a boundary and signals a tool-set problem. To earn a 5 it says: "Make purposes disjoint and say so in both descriptions, or collapse overlapping tools into one." `verified at source`.

So the ADR's mechanism claim is unsupported: a `Boundary:` line is one way to make purposes describable, not a scored artifact, and writing one cannot by itself lift Disambiguation to 5. What the rubric's own guidance offers instead is a two-option fork: disjoint descriptions, or collapse.

Also worth keeping: TDQS v1.1 added a shadowing flag (a tool whose purpose is substantially covered by a cheaper sibling) and the spec states it "changes no score" ([changelog](https://tdqs.dev/changelog)). If someone is looking for a *quantitative* overlap signal from TDQS, this is the only one, and it is deliberately score-neutral. `verified at source`.

A GitHub repo exists at <https://github.com/glama-ai/tool-definition-quality-score> and its README restates the same framework: six weighted dimensions, 70/30 rollup, and the explicit instruction not to lower disambiguation because a shadowing candidate pair was supplied. `verified at source`.

---

## RQ2. Measuring tool-selection error

Short answer: yes, methods exist, but **none of them measures an arbitrary MCP server's tool set out of the box**, and the ecosystem's most visible per-server score (TDQS) explicitly does not measure selection at all. `verified at source`.

What exists, and what each one actually measures:

| Method | What it measures | Fit for this question | Standing |
|---|---|---|---|
| [BFCL V4](https://gorilla.cs.berkeley.edu/leaderboard.html) | Function-call accuracy on a fixed function corpus; "the LLM's ability to call functions (aka tools) accurately"; overall accuracy is the unweighted average of sub-categories; leaderboard also reports per-run USD cost and latency. Runnable locally via `bfcl-eval` PyPI package with a pinned commit. | Fixed corpus, not *your* 25 tools. Useful as a regression floor, not as a measurement of your overlap. | `verified at source` |
| [MetaTool](https://arxiv.org/abs/2310.03128) | "whether LLMs have tool usage awareness and can correctly choose tools", incl. an explicit "tool selection with similar choices" subtask. Finds "the majority of them still struggle to effectively select tools" across eight LLMs. | Closest published construct to "9 sibling tools with overlapping purposes". Dataset is theirs, not yours. | `verified at source` |
| [τ-bench](https://github.com/sierra-research/tau-bench) | Multi-turn agent + simulated user + domain API tools and policy; reported as Pass^k. Locally runnable. | Measures end-to-end task success, not first-call routing. | `verified at source` |
| [MCPMark](https://github.com/eval-sys/mcpmark) | "stress-testing MCP benchmark" over 5 real MCP servers (Notion, GitHub, Filesystem, Postgres, Playwright), 127 tasks, `pass@1/pass@k/pass^k/avg@k`, sandboxed. | Real MCP servers, but each server's tools are fixed; you cannot point it at Maya. Its own README does not separate selection errors from grounding errors. | `verified at source` |
| [MCP-Universe](https://github.com/SalesforceAIResearch/MCP-Universe) | Real MCP servers across six domains, "large, unfamiliar tool spaces", evaluator-based pass/fail. | Framework for agent runs; no tool-selection metric defined. | `verified at source` |
| [MCPEval](https://github.com/SalesforceAIResearch/MCPEval) | Auto-generates tasks against a live MCP server, `--num-tasks`, bootstrap CIs. Multi-turn judge scores "clarification handling, context maintenance, tool usage efficiency, goal achievement, and response quality". | Closest thing to "run an eval against my own server". But no selection-correctness metric; needs the server running and API keys. | `verified at source` |
| [TDQS](https://tdqs.dev/spec) | Definition quality only. | **Not a selection measurement.** This is the limitation to state plainly whenever the 4/5 is quoted. | `verified at source` |

Cost, honestly: BFCL publishes a per-run USD estimate on its leaderboard (`verified at source`); the others publish no cost and cost whatever your model calls cost. A run against a 25-tool server with a handful of intents is tens of dollars at most, not thousands — but that is **my estimate**, `unknown`.

Ecosystem maturity: searching GitHub for MCP tool-selection evaluation surfaces only small hobby projects (a "tool-selection-lab" with 100 tools and 9 strategies, an "agent-tool-selection-tester" for how selection changes as names/descriptions/schemas/ordering change, both in single-digit stars). I found no de facto standard, and no registry-level harness. `verified at source` for the repos existing; `unknown` for "none exists anywhere".

### A minimal credible local measurement (my construction — this part is design, not citation)

1. **Unit.** One item = one user request plus the full 25-tool list; the outcome is whether the model's first `tools/call` names the intended tool. Binary.
2. **Ground truth.** An author writes N intents per tool *before* looking at which tool the description steers toward, then a second person assigns the intended tool. Otherwise the ground truth inherits the ambiguity you are trying to measure.
3. **Sample size.** 60 items for the one family under test, not 60 for all nine. Justification is statistical, not aesthetic: the rule of three says zero events in n trials bounds the rate at 3/n at 95%, so 30 clean trials can only prove "≤10%" and 60 can prove "≤5%" ([rule of three](https://en.wikipedia.org/wiki/Rule_of_three_(statistics)); original is Hanley & Lippman-Hand, *JAMA* 249:1743–5, cited there — `secondhand`).
4. **Report.** A 9×9 confusion matrix, per-pair misroute rate with Wilson 95% intervals, and the raw transcripts committed under `docs/evidence/probes/`, which is this repo's existing store for decision-grade artifacts ([docs/evidence/README.md](../evidence/README.md)).
5. **Argument correctness as a second axis.** After any merge, re-measure argument accuracy on the merged tool. D-094's constraint exists because conditional schemas hurt parameter accuracy; a merge that improves routing and degrades arguments is a net loss and a routing-only test cannot see it.

---

## RQ3. Prior art: merging and splitting MCP tools

### GitHub's official server — the closest and best-documented case

`verified at source` from release notes (via `gh api repos/github/github-mcp-server/releases`) and the in-repo guide.

- **v0.18.0 (2025-10-10)** — under a heading literally titled "Breaking changes", six pull-request tools (`get_pull_request`, `get_pull_request_files`, `get_pull_request_status`, `get_pull_request_diff`, `get_pull_request_reviews`, `get_pull_request_review_comments`) collapsed into `pull_request_read` with a `method` enum: `get`, `get_files`, `get_status`, `get_diff`, `get_reviews`, `get_review_comments`. The release note says "decreasing from 6 to 1 tools". ([v0.18.0](https://github.com/github/github-mcp-server/releases/tag/v0.18.0))
- **v0.20.0 (2025-10-27)** — same pattern for issues: four read tools into `issue_read`; `create_issue` + `update_issue` into `issue_write` with `method: create|update`; three sub-issue tools into `sub_issue_write` with `method: add|reprioritize|remove`. ([v0.20.0](https://github.com/github/github-mcp-server/releases/tag/v0.20.0))
- **v0.25.0 (2025-12-16)** — after the fact, "Add support for safe tool renaming". ([v0.25.0](https://github.com/github/github-mcp-server/releases/tag/v0.25.0))
- **v0.26.0 (2025-12-18)** — the [tool renaming guide](https://github.com/github/github-mcp-server/blob/main/docs/tool-renaming.md).

The guide is the single most useful artifact I found. Quoted: "When tools are renamed, users who have the old tool name in their MCP configuration (for example, in `X-MCP-Tools` headers for the remote MCP server or `--tools` flags for the local MCP server) would normally get errors. The deprecation alias system allows us to maintain backward compatibility by silently resolving old tool names to their new canonical names."

Mechanically it is a map in code: `var DeprecatedToolAliases = map[string]string{"old_tool_name": "new_tool_name"}`. The published alias table currently lists `get_issue` → `issue_read` and ~24 workflow/projects aliases. `verified at source`.

What they learned, stated as fact rather than inference: the breaking consolidation shipped **first**, in 0.x *minor* releases, with no aliases; the alias layer arrived roughly two months later. The release note for v0.25.0 does not call itself a fix for breakage, so I will not claim it was one — but the ordering is the pattern, and it is the pattern to avoid. `verified at source` for the ordering; `unknown` for whether user breakage drove it.

Staged rollout is also visible: **v0.30.0 (2026-01-26)** "Default to consolidated actions/projects toolsets and add hold back flag", then **v0.31.0 (2026-02-19)** "Remove old non-consolidated Actions and Projects toolsets". That is a ~3.5 week default-on window before deletion. `verified at source`.

And later still, **v1.5.0 (2026-06-27)** "Promote issue fields and deprecate legacy issue write tool" — the deprecation cycle continues well after the merge. `verified at source`.

### Playwright MCP — the split direction

`verified at source` from [release notes](https://github.com/microsoft/playwright-mcp/releases).

- **v0.0.72 (2026-04-30)** went *up* in count: `browser_network_requests` became a numbered list, and a "new `browser_network_request` tool" takes an index to fetch headers/body. The stated reason is payload size, not ambiguity.
- Same release renamed `browser_run_code` → `browser_run_code_unsafe`, "to make the sandbox-escape implication explicit". No alias mentioned in the note.

The lesson is the one that matters here: tool count is not the objective. They split a tool when the response payload was too large, and renamed one when the name under-described the risk. Neither change is about disambiguation, and neither was blocked on a major version.

### Cloudflare "Code Mode" — cited widely, weaker than it looks

`verified at source`: [blog.cloudflare.com/code-mode](https://blog.cloudflare.com/code-mode/). The post argues LLMs "are better at writing code to call MCP, than at calling MCP directly" and proposes converting an MCP server's schema into a TypeScript API executed in a sandbox.

Important correction to the folklore: the post gives **no tool-count numbers and no quantitative results**. Its only concrete example is `gitmcp.io/cloudflare/agents`, whose schema yields four callable functions. Any "Cloudflare cut 2,500 endpoints to 2 tools" claim is not in this source. Treat it as `unknown` unless someone produces the page that says it.

### Failure evidence

- GitHub's hosted server, Dec 2025: an SDK bump changed `serverInfo.icons[].sizes` from string to array and made the server "completely unusable with affected clients" until reverted — a reminder that clients are strict about the *shape* of `tools/list` payloads, not just tool names. ([issue #1644](https://github.com/github/github-mcp-server/issues/1644)) `verified at source`.
- I found no first-party post-mortem of a consolidation that was reverted. `unknown`, and I am not going to invent one.

---

## RQ4. Breaking-change practice

### What semver actually requires here

`verified at source`, [semver.org 2.0.0](https://semver.org/spec/v2.0.0.html):

- Rule 4: "Major version zero (0.y.z) is for initial development. Anything MAY change at any time."
- Rule 5: "Version 1.0.0 defines the public API."
- Rule 7 (minor): the minor version "MUST be incremented if any public API functionality is marked as deprecated."
- Rule 8: "Major version X (X.y.z | X > 0) MUST be incremented if any backward incompatible changes are introduced to the public API."

Consequence for this repo: at **0.8.0**, semver does not require a major bump for a breaking tool-surface change. The issue's premise — "a major version plus a migration path" — is only true once the project crosses 1.0.0. The ledger says the same thing in its own words, and it says more: see below.

### What the MCP protocol negotiates, and what it does not

`verified at source`, [specification: versioning and compatibility](https://modelcontextprotocol.io/specification/latest/basic/lifecycle):

- Every request declares its protocol version in `_meta`; on HTTP also via `MCP-Protocol-Version`.
- An unsupported version gets `UnsupportedProtocolVersionError` (code `-32022`) listing supported versions.
- Revisions are dated (`2026-07-28` and later are "modern"; `2025-11-25` and earlier are "legacy" `initialize`-handshake revisions); dual-era implementations may serve both.

What this means for tool names: protocol version negotiation covers *the protocol*, not the server's tool surface. Renaming `scene_snapshot` breaks nothing at the protocol layer and everything at the client-config layer. There is no version gate a client can use to ask for "the old tools". `verified at source` for the spec text; the inference is mine and I rank it `unknown`-risk only in the sense that nobody has published a contrary mechanism.

The one spec-level hook that does exist: `tools/list` may change over time, and servers that advertise `listChanged` SHOULD emit `notifications/tools/list_changed` ([server/tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)). Also normative there: tool names SHOULD be unique within a server, and 1–128 chars of `[A-Za-z0-9_.-]`. Nothing in the spec provides aliasing. GitHub's alias map is a server-side invention, not a protocol feature. `verified at source`.

### What the official registry requires

`verified at source`, [registry versioning doc](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/versioning.mdx):

- "MCP servers MUST define a version string in `server.json`."
- "The version string MUST be unique for each publication of the server. Once published, the version string (and other metadata) cannot be changed."
- Semver is recommended, not required; version *ranges* are prohibited as version strings.

And the [moderation policy](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/moderation-policy.mdx) is explicit that the registry will not police quality or tool surfaces: it removes only illegal content, malware, spam, and non-functioning servers, and it "**won't** remove" "low-quality or buggy servers". `verified at source`.

Net: the registry gives you immutability and a version string. It gives you no compatibility guarantee, no alias layer, and no protection from a rename. Every bit of migration safety is the server author's job.

### Real changelogs showing the practice

1. GitHub MCP server at 0.x, minor bumps, "Breaking changes" heading, alias layer added afterwards. `verified at source` (above).
2. Playwright MCP, 0.0.x, renames shipped in patch-level releases with the reason stated in the note. `verified at source` (above).
3. This repo itself, which is honest about the cost: `docs/threat-model.md` and the retired ledger both treat the tool surface as a frozen promise once 1.0.0 lands (D-131 in the ledger, cited below).

Deprecation-window length: I found no published minimum from the MCP project. GitHub's observed window from default-on to removal was ~3.5 weeks. `verified at source` for the interval; there is no norm to cite, and I am not going to manufacture one.

---

## RQ5. What first-party guidance says about granularity

### Anthropic, "Writing effective tools for agents"

`verified at source`, [anthropic.com/engineering/writing-tools-for-agents](https://www.anthropic.com/engineering/writing-tools-for-agents). Quoted:

- "More tools don't always lead to better outcomes."
- "We recommend building a few thoughtful tools targeting specific high-impact workflows"
- "Tools can consolidate functionality, handling potentially multiple discrete operations (or API calls) under the hood."
- "Instead of implementing a list_users, list_events, and create_event tools, consider implementing a schedule_event tool"
- "Make sure each tool you build has a clear, distinct purpose."
- "Too many tools or overlapping tools can also distract agents from pursuing efficient strategies."
- "Tracking tool calls can help reveal common workflows that agents pursue and offer some opportunities for tools to consolidate."
- On namespacing: "Namespacing (grouping related tools under common prefixes) can help delineate boundaries between lots of tools" and "We have found selecting between prefix- and suffix-based namespacing to have non-trivial effects".

Note what this does *not* say. It does not say to merge tools that take different argument shapes into one dispatch tool. Its examples are workflow-shaped merges (`schedule_event`, `get_customer_context`), not "one tool, nine modes". Anyone quoting this page as blanket endorsement of a `mode` parameter is reading past the text.

### OpenAI, function calling guide

`verified at source`, [developers.openai.com function calling](https://developers.openai.com/api/docs/guides/function-calling). Quoted:

- "Keep the number of initially available functions small for higher accuracy."
- "Aim for fewer than 20 functions available at the start of a turn at any one time, though this is just a soft suggestion."
- "Use tool search to defer large or infrequently used parts of your tool surface instead of exposing everything up front."
- "Combine functions that are always called in sequence." Example: "if you always call `mark_location()` after `query_location()`, just move the marking logic into the query function call."
- "Evaluate your performance with different numbers of functions."

The 20-tool soft cap is the only first-party number I found, and it is explicitly soft. This server at 25 is above it. Note the recommended remedy is *deferral*, not merging.

### TDQS, on the same question

`verified at source`, [tool count page](https://tdqs.dev/dimensions/tool-count-appropriateness): "Each tool should earn its place. Fold variants that differ only by a parameter into one tool with an enum." And: "An agent sees every tool at once" and a surface that is too wide "costs context and selection accuracy".

That is the sharpest published rule for this decision, and its condition is narrow: **fold variants that differ only by a parameter.** It endorses merging the homogeneous subset and says nothing about merging tools with different argument shapes.

### MCP spec / security best practices

`verified at source`, [server/tools](https://modelcontextprotocol.io/specification/2026-07-28/server/tools): tools are "uniquely identified by a name", names SHOULD be unique within a server, `tools/list` MAY change over time and clients SHOULD be told via `list_changed`. The spec says nothing about how many tools a server should expose, or whether to prefer a mode parameter. Anyone claiming the MCP spec mandates a tool count is `unknown` to me and I found no such text.

---

## RQ6. The number behind the issue

`verified at source`: the Glama listing [glama.ai/mcp/servers/@Xxx91n/mcp-for-maya](https://glama.ai/mcp/servers/@Xxx91n/mcp-for-maya) is readable without JavaScript. It shows:

- Overall **4.1/5.0**
- "Scored 2026-10-30 02:30 across 25 tools"
- **Disambiguation 4/5**
- Naming Consistency 4/5
- **Tool Count 3/5**
- Completeness 4/5

The tool count matches the issue's "25". The repo agrees: `llms.txt` is generated from the tool registry and lists exactly 25 tools, and its own section headers group nine of them under "Spatial awareness" (5), "Introspection" (2), and "Analysis" (2) — the nine `scene_*` tools the issue refers to. `verified at source` (local file `llms.txt`, generated from the registry at v0.8.0).

But the **Disambiguation score is 4/5, not 3/5**. The issue's "score 3/5 on description disambiguation" is not supported by the public page. Two possible readings, both `unknown`:

- the 3/5 was a pre-2026-10-30 run, or
- it was never the Disambiguation sub-score and got transposed with Tool Count (which *is* 3/5).

I could not distinguish these. What I can say: as of the most recent published scoring run, the premise "the nine `scene_*` tools score 3/5" is false at source, and `Tool Count 3/5` is real.

### The arithmetic nobody ran

Using the published rollup and the published sub-scores (`verified at source` for the formula; the arithmetic is mine, `unknown` in the sense that it is a derivation):

- Coherence now = (4 + 4 + 3 + 4) / 4 = 3.75 → 3.8.
- Overall 4.1 with coherence 3.8 implies descriptionQuality ≈ 4.2, since 0.7(4.2) + 0.3(3.8) = 4.08 → 4.1. Consistent.
- Merge to ≤15 tools: Tool Count 3 → 5, all else unchanged. Coherence = (4+4+5+4)/4 = 4.25 → 4.3. Overall = 0.7(4.2) + 0.3(4.3) = 4.23 → **4.2**.

The whole prize is **+0.1 overall, one point on one sub-score**. If any sub-score slips — and collapsing three tools into one will make "Naming Consistency" or "Completeness" arguable — the gain can vanish entirely. That is consistent with the ledger's own sunset clause: "Glama 调分带收益归零自动作废" (the P3 item auto-voids if the score-band gain goes to zero).

---

## The internal record (what the issue gets wrong about its own history)

The issue says the merge "was explicitly deferred because it is an API-breaking change that needs a major version plus a migration path." The retired ledger says the opposite. Read with:

```
git show '1c5befe^:docs/decision-ledger.md'
```

Entry **D-179** (R39-Q2', P3 deferral review) records the correction explicitly: the real reasons were D-094's heterogeneity ban (nine `scene_*` tools are heterogeneous; only homogeneous subsets are mergeable; the "25→15" target number is unproven and needs re-argument), a collision with an in-flight description batch, and gate bandwidth — "非「semver major 成本」（0.x breaking 合法，semver §4）", i.e. **not** the cost of a semver major, because 0.x breaking changes are legal. `verified at source` for the file contents; it is the project's own record.

D-179 also sets the trigger conditions, which is the part issue #80 should carry forward but does not:

- Unfreeze early if real-client misselection evidence appears, without waiting for the gate review.
- At gate review, decline the merge → P3 converts into a conditional debt with three triggers: Disambiguation still 3/5 after the Boundary batch **and** real client evidence of misselection; or the Glama band gain going to zero; or the tool surface passing ~35 tools and becoming a usability problem.
- Merging silently inside 1.x without a major, after 1.0.0, violates the freeze promise (D-131).

D-094 is the constraint that decides the shape of any merge: do not merge heterogeneous shapes into one composite tool, because "conditional schema hurts parameter accuracy"; the WordPress MCP merge formula only applies to homogeneous families; tool count 25 stays inside the "30 threshold safety zone". `verified at source`.

And the arithmetic that follows from it, which I did not find written down anywhere (`unknown`, my count from `llms.txt`):

- assert+validate → 1 saves 1; snapshot+inspect → 1 saves 1; aesthetics+review → 1 saves 1.
- checkpoint trio → 1 saves 2; the two image tools → 1 saves 1 (and would reverse D-003, which split them deliberately on cost grounds).
- Total: 25 → 19. **Not 15.** Reaching ~15 requires exactly the heterogeneous merges D-094 forbids.

That is the strongest single fact in this document after the 4/5 correction: the "25 → ~15" target and the "only homogeneous merges" constraint cannot both hold.

---

## What this means for the Maya server

A plan that is falsifiable, small, and does not presume the answer.

**1. Fix the premises before touching code.** Two claims in #80 are wrong at source: Disambiguation is 4/5, and the deferral was not about semver cost. Rewrite the issue to say what the ledger says, or the measurement will be aimed at a problem that does not exist. Cost: one edit.

**2. Measure the pairs the design says are confusable, not the nine.** Four pairs, chosen for argument-shape similarity (`verified at source` by reading the signatures in `src/maya_mcp_server/scene_tools.py`):

- `scene_assert(expectations: str)` vs `scene_validate(rules: str)` — both take one JSON string of checks, both return pass/fail with mismatches. The only genuinely homogeneous family in the set. If anything merges, this does.
- `scene_snapshot()` vs `scene_inspect(target: str)` — no-arg broad overview vs deep single-target. Heterogeneous; measure it, expect low confusion.
- `scene_aesthetics()` vs `scene_review()` — both no-arg whole-scene judgements returning scored findings. Second-best merge candidate.
- `scene_inspect(target)` vs `scene_describe(node)` — spatial vs API metadata. The pair most likely to be confused by *name* rather than purpose.

**3. Protocol.** 60 items per pair, 15 per tool per pair, written blind as in RQ2. Judge only the first tool call. Commit the confusion matrices and transcripts to `docs/evidence/probes/` with the date and model version in the filename, matching the existing `probe-*` convention. Run it on at least two clients — one Anthropic, one OpenAI — because the ledger's trigger says "real client", and one client's routing habits are not "real clients".

**4. Decision rule, stated before the run.**

- *Merge* a family only if all three hold: (a) the tools are parameter-homogeneous, i.e. they could be one tool with an enum per TDQS's "fold variants that differ only by a parameter"; (b) the measured misroute rate for that family has a 95% lower bound above 5% (roughly: 6 or more misroutes out of 60 clears it); (c) the post-merge argument-accuracy re-measurement does not drop.
- *Leave alone* if any of: misroutes ≤ 2/60 with no systematic pattern (which bounds the true rate near 5% by the rule of three and makes the +0.1 Glama delta the only upside); or the family is heterogeneous, because then the merge's failure mode moves from routing to arguments and a routing test cannot validate it; or the only candidate is the `checkpoint` trio or the image pair, both of which are documented decisions rather than accidents (D-007, D-003).
- *Retire the "~15" number* regardless of outcome. It is unreachable under the homogeneity constraint, and leaving it in the issue guarantees a merge debate that cannot be won or lost on evidence.

**5. If a merge is justified, migrate like GitHub did, not like GitHub's first attempt.**

- Register the consolidated tool *and* keep the old names, in the same release. In MCP that means two registrations pointing at one handler — there is no protocol alias mechanism, and the GitHub alias map resolves *client configuration* names, not calls.
- Add the alias map equivalent for `--tools`-style filters and document it in `docs/guide/`.
- Use a minor version at 0.x (semver rule 4 permits it), with the word "Breaking" in the changelog heading, exactly as GitHub's v0.18.0 did.
- Pick a removal window and publish it. GitHub's observed window was ~3.5 weeks and there is no published norm to lean on; I would use one full minor release plus 90 days, and I am flagging that as **my judgement, not a sourced rule**.
- Do not let 1.0.0 ship with both surfaces live. That is the one constraint the project's own D-131 freeze promise imposes.

**Where I am guessing.** The 5% floor, the 60-item sample, the 90-day window, the claim that two clients is enough, and the estimate that a run costs tens of dollars. None of them is sourced. They are choices that make the plan executable and falsifiable; each should be argued in the issue rather than inherited from this document.

---

## Sources

Opened and readable:

1. <https://tdqs.dev/spec> — spec, v1.2, 2026-09-01.
2. <https://tdqs.dev/> — site index, confirms v1.2 and the GitHub repo link.
3. <https://tdqs.dev/changelog> — v1.0 (2026-06-07), v1.1 (2026-08-23), v1.2 (2026-09-01); 25-tool band fix; rounding definition.
4. <https://tdqs.dev/dimensions/disambiguation> — five anchors, guidance, no mention of `Boundary:`.
5. <https://tdqs.dev/dimensions/tool-count-appropriateness> — five anchors with exact ranges, "fold variants… into one tool with an enum".
6. <https://github.com/glama-ai/tool-definition-quality-score> — repo README, framework restatement.
7. <https://glama.ai/mcp/servers/@Xxx91n/mcp-for-maya> — live score card: 4.1, 25 tools, Disambiguation 4/5, Tool Count 3/5, scored 2026-10-30.
8. <https://gorilla.cs.berkeley.edu/leaderboard.html> — BFCL V4 scope, metrics, local runnability.
9. <https://arxiv.org/abs/2310.03128> — MetaTool, "tool selection with similar choices".
10. <https://github.com/sierra-research/tau-bench> — τ-bench, Pass^k.
11. <https://github.com/eval-sys/mcpmark> — 127 tasks over 5 MCP servers.
12. <https://github.com/SalesforceAIResearch/MCP-Universe> — multi-domain MCP benchmark framework.
13. <https://github.com/SalesforceAIResearch/MCPEval> — task generation against a live server.
14. <https://en.wikipedia.org/wiki/Rule_of_three_(statistics)> — 3/n bound, Hanley & Lippman-Hand citation (`secondhand`).
15. <https://www.anthropic.com/engineering/writing-tools-for-agents> — consolidation and namespacing guidance.
16. <https://www.anthropic.com/engineering/code-execution-with-mcp> — tool-definition token cost; 150,000 → 2,000 tokens, 98.7%.
17. <https://developers.openai.com/api/docs/guides/function-calling> — "fewer than 20 functions", soft.
18. <https://blog.cloudflare.com/code-mode/> — code mode argument; contains no tool counts.
19. <https://semver.org/spec/v2.0.0.html> — rules 4, 5, 7, 8.
20. <https://modelcontextprotocol.io/specification/latest/basic/lifecycle> — per-request versioning, `UnsupportedProtocolVersionError`.
21. <https://modelcontextprotocol.io/specification/2026-07-28/server/tools> — tool identity, name rules, `list_changed`.
22. <https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/versioning.mdx> — version string immutable.
23. <https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/moderation-policy.mdx> — registry does not police tool quality.
24. <https://github.com/modelcontextprotocol/registry> — publishing via `mcp-publisher`, namespace auth.
25. <https://github.com/github/github-mcp-server/releases/tag/v0.18.0> — 6→1 `pull_request_read`, heading "Breaking changes".
26. <https://github.com/github/github-mcp-server/releases/tag/v0.20.0> — `issue_read`, `issue_write`, `sub_issue_write`.
27. <https://github.com/github/github-mcp-server/releases/tag/v0.25.0> — "Add support for safe tool renaming".
28. <https://github.com/github/github-mcp-server/releases/tag/v0.26.0> — renaming guide.
29. <https://github.com/github/github-mcp-server/releases/tag/v0.30.0> — default to consolidated toolsets plus hold-back flag.
30. <https://github.com/github/github-mcp-server/releases/tag/v0.31.0> — removal of old toolsets.
31. <https://github.com/github/github-mcp-server/releases/tag/v1.5.0> — deprecate legacy issue write tool.
32. <https://github.com/github/github-mcp-server/blob/main/docs/tool-renaming.md> — `DeprecatedToolAliases` map and current table.
33. <https://github.com/github/github-mcp-server/issues/1644> — hosted server broken by `icons.sizes` type change.
34. <https://github.com/microsoft/playwright-mcp/releases> — v0.0.72 split and rename.

Could not open (recorded as limitations, not filled with guesses):

- <https://modelcontextprotocol.io/registry/publish> — HTTP 404.
- <https://raw.githubusercontent.com/github/github-mcp-server/main/CHANGELOG.md> — HTTP 404; the repo has no `CHANGELOG.md`, release notes serve that role.
- <https://raw.githubusercontent.com/microsoft/playwright-mcp/main/CHANGELOG.md> — HTTP 404; same, no changelog file.
- Glama's own methodology page for how the coherence sub-scores are assigned was not opened; the sub-scores above are what the listing reports, and I did not verify the prompt or rubric version Glama applied on 2026-10-30. That is a real gap: `unknown` whether Glama used TDQS v1.2 for that run.

Local files read (this worktree, `fc243f9c`):

- `llms.txt` — 25 tools, grouped; generated from the registry at v0.8.0.
- `src/maya_mcp_server/scene_tools.py` — `Boundary:` lines, `scene_measure` already has a `mode` parameter, `scene_assert`/`scene_validate` signatures.
- `src/maya_mcp_server/introspect_tools.py` — `scene_describe`, `scene_nodes`.
- `docs/evidence/README.md` — artifact convention.
- The retired ledger, via `git show '1c5befe^:docs/decision-ledger.md'`, entries D-094 and D-179.
