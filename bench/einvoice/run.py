"""Run the benchmark: every task, without and with the yoke, `--reps` times; one JSON line per run; a report at the end.

    python -m bench.einvoice.run --model scripted                                   # offline dry run, zero cost
    python -m bench.einvoice.run --model anthropic:claude-sonnet-5 --only order-02,order-10,order-13,order-15,order-18   # the pilot
    python -m bench.einvoice.run --model anthropic:claude-sonnet-5 --reps 3         # the full run
    python -m bench.einvoice.run --report bench/einvoice/results/<file>.jsonl      # the report of a finished run
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from bench.einvoice.agent import INVOICE_PATH, ScriptedInvoiceModel, build_agent, task_message
from bench.einvoice.grade import grade
from bench.einvoice.orders import load_orders

RESULTS = Path(__file__).resolve().parent / "results"
# USD per million tokens: input, output, cache read, cache write — list prices (Anthropic first-party API), for an estimate only
PRICES = {"claude-sonnet-5": (2.00, 10.00, 0.20, 2.50), "claude-opus-5": (5.00, 25.00, 0.50, 6.25), "claude-haiku-4-5": (1.00, 5.00, 0.10, 1.25)}


def _model(spec: str, order: dict) -> Any:
    if spec == "scripted":
        return ScriptedInvoiceModel(order=order)
    from langchain.chat_models import init_chat_model
    # a whole invoice plus adaptive thinking is a long answer: stream it, so no request hits the HTTP client's timeout
    return init_chat_model(spec, max_tokens=32000, streaming=True)


def _usage(messages: list[Any]) -> dict[str, int]:
    u = {"input_tokens": 0, "output_tokens": 0, "cache_read": 0, "cache_write": 0, "model_calls": 0}
    for m in messages:
        if isinstance(m, AIMessage):
            u["model_calls"] += 1
            meta = m.usage_metadata or {}
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


def run_one(spec: str, order: dict, arm: str, rep: int, keep: Path | None) -> dict[str, Any]:
    record: dict[str, Any] = {"model": spec, "arm": arm, "rep": rep, "task": order["id"], "scenario": order["scenario"]}
    t0 = time.perf_counter()
    try:
        agent = build_agent(_model(spec, order), yoke=(arm == "with"))
        out = agent.invoke({"messages": [{"role": "user", "content": task_message(order)}]},
                           config={"configurable": {"thread_id": f"{order['id']}-{arm}-{rep}"}, "recursion_limit": 60})
    except Exception as e:  # noqa: BLE001 — an API error is recorded, the benchmark goes on
        return {**record, "error": f"{type(e).__name__}: {str(e)[:300]}", "seconds": round(time.perf_counter() - t0, 1)}
    messages = out["messages"]
    data = out.get("files", {}).get(INVOICE_PATH)
    xml = data.get("content") if isinstance(data, dict) else data
    xml = "\n".join(xml) if isinstance(xml, list) else xml
    attempts = _written(messages)
    usage = _usage(messages)
    record.update(grade(order, xml))
    record.update({
        "first_write_valid": grade(order, attempts[0])["valid"] if attempts else False,
        "writes": len(attempts),
        "pit_stops": sum(1 for m in messages if isinstance(m, ToolMessage) and "red flag" in str(m.content)),
        **usage, "cost_usd": _cost(spec, usage), "seconds": round(time.perf_counter() - t0, 1),
    })
    if keep is not None and xml:
        (keep / f"{order['id']}-{arm}-{rep}.xml").write_text(xml, encoding="utf-8")
    return record


def _pct(xs: list[bool]) -> str:
    return f"{100 * sum(xs) / len(xs):.0f}%" if xs else "—"


def report(path: Path) -> str:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [r for r in rows if "error" not in r]
    lines = [f"# einvoice benchmark — {path.name}", "",
             f"{len(rows)} runs · model {', '.join(sorted({r['model'] for r in rows}))} · {len(rows) - len(ok)} API error(s)", "",
             "| arm | runs | invoice delivered | valid (CEN) | right (order) | **correct** | first write valid | writes / run | pit stops / run | cost / run | time / run |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for arm in ("without", "with"):
        rs = [r for r in ok if r["arm"] == arm]
        if not rs:
            continue
        cost = [r["cost_usd"] for r in rs if r.get("cost_usd") is not None]
        lines.append(f"| {arm} yoke | {len(rs)} | {_pct([r['delivered'] for r in rs])} | {_pct([r['valid'] for r in rs])} | "
                     f"{_pct([r['right'] for r in rs])} | **{_pct([r['correct'] for r in rs])}** | {_pct([r['first_write_valid'] for r in rs])} | "
                     f"{sum(r['writes'] for r in rs) / len(rs):.1f} | {sum(r['pit_stops'] for r in rs) / len(rs):.1f} | "
                     + (f"${sum(cost) / len(cost):.3f}" if cost else "—") + f" | {sum(r['seconds'] for r in rs) / len(rs):.0f} s |")
    lines += ["", "Correct = valid for the official CEN EN 16931 rules (no fatal finding) **and** matching the order (lines, VAT breakdown, totals).", "",
              "| scenario | without yoke: correct | with yoke: correct |", "|---|---|---|"]
    for sc in sorted({r["scenario"] for r in ok}):
        cells = [_pct([r["correct"] for r in ok if r["scenario"] == sc and r["arm"] == arm]) for arm in ("without", "with")]
        lines.append(f"| {sc} | {cells[0]} | {cells[1]} |")
    fatal: dict[str, int] = {}
    for r in ok:
        if r["arm"] == "without":
            for rule in r.get("fatal", []):
                fatal[rule] = fatal.get(rule, 0) + 1
    if fatal:
        lines += ["", "Rules broken in delivered invoices without the yoke: " + ", ".join(f"{k} ×{v}" for k, v in sorted(fatal.items(), key=lambda kv: -kv[1]))]
    return "\n".join(lines) + "\n"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="einvoice benchmark: the same agent without and with the yoke")
    p.add_argument("--model", default="scripted", help="scripted (offline) or an init_chat_model string, e.g. anthropic:claude-sonnet-5")
    p.add_argument("--tasks", type=int, default=0, help="only the first N tasks (0: all 20)")
    p.add_argument("--only", default="", help="only these tasks, e.g. order-02,order-10 (one per scenario makes a good pilot)")
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--arms", default="without,with")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--keep-invoices", action="store_true", help="save every delivered invoice next to the results")
    p.add_argument("--report", type=Path, help="print the report of a results file and exit")
    args = p.parse_args()
    if args.report:
        print(report(args.report)); return 0
    orders = load_orders()[: args.tasks or None]
    if args.only:
        wanted = set(args.only.split(","))
        orders = [o for o in orders if o["id"] in wanted]
    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = RESULTS / f"{stamp}-{args.model.split(':')[-1]}.jsonl"
    keep = RESULTS / out.stem if args.keep_invoices else None
    if keep:
        keep.mkdir(exist_ok=True)
    jobs = [(o, arm, rep) for rep in range(1, args.reps + 1) for o in orders for arm in args.arms.split(",")]
    print(f"{len(jobs)} runs · {args.model} · results: {out}")
    with ThreadPoolExecutor(max_workers=args.workers) as pool, open(out, "a", encoding="utf-8") as f:
        for r in pool.map(lambda j: run_one(args.model, j[0], j[1], j[2], keep), jobs):
            f.write(json.dumps(r, ensure_ascii=False) + "\n"); f.flush()
            status = r.get("error") or ("correct" if r["correct"] else f"valid={r['valid']} right={r['right']}")
            print(f"  {r['task']} {r['arm']:<7} rep {r['rep']}: {status}" + (f" · ${r['cost_usd']}" if r.get("cost_usd") else ""))
    report_text = report(out)
    out.with_suffix(".md").write_text(report_text, encoding="utf-8")
    print("\n" + report_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
