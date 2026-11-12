# Security Policy

## Scope

mcp-for-maya is a **local, single-user** bridge between an MCP client
and Autodesk Maya. The guards against slips (validation, rate limits,
pattern scan, call record) catch accidents and agents that were talked
into doing something the user never asked for — see
[docs/threat-model.md](docs/threat-model.md). They are not a boundary
against a malicious MCP client: any client can already ask for arbitrary
tool calls by design.

## Reporting a vulnerability

Please report suspected vulnerabilities **privately** — do not open a
public issue for exploitable problems.

- GitHub: use the repository's **Security → Report a vulnerability**
  (private advisory) flow.
- Or email the maintainer listed in the repository profile.

Include: affected version/commit, reproduction steps, and what the
impact looks like from the client's seat.

## What counts as a vulnerability here

In scope:
- A bug that lets a *confused but non-malicious* agent cause damage the
  guards against slips were designed to catch (e.g., path traversal in a
  filename parameter reaching the filesystem).
- Call record corruption or silent loss of rejection events.
- userSetup.py merge writing outside the one maintained block or without backup.
- Checkpoint/rollback writing outside the checkpoints directory.

Out of scope (by design):
- "A connected MCP client can run arbitrary code in Maya" — true and
  intended; the client is trusted.
- Bypassing the regex pattern scan with an obfuscated payload — the scan
  is documented as detection-only.
- Maya command-port exposure on localhost — that is Maya's own model.

## Response

We aim to acknowledge reports within a few days. Fixes land on the main
branch and are noted in the changelog; credit in release notes unless
you prefer anonymity.
