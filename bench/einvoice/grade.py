"""Grading, outside the agent and outside Keyross: an invoice is **correct** when the independent validator finds no fatal
rule, the official schema accepts it, and it matches the order (lines, VAT breakdown, totals). The order check catches an
invoice made valid by bending the order. Keyross' own verdict, with the order in its context, is recorded only to measure
agreement: its official rules against the validator, its delta oracles (`order.*`) against the order judge.

`python -m bench.einvoice.grade` checks that every reference invoice is correct: every task is solvable."""
from __future__ import annotations

import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any

from keyross.core.invoice import load_invoice
from keyross.core.runner import check_file
from keyross.gauges import load_gauge

from bench.einvoice.judges import schema_errors, validator
from bench.einvoice.orders import expected, load_orders

TOL = Decimal("0.005")
DELTA = "einvoice.delta."            # Keyross' delta oracles: the invoice against its order


def _same(a: Any, b: Any) -> bool:
    return a is not None and b is not None and abs(Decimal(str(a)) - Decimal(str(b))) <= TOL


def order_mismatches(order: dict, path: Path) -> list[str]:
    """What the invoice gets wrong compared with the order (empty: it matches)."""
    exp, inv = expected(order), load_invoice(path)
    out = []
    if inv.number != order["invoice"]["number"]:
        out.append("number")
    if inv.currency != order["invoice"]["currency"]:
        out.append("currency")
    by_id = {l.number: l for l in inv.lines}
    if len(inv.lines) != len(order["lines"]):
        out.append("line count")
    for l in order["lines"]:
        got = by_id.get(l["id"])
        if got is None:
            out.append(f"line {l['id']} missing"); continue
        for name, want, have in (("quantity", l["quantity"], got.qty), ("price", l["net_price"], got.unit_price),
                                 ("net amount", exp["line_net"][l["id"]], got.amount), ("VAT rate", l["vat_rate"], got.vat_rate)):
            if not _same(want, have):
                out.append(f"line {l['id']} {name}")
        if got.vat_category != l["vat_category"]:
            out.append(f"line {l['id']} VAT category")
    t = inv.totals
    for name, want, have in (("line total", exp["line_total"], t.line_net), ("total without VAT", exp["tax_exclusive"], t.tax_exclusive),
                             ("VAT total", exp["tax"], t.tax), ("total with VAT", exp["tax_inclusive"], t.tax_inclusive),
                             ("amount due", exp["payable"], t.payable)):
        if not _same(want, have):
            out.append(name)
    got_vat = {(b.category, round(b.rate or 0, 2)): b for b in inv.vat}
    for key, v in exp["vat"].items():
        category, rate = key.split()
        b = got_vat.get((category, round(float(rate), 2)))
        if b is None or not _same(v["taxable"], b.taxable_amount) or not _same(v["tax"], b.tax_amount):
            out.append(f"VAT {category} {rate}")
    return out


def grade(order: dict, xml: str | None) -> dict[str, Any]:
    """The verdict of the three independent judges on one invoice (`xml` None: nothing was delivered)."""
    if xml is None:
        return {"delivered": False, "valid": False, "schema_valid": False, "right": False, "correct": False,
                "fatal": [], "schema": [], "mismatches": ["not delivered"], "keyross_fatal": [], "agree": None,
                "keyross_order": [], "order_agree": None}
    data = xml.encode("utf-8")
    independent = validator(data)
    schema = schema_errors(data)
    load_gauge("einvoice")
    with tempfile.TemporaryDirectory(prefix="keyross-bench-", ignore_cleanup_errors=True) as tmp:
        f = Path(tmp) / "invoice.xml"
        f.write_bytes(data)
        report = check_file(f, gauge="einvoice", ctx={"order": order})
        try:
            mismatches = order_mismatches(order, f)
        except Exception as e:  # noqa: BLE001 — an unreadable invoice is not right
            mismatches = [f"unreadable: {type(e).__name__}"]
    valid, schema_valid, right = not independent["fatal"], not schema, not mismatches
    fails = report.hard_failures
    keyross_fatal = sorted({v.category for v in fails if not v.oracle_id.startswith(DELTA)})    # the official rules
    keyross_order = sorted({v.category for v in fails if v.oracle_id.startswith(DELTA)})        # the delta oracles
    delta_ran = any(v.oracle_id.startswith(DELTA) for v in report.verdicts)                     # not on an unreadable XML
    return {"delivered": True, "valid": valid, "schema_valid": schema_valid, "right": right,
            "correct": valid and schema_valid and right, "fatal": independent["fatal"], "warnings": len(independent["warnings"]),
            "schema": schema, "mismatches": mismatches, "keyross_fatal": keyross_fatal, "agree": keyross_fatal == independent["fatal"],
            "keyross_order": keyross_order, "order_agree": (not keyross_order) == right if delta_ran else None}


def check_references() -> list[tuple[str, dict]]:
    from bench.einvoice.reference import to_cii
    return [(o["id"], grade(o, to_cii(o))) for o in load_orders()]


if __name__ == "__main__":
    import sys
    results = check_references()
    for oid, g in results:
        print(f"  {'OK ' if g['correct'] else 'XX '} {oid}  fatal={g['fatal']}  schema={g['schema'][:1]}  mismatches={g['mismatches']}"
              f"  keyross={g['keyross_fatal'] + g['keyross_order']}")
    bad = [oid for oid, g in results if not g["correct"] or g["keyross_fatal"] or g["keyross_order"]]
    print(f"{len(results) - len(bad)}/{len(results)} reference invoices correct for the three independent judges, and green for Keyross")
    sys.exit(1 if bad else 0)
