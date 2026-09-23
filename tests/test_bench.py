"""The benchmark checks itself: balanced, solvable tasks; judges that are not Keyross; statistics that match known values;
a harness that runs offline. Tests that need the independent validator skip when it is not running (CI starts it)."""
import copy
import json
from collections import Counter
from datetime import date
from pathlib import Path

import pytest

pytest.importorskip("deepagents")
pytest.importorskip("saxonche")
pytest.importorskip("lxml")

from bench.einvoice.judges import SCHEMA_DIR, SCHEMA_ROOT, JudgeUnavailable, validator  # noqa: E402
from bench.einvoice.orders import load_orders  # noqa: E402
from bench.einvoice.reference import to_cii  # noqa: E402
from bench.einvoice.stats import holm, mcnemar_exact, paired_bootstrap, wilson  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def _judges_up() -> bool:
    try:
        validator(b"<x/>")
    except JudgeUnavailable:
        return False
    return (SCHEMA_DIR / SCHEMA_ROOT).exists()


judges = pytest.mark.skipif(not _judges_up(), reason="independent judges not running: python -m bench.einvoice.judges --setup")


def test_fifty_balanced_orders():
    orders = load_orders()
    assert len(orders) == 50 and set(Counter(o["scenario"] for o in orders).values()) == {10}
    assert all(1 <= len(o["lines"]) <= 6 and date.fromisoformat(o["invoice"]["issue_date"]) for o in orders)


def test_statistics_match_known_values():
    assert mcnemar_exact(2, 12) == pytest.approx(0.012939, abs=1e-6) and mcnemar_exact(5, 5) == 1.0 and mcnemar_exact(0, 0) == 1.0
    assert wilson(81, 100) == pytest.approx((0.7222, 0.8749), abs=1e-4)
    mean, lo, hi = paired_bootstrap([1, 2, 3, 4])
    assert mean == 2.5 and lo <= mean <= hi
    assert holm([0.01, 0.04]) == [0.02, 0.04] and holm([0.5, 0.01]) == [0.5, 0.02] and holm([0.03, 0.02]) == [0.04, 0.04]


def _row(task: str, arm: str, correct: bool, **fields) -> dict:
    """One run as run_one records it, with the fields the report reads."""
    return {"model": "m", "arm": arm, "rep": 1, "task": task, "scenario": "domestic", "commit": "c", "delivered": True,
            "valid": True, "schema_valid": True, "right": correct, "correct": correct, "fatal": [], "mismatches": [] if correct else ["line total"],
            "keyross_fatal": [], "agree": True, "keyross_order": [] if correct else ["order.totals"], "order_agree": True,
            "first_correct": correct, "first_valid": True, "first_schema_valid": True, "first_right": correct, "first_agree": True,
            "first_order_agree": True, "first_keyross_order": [], "first_mismatches": [], "writes": 1, "write_attempts": 1,
            "task_calls": 0, "pit_stops": 0, "flags": [], "yoke_checks": int(arm != "without"), "yoke_check_ms": 0,
            "tokens": 1000, "seconds": 10.0, "cost_usd": 0.01, **fields}


def test_report_tests_h1_and_h4_with_holm_and_explores_the_third_pair(tmp_path):
    from bench.einvoice.run import report
    rows = [_row(f"order-{i:02d}", arm, i < n, flags=["order.totals", "order.vat"] if (arm, i) == ("with_order", 9) else [])
            for i in range(10) for arm, n in (("without", 2), ("with", 4), ("with_order", 9))]
    rows.insert(0, {**rows[-1], "error": "APIError: overloaded"})                  # an API error, then its retry: only the retry counts
    path = tmp_path / "run.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    text = report(path)
    assert "30 runs · 1 API error(s), 0 run(s) lost after the retry · 10 complete blocks" in text
    assert "| without yoke → yoke: rules (H1) | 2 | 0 | 2 | 6 | 0.5 | 0.5 |" in text
    assert "| without yoke → yoke: rules + order (H4) | 2 | 0 | 7 | 1 | 0.01562 | 0.03125 |" in text
    assert "| yoke: rules → yoke: rules + order (exploratory) | 4 | 0 | 5 | 1 | 0.0625 | — |" in text
    assert "- yoke: rules + order: order.totals ×1, order.vat ×1" in text and "Same verdict — matches the order or not — on 60/60" in text
    path.write_text("\n".join(json.dumps(r) for r in rows if r["arm"] == "with_order"), encoding="utf-8")
    alone = report(path)                                                            # the pilot of the third arm: one arm, no test
    assert "| correct | 9/10 (90 %" in alone and "paired comparison" not in alone and "Paired overhead" not in alone


