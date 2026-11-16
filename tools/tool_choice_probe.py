"""Measure how often a model picks the wrong one of two similar Maya tools.

The pair under test is ``scene_assert`` and ``scene_validate``. Both take a
single JSON string and both answer pass/fail, so a request can be steered to
either one. The question this probe answers is whether a real client actually
misroutes that pair, and how often.

Design, fixed before the first run:

* One item is one user request plus the server's full tool list. The outcome is
  the name of the model's first tool call: the expected tool, a different tool
  (a misroute), or no call at all.
* The items and their ``expected`` labels live in ``tool_choice_items.json``,
  written before any run. Labels are frozen: the decision rule recorded in the
  issue is applied to the number this probe prints, and neither is re-tuned
  afterwards.
* Sixty items, thirty per tool. They mix the plainly separable cases with the
  ones sitting on the semantic boundary - an exact expected value versus a
  limit the scene must respect.
* The tool list is read from the live server in this checkout, so the model
  sees the same names, descriptions and schemas a client would see, including
  the ``Boundary:`` lines.

Run it with the judge endpoint taken from the environment::

    uv run python tools/tool_choice_probe.py --out report.json

The report is a measurement artifact, not a gate. It is never wired into CI:
the exit code is 0 whenever the run completes, whatever the misroute count.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


BASE_URL_ENV = "R18_JUDGE_BASE_URL"
API_KEY_ENV = "R18_JUDGE_API_KEY"
DEFAULT_MODEL = "claude-haiku-5-5"
ITEMS_FILE = Path(__file__).with_name("tool_choice_items.json")

SYSTEM_PROMPT = (
    "You operate Autodesk Maya through the tools provided. Read the user's "
    "request and call exactly one tool that best fits it. Do not ask "
    "clarifying questions; pick the closest tool and call it."
)


async def tool_payload() -> list[dict[str, Any]]:
    """Read the live tool list and shape it as OpenAI-style function schemas."""
    from maya_mcp_server.server import mcp

    listed = await mcp.list_tools()
    out: list[dict[str, Any]] = []
    for tool in listed:
        params = tool.parameters or {"type": "object", "properties": {}}
        out.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": params,
                },
            }
        )
    return out


def load_items(path: Path) -> list[dict[str, str]]:
    """Read the frozen item set."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list) or not raw:
        raise SystemExit(f"{path}: expected a non-empty JSON list")
    return raw


def post(
    base: str, key: str, body: dict[str, Any], timeout: float = 120.0, attempts: int = 6
) -> dict[str, Any]:
    """Send one chat-completions request and return the decoded reply.

    Rate limits and gateway outages are retried with a widening wait; the
    request is not idempotent in principle, but a 429 or 503 means the
    upstream never started the call, so a retry cannot double-count an item.
    """
    data = json.dumps(body).encode("utf-8")
    wait = 5.0
    for attempt in range(1, attempts + 1):
        req = urllib.request.Request(
            base.rstrip("/") + "/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                # This gateway answers 403 to urllib's default
                # "Python-urllib/x.y" agent and 200 to a named one.
                "User-Agent": "maya-mcp-server-tool-choice-probe/1.0",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts:
                raise
            print(f"  {exc.code} upstream, retrying in {wait:.0f}s", file=sys.stderr)
        except (urllib.error.URLError, TimeoutError):
            if attempt == attempts:
                raise
            print(f"  transport error, retrying in {wait:.0f}s", file=sys.stderr)
        time.sleep(wait)
        wait = min(wait * 2, 120.0)
    raise SystemExit("unreachable")


def first_call(reply: dict[str, Any]) -> tuple[str | None, str]:
    """Return (tool name, finish reason) for the reply's first tool call."""
    choices = reply.get("choices") or []
    if not choices:
        return None, "empty"
    message = choices[0].get("message") or {}
    calls = message.get("tool_calls") or []
    if not calls:
        return None, str(choices[0].get("finish_reason") or "no_tool_call")
    name = (calls[0].get("function") or {}).get("name")
    return name, str(choices[0].get("finish_reason") or "")


def ask(
    base: str, key: str, model: str, request: str, tools: list[dict[str, Any]]
) -> tuple[str | None, str]:
    """Put one request to the model with the full tool list."""
    body = {
        "model": model,
        # No temperature field: this judge rejects any non-default value,
        # and the report records that the run used the endpoint default.
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request},
        ],
        "tools": tools,
        "tool_choice": "auto",
    }
    return first_call(post(base, key, body))


