"""The README's first screen states what the published run's raw results give — and the stack diagram agrees.
No extra needed: the raw results and the interval are plain Python."""
import json
from pathlib import Path

from bench.einvoice.stats import wilson

ROOT = Path(__file__).resolve().parent.parent
RUN = ROOT / "bench" / "einvoice" / "results" / "20260923T162255Z-claude-haiku-4-5.jsonl"


def _interval(k: int, n: int) -> str:
    lo, hi = wilson(k, n)
    return f"{100 * lo:.0f}–{100 * hi:.0f}"


def test_the_readme_table_is_the_raw_results():
    rows = [json.loads(line) for line in RUN.read_text(encoding="utf-8").splitlines() if line.strip()]
    without = [r for r in rows if r["arm"] == "without"]
    keyross = [r for r in rows if r["arm"] == "with_order"]       # the official rules + the order

    def fatal(rs):
        return sum(r["delivered"] and not r["valid"] for r in rs)

    def wrong(rs):
        return [r for r in rs if r["delivered"] and not r["correct"]]

    def held(rs):
        return sum(not r["delivered"] for r in rs)

    def cost(rs):
        return sum(r["cost_usd"] for r in rs) / len(rs)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert len(rows) == 300 and len(without) == len(keyross) == 100 and "| per 100 invoices |" in readme
    assert (f"| official-rule violations shipped | {fatal(without)} (95 % CI {_interval(fatal(without), 100)}) "
            f"| **{fatal(keyross)}** ({_interval(fatal(keyross), 100)}) |") in readme
    assert f"| shipped wrong, nobody told | {len(wrong(without))} | {len(wrong(keyross))} — all XML schema errors" in readme
    assert all(not r["schema_valid"] for r in wrong(keyross))
    assert f"| held for a human | {held(without)} | {held(keyross)} |" in readme
    assert f"| cost per invoice | {cost(without):.3f} USD | {cost(keyross):.3f} USD |" in readme
    stack = (ROOT / "docs" / "assets" / "keyross_stack.svg").read_text(encoding="utf-8")
    assert f"{fatal(without)} → {fatal(keyross)} official-rule" in stack
