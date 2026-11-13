"""Pins for tools/check_plain_language.py (issue #187).

The checker's whole job is one sentence: an old word listed on a GLOSSARY
``_Avoid_:`` line must not appear in current prose, and historical records are
exempt. Three behaviours carry that, and each one here is paired with its
control so a checker that fires on everything is as visible as one that fires
on nothing:

* an active doc using an old word fails, with file and line;
* the same old word in a historical path passes, because the record stays;
* a clean doc passes.

Extra pins cover the boundaries the checker would otherwise get wrong quietly:
the CHANGELOG's ``[Unreleased]`` window, inline code spans (identifier names
never count as prose), and `_Avoid_` terms whose ASCII word edges must not fire
inside a longer name.

The checker is deliberately NOT a CI gate, so there is no gate-registry entry
and no workflow wiring to test. Its tests run with the normal pytest suite.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "tools" / "check_plain_language.py"

GLOSSARY = """# GLOSSARY

## 验证与事务

**场景存档（checkpoint）**: 把当前场景导出成磁盘文件。
_Avoid_: 内存快照、in-memory snapshot

**读档（rollback）**: 打开一个存档。
_Avoid_: 回滚
"""


def _load():
    spec = importlib.util.spec_from_file_location("check_plain_language", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


M = _load()


def _repo(tmp_path: Path, *, doc: str, name: str = "NOTES.md") -> Path:
    """A miniature repo: the glossary plus one active doc."""
    (tmp_path / "GLOSSARY.md").write_text(GLOSSARY, encoding="utf-8")
    (tmp_path / name).write_text(doc, encoding="utf-8")
    return tmp_path


def _clean_env() -> dict[str, str]:
    """The child environment a temporary-repo git command needs.

    A test can be started from a git hook, where GIT_DIR points at the real
    repository. `git -C <tmp>` does not override that, so `init`/`add` here
    would touch the caller's index instead of the temporary repo.
    """
    return {k: v for k, v in os.environ.items() if k not in M.GIT_LOCATORS}


def _git(root: Path) -> Path:
    """Turn a miniature repo into a real one, so the tracked-file path is used."""
    for args in (["init"], ["add", "-A"]):
        subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            env=_clean_env(),
            check=True,
        )
    return root


def test_an_active_doc_with_an_old_word_fails(tmp_path):
    """The control for every skip rule: an old word in plain prose is reported."""
    root = _repo(tmp_path, doc="写入前先做一张内存快照。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == ["NOTES.md:1: 内存快照 -> 场景存档（checkpoint）"]


def test_a_historical_path_with_the_same_word_is_skipped(tmp_path):
    """A record keeps its words; only the path decides, not the word."""
    root = _repo(tmp_path, doc="")
    historical = root / "docs" / "reference" / "old-audit.md"
    historical.parent.mkdir(parents=True)
    historical.write_text("当年写的是内存快照。\n", encoding="utf-8")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == []


def test_a_clean_doc_passes(tmp_path):
    root = _repo(tmp_path, doc="写入前先做一张场景存档。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == []


def test_main_reports_old_words_and_exits_one(tmp_path, capsys):
    root = _repo(tmp_path, doc="这里会回滚到上一个存档。\n")
    assert M.main([str(root)]) == 1
    out = capsys.readouterr().out
    assert "NOTES.md:1: 回滚 -> 读档（rollback）" in out


def test_main_exits_zero_on_a_clean_tree(tmp_path, capsys):
    root = _git(_repo(tmp_path, doc="这里会读档到上一个存档。\n"))
    assert M.main([str(root)]) == 0
    assert "no old words found" in capsys.readouterr().out


def test_a_released_changelog_section_is_skipped(tmp_path):
    """Released sections are records; the unreleased lane is still checked."""
    root = _repo(tmp_path, doc="")
    (root / "CHANGELOG.md").write_text(
        "# Changelog\n\n## [Unreleased]\n\n- 加了内存快照。\n\n"
        "## [0.7.0]\n\n- 早就有的内存快照。\n",
        encoding="utf-8",
    )
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == ["CHANGELOG.md:5: 内存快照 -> 场景存档（checkpoint）"]


def test_an_inline_code_span_is_not_prose(tmp_path):
    """A name in backticks is an identifier, and identifiers never rename."""
    root = _repo(tmp_path, doc="调用 `in-memory snapshot` 这个函数名。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == []


def test_an_ascii_old_word_does_not_fire_inside_a_longer_name(tmp_path):
    """`monolith` must not match `check_monolith_budget`: the name stays."""
    (tmp_path / "GLOSSARY.md").write_text(
        "**单文件大模块**: 很大的单文件。\n_Avoid_: monolith\n", encoding="utf-8"
    )
    (tmp_path / "NOTES.md").write_text(
        "跑 .github/scripts/check_monolith_budget.py 和 monolith-budget.json。\n",
        encoding="utf-8",
    )
    findings, _, _ = M.scan(tmp_path, M.load_avoid_map(tmp_path / "GLOSSARY.md"))
    assert findings == []


def test_a_sentence_final_hit_still_reports(tmp_path):
    """A period is not a name edge: `The audit log.` is prose, not a filename."""
    (tmp_path / "GLOSSARY.md").write_text(
        "**调用记录**: 每次调用写一行。\n_Avoid_: audit log\n", encoding="utf-8"
    )
    (tmp_path / "NOTES.md").write_text(
        "- The audit log. It records what happened.\n", encoding="utf-8"
    )
    findings, _, _ = M.scan(tmp_path, M.load_avoid_map(tmp_path / "GLOSSARY.md"))
    assert findings == ["NOTES.md:1: audit log -> 调用记录"]


def test_a_plural_hit_still_reports(tmp_path):
    """`net-zero side effects` carries the term; the trailing s is not a name."""
    (tmp_path / "GLOSSARY.md").write_text(
        "**改完复原**: 结束时恢复原样。\n_Avoid_: net-zero side effect\n", encoding="utf-8"
    )
    (tmp_path / "NOTES.md").write_text("render_preview net-zero side effects.\n", encoding="utf-8")
    findings, _, _ = M.scan(tmp_path, M.load_avoid_map(tmp_path / "GLOSSARY.md"))
    assert findings == ["NOTES.md:1: net-zero side effects -> 改完复原"]


def test_a_python_docstring_is_prose_but_a_plain_string_is_not(tmp_path):
    """Function descriptions are prose; an unrelated literal is not."""
    (tmp_path / "GLOSSARY.md").write_text(
        "**读档（rollback）**: 打开一个存档。\n_Avoid_: 回滚\n", encoding="utf-8"
    )
    (tmp_path / "mod.py").write_text(
        '"""Module: 回滚 goes through the entry point."""\n'
        "def f():\n"
        '    """旧的说法：回滚"""\n'
        "    return 1\n"
        "\n"
        'LABEL = "回滚"\n',
        encoding="utf-8",
    )
    findings, _, _ = M.scan(tmp_path, M.load_avoid_map(tmp_path / "GLOSSARY.md"))
    assert findings == ["mod.py:1: 回滚 -> 读档（rollback）", "mod.py:3: 回滚 -> 读档（rollback）"]


def test_python_comments_are_read_but_code_is_not(tmp_path):
    """Old words in a code comment are prose; in a string literal they are not."""
    (tmp_path / "GLOSSARY.md").write_text(
        "**读档（rollback）**: 打开一个存档。\n_Avoid_: 回滚\n", encoding="utf-8"
    )
    (tmp_path / "mod.py").write_text("# 旧的说法：回滚\nLABEL = '回滚'\n", encoding="utf-8")
    findings, _, _ = M.scan(tmp_path, M.load_avoid_map(tmp_path / "GLOSSARY.md"))
    assert findings == ["mod.py:1: 回滚 -> 读档（rollback）"]


def test_a_fenced_code_block_is_not_prose(tmp_path):
    """A code sample keeps the words it shows; only surrounding prose counts."""
    root = _repo(tmp_path, doc="```bash\n# 回滚\n```\n正文里也会读档。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == []


def test_a_double_backtick_code_span_is_one_span(tmp_path):
    """A two-backtick delimiter keeps its contents out; single pairs do not split it."""
    root = _repo(tmp_path, doc="正文 ``回滚`` 结束，而 `回滚` 也是代码。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == []


def test_a_span_with_an_inner_single_backtick_is_one_span(tmp_path):
    """A two-backtick span may hold a single backtick, and it stays one span."""
    root = _repo(tmp_path, doc="正文 ``回滚`x`` 结束。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == []


def test_a_word_between_two_code_spans_still_reports(tmp_path):
    """Spans are matched one at a time; the cursor must resume after each closer."""
    root = _repo(tmp_path, doc="正文 `x` 回滚 `y` 结束。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == ["NOTES.md:1: 回滚 -> 读档（rollback）"]


def test_an_unclosed_block_at_the_end_is_read_as_prose(tmp_path):
    """A bad guess about the end of a block must not hide the rest of the file."""
    root = _repo(tmp_path, doc="   ```\n    ```\n   ```\n回滚\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == ["NOTES.md:4: 回滚 -> 读档（rollback）"]


def test_a_closer_one_space_deeper_than_its_opener_still_closes(tmp_path):
    """The three-space allowance is relative to the opener, not to column zero."""
    root = _repo(tmp_path, doc="- 步骤\n\n    ```\n    x\n     ```\n回滚\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == ["NOTES.md:6: 回滚 -> 读档（rollback）"]


def test_an_indented_fence_marker_inside_a_block_is_content(tmp_path):
    """A closer may sit three spaces deep at most; four is part of the sample."""
    root = _repo(tmp_path, doc="```text\n    ```\n回滚\n```\n正文里的回滚会被报告。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == ["NOTES.md:5: 回滚 -> 读档（rollback）"]


def test_a_fence_indented_under_a_nested_item_still_closes(tmp_path):
    """A closer is looked for at any indent, or the fence swallows the prose after it."""
    root = _repo(tmp_path, doc="- 外层\n    - 内层\n\n    ```\n    x\n    ```\n回滚\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == ["NOTES.md:7: 回滚 -> 读档（rollback）"]


def test_a_fence_after_a_list_ends_the_list(tmp_path):
    """A flush-left fence cannot live inside an item, so the next indented block is code."""
    root = _repo(tmp_path, doc="- 步骤\n\n```\nx\n```\n\n    回滚\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == []


def test_a_nested_list_item_is_prose(tmp_path):
    """Inside a list, four spaces is a nested item, not an indented code block."""
    root = _repo(tmp_path, doc="- 步骤\n    - 回滚\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == ["NOTES.md:2: 回滚 -> 读档（rollback）"]


def test_a_four_backtick_fence_is_not_closed_by_three(tmp_path):
    """A four-backtick block may contain ```; the prose after the real close is read."""
    root = _repo(tmp_path, doc="````md\n```\n回滚\n```\n````\n正文里的回滚会被报告。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == ["NOTES.md:6: 回滚 -> 读档（rollback）"]


def test_a_tilde_fence_is_a_fence(tmp_path):
    """`~~~` fences exist in CommonMark; a backtick-only reader reports their contents."""
    root = _repo(tmp_path, doc="~~~\n回滚\n~~~\n正文里也会读档。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == []


def test_a_fence_closes_only_on_its_own_character(tmp_path):
    """A ``` inside a ~~~ block is content, so the block stays closed until ~~~."""
    root = _repo(tmp_path, doc="~~~\n```\n回滚\n~~~\n正文里也会读档。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == []


def test_a_fence_with_an_info_string_does_not_close_a_block(tmp_path):
    """` ```python ` inside a block is a line of the sample, not its end."""
    root = _repo(tmp_path, doc="```\n```python\n回滚\n```\n正文里也会读档。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == []


