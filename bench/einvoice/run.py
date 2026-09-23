"""Run the benchmark (protocol: bench/einvoice/PROTOCOL.md): every task in every arm — without the yoke, the yoke with the
official rules, the yoke with the rules and the order — `--reps` times; one JSON line per run, every delivered invoice kept
for review; then the report — exact counts, paired tests, costs.

    python -m bench.einvoice.judges --setup                                         # once: the schema, the validator command
    python -m bench.einvoice.run --model scripted                                   # offline dry run: checks the harness, measures nothing
    python -m bench.einvoice.run --model anthropic:claude-haiku-4-5 --arms with_order --only order-01,order-02,order-03,order-04,order-05   # pilot of the third arm
    python -m bench.einvoice.run --model anthropic:claude-haiku-4-5 --reps 2         # the full run: 50 tasks × 3 arms × 2
    python -m bench.einvoice.run --report bench/einvoice/results/<run>.jsonl       # the report of a finished run
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.callbacks import UsageMetadataCallbackHandler
from langchain_core.messages import AIMessage, ToolMessage

from bench.einvoice.agent import ARMS, INVOICE_PATH, ScriptedInvoiceModel, build_agent, task_message
from bench.einvoice.grade import grade
from bench.einvoice.judges import RULES_VERSION, VALIDATOR_DIGEST, validator
from bench.einvoice.orders import load_orders
from bench.einvoice.stats import holm, mcnemar_exact, paired_bootstrap, wilson

RESULTS = Path(__file__).resolve().parent / "results"
# USD per million tokens: input, output, cache read, cache write — list prices (Anthropic first-party API), for an estimate only
PRICES = {"claude-sonnet-5": (2.00, 10.00, 0.20, 2.50), "claude-opus-5": (5.00, 25.00, 0.50, 6.25), "claude-haiku-4-5": (1.00, 5.00, 0.10, 1.25)}
# the paired comparisons of the primary endpoint (protocol, deviation 4): H1 and H4 are tested, Holm-adjusted; the third is exploratory
COMPARISONS = (("without", "with", "H1"), ("without", "with_order", "H4"), ("with", "with_order", "exploratory"))
RED_FLAG = "red flag: "


class _Checks:
    """The yoke's telemetry, kept in memory: how many checks it ran, and how long they took."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def event(self, **fields: Any) -> None:
        self.events.append(fields)


def _model(spec: str, order: dict) -> Any:
    if spec == "scripted":
        return ScriptedInvoiceModel(order=order)
    from langchain.chat_models import init_chat_model
    # a whole invoice plus adaptive thinking is a long answer: stream it, so no request hits the HTTP client's timeout
    return init_chat_model(spec, max_tokens=32000, streaming=True)


def _usage(messages: list[Any], counted: UsageMetadataCallbackHandler) -> dict[str, int]:
    """Tokens over every model call of the run — a callback sees the calls no message of the main thread records."""
    u = {"input_tokens": 0, "output_tokens": 0, "cache_read": 0, "cache_write": 0,
         "model_calls": sum(1 for m in messages if isinstance(m, AIMessage))}
    for meta in counted.usage_metadata.values():
        details = meta.get("input_token_details") or {}
        u["input_tokens"] += meta.get("input_tokens", 0)
        u["output_tokens"] += meta.get("output_tokens", 0)
        u["cache_read"] += details.get("cache_read", 0) or 0
        u["cache_write"] += details.get("cache_creation", 0) or 0
    return u


def _cost(model: str, u: dict[str, int]) -> float | None:
    price = PRICES.get(model.split(":")[-1])
    if price is None:
        return None
    p_in, p_out, p_read, p_write = price
    uncached = max(u["input_tokens"] - u["cache_read"] - u["cache_write"], 0)   # usage input_tokens includes the cached parts
    return round((uncached * p_in + u["output_tokens"] * p_out + u["cache_read"] * p_read + u["cache_write"] * p_write) / 1e6, 4)


