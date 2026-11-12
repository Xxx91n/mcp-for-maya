"""Local checker: old words must not creep back into the project's prose.

`GLOSSARY.md` is the term standard. Every entry carries an `_Avoid_:` line
listing the words that entry replaced. This checker reads those lines, builds
an old-word -> new-word map, and reports every prose use of an old word with
file and line, so a rewrite cannot silently slide back.

What it reads -- tracked files only, so local scratch files and build output
never show up as findings:

* ``*.md``       prose only. Fenced code blocks and inline code spans are
                 skipped: they carry identifiers, paths, commands and literal
                 markers, and those stay exactly as they are.
* ``*.py``       comments and docstrings. Docstrings are the function and tool
                 descriptions the term cleanup has to reach; code and other
                 string literals are not prose.
* ``*.toml``, ``*.yaml``, ``*.yml``
                 full-line ``#`` comments only.

What it never reads, because those are records rather than prose to rewrite.
`SKIP_FILES` and `SKIP_PREFIXES` hold most of the membership; the
`[Unreleased]` window for ``CHANGELOG.md`` is applied in ``prose_lines_of``
because it is a line range, not a path:

* ``docs/reference/``       the historical shelf: the runbook body,
                            release-prep, and the archived verification script
* ``docs/evidence/``        evidence artifacts
* ``CHANGELOG.md`` outside the ``[Unreleased]`` section
                            released sections are point-in-time records
* ``llms.txt``              derived; regenerate it, never hand-edit
* ``mypy-baseline.txt``     generated
* ``GLOSSARY.md``           its `_Avoid_` lines are the source, not a target
* ``Vulnscan_results.md`` and ``.security-review-raw/``
                            security-audit evidence artifacts
* ``.github/assets-src/``   README/showcase image generators, out of the
                            PR0 map's scope

Two files PR0 proposed to skip are read on purpose: ``docs/upstream-issue-status.md``
(a live upstream-issue table) and ``docs/upstream-issue-response-drafts.md``
(a drafted reply). PR0 marked both "X -- proposed record skip, your decision".
Group 4 (#191) rewrote their wording instead of skipping them, so both now scan
clean; `SKIP_FILES` still leaves them out of the skip list, which keeps that
choice visible rather than silently inherited.

A hit is a LEAD, not a verdict. Three spellings carry a second, unrelated
meaning, and PR0's location table rules them out: the call record's
``append-only JSONL`` is file-append mode, a URL ``fragment anchor`` is not a
same-unit source file, and the Chinese word for "mirror" also names a
container image or a registry mirror, not the README translation. That
exclusion lives in ``OTHER_MEANING`` as data, and a test pins the set of
entries so a new one cannot be added unpinned.

Scope limits, disclosed rather than papered over:

* Only prose is read. Fenced code blocks, inline code spans, and string
  literals that are not docstrings (the instructions block in ``server.py``,
  for one) are not reported, so "every remaining use" is a claim this checker
  cannot make. The group tickets own those lines.
* A hit inside a table cell or a link is still a hit: the checker reads prose
  lines, not document structure.
* Markdown indentation is read by a rule, not a parser. A four-space line
  counts as indented code only when no list is open. Two shapes still read
  wrong: a code block indented deeper than a list item's own margin is read as
  prose, and a two-space continuation paragraph under a list item may be read
  as prose too. Both cost false positives, never a silent pass on a plain
  paragraph.
* ``docs/reference/real-maya-runbook.md`` is skipped whole, including the
  plain summary #192 added above its body.

Scope limit beyond prose: this is a local checker, not a CI gate. It is
deliberately not wired into ``.github/workflows/ci.yml`` and has no
gate-registry entry (issue #187). Its tests run with the normal pytest suite.

Invocation: ``python tools/check_plain_language.py [repo-root]``
Exit codes: 0 clean; 1 old words found; 2 GLOSSARY.md unreadable, or it carries
no `_Avoid_` lines to check.
"""

from __future__ import annotations

import ast
import io
import os
import re
import subprocess
import sys
import tokenize
from pathlib import Path


ENTRY = re.compile(r"^\*\*(.+?)\*\*")
AVOID_PREFIX = "_Avoid_"
AVOID_SPLIT = "、"
# A list item opens with a marker at any indent, so a nested item ("    - x")
# is still list prose and not an indented code block.
LIST_ITEM = re.compile(r"^(\s*)(?:[-*+]|\d{1,9}[.)])(?:\s|$)")

# A fence opens with three or more backticks or tildes and closes with the
# same character at the same length or longer. An info string may follow the
# OPENER (```bash), but a closer's marker may also be followed by an info
# string, which means ` ```python ` inside a block does not close it.
FENCE = re.compile(r"^(`{3,}|~{3,})")
FENCE_CLOSE = re.compile(r"^(`{3,}|~{3,})\s*$")

