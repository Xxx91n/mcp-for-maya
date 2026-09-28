"""Regression tests for .github/scripts/check_pypi_index.py.

D-142gamma: the simple index is the install-resolution truth surface —
asserted in BOTH serializations (PEP 691 JSON + HTML; pip negotiates
either). Missing in both = install face broken (highest severity);
missing in only one = CDN serialization split (still red, honestly
worded — D-139 residue class). The project-JSON lane catches API drift.
All lanes fail loud: transport errors and non-200s are red, never
silently skipped.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "check_pypi_index.py"


def _load():
    spec = importlib.util.spec_from_file_location("check_pypi_index", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _simple(versions):
    return 200, json.dumps({"versions": versions, "files": []})


def _simple_html(versions):
    anchors = "".join(
        f'<a href="x">mcp_for_maya-{v}-py3-none-any.whl</a>\n'
        f'<a href="y">mcp_for_maya-{v}.tar.gz</a>\n'
        for v in versions
    )
    return 200, f"<html><body>{anchors}</body></html>"


def _project(version):
    return 200, json.dumps({"info": {"name": "mcp-for-maya", "version": version}})


class FakeFetch:
    """Routes (url, accept) -> (status, body); missing = transport error."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, accept):
        self.calls.append((url, accept))
        return self.routes.get((url, accept), (0, "no route"))


def _routes(simple=None, project=None, simple_html=None):
    """simple/simple_html take a version list or an explicit (status,
    body) tuple; simple_html=None mirrors the simple lane (an index that
    is down is down in both serializations)."""
    mod = _load()
    simple_url = mod.SIMPLE_URL.format(package="mcp-for-maya")
    sj = _simple(simple) if isinstance(simple, list) else (simple or (0, "unset"))
    if simple_html is None:
        sh = _simple_html(simple) if isinstance(simple, list) else sj
    else:
        sh = _simple_html(simple_html) if isinstance(simple_html, list) else simple_html
    return {
        (simple_url, mod.PEP691_ACCEPT): sj,
        (simple_url, mod.HTML_ACCEPT): sh,
        (mod.JSON_URL.format(package="mcp-for-maya"), "application/json"): project or (0, "unset"),
    }


def test_both_green_is_clean():
    mod = _load()
    fetch = FakeFetch(_routes(["0.3.0", "0.4.0"], _project("0.4.0")))
    assert mod.probe("mcp-for-maya", "0.4.0", fetch) == []
    accepts = {a for _, a in fetch.calls}
    assert {mod.PEP691_ACCEPT, mod.HTML_ACCEPT} <= accepts


def test_missing_in_both_serializations_is_highest_severity():
    mod = _load()
    fetch = FakeFetch(_routes(["0.3.0"], _project("0.4.0")))
    problems = mod.probe("mcp-for-maya", "0.4.0", fetch)
    assert len(problems) == 1
    assert "BOTH serializations" in problems[0] and "highest severity" in problems[0]


def test_json_stale_html_fresh_is_split_not_broken():
    mod = _load()
    fetch = FakeFetch(_routes(["0.3.0"], _project("0.4.0"), simple_html=["0.3.0", "0.4.0"]))
    problems = mod.probe("mcp-for-maya", "0.4.0", fetch)
    assert len(problems) == 1
    assert "CDN split" in problems[0]
    assert "highest severity" not in problems[0]


def test_simple_unusable_is_red():
    mod = _load()
    fetch = FakeFetch(_routes((503, "maintenance"), _project("0.4.0")))
    problems = mod.probe("mcp-for-maya", "0.4.0", fetch)
    assert any("unusable" in p and "503" in p for p in problems)


def test_json_drift_with_green_simple_is_secondary_lane():
    mod = _load()
    fetch = FakeFetch(_routes(["0.4.0"], _project("0.3.0")))
    problems = mod.probe("mcp-for-maya", "0.4.0", fetch)
    assert len(problems) == 1
    assert "info.version=0.3.0" in problems[0] and "API drift" in problems[0]


def test_json_non_200_is_red():
    mod = _load()
    fetch = FakeFetch(_routes(["0.4.0"], (404, "")))
    problems = mod.probe("mcp-for-maya", "0.4.0", fetch)
    assert any("project JSON HTTP 404" in p for p in problems)


def test_all_lanes_red_reported_independently():
    mod = _load()
    fetch = FakeFetch(_routes((503, ""), (503, "")))
    # simple JSON + simple HTML + project JSON = three independent reds
    assert len(mod.probe("mcp-for-maya", "0.4.0", fetch)) == 3


def test_version_sort_is_numeric_not_lexical():
    mod = _load()
    assert mod._latest({"0.4.0", "0.10.0", "0.3.0"}) == "0.10.0"


def test_html_version_parsing():
    mod = _load()
    _, body = _simple_html(["0.3.0", "0.4.0"])
    assert mod._versions_from_html(body, "mcp-for-maya") == {"0.3.0", "0.4.0"}
    assert mod._versions_from_html("not html", "mcp-for-maya") is None


def test_main_without_latest_tag_is_misuse(monkeypatch):
    mod = _load()
    monkeypatch.delenv("LATEST_TAG", raising=False)
    assert mod.main() == 2