def _written(messages: list[Any]) -> list[str]:
    """The invoice contents the agent tried to write, in order."""
    return [c["args"].get("content", "") for m in messages if isinstance(m, AIMessage) for c in (m.tool_calls or [])
            if c["name"] == "write_file" and c["args"].get("file_path", "").lstrip("/") == INVOICE_PATH.lstrip("/")]


def _flags(messages: list[Any]) -> list[str]:
    """The categories of every red flag the yoke returned, in order: official rule ids, or order.* from the delta oracles."""
    return [c for m in messages if isinstance(m, ToolMessage) and str(m.content).startswith(RED_FLAG)
            for c in str(m.content)[len(RED_FLAG):].split(" — ", 1)[0].split(", ")]


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run_one(spec: str, order: dict, arm: str, rep: int, keep: Path | None, commit: str = "") -> dict[str, Any]:
    record: dict[str, Any] = {"model": spec, "arm": arm, "rep": rep, "task": order["id"], "scenario": order["scenario"], "commit": commit}
    checks, counted = _Checks(), UsageMetadataCallbackHandler()
    t0 = time.perf_counter()
    try:
        agent = build_agent(_model(spec, order), arm=arm, order=order, telemetry=checks)
        out = agent.invoke({"messages": [{"role": "user", "content": task_message(order)}]},
                           config={"configurable": {"thread_id": f"{order['id']}-{arm}-{rep}"}, "recursion_limit": 60,
                                   "callbacks": [counted]})
    except Exception as e:  # noqa: BLE001 — an API error is recorded, the benchmark goes on
        return {**record, "error": f"{type(e).__name__}: {str(e)[:300]}", "seconds": round(time.perf_counter() - t0, 1)}
    seconds = round(time.perf_counter() - t0, 1)
    messages = out["messages"]
    data = out.get("files", {}).get(INVOICE_PATH)
    xml = data.get("content") if isinstance(data, dict) else data
    xml = "\n".join(xml) if isinstance(xml, list) else xml
    attempts = _written(messages)
    usage = _usage(messages, counted)
    executed = [m for m in messages if isinstance(m, ToolMessage) and m.name == "write_file"
                and not str(m.content).startswith("Tool call limit exceeded")]
    record.update(grade(order, xml))
    first = grade(order, attempts[0]) if attempts else grade(order, None)
    record.update({
        "first_correct": first["correct"], "first_valid": first["valid"], "first_schema_valid": first["schema_valid"],
        "first_right": first["right"], "first_agree": first["agree"], "first_order_agree": first["order_agree"],
        "first_keyross_order": first["keyross_order"], "first_mismatches": first["mismatches"],
        "writes": len(executed), "write_attempts": len(attempts),
        "task_calls": sum(1 for m in messages if isinstance(m, AIMessage) for c in (m.tool_calls or []) if c["name"] == "task"),
        "pit_stops": sum(1 for m in messages if isinstance(m, ToolMessage) and "red flag" in str(m.content)), "flags": _flags(messages),
        "yoke_checks": len(checks.events), "yoke_check_ms": sum(e.get("duration_ms", 0) for e in checks.events),
        **usage, "tokens": usage["input_tokens"] + usage["output_tokens"], "cost_usd": _cost(spec, usage), "seconds": seconds,
    })
    if keep is not None and xml:
        (keep / f"{order['id']}-{arm}-{rep}.xml").write_text(xml, encoding="utf-8")
    return record


def _log(f: Any, r: dict[str, Any]) -> None:
    f.write(json.dumps(r, ensure_ascii=False) + "\n"); f.flush()
    status = r.get("error") or ("correct" if r["correct"] else
                                f"valid={r['valid']} schema={r['schema_valid']} right={r['right']} delivered={r['delivered']}")
    print(f"  {r['task']} {r['arm']:<10} rep {r['rep']}{' (retry)' if r.get('retry') else ''}: {status}"
          + (f" · ${r['cost_usd']}" if r.get("cost_usd") else ""))


# -- the report ----------------------------------------------------------------------------------------------------

def _share(xs: list[bool]) -> str:
    k, n = sum(xs), len(xs)
    if not n:
        return "—"
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({100 * k / n:.0f} %, CI {100 * lo:.0f}–{100 * hi:.0f})"