def test_the_arms_are_built_as_declared():
    from bench.einvoice.agent import ScriptedInvoiceModel, build_agent
    order = load_orders()[0]
    with pytest.raises(ValueError, match="unknown arm"):
        build_agent(ScriptedInvoiceModel(order=order), arm="both")
    with pytest.raises(ValueError, match="needs the order"):
        build_agent(ScriptedInvoiceModel(order=order), arm="with_order")


@judges
def test_every_task_is_solvable_for_the_independent_judges():
    from bench.einvoice.grade import check_references
    results = check_references()
    assert len(results) == 50 and all(g["correct"] for _, g in results), [oid for oid, g in results if not g["correct"]]
    green = [oid for oid, g in results if g["keyross_fatal"] or g["keyross_order"]]      # the delta oracles accept every reference
    assert not green, green


@judges
def test_keyross_agrees_with_the_independent_validator():
    """Same fatal rules, bad cases and clean invoices alike: a verdict that differs from the official rules is a bug."""
    from bench.einvoice.grade import grade
    order = load_orders()[0]
    files = sorted((ROOT / "badset").glob("einvoice.*.xml")) + sorted((ROOT / "tests" / "fixtures" / "einvoice").glob("*.xml"))
    disagree = [f.name for f in files if not grade(order, f.read_text(encoding="utf-8"))["agree"]]
    assert not disagree, disagree


@judges
def test_grader_separates_invalid_from_wrong():
    from bench.einvoice.grade import grade
    order = load_orders()[4]
    draft = grade(order, to_cii(order, line_total_shift="1.00"))
    assert not draft["valid"] and draft["fatal"] == ["BR-CO-10", "BR-CO-13"] and draft["schema_valid"]
    bent = copy.deepcopy(order)
    bent["lines"][0]["net_price"] = "18.00"                         # a coherent invoice that bends the order
    wrong = grade(order, to_cii(bent))
    assert wrong["valid"] and wrong["schema_valid"] and not wrong["right"] and "line 1 price" in wrong["mismatches"]
    assert wrong["keyross_order"] == ["order.lines", "order.totals", "order.vat"] and wrong["order_agree"]   # the yoke's third arm sees it
    assert grade(order, None)["delivered"] is False


@judges
def test_harness_runs_the_three_arms_offline():
    from bench.einvoice.run import run_one
    order = load_orders()[2]                                         # intra-community supply
    without, with_yoke, with_order = (run_one("scripted", order, arm, 1, None) for arm in ("without", "with", "with_order"))
    assert without["delivered"] and not without["correct"] and without["pit_stops"] == 0 and without["yoke_checks"] == 0
    assert with_yoke["correct"] and with_yoke["writes"] == 2 and with_yoke["pit_stops"] == 1 and not with_yoke["first_correct"]
    assert with_yoke["yoke_checks"] == 2 and with_yoke["agree"] and with_yoke["first_agree"]
    assert with_yoke["flags"] == ["BR-CO-10", "BR-CO-13"]
    assert with_order["correct"] and with_order["writes"] == 2 and with_order["pit_stops"] == 1
    assert "order.totals" in with_order["flags"] and with_order["order_agree"] and with_order["first_order_agree"]


@judges
def test_the_worked_example_is_correct_and_not_a_task(tmp_path):
    """The system prompt's example (deviation 3) passes the three judges and gives away none of the 50 tasks."""
    import json
    from bench.einvoice.agent import EXAMPLE_DIR, SYSTEM_PROMPT
    from bench.einvoice.grade import grade
    order = {"id": "example", "scenario": "example", **json.loads((EXAMPLE_DIR / "example-order.json").read_text(encoding="utf-8"))}
    assert grade(order, (EXAMPLE_DIR / "example-invoice.xml").read_text(encoding="utf-8"))["correct"]
    assert order["invoice"]["number"] not in {o["invoice"]["number"] for o in load_orders()} and order["invoice"]["number"] in SYSTEM_PROMPT
