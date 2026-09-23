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


def skeleton(path: Path) -> list[int]:
    """Ordered list of heading levels (1-6) - language-agnostic shape.

    Fenced code blocks are stripped first: Python comments like
    "# comment" would otherwise masquerade as H1 headings.
    """
    text = re.sub(r"^```.*?^```", "", path.read_text(encoding="utf-8"), flags=re.M | re.S)
    return [
        len(m.group(1))
        for m in re.finditer(r"^(#{1,6})\s", text, re.M)
    ]


def main() -> int:
    repo = Path(__file__).resolve().parent.parent.parent
    en = repo / "README.md"
    zh = repo / "README.zh-CN.md"
    if not en.exists() or not zh.exists():
        print("::error::README.md or README.zh-CN.md missing")
        return 1

    en_text = en.read_text(encoding="utf-8")
    zh_text = zh.read_text(encoding="utf-8")

    failed = False
    if "**English** | [简体中文](README.zh-CN.md)" not in en_text:
        print("::error::README.md missing top language selector")
        failed = True
    if "[English](README.md) | **简体中文**" not in zh_text:
        print("::error::README.zh-CN.md missing top language selector")
        failed = True
    if not re.search(
        r"synced-with:\s*README\.md\s*@\s*[0-9a-f]{7,40}", zh_text
    ):
        print(
            "::error::README.zh-CN.md missing synced-with anchor comment"
        )
        failed = True

    en_sk, zh_sk = skeleton(en), skeleton(zh)
    if en_sk != zh_sk:
        failed = True
        print("::error::README heading skeleton divergence")
        print(f"  EN ({len(en_sk)} headings): {en_sk}")
        print(f"  zh ({len(zh_sk)} headings): {zh_sk}")
    else:
        print(
            f"README skeleton OK: {len(en_sk)} headings match 1:1 "
            "(levels identical, order identical)"
        )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