# Same word, different meaning. PR0's location table rules these out as
# unrelated, so a bare hit on them would send a rewrite after the wrong
# sentence. (term, phrase that covers the hit)
OTHER_MEANING = (
    ("append-only", re.compile(r"append-only\s+JSONL", re.IGNORECASE)),
    ("fragment", re.compile(r"fragment\s+anchor", re.IGNORECASE)),
    ("镜像", re.compile(r"(容器|推|下游|GitHub|Docker|官方)\s*镜像")),
)

SUFFIXES = {".md", ".py", ".toml", ".yaml", ".yml"}

# Environment variables that point git at a repository or index other than
# the one named by `-C`. Dropped before the child runs.
GIT_LOCATORS = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY")

SKIP_FILES = (
    "llms.txt",
    "mypy-baseline.txt",
    "Vulnscan_results.md",
    "GLOSSARY.md",
)

SKIP_PREFIXES = (
    "docs/reference/",  # historical shelf: runbook body, release-prep
    "docs/evidence/",  # evidence artifacts
    ".security-review-raw/",  # security-audit evidence artifacts
    ".github/assets-src/",  # README/showcase image generators, out of scope
)

WALK_SKIP_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache"}

# The replacement word for a term whose entry was deleted rather than rewritten.
DELETED = "（已删除）"


def split_avoid(line: str) -> list[str]:
    """Terms listed after `_Avoid_:`, split on the Chinese comma."""
    _, _, terms = line.partition(AVOID_PREFIX)
    terms = terms.lstrip(":")
    return [t.strip() for t in terms.split(AVOID_SPLIT) if t.strip()]


def load_avoid_map(glossary: Path) -> dict[str, str]:
    """old word -> new word, read from the glossary's `_Avoid_` lines.

    The new word is the entry heading the `_Avoid_` line belongs to. An
    `_Avoid_` line with no heading above it says the old words were deleted.
    """
    text = glossary.read_text(encoding="utf-8")
    avoid: dict[str, str] = {}
    current: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            current = None
            continue
        heading = ENTRY.match(stripped)
        if heading:
            current = heading.group(1).strip()
            continue
        if stripped.startswith(AVOID_PREFIX):
            for term in split_avoid(stripped):
                avoid.setdefault(term, current or DELETED)
    return avoid


# A term is inside a longer name when the neighbour chain has no space: `_`,
# a letter or a digit on the left; and on the right `_`, a letter/digit, or
# punctuation glued to one (`-budget`, `.json`, `/x`). Sentence punctuation
# is not a name edge, so a term followed by a full stop still reports.
RIGHT_EDGE = r"(?![A-Za-z0-9_])(?!-[A-Za-z0-9])(?!\.[A-Za-z0-9])(?!/[A-Za-z0-9])"


def term_pattern(term: str) -> re.Pattern[str]:
    """Match a term case-insensitively, whole-word, allowing a plural.

    A Chinese term gets no LEFT word edge, because Chinese prose puts no
    spaces between words. The right edge still applies to every term, so a
    spaced-out English or numeric tail after it is treated as a longer name.

    Scope limit: an ASCII term glued to another word by a hyphen
    (`monolith-wide`) reads as a name and is not reported. The shipped
    vocabulary has no such compound, and a false negative there costs less
    than a report on every correct filename citation.
    """
    left = r"(?<![A-Za-z0-9_])" if term[0].isascii() and term[0].isalnum() else ""
    plural = r"(?:s|es)?" if term[-1].isascii() and term[-1].isalpha() else ""
    return re.compile(left + re.escape(term) + plural + RIGHT_EDGE, re.IGNORECASE)


def strip_code_spans(line: str) -> str:
    """Remove CommonMark code spans, matching their delimiter runs by length.

    A span closes only on a run of the SAME length; the search for that closer
    skips every run of a different length, longer or shorter. A two-backtick
    span may hold a single backtick, and stopping there would put the code back
    in the prose.
    """
    out: list[str] = []
    pos = 0
    index = 0
    length = len(line)
    while index < length:
        if line[index] != "`":
            index += 1
            continue
        start = index
        while index < length and line[index] == "`":
            index += 1
        opening = index - start
        closing = -1
        end = -1
        probe = index
        while probe < length:
            if line[probe] != "`":
                probe += 1
                continue
            run_start = probe
            while probe < length and line[probe] == "`":
                probe += 1
            if probe - run_start == opening:
                closing = run_start
                end = probe
                break
        if closing < 0:
            continue  # no closer of this length: the run stays prose
        out.append(line[pos:start])
        out.append(" ")
        pos = end
        index = end  # resume after the closer, not inside the span
    out.append(line[pos:])
    return "".join(out)