def _mean(xs: list[float], digits: int = 1) -> str:
    return f"{statistics.fmean(xs):.{digits}f}" if xs else "—"


def _table(arms: list[str], rows: list[tuple[str, Callable[[str], str]]], first: str = "") -> list[str]:
    """A markdown table with one column per arm."""
    return ([f"| {first} | " + " | ".join(ARMS[a] for a in arms) + " |", "|---" * (len(arms) + 1) + "|"]
            + [f"| {name} | " + " | ".join(cell(a) for a in arms) + " |" for name, cell in rows])


def report(path: Path) -> str:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [r for r in rows if "error" not in r]                      # a successful retry replaces its failed run
    by_arm = {arm: {(r["task"], r["rep"]): r for r in ok if r["arm"] == arm} for arm in ARMS}
    arms = [arm for arm in ARMS if by_arm[arm]]
    keys = sorted(set.intersection(*(set(by_arm[a]) for a in arms))) if arms else []   # a lost run takes its block out of every arm
    runs = {(r["task"], r["arm"], r["rep"]) for r in rows}
    lost = len(runs - {(r["task"], r["arm"], r["rep"]) for r in ok})
    out = [f"# einvoice benchmark — {path.name}", "",
           f"{len(runs)} runs · {len(rows) - len(ok)} API error(s), {lost} run(s) lost after the retry · {len(keys)} complete blocks "
           f"(task, repetition) over {len(arms)} arm(s) · model {', '.join(sorted({r['model'] for r in rows}))} · "
           f"commit {', '.join(sorted({r.get('commit') or '?' for r in rows}))} · judges: validator {VALIDATOR_DIGEST[:19]}… (CEN {RULES_VERSION}), "
           "Factur-X 1.09 EN 16931 schema, order match", ""]
    if not keys:
        return "\n".join(out + ["No complete block: nothing to report."]) + "\n"
    delegated = sum(r.get("task_calls", 0) for r in ok)
    if delegated:
        out += [f"**Warning: {delegated} call(s) to the `task` tool — subagents write outside the harness; this run is not valid.**", ""]
    of = {arm: [by_arm[arm][k] for k in keys] for arm in arms}

    def share(test: Callable[[dict], Any]) -> Callable[[str], str]:
        return lambda arm: _share([bool(test(r)) for r in of[arm]])

    def mean(value: Callable[[dict], Any], digits: int = 1, yoked: bool = False) -> Callable[[str], str]:
        return lambda arm: "—" if yoked and arm == "without" else _mean([value(r) for r in of[arm] if value(r) is not None], digits)

    out += ["## Primary endpoint — correct delivered invoice (three independent judges)", "",
            *_table(arms, [("correct", share(lambda r: r["correct"]))]), ""]
    tests = [(a, b, role) for a, b, role in COMPARISONS if a in of and b in of]
    if tests:
        counts, ps = [], []
        for a, b, _ in tests:
            pairs = list(zip(of[a], of[b]))
            both = sum(1 for x, y in pairs if x["correct"] and y["correct"])
            only_a = sum(1 for x, y in pairs if x["correct"] and not y["correct"])
            only_b = sum(1 for x, y in pairs if not x["correct"] and y["correct"])
            counts.append((both, only_a, only_b, len(pairs) - both - only_a - only_b))
            ps.append(mcnemar_exact(only_a, only_b))
        tested = [i for i, (_, _, role) in enumerate(tests) if role != "exploratory"]
        adjusted = dict(zip(tested, holm([ps[i] for i in tested])))
        out += ["| paired comparison | both correct | only the first | only the second | neither | exact McNemar p | Holm-adjusted p |",
                "|---|---|---|---|---|---|---|"]
        for i, (a, b, role) in enumerate(tests):
            out.append(f"| {ARMS[a]} → {ARMS[b]} ({role}) | " + " | ".join(str(c) for c in counts[i])
                       + f" | {ps[i]:.4g} | " + (f"{adjusted[i]:.4g}" if i in adjusted else "—") + " |")
        out.append("")
    if "with_order" in of:
        out += ["H1 and H4 are tested at α = 0.05 after Holm's correction; the third comparison is exploratory (protocol, deviation 4). "
                "In the third arm, the yoke checks the invoice against the order with Keyross' delta oracles, and the order judge checks the "
                "same property with its own code: a delivered invoice of that arm matches the order almost by construction. What the arm "
                "measures is whether the agent gets there from the categories alone, within its limits, and at what cost — an invoice it "
                "does not deliver is not correct. The validator and the schema stay independent; the blind human review checks the order judge.", ""]

    out += ["## Residual errors in what ships", "", *_table(arms, [
        ("not delivered (gave up)", share(lambda r: not r["delivered"])),
        ("fatal rule — independent validator", share(lambda r: r["delivered"] and not r["valid"])),
        ("schema violation", share(lambda r: r["delivered"] and not r["schema_valid"])),
        ("does not match the order", share(lambda r: r["delivered"] and not r["right"])),
        ("valid but wrong (passes validator and schema, does not match the order)",
         share(lambda r: r["delivered"] and r["valid"] and r["schema_valid"] and not r["right"]))])]

    out += ["", "## The model alone — its first write, graded by the same judges", "", *_table(arms, [
        ("first write correct (first-pass)", share(lambda r: r["first_correct"])),
        ("first write valid (validator)", share(lambda r: r["first_valid"]))]),
        "", "The arms differ only after the first write, so their first-pass rates should agree; a gap is noise or a harness defect."]

    out += ["", "## Cost of the yoke", "", *_table(arms, [
        ("writes (executed)", mean(lambda r: r["writes"])),
        ("write attempts (including those the limit blocked)", mean(lambda r: r.get("write_attempts", r["writes"]))),
        ("pit stops (red flags returned)", mean(lambda r: r["pit_stops"])),
        ("tokens", mean(lambda r: r["tokens"])),
        ("seconds", mean(lambda r: r["seconds"])),
        ("cost, USD at list prices", mean(lambda r: r.get("cost_usd"), digits=4)),
        ("yoke checks", mean(lambda r: r["yoke_checks"], yoked=True)),
        ("yoke check time (ms)", mean(lambda r: r["yoke_check_ms"], yoked=True))], first="per run"), ""]
    for arm in (a for a in arms if a != "without" and "without" in of):
        pairs = list(zip(of["without"], of[arm]))
        tok = [y["tokens"] - x["tokens"] for x, y in pairs]
        sec = [y["seconds"] - x["seconds"] for x, y in pairs]
        cost = [y["cost_usd"] - x["cost_usd"] for x, y in pairs if x.get("cost_usd") is not None and y.get("cost_usd") is not None]
        t_mean, t_lo, t_hi = paired_bootstrap(tok)
        s_mean, s_lo, s_hi = paired_bootstrap(sec)
        base_tok = statistics.fmean([x["tokens"] for x, _ in pairs]) or 1
        out += [f"Paired overhead, {ARMS[arm]} − without yoke (95 % bootstrap CI): tokens {t_mean:+.0f} ({t_lo:+.0f} to {t_hi:+.0f}, "
                f"{100 * t_mean / base_tok:+.0f} %) · seconds {s_mean:+.1f} ({s_lo:+.1f} to {s_hi:+.1f})"
                + (f" · cost {statistics.fmean(cost):+.4f} USD per invoice (list prices)" if cost else "") + ".", ""]

    judged = [r["agree"] for r in ok if r.get("agree") is not None] + [r["first_agree"] for r in ok if r.get("first_agree") is not None]
    out += ["## Keyross against the independent validator", "",
            f"Same fatal rules on {sum(judged)}/{len(judged)} invoices graded (delivered and first writes)." if judged else "No invoice graded."]

    order_judged = ([(r, "delivered", r["order_agree"], r["keyross_order"], r["mismatches"]) for r in ok if r.get("order_agree") is not None]
                    + [(r, "first write", r["first_order_agree"], r["first_keyross_order"], r["first_mismatches"])
                       for r in ok if r.get("first_order_agree") is not None])
    out += ["", "## Keyross' delta oracles against the order judge", ""]
    if order_judged:
        out.append(f"Same verdict — matches the order or not — on {sum(1 for j in order_judged if j[2])}/{len(order_judged)} invoices "
                   "graded (delivered and first writes). Both check the same property with separate code: they are independent of the "
                   "model, not of each other.")
        out += [f"- {r['task']}, {ARMS[r['arm']]}, rep {r['rep']}, {which}: Keyross {', '.join(keyross) or 'green'} · "
                f"order judge {', '.join(judge) or 'matches'}" for r, which, agree, keyross, judge in order_judged if not agree]
    else:
        out.append("Not recorded in this run.")

    flagged = {arm: Counter(c for r in of[arm] for c in r.get("flags", [])) for arm in arms if arm != "without"}
    if any(flagged.values()):
        out += ["", "## Red flags returned to the agent, by category", ""]
        out += [f"- {ARMS[arm]}: " + ", ".join(f"{k} ×{v}" for k, v in counts.most_common(12)) for arm, counts in flagged.items() if counts]

    scenarios = sorted({r["scenario"] for r in of[arms[0]]})
    out += ["", "## Per scenario — correct", "", *_table(arms, [
        (sc, lambda arm, sc=sc: _share([r["correct"] for r in of[arm] if r["scenario"] == sc])) for sc in scenarios], first="scenario")]
    for arm in arms:
        rules = Counter(rule for r in of[arm] for rule in r.get("fatal", []))
        if rules:
            out += ["", f"Fatal rules in delivered invoices, {ARMS[arm]}: " + ", ".join(f"{k} ×{v}" for k, v in rules.most_common(12))]
    return "\n".join(out) + "\n"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="einvoice benchmark: the same agent without the yoke, with the rules, with the rules and the order")
    p.add_argument("--model", default="scripted", help="scripted (offline) or an init_chat_model string, e.g. anthropic:claude-haiku-4-5")
    p.add_argument("--tasks", type=int, default=0, help="only the first N tasks (0: all 50)")
    p.add_argument("--only", default="", help="only these tasks, e.g. order-01,order-02")
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--arms", default=",".join(ARMS), help=f"a subset of {','.join(ARMS)}")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--no-keep", action="store_true", help="do not keep the delivered invoices (they are needed for the human review)")
    p.add_argument("--report", type=Path, help="print the report of a results file and exit")
    args = p.parse_args()
    if args.report:
        print(report(args.report)); return 0
    arms = args.arms.split(",")
    if unknown := [a for a in arms if a not in ARMS]:
        sys.exit(f"unknown arm(s) {', '.join(unknown)}: choose among {', '.join(ARMS)}")
    if args.model.startswith("anthropic:") and not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")):
        sys.exit("ANTHROPIC_API_KEY is not set in this terminal: $env:ANTHROPIC_API_KEY = \"sk-ant-...\" (PowerShell), then run again")
    validator(b"<x/>")                                   # every judge must be up before the first run: fail now, not after paying
    orders = load_orders()[: args.tasks or None]
    if args.only:
        wanted = set(args.only.split(","))
        orders = [o for o in orders if o["id"] in wanted]
    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS / f"{stamp}-{args.model.split(':')[-1]}.jsonl"
    keep = None if args.no_keep else RESULTS / out.stem
    if keep:
        keep.mkdir(exist_ok=True)
    commit = _commit()
    jobs = [(o, arm, rep) for rep in range(1, args.reps + 1) for o in orders for arm in arms]
    print(f"{len(jobs)} runs · {args.model} · commit {commit} · results: {out}")
    failed = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool, open(out, "a", encoding="utf-8") as f:
        for job, r in zip(jobs, pool.map(lambda j: run_one(args.model, j[0], j[1], j[2], keep, commit), jobs)):
            _log(f, r)
            if "error" in r:
                failed.append(job)
        for o, arm, rep in failed:                          # protocol: an API error is run again once, at the end
            _log(f, {**run_one(args.model, o, arm, rep, keep, commit), "retry": True})
    report_text = report(out)
    out.with_suffix(".md").write_text(report_text, encoding="utf-8")
    print("\n" + report_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
