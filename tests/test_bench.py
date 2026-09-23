"""The benchmark checks itself: balanced, solvable tasks; judges that are not Keyross; statistics that match known values;
a harness that runs offline. Tests that need the independent validator skip when it is not running (CI starts it)."""
import copy
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
from bench.einvoice.stats import mcnemar_exact, paired_bootstrap, wilson  # noqa: E402

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


@judges
def test_every_task_is_solvable_for_the_independent_judges():
    from bench.einvoice.grade import check_references
    results = check_references()
    assert len(results) == 50 and all(g["correct"] for _, g in results), [oid for oid, g in results if not g["correct"]]


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
    assert grade(order, None)["delivered"] is False


@judges
def test_harness_runs_both_arms_offline():
    from bench.einvoice.run import run_one
    order = load_orders()[2]                                         # intra-community supply
    without, with_yoke = (run_one("scripted", order, arm, 1, None) for arm in ("without", "with"))
    assert without["delivered"] and not without["correct"] and without["pit_stops"] == 0 and without["yoke_checks"] == 0
    assert with_yoke["correct"] and with_yoke["writes"] == 2 and with_yoke["pit_stops"] == 1 and not with_yoke["first_correct"]
    assert with_yoke["yoke_checks"] == 2 and with_yoke["agree"] and with_yoke["first_agree"]
