"""D-072 README mirror skeleton check.

README.md is the English source-of-truth; README.zh-CN.md is its
convenience mirror. Mirrors may lag, never diverge: the heading
skeleton (level sequence, order) must match 1:1 so a stale mirror is
detectable. Titles differ by language - only structure is compared.

Also verifies the mirror contract markers:
- README.md starts with the language selector (EN bold, zh linked)
- README.zh-CN.md carries the synced-with anchor comment pointing at
  the EN commit it mirrors
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent.parent


def skeleton(path: Path) -> list[int]:
    """Ordered list of heading levels (1-6) - language-agnostic shape.

    Fenced code blocks are stripped first: Python comments like
    "# comment" would otherwise masquerade as H1 headings.
    """
    text = re.sub(r"^```.*?^```", "", path.read_text(encoding="utf-8"), flags=re.M | re.S)
    return [len(m.group(1)) for m in re.finditer(r"^(#{1,6})\s", text, re.M)]


def check(repo: Path) -> list[str]:
    """Findings for one repo root. Empty list == mirror is in sync.

    Takes the root as an argument, and prints nothing, so a pin can hand it a
    corrupted tmp_path copy and assert a NON-EMPTY red (D-213 1/2). The other
    checkers in this family already have this shape; this one used to resolve
    the repo inline inside main(), which left a real gate unpinnable.
    """
    findings: list[str] = []
    en = repo / "README.md"
    zh = repo / "README.zh-CN.md"
    if not en.exists() or not zh.exists():
        return ["README.md or README.zh-CN.md missing"]

    en_text = en.read_text(encoding="utf-8")
    zh_text = zh.read_text(encoding="utf-8")

    if "**English** | [简体中文](README.zh-CN.md)" not in en_text:
        findings.append("README.md missing top language selector")
    if "[English](README.md) | **简体中文**" not in zh_text:
        findings.append("README.zh-CN.md missing top language selector")
    if not re.search(r"synced-with:\s*README\.md\s*@\s*[0-9a-f]{7,40}", zh_text):
        findings.append("README.zh-CN.md missing synced-with anchor comment")

    en_sk, zh_sk = skeleton(en), skeleton(zh)
    if en_sk != zh_sk:
        findings.append(f"README heading skeleton divergence: EN {en_sk} vs zh {zh_sk}")
    return findings


def main() -> int:
    findings = check(REPO)
    for finding in findings:
        print(f"::error::{finding}")
    if findings:
        return 1
    print(
        f"README skeleton OK: {len(skeleton(REPO / 'README.md'))} headings match 1:1 "
        "(levels identical, order identical)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
