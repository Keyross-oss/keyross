"""The benchmark checks itself: every task is solvable, the grader separates invalid from wrong, the harness runs offline."""
import copy

import pytest

pytest.importorskip("deepagents")
pytest.importorskip("saxonche")

from bench.einvoice.grade import check_references, grade  # noqa: E402
from bench.einvoice.orders import load_orders  # noqa: E402
from bench.einvoice.reference import to_cii  # noqa: E402
from bench.einvoice.run import run_one  # noqa: E402


def test_twenty_solvable_tasks():
    results = check_references()
    assert len(results) == 20 and all(g["correct"] for _, g in results), [oid for oid, g in results if not g["correct"]]


def test_grader_separates_invalid_from_wrong():
    order = load_orders()[16]
    draft = grade(order, to_cii(order, line_total_shift="1.00"))
    assert not draft["valid"] and draft["fatal"] == ["BR-CO-10", "BR-CO-13"]
    bent = copy.deepcopy(order)
    bent["lines"][0]["net_price"] = "18.00"                         # a coherent invoice that bends the order
    wrong = grade(order, to_cii(bent))
    assert wrong["valid"] and not wrong["right"] and "line 1 price" in wrong["mismatches"]
    assert grade(order, None)["delivered"] is False


def test_harness_runs_both_arms_offline():
    order = load_orders()[12]                                        # intra-community supply
    without, with_yoke = (run_one("scripted", order, arm, 1, None) for arm in ("without", "with"))
    assert without["delivered"] and not without["correct"] and without["pit_stops"] == 0
    assert with_yoke["correct"] and with_yoke["writes"] == 2 and with_yoke["pit_stops"] == 1 and not with_yoke["first_write_valid"]
