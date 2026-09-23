"""Gauge einvoice — delta oracles: what the official rules cannot know. The invoice against the order it is issued for.

The official EN 16931 rules check that an invoice is coherent with itself; an invoice can be coherent and still bill the
wrong quantity, price or amount. These oracles compare it with its order, given in the context (`ctx["order"]`, the format
in README.md). Amounts follow EN 16931 arithmetic: a line net amount is quantity × net price, a VAT amount is taxable amount
× rate, each rounded half-up to the cent. Without an order in the context, they skip."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from keyross.core.registry import oracle
from keyross.core.verdict import Verdict

CENT = Decimal("0.01")
INVOICE = ["invoice"]                 # these oracles read the canonical Invoice, not a table


def _dec(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _differs(expected: Decimal | None, actual: Any) -> bool:
    got = _dec(actual)
    return expected is None or got is None or abs(got - expected) >= CENT / 2


def _rate(value: Any) -> Decimal | None:
    got = _dec(value)
    return None if got is None else got.quantize(CENT)


def _implied(order: dict) -> dict[str, Any]:
    """What the order implies: line net amounts, the VAT breakdown, the totals."""
    lines = {}
    for line in order.get("lines", []):
        qty, price = _dec(line.get("quantity")), _dec(line.get("net_price"))
        lines[str(line.get("id"))] = {"qty": qty, "price": price, "net": _cents(qty * price) if qty is not None and price is not None else None,
                                      "category": line.get("vat_category"), "rate": _rate(line.get("vat_rate"))}
    bases: dict[tuple[str, Decimal | None], Decimal] = {}
    for line in lines.values():
        key = (line["category"], line["rate"])
        bases[key] = bases.get(key, Decimal("0")) + (line["net"] or Decimal("0"))
    allowances = charges = Decimal("0")
    for sign, entries in ((-1, order.get("allowances", [])), (1, order.get("charges", []))):
        for entry in entries:
            amount = _dec(entry.get("amount")) or Decimal("0")
            key = (entry.get("vat_category"), _rate(entry.get("vat_rate")))
            bases[key] = bases.get(key, Decimal("0")) + sign * amount
            if sign < 0:
                allowances += amount
            else:
                charges += amount
    vat = {key: (_cents(base), _cents(base * (key[1] or Decimal("0")) / 100)) for key, base in bases.items()}
    line_total = sum((line["net"] or Decimal("0") for line in lines.values()), Decimal("0"))
    without_vat = line_total - allowances + charges
    tax = sum((amount for _, amount in vat.values()), Decimal("0"))
    return {"lines": lines, "vat": vat, "totals": {"line total": line_total, "allowances": allowances, "charges": charges,
                                                   "total without VAT": without_vat, "VAT total": tax,
                                                   "total with VAT": without_vat + tax, "amount due": without_vat + tax}}


@oracle("einvoice.delta.order.header", severity="hard", tags=INVOICE)
def order_header(inv: Any, ctx: dict) -> Verdict:
    """The invoice carries the invoice number and the currency the order gives."""
    order = ctx.get("order")
    if not order:
        return Verdict.skip("no order in context")
    head = order.get("invoice", {})
    wrong = [{"field": field, "expected": want, "actual": got}
             for field, want, got in (("number", head.get("number"), inv.number), ("currency", head.get("currency"), inv.currency))
             if want is not None and want != got]
    return Verdict.fail(f"header differs from the order: {', '.join(w['field'] for w in wrong)}", "order.header", deviations=wrong) if wrong else Verdict.ok()


@oracle("einvoice.delta.order.lines", severity="hard", tags=INVOICE)
def order_lines(inv: Any, ctx: dict) -> Verdict:
    """Every line of the order is invoiced once, with its quantity, net price, VAT category and rate, and a net amount of
    quantity × net price."""
    order = ctx.get("order")
    if not order:
        return Verdict.skip("no order in context")
    expected = _implied(order)["lines"]
    invoiced: dict[str, list[Any]] = {}
    for line in inv.lines:
        invoiced.setdefault(str(line.number), []).append(line)
    wrong = [{"line": lid, "issue": "missing"} for lid in expected if lid not in invoiced]
    wrong += [{"line": lid, "issue": "not in the order" if lid not in expected else "invoiced twice"}
              for lid, found in invoiced.items() if lid not in expected or len(found) > 1]
    for lid, want in expected.items():
        if lid not in invoiced:
            continue
        got = invoiced[lid][0]
        for field, value, actual in (("quantity", want["qty"], got.qty), ("net price", want["price"], got.unit_price), ("net amount", want["net"], got.amount)):
            if _differs(value, actual):
                wrong.append({"line": lid, "issue": field, "expected": str(value), "actual": actual})
        if got.vat_category != want["category"] or _rate(got.vat_rate) != want["rate"]:
            wrong.append({"line": lid, "issue": "VAT", "expected": f"{want['category']} {want['rate']}", "actual": f"{got.vat_category} {got.vat_rate}"})
    return Verdict.fail(f"{len(wrong)} line deviation(s) from the order", "order.lines", deviations=wrong) if wrong else Verdict.ok()


@oracle("einvoice.delta.order.vat", severity="hard", tags=INVOICE)
def order_vat(inv: Any, ctx: dict) -> Verdict:
    """The VAT breakdown has one entry per VAT category and rate of the order, with the taxable amount (lines − allowances +
    charges) and the VAT amount (taxable amount × rate) the order implies."""
    order = ctx.get("order")
    if not order:
        return Verdict.skip("no order in context")
    expected = _implied(order)["vat"]
    breakdown = {(b.category, _rate(b.rate)): b for b in inv.vat}
    wrong = [{"vat": f"{cat} {rate}", "issue": "not in the order"} for (cat, rate) in breakdown if (cat, rate) not in expected]
    for (cat, rate), (taxable, tax) in expected.items():
        got = breakdown.get((cat, rate))
        if got is None:
            wrong.append({"vat": f"{cat} {rate}", "issue": "missing"})
            continue
        for field, value, actual in (("taxable amount", taxable, got.taxable_amount), ("VAT amount", tax, got.tax_amount)):
            if _differs(value, actual):
                wrong.append({"vat": f"{cat} {rate}", "issue": field, "expected": str(value), "actual": actual})
    return Verdict.fail(f"{len(wrong)} VAT breakdown deviation(s) from the order", "order.vat", deviations=wrong) if wrong else Verdict.ok()


@oracle("einvoice.delta.order.totals", severity="hard", tags=INVOICE)
def order_totals(inv: Any, ctx: dict) -> Verdict:
    """The document totals — lines, allowances, charges, without VAT, VAT, with VAT, amount due — are those the order implies."""
    order = ctx.get("order")
    if not order:
        return Verdict.skip("no order in context")
    t = inv.totals
    actual = {"line total": t.line_net, "allowances": t.allowances or 0, "charges": t.charges or 0, "total without VAT": t.tax_exclusive,
              "VAT total": t.tax, "total with VAT": t.tax_inclusive, "amount due": t.payable}
    wrong = [{"total": name, "expected": str(value), "actual": actual[name]}
             for name, value in _implied(order)["totals"].items() if _differs(value, actual[name])]
    return Verdict.fail(f"{len(wrong)} total(s) differ from the order", "order.totals", deviations=wrong) if wrong else Verdict.ok()