def prose_lines(text: str) -> list[tuple[int, str]]:
    """Markdown lines with fenced and indented code blocks, and code spans, removed.

    A fence closes only on the same character at the same length or longer,
    and only on a marker followed by whitespace alone: ` ```python ` inside a
    block is content. A line indented four spaces or more is indented code only
    when no list is open: inside a list, four spaces is a nested item's own
    margin, so that line is prose. A fence at or left of the open item's indent
    ends the list, because a list item holds a fence only when it is indented
    under it.
    """
    out: list[tuple[int, str]] = []
    fence: str | None = None
    fence_indent = 0
    list_indent: int | None = None
    for number, line in enumerate(text.splitlines(), 1):
        body = line.lstrip(" ")
        indent = len(line) - len(body)
        if fence is not None:
            # A closer is checked before the indented-code skip, because a fence
            # held by a list item is indented with it. It may sit up to three
            # spaces deeper than the opener; deeper than that and it is sample
            # content, not a closer.
            closer = FENCE_CLOSE.match(body)
            if (
                closer
                and closer.group(1)[0] == fence[0]
                and len(closer.group(1)) >= len(fence)
                and indent <= fence_indent + 3
            ):
                fence = None
            continue
        if indent >= 4 and list_indent is None:
            continue
        opener = FENCE.match(body)
        # ```name``` on one line is a code span, not a fence: CommonMark
        # forbids a backtick in a backtick fence's info string.
        if opener and (opener.group(1)[0] != "`" or "`" not in body[opener.end() :]):
            fence = opener.group(1)
            fence_indent = indent
            if list_indent is not None and indent <= list_indent:
                list_indent = None
            continue
        item = LIST_ITEM.match(line)
        if item:
            list_indent = indent
        elif list_indent is not None and body.strip() and indent <= list_indent:
            list_indent = None
        out.append((number, strip_code_spans(line)))
    return out


def comment_lines(text: str) -> list[tuple[int, str]]:
    """Python comments, as (line number, comment) pairs."""
    # tokenize.tokenize, not the deprecated generate_tokens: the suite runs
    # with warnings-as-errors, and a deprecation notice would red the run.
    tokens = tokenize.tokenize(io.BytesIO(text.encode("utf-8")).readline)
    return [(t.start[0], t.string) for t in tokens if t.type == tokenize.COMMENT]


def docstring_lines(text: str) -> list[tuple[int, str]]:
    """Docstring lines of a Python module, mapped back to file line numbers.

    The literal starts on its node's `lineno` and its value's lines follow one
    for one, so a hit keeps the line number a reader can open.

    Scope limit: a docstring whose value contains escape sequences, or is built
    by implicit concatenation, splits on more lines than the source does, and
    its reported line drifts by that difference. Escaped newlines exist in this
    repo (``scene_tools.py`` and ``check_doc_claims.py`` both carry one) but
    neither drifts today; a docstring that starts to drift needs the
    tokenizer's own position instead.
    """
    tree = ast.parse(text)
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", [])
        if not body or not isinstance(body[0], ast.Expr):
            continue
        value = body[0].value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue
        for offset, line in enumerate(value.value.splitlines()):
            if line.strip():
                out.append((value.lineno + offset, strip_code_spans(line)))
    return out


def config_comment_lines(text: str) -> list[tuple[int, str]]:
    """Full-line `#` comments of a TOML/YAML file."""
    return [
        (number, line)
        for number, line in enumerate(text.splitlines(), 1)
        if line.lstrip().startswith("#")
    ]


def unreleased_window(text: str) -> tuple[int, int] | None:
    """0-based [start, end) of the `[Unreleased]` section, or None.

    Released sections are point-in-time records and are never re-checked, so
    only this window is read.
    """
    lines = text.splitlines()
    for start, line in enumerate(lines):
        if line.strip() == "## [Unreleased]":
            break
    else:
        return None
    for end in range(start + 1, len(lines)):
        if lines[end].startswith("## ["):
            return (start, end)
    return (start, len(lines))


def prose_lines_of(rel: str, text: str) -> list[tuple[int, str]]:
    """The lines of one file that count as prose."""
    suffix = Path(rel).suffix.lower()
    if suffix == ".md":
        lines = prose_lines(text)
        if rel == "CHANGELOG.md":
            window = unreleased_window(text)
            if window is None:
                return []
            first, last = window
            lines = [(n, line) for n, line in lines if first <= n - 1 < last]
        return lines
    if suffix == ".py":
        return comment_lines(text) + docstring_lines(text)
    return config_comment_lines(text)