def test_a_fence_indented_four_spaces_is_not_a_fence(tmp_path):
    """Four-space indentation is an indented code block, so its content is code."""
    root = _repo(tmp_path, doc="    ```\n    回滚\n    ```\n正文里也会读档。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == []


def test_an_unreadable_file_never_reports_a_clean_pass(tmp_path, capsys):
    """A scan that skipped a file did not finish, so exit 0 would be a false pass."""
    root = _git(_repo(tmp_path, doc="这里会读档。\n"))
    (root / "mod.py").write_text("def broken(:\n    pass\n", encoding="utf-8")
    subprocess.run(
        ["git", "-C", str(root), "add", "-A"],
        capture_output=True,
        env=_clean_env(),
        check=True,
    )
    assert M.main([str(root)]) == 2
    out = capsys.readouterr().out
    assert "did not finish" in out


def test_a_line_starting_with_a_code_span_is_not_a_fence(tmp_path):
    """`` ```name``` `` is a code span; CommonMark forbids backticks in a fence's info string."""
    root = _repo(tmp_path, doc="```回滚``` 后面的正文不能被当成围栏。\n第二行的回滚要报。\n")
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == ["NOTES.md:2: 回滚 -> 读档（rollback）"]


def test_a_word_with_a_second_meaning_is_not_reported(tmp_path):
    """The call record appends to a file and a URL has an anchor; neither renames."""
    (tmp_path / "GLOSSARY.md").write_text(
        "**调用记录**: 每次调用写一行。\n_Avoid_: audit log\n"
        "**资产目录只增不删**: 只加新文件。\n_Avoid_: append-only\n"
        "**同一个注入模块里的单独文件**: 另开一个文件。\n_Avoid_: fragment\n",
        encoding="utf-8",
    )
    (tmp_path / "NOTES.md").write_text(
        "调用记录是 append-only JSONL；链接用 fragment anchor 定位；真正的 audit log 会被报告。\n",
        encoding="utf-8",
    )
    findings, _, _ = M.scan(tmp_path, M.load_avoid_map(tmp_path / "GLOSSARY.md"))
    assert findings == ["NOTES.md:1: audit log -> 调用记录"]


def test_a_deleted_word_still_reports_with_no_replacement(tmp_path):
    """An `_Avoid_` line under a heading, with no entry above it, means deleted."""
    (tmp_path / "GLOSSARY.md").write_text(
        "# GLOSSARY\n\n## 已删除的说法\n\n这两条删了。\n\n_Avoid_: 脏场景守卫\n",
        encoding="utf-8",
    )
    (tmp_path / "NOTES.md").write_text("旧的脏场景守卫写法。\n", encoding="utf-8")
    findings, _, _ = M.scan(tmp_path, M.load_avoid_map(tmp_path / "GLOSSARY.md"))
    assert findings == ["NOTES.md:1: 脏场景守卫 -> （已删除）"]


def test_a_word_listed_twice_binds_to_its_first_entry(tmp_path):
    """`setdefault` keeps the first heading, so a shared word keeps one target."""
    (tmp_path / "GLOSSARY.md").write_text(
        "**同一个注入模块里的单独文件**: 另开一个文件。\n_Avoid_: 巨石\n"
        "**单文件大模块**: 很大的单文件。\n_Avoid_: 巨石\n",
        encoding="utf-8",
    )
    avoid = M.load_avoid_map(tmp_path / "GLOSSARY.md")
    assert avoid["巨石"] == "同一个注入模块里的单独文件"


def test_a_glossary_with_no_avoid_lines_is_refused(tmp_path, capsys):
    """An empty map would pass everything, so it stops instead of passing."""
    (tmp_path / "GLOSSARY.md").write_text(
        "# GLOSSARY\n\n**读档**: 打开一个存档。\n", encoding="utf-8"
    )
    assert M.main([str(tmp_path)]) == 2
    assert "no _Avoid_ lines" in capsys.readouterr().out


def test_an_untracked_file_is_not_read_in_a_git_repo(tmp_path, monkeypatch):
    """Only tracked files are prose; local scratch must not show up as findings."""
    root = _repo(tmp_path, doc="正文里也会读档。\n")
    scratch = root / "scratch.md"
    scratch.write_text("这是回滚草稿。\n", encoding="utf-8")
    monkeypatch.setattr(M, "tracked_files", lambda _root: {"GLOSSARY.md", "NOTES.md"})
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == []


def test_a_non_git_root_is_read_but_never_called_a_clean_pass(tmp_path, capsys):
    """No git means no filter, so the run says so and refuses to claim success."""
    root = _repo(tmp_path, doc="正文里也会读档。\n")
    (root / "README.md").write_text("这里会读档。\n", encoding="utf-8")
    assert M.main([str(root)]) == 2
    out = capsys.readouterr().out
    assert "not a git repo" in out
    assert "did not finish" in out


def test_the_real_repo_loads_the_glossary_and_skips_the_records():
    """The live tree: a real map, every exempt path silent, every skip stated."""
    avoid = M.load_avoid_map(REPO / "GLOSSARY.md")
    assert len(avoid) > 100, "GLOSSARY.md carries far fewer _Avoid_ terms than expected"
    findings, notes, _ = M.scan(REPO, avoid)
    assert notes == [], notes
    for exempt in M.SKIP_FILES:
        assert not [f for f in findings if f.startswith(exempt)], exempt
    for exempt in M.SKIP_PREFIXES:
        assert not [f for f in findings if f.startswith(exempt)], exempt
    assert all(":" in f for f in findings)


def test_every_other_meaning_is_pinned():
    """Each entry in OTHER_MEANING has a test here; a new entry without one is a hole."""
    pinned = {"append-only", "fragment", "镜像"}
    assert {term for term, _ in M.OTHER_MEANING} == pinned


def test_a_mirror_that_means_a_container_image_is_not_reported(tmp_path):
    """`容器镜像` and `下游镜像` are Docker words; `便利性镜像` is the retired term."""
    (tmp_path / "GLOSSARY.md").write_text(
        "**中文译本**: 英文原稿是唯一准稿。\n_Avoid_: 镜像\n", encoding="utf-8"
    )
    (tmp_path / "NOTES.md").write_text(
        "服务器必须是容器镜像；下游镜像有同步缺口。便利性镜像才是旧词。\n", encoding="utf-8"
    )
    findings, _, _ = M.scan(tmp_path, M.load_avoid_map(tmp_path / "GLOSSARY.md"))
    assert findings == ["NOTES.md:1: 镜像 -> 中文译本"]


def test_a_tracked_file_with_a_chinese_name_is_read(tmp_path, monkeypatch):
    """`git ls-files` quotes non-ASCII names by default; -z sends them raw."""
    root = _repo(tmp_path, doc="正文里也会读档。\n")
    chinese = root / "说明.md"
    chinese.write_text("这里会回滚。\n", encoding="utf-8")
    monkeypatch.setattr(M, "tracked_files", lambda _root: {"GLOSSARY.md", "NOTES.md", "说明.md"})
    findings, _, _ = M.scan(root, M.load_avoid_map(root / "GLOSSARY.md"))
    assert findings == ["说明.md:1: 回滚 -> 读档（rollback）"]


def test_tracked_files_ignores_repo_locators_in_the_environment(tmp_path, monkeypatch):
    """A stray GIT_DIR must not redirect the listing at another repository."""
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "a.md").write_text("正文。\n", encoding="utf-8")
    for args in (["init"], ["add", "a.md"]):
        subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            env=_clean_env(),
            check=True,
        )

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.setenv("GIT_DIR", str(elsewhere))

    assert M.tracked_files(repo) == {"a.md"}