def summarise(
    records: list[dict[str, Any]],
    model: str,
    tools_offered: int,
    seed: int,
    base: str,
    items_file: str,
    variant: str,
) -> dict[str, Any]:
    """Build the report body from the per-item records.

    ``sibling_misroutes`` counts the case this probe is about: the model picked
    the other tool of the tested pair. Misroutes to anything else are recorded
    separately, because a model that answers the same unrelated tool every time
    is biased or too weak, and that is not evidence about this pair.

    ``meta`` and ``claim_boundary`` are required by ``docs/evidence/README.md``
    for anything that lands in the evidence store.
    """
    total = len(records)
    misroutes = [r for r in records if r["verdict"] == "misroute"]
    no_calls = [r for r in records if r["verdict"] == "no_call"]
    pair = {"scene_assert", "scene_validate"}
    pairs: dict[str, int] = {}
    sibling = 0
    for record in misroutes:
        name = f"{record['expected']} -> {record['actual']}"
        pairs[name] = pairs.get(name, 0) + 1
        if record["actual"] in pair:
            sibling += 1
    actuals = [r["actual"] for r in records if r["actual"]]
    return {
        "probe": "tool choice: scene_assert versus scene_validate",
        "date": "2026-11-16",
        "model": model,
        "seed": seed,
        "tools_offered": tools_offered,
        "items": total,
        "correct": total - len(misroutes) - len(no_calls),
        "misroute": len(misroutes),
        "sibling_misroute": sibling,
        "no_call": len(no_calls),
        "misroute_rate": round(len(misroutes) / total, 4) if total else 0.0,
        "sibling_misroute_rate": round(sibling / total, 4) if total else 0.0,
        "misroute_pairs": pairs,
        "first_position_picks": sum(1 for r in records if r.get("chosen_index") == 0),
        "distinct_tools_chosen": len(set(actuals)),
        "meta": {
            "date": "2026-11-16",
            "host": platform.platform(),
            "python": sys.version.split()[0],
            "pid": os.getpid(),
            "endpoint_host": urllib.parse.urlsplit(base).netloc,
            "model": model,
            "seed": seed,
            "script": "tools/tool_choice_probe.py",
            "items_file": items_file,
            "temperature": "endpoint default; this judge rejects a non-default value",
            "tools_source": "maya_mcp_server.server.mcp.list_tools() at HEAD of the run tree",
            "variant": variant,
        },
        "claim_boundary": (
            "Supports: for the model in meta, on these 60 written requests, with the "
            "tool order reshuffled per item, which tool the first call named. Does not "
            "support: any statement about other models or about real client "
            "applications, any general claim that the two tools are or are not "
            "confusable, or anything about argument correctness."
        ),
        "records": records,
    }


def build_arm_b(
    tools: list[dict[str, Any]], tool_name: str, description: str, append: str
) -> list[dict[str, Any]]:
    """Return a copy of the tool list with one tool's description changed.

    A non-empty ``append`` extends the shipped description; a non-empty
    ``description`` replaces it. One of the two, never both, so an arm tests a
    single edit.
    """
    out: list[dict[str, Any]] = []
    for tool in tools:
        fn = tool["function"]
        if fn["name"] != tool_name:
            out.append(tool)
            continue
        if append:
            changed = f"{fn.get('description') or ''}\n\n{append}"
        else:
            changed = description
        out.append({"type": "function", "function": {**fn, "description": changed}})
    return out


def summarise_ab(records: list[dict[str, Any]], watched: str) -> dict[str, Any]:
    """Per-arm count of how often the watched tool was the first call."""
    arms: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        arms.setdefault(str(record["arm"]), []).append(record)
    out: dict[str, Any] = {}
    for arm, rows in sorted(arms.items()):
        picks = sum(1 for r in rows if r["actual"] == watched)
        out[arm] = {
            "observations": len(rows),
            "watched_tool_picks": picks,
            "watched_tool_share": round(picks / len(rows), 4) if rows else 0.0,
        }
    per_item: dict[str, dict[str, int]] = {}
    for record in records:
        slot = per_item.setdefault(str(record["id"]), {})
        if record["actual"] == watched:
            slot[str(record["arm"])] = slot.get(str(record["arm"]), 0) + 1
    out["per_item_watched_picks"] = per_item
    return out


