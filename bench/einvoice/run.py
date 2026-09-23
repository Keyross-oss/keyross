"""Run the benchmark (protocol: bench/einvoice/PROTOCOL.md): every task, without and with the yoke, `--reps` times; one JSON
line per run, every delivered invoice kept for review; then the report — exact counts, paired tests, costs.

    python -m bench.einvoice.judges --setup                                         # once: the schema, the validator command
    python -m bench.einvoice.run --model scripted                                   # offline dry run: checks the harness, measures nothing
    python -m bench.einvoice.run --model anthropic:claude-sonnet-5 --only order-01,order-02,order-03,order-04,order-05   # pilot
    python -m bench.einvoice.run --model anthropic:claude-sonnet-5 --reps 2         # the full run: 50 tasks × 2 arms × 2
    python -m bench.einvoice.run --report bench/einvoice/results/<run>.jsonl       # the report of a finished run
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage

from bench.einvoice.agent import INVOICE_PATH, ScriptedInvoiceModel, build_agent, task_message
from bench.einvoice.grade import grade
from bench.einvoice.judges import RULES_VERSION, VALIDATOR_DIGEST, validator
from bench.einvoice.orders import load_orders
from bench.einvoice.stats import mcnemar_exact, paired_bootstrap, wilson

RESULTS = Path(__file__).resolve().parent / "results"
# USD per million tokens: input, output, cache read, cache write — list prices (Anthropic first-party API), for an estimate only
PRICES = {"claude-sonnet-5": (2.00, 10.00, 0.20, 2.50), "claude-opus-5": (5.00, 25.00, 0.50, 6.25), "claude-haiku-4-5": (1.00, 5.00, 0.10, 1.25)}


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


def _commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def run_one(spec: str, order: dict, arm: str, rep: int, keep: Path | None, commit: str = "") -> dict[str, Any]:
    record: dict[str, Any] = {"model": spec, "arm": arm, "rep": rep, "task": order["id"], "scenario": order["scenario"], "commit": commit}
    checks = _Checks()
    t0 = time.perf_counter()
    try:
        agent = build_agent(_model(spec, order), yoke=(arm == "with"), telemetry=checks)
        out = agent.invoke({"messages": [{"role": "user", "content": task_message(order)}]},
                           config={"configurable": {"thread_id": f"{order['id']}-{arm}-{rep}"}, "recursion_limit": 60})
    except Exception as e:  # noqa: BLE001 — an API error is recorded, the benchmark goes on
        return {**record, "error": f"{type(e).__name__}: {str(e)[:300]}", "seconds": round(time.perf_counter() - t0, 1)}
    seconds = round(time.perf_counter() - t0, 1)
    messages = out["messages"]
    data = out.get("files", {}).get(INVOICE_PATH)
    xml = data.get("content") if isinstance(data, dict) else data
    xml = "\n".join(xml) if isinstance(xml, list) else xml
    attempts = _written(messages)
    usage = _usage(messages)
    record.update(grade(order, xml))
    first = grade(order, attempts[0]) if attempts else grade(order, None)
    record.update({
        "first_correct": first["correct"], "first_valid": first["valid"], "first_schema_valid": first["schema_valid"],
        "first_right": first["right"], "first_agree": first["agree"],
        "writes": len(attempts),
        "pit_stops": sum(1 for m in messages if isinstance(m, ToolMessage) and "red flag" in str(m.content)),
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
    print(f"  {r['task']} {r['arm']:<7} rep {r['rep']}{' (retry)' if r.get('retry') else ''}: {status}"
          + (f" · ${r['cost_usd']}" if r.get("cost_usd") else ""))


# -- the report ----------------------------------------------------------------------------------------------------

def _share(xs: list[bool]) -> str:
    k, n = sum(xs), len(xs)
    if not n:
        return "—"
    lo, hi = wilson(k, n)
    return f"{k}/{n} ({100 * k / n:.0f} %, CI {100 * lo:.0f}–{100 * hi:.0f})"


def _mean(xs: list[float]) -> str:
    return f"{statistics.fmean(xs):.1f}" if xs else "—"


def report(path: Path) -> str:
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    ok = [r for r in rows if "error" not in r]                      # a successful retry replaces its failed run
    arms = {arm: {(r["task"], r["rep"]): r for r in ok if r["arm"] == arm} for arm in ("without", "with")}
    keys = sorted(set(arms["without"]) & set(arms["with"]))
    pairs = [(arms["without"][k], arms["with"][k]) for k in keys]
    runs = {(r["task"], r["arm"], r["rep"]) for r in rows}
    lost = len(runs - {(r["task"], r["arm"], r["rep"]) for r in ok})
    out = [f"# einvoice benchmark — {path.name}", "",
           f"{len(runs)} runs · {len(rows) - len(ok)} API error(s), {lost} run(s) lost after the retry · {len(pairs)} complete pairs · model {', '.join(sorted({r['model'] for r in rows}))} · "
           f"commit {', '.join(sorted({r.get('commit') or '?' for r in rows}))} · judges: validator {VALIDATOR_DIGEST[:19]}… (CEN {RULES_VERSION}), "
           "Factur-X 1.09 EN 16931 schema, order match", ""]
    if not pairs:
        return "\n".join(out + ["No complete pair: nothing to compare."]) + "\n"
    a = [p[0] for p in pairs]
    b = [p[1] for p in pairs]

    both = sum(1 for x, y in pairs if x["correct"] and y["correct"])
    only_without = sum(1 for x, y in pairs if x["correct"] and not y["correct"])
    only_with = sum(1 for x, y in pairs if not x["correct"] and y["correct"])
    neither = len(pairs) - both - only_without - only_with
    out += ["## Primary endpoint — correct delivered invoice (three independent judges)", "",
            "| | without yoke | with yoke |", "|---|---|---|",
            f"| correct | {_share([r['correct'] for r in a])} | {_share([r['correct'] for r in b])} |", "",
            f"Paired outcomes: both correct {both} · only without {only_without} · only with {only_with} · neither {neither} — "
            f"exact McNemar p = {mcnemar_exact(only_without, only_with):.4g}.", ""]

    def residual(rs: list[dict]) -> list[str]:
        return [_share([not r["delivered"] for r in rs]), _share([r["delivered"] and not r["valid"] for r in rs]),
                _share([r["delivered"] and not r["schema_valid"] for r in rs]), _share([r["delivered"] and not r["right"] for r in rs]),
                _share([r["delivered"] and r["valid"] and r["schema_valid"] and not r["right"] for r in rs])]
    ra, rb = residual(a), residual(b)
    out += ["## Residual errors in what ships", "", "| | without yoke | with yoke |", "|---|---|---|"]
    for i, name in enumerate(("not delivered (gave up)", "fatal rule — independent validator", "schema violation",
                              "does not match the order", "valid but wrong (passes validator and schema, does not match the order)")):
        out.append(f"| {name} | {ra[i]} | {rb[i]} |")

    out += ["", "## The model alone — its first write, graded by the same judges", "", "| | without yoke | with yoke |", "|---|---|---|",
            f"| first write correct (first-pass) | {_share([r['first_correct'] for r in a])} | {_share([r['first_correct'] for r in b])} |",
            f"| first write valid (validator) | {_share([r['first_valid'] for r in a])} | {_share([r['first_valid'] for r in b])} |",
            "", "The arms differ only after the first write, so their first-pass rates should agree; a gap is noise or a harness defect."]

    tok = [y["tokens"] - x["tokens"] for x, y in pairs]
    sec = [y["seconds"] - x["seconds"] for x, y in pairs]
    cost = [y["cost_usd"] - x["cost_usd"] for x, y in pairs if x.get("cost_usd") is not None and y.get("cost_usd") is not None]
    t_mean, t_lo, t_hi = paired_bootstrap(tok)
    s_mean, s_lo, s_hi = paired_bootstrap(sec)
    base_tok = statistics.fmean([x["tokens"] for x in a]) or 1
    out += ["", "## Cost of the yoke", "", "| per run | without yoke | with yoke |", "|---|---|---|",
            f"| writes | {_mean([r['writes'] for r in a])} | {_mean([r['writes'] for r in b])} |",
            f"| pit stops (red flags returned) | {_mean([r['pit_stops'] for r in a])} | {_mean([r['pit_stops'] for r in b])} |",
            f"| tokens | {_mean([r['tokens'] for r in a])} | {_mean([r['tokens'] for r in b])} |",
            f"| seconds | {_mean([r['seconds'] for r in a])} | {_mean([r['seconds'] for r in b])} |",
            f"| yoke checks · check time (ms) | — | {_mean([r['yoke_checks'] for r in b])} · {_mean([r['yoke_check_ms'] for r in b])} |",
            "", f"Paired overhead of the yoke (with − without, 95 % bootstrap CI): tokens {t_mean:+.0f} ({t_lo:+.0f} to {t_hi:+.0f}, "
            f"{100 * t_mean / base_tok:+.0f} %) · seconds {s_mean:+.1f} ({s_lo:+.1f} to {s_hi:+.1f})"
            + (f" · cost {statistics.fmean(cost):+.4f} USD per invoice (list prices)" if cost else "") + "."]

    judged = [r["agree"] for r in ok if r.get("agree") is not None] + [r["first_agree"] for r in ok if r.get("first_agree") is not None]
    out += ["", "## Keyross against the independent validator", "",
            f"Same fatal rules on {sum(judged)}/{len(judged)} invoices graded (delivered and first writes)." if judged else "No invoice graded."]

    out += ["", "## Per scenario — correct", "", "| scenario | without yoke | with yoke |", "|---|---|---|"]
    for sc in sorted({r["scenario"] for r in a}):
        out.append(f"| {sc} | {_share([r['correct'] for r in a if r['scenario'] == sc])} | {_share([r['correct'] for r in b if r['scenario'] == sc])} |")
    for arm, rs in (("without", a), ("with", b)):
        rules = Counter(rule for r in rs for rule in r.get("fatal", []))
        if rules:
            out += ["", f"Fatal rules in delivered invoices {arm} the yoke: " + ", ".join(f"{k} ×{v}" for k, v in rules.most_common(12))]
    return "\n".join(out) + "\n"


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="einvoice benchmark: the same agent without and with the yoke")
    p.add_argument("--model", default="scripted", help="scripted (offline) or an init_chat_model string, e.g. anthropic:claude-sonnet-5")
    p.add_argument("--tasks", type=int, default=0, help="only the first N tasks (0: all 50)")
    p.add_argument("--only", default="", help="only these tasks, e.g. order-01,order-02")
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--arms", default="without,with")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--no-keep", action="store_true", help="do not keep the delivered invoices (they are needed for the human review)")
    p.add_argument("--report", type=Path, help="print the report of a results file and exit")
    args = p.parse_args()
    if args.report:
        print(report(args.report)); return 0
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
    jobs = [(o, arm, rep) for rep in range(1, args.reps + 1) for o in orders for arm in args.arms.split(",")]
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