def tracked_files(root: Path) -> set[str] | None:
    """Repo-relative paths git tracks, or None when this is not a git repo.

    `None` is not "everything is tracked": it means the caller cannot filter,
    and `scanned_files` says so in a warning. Local scratch files and build
    output are exactly what an unfiltered walk would wrongly report.

    Two details matter:
    * `-z` sends raw NUL-separated names. Without it git quotes and escapes
      non-ASCII paths, and a quoted name would never match the walk's path,
      so a tracked Chinese-named file would be silently skipped.
    * The repo-locating variables are removed from the child's environment.
      `git -C <root>` still honours `GIT_DIR`, `GIT_WORK_TREE` and
      `GIT_INDEX_FILE`, so a caller that has them set would list a DIFFERENT
      repository and the filter would drop files from this one.
    """
    env = {k: v for k, v in os.environ.items() if k not in GIT_LOCATORS}
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=env,
            check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return {name for name in result.stdout.split("\0") if name}


def scanned_files(root: Path) -> tuple[list[tuple[Path, str]], list[str], bool]:
    """(files to read, notes, complete).

    `complete` is False when a git repo could not be listed, because then the
    walk cannot filter and the result must not be reported as a clean pass.

    With git's list in hand this visits exactly those paths: a `rglob("*")`
    expands `.git` and `.venv` before any skip can apply, which costs seconds
    on a checkout this size for files that are never read anyway.
    """
    tracked = tracked_files(root)
    notes: list[str] = []
    complete = True
    if tracked is None:
        notes.append(f"{root} is not a git repo: reading every file, tracked or not")
        complete = False

    found: list[tuple[Path, str]] = []
    if tracked is not None:
        for rel in sorted(tracked):
            if Path(rel).suffix.lower() not in SUFFIXES:
                continue
            if rel in SKIP_FILES or rel.startswith(SKIP_PREFIXES):
                continue
            found.append((root / rel, Path(rel).as_posix()))
        return found, notes, complete

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES:
            continue
        rel = path.relative_to(root).as_posix()
        if any(part in WALK_SKIP_DIRS for part in rel.split("/")):
            continue
        if rel in SKIP_FILES or rel.startswith(SKIP_PREFIXES):
            continue
        found.append((path, rel))
    return found, notes, complete


def is_other_meaning(term: str, line: str, start: int, end: int) -> bool:
    """True when the hit sits inside a phrase that means something else."""
    for excluded_term, phrase in OTHER_MEANING:
        if excluded_term != term:
            continue
        for match in phrase.finditer(line):
            if match.start() <= start and end <= match.end():
                return True
    return False


def scan(root: Path, avoid: dict[str, str]) -> tuple[list[str], list[str], bool]:
    """(findings, notes, complete) — findings are `path:line: old -> new`.

    `complete` is False when a file could not be read or parsed, so `main`
    can tell "nothing found" apart from "did not finish looking".
    """
    patterns = [(term, term_pattern(term)) for term in sorted(avoid, key=len, reverse=True)]
    findings: list[str] = []
    files, notes, complete = scanned_files(root)
    for path, rel in files:
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            notes.append(f"{rel}: unreadable ({e})")
            complete = False
            continue
        try:
            lines = prose_lines_of(rel, text)
        except (tokenize.TokenError, SyntaxError, IndentationError) as e:
            notes.append(f"{rel}: prose unreadable ({e})")
            complete = False
            continue
        for number, line in lines:
            taken: list[tuple[int, int]] = []
            for term, pattern in patterns:
                for match in pattern.finditer(line):
                    span = (match.start(), match.end())
                    if any(span[0] < end and start < span[1] for start, end in taken):
                        continue
                    if is_other_meaning(term, line, *span):
                        continue
                    taken.append(span)
                    findings.append(f"{rel}:{number}: {match.group(0)} -> {avoid[term]}")
    return findings, notes, complete


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    root = Path(args[0]).resolve() if args else Path(__file__).resolve().parent.parent
    glossary = root / "GLOSSARY.md"
    try:
        avoid = load_avoid_map(glossary)
    except (OSError, UnicodeDecodeError) as e:
        print(f"::error::cannot read {glossary}: {e}")
        return 2
    if not avoid:
        print(f"::error::{glossary} carries no _Avoid_ lines to check")
        return 2

    findings, notes, complete = scan(root, avoid)
    print(f"loaded {len(avoid)} old words from GLOSSARY.md")
    for note in notes:
        print(f"::warning::{note}")
    for finding in findings:
        print(finding)
    if findings:
        print(
            f"\n{len(findings)} use(s) of an old word. Pick the plain wording from"
            " GLOSSARY.md, or add the word to its entry when the old word is a"
            " name that must stay."
        )
        return 1
    if not complete:
        print(
            "\nno old words found, but the scan did not finish: the warnings above"
            " name the files it could not read. That is not a clean pass."
        )
        return 2
    print("no old words found")
    return 0


if __name__ == "__main__":
    sys.exit(main())