def run(args: argparse.Namespace, base: str, key: str, tools: list[dict[str, Any]]) -> int:
    """Run the items, optionally over two arms, with repeats.

    Both arms see the same shuffled order for a given item and repeat, so the
    watched tool sits in the same position in both and position bias cancels
    instead of becoming noise.
    """
    items = load_items(Path(args.items))
    if args.ids:
        wanted = {x.strip() for x in args.ids.split(",") if x.strip()}
        missing = wanted - {i["id"] for i in items}
        if missing:
            print(f"unknown ids: {sorted(missing)}", file=sys.stderr)
            return 2
        items = [i for i in items if i["id"] in wanted]
    arms: dict[str, list[dict[str, Any]]] = {"A": tools}
    if args.ab_tool:
        arms["B"] = build_arm_b(tools, args.ab_tool, args.ab_description, args.ab_append)
    names = [t["function"]["name"] for t in tools]
    records: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        for repeat in range(args.repeats):
            order = list(names)
            random.Random(args.seed + index).shuffle(order)
            for arm, arm_tools in arms.items():
                by_name = {t["function"]["name"]: t for t in arm_tools}
                offered = [by_name[name] for name in order]
                try:
                    actual, finish = ask(base, key, args.model, item["request"], offered)
                except urllib.error.HTTPError as exc:
                    detail = exc.read().decode("utf-8", "replace")[:300]
                    print(f"{item['id']}/{arm}/{repeat} HTTP {exc.code}: {detail}", file=sys.stderr)
                    return 1
                except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                    print(f"{item['id']}/{arm}/{repeat} failed: {exc}", file=sys.stderr)
                    return 1
                expected = item["expected"]
                if actual is None:
                    verdict = "no_call"
                elif actual == expected:
                    verdict = "correct"
                else:
                    verdict = "misroute"
                records.append(
                    {
                        **item,
                        "arm": arm,
                        "repeat": repeat,
                        "actual": actual,
                        "verdict": verdict,
                        "finish_reason": finish,
                        "chosen_index": order.index(actual) if actual in order else None,
                        "expected_index": order.index(expected) if expected in order else None,
                    }
                )
                print(f"{item['id']} r{repeat} arm{arm} {verdict:8s} actual={actual}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "date": "2026-11-16",
        "host": platform.platform(),
        "python": sys.version.split()[0],
        "pid": os.getpid(),
        "endpoint_host": urllib.parse.urlsplit(base).netloc,
        "model": args.model,
        "seed": args.seed,
        "script": "tools/tool_choice_probe.py",
        "items_file": args.items,
        "items_used": [i["id"] for i in items],
        "repeats": args.repeats,
        "arms": sorted(arms),
        "ab_tool": args.ab_tool,
        "ab_description": args.ab_description,
        "ab_append": args.ab_append,
        "temperature": "endpoint default; this judge rejects a non-default value",
        "tools_source": "maya_mcp_server.server.mcp.list_tools() at HEAD of the run tree",
        "variant": args.variant,
    }
    boundary = (
        "Supports: for the model in meta, on these written requests, with the tool "
        "order reshuffled per item, which tool the first call named, and how that "
        "differs between the two arms over the stated repeats. Does not support: any "
        "statement about other models or real client applications, anything about "
        "argument correctness, or any claim about the tool surface beyond the items "
        "listed in meta."
    )
    if len(arms) == 1:
        report = summarise(
            records, args.model, len(tools), args.seed, base, args.items, args.variant
        )
    else:
        report = {
            "probe": "tool choice: watched-tool share across two arms",
            "date": "2026-11-16",
            "model": args.model,
            "seed": args.seed,
            "items": len(items),
            "repeats": args.repeats,
            "ab_tool": args.ab_tool,
            "ab_description": args.ab_description,
            "meta": meta,
            "claim_boundary": boundary,
            "ab": summarise_ab(records, args.ab_tool or ""),
            "arms": {
                arm: summarise(
                    [r for r in records if r["arm"] == arm],
                    args.model,
                    len(tools),
                    args.seed,
                    base,
                    args.items,
                    f"arm {arm}: {args.variant}",
                )
                for arm in sorted(arms)
            },
            "records": records,
        }
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if len(arms) == 1:
        print(
            f"\n{report['items']} items: correct={report['correct']} "
            f"misroute={report['misroute']} no_call={report['no_call']}"
        )
        print(f"misroute rate={report['misroute_rate']} pairs={report['misroute_pairs']}")
    else:
        for arm, stats in report["ab"].items():
            if arm == "per_item_watched_picks":
                continue
            print(f"arm {arm}: {stats['watched_tool_picks']}/{stats['observations']} watched")
        print(f"per item: {report['ab']['per_item_watched_picks']}")
    print(f"report -> {out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments, load the tool list, run the items."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", default=os.environ.get("TOOL_CHOICE_MODEL", DEFAULT_MODEL))
    parser.add_argument("--items", default=str(ITEMS_FILE))
    parser.add_argument("--ids", default="", help="comma-separated item ids to run")
    parser.add_argument("--out", default="tool-choice-report.json")
    parser.add_argument("--seed", type=int, default=80)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--ab-tool", default="", help="tool whose description arm B replaces")
    parser.add_argument("--ab-description", default="", help="description arm B uses for it")
    parser.add_argument(
        "--ab-append", default="", help="text arm B appends to that tool description"
    )
    parser.add_argument("--variant", default="as shipped")
    args = parser.parse_args(argv)
    base = os.environ.get(BASE_URL_ENV)
    key = os.environ.get(API_KEY_ENV)
    if not base or not key:
        print(f"set {BASE_URL_ENV} and {API_KEY_ENV} first", file=sys.stderr)
        return 2
    if bool(args.ab_description) and bool(args.ab_append):
        print("pick --ab-description or --ab-append, not both", file=sys.stderr)
        return 2
    if args.ab_tool and not (args.ab_description or args.ab_append):
        print("--ab-tool needs a description or an append", file=sys.stderr)
        return 2
    tools = asyncio.run(tool_payload())
    print(f"{len(tools)} tools offered")
    return run(args, base, key, tools)


if __name__ == "__main__":
    raise SystemExit(main())
