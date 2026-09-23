"""The benchmark's tasks: 50 purchase orders to invoice (10 per scenario), and the amounts an invoice for each must carry.

The orders are fictitious and deterministic (seeded), across five scenarios: several VAT rates, exempt lines that need an
exemption reason, intra-community supplies and reverse charge (extra identifiers and delivery data), document-level
allowances and charges, quantities and prices whose product needs rounding. `python -m bench.einvoice.orders` rewrites
bench/einvoice/orders/*.json; the committed files are the benchmark."""
from __future__ import annotations

import json
import random
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

HERE = Path(__file__).resolve().parent
ORDERS_DIR = HERE / "orders"
CENT = Decimal("0.01")

ITEMS = [("Consulting, senior", "HUR"), ("Consulting, junior", "HUR"), ("Laptop stand", "C62"), ("USB-C dock", "C62"),
         ("Office chair", "C62"), ("Printer paper A4", "C62"), ("Cable, 5 m", "C62"), ("Training day", "DAY"),
         ("Software licence, annual", "C62"), ("Maintenance visit", "C62"), ("Diesel", "LTR"), ("Coffee beans", "KGM")]
STANDARD_RATES = ["20.00", "10.00", "5.50"]
SCENARIOS = ["domestic", "exempt", "intra_community", "reverse_charge", "allowances"]
FIRST_ISSUE = date(2026, 9, 1)
EXEMPTIONS = {
    "E": ("Exempt: medical care", "VATEX-EU-132-1C"),
    "K": ("Intra-community supply", "VATEX-EU-IC"),
    "AE": ("Reverse charge", "VATEX-EU-AE"),
}


def money(x: Decimal) -> Decimal:
    return x.quantize(CENT, rounding=ROUND_HALF_UP)


def _party(n: int, country: str, prefix: str) -> dict:
    digits = f"{n:02d}{n * 7919 % 1000000000:09d}"
    return {"name": f"{prefix} {n:02d} {'SAS' if country == 'FR' else 'GmbH'}", "vat_id": f"{country}{digits}",
            "address": {"line": f"{n} Example Street", "city": "Lille" if country == "FR" else "Cologne",
                        "postcode": "59000" if country == "FR" else "50667", "country": country}}


def make_order(i: int, rng: random.Random) -> dict:
    """Order i (1-based): scenarios in turn, 1 to 6 lines, one to three VAT rates."""
    scenario = SCENARIOS[(i - 1) % len(SCENARIOS)]
    buyer_country = "DE" if scenario in ("intra_community", "reverse_charge") else "FR"
    n_lines = 1 + (i % 4) + (i % 3)
    issued = FIRST_ISSUE + timedelta(days=i - 1)
    rates = STANDARD_RATES[: 1 + (i % 3)] if scenario in ("domestic", "exempt", "allowances") else []
    lines = []
    for k in range(n_lines):
        name, unit = ITEMS[(i * 3 + k) % len(ITEMS)]
        qty = Decimal(str(rng.choice([1, 2, 3, 5, 12]))) if unit == "C62" else Decimal(str(rng.choice(["1.5", "2.25", "7", "0.5", "12.75"])))
        price = Decimal(str(rng.choice(["19.99", "49.90", "120.00", "7.45", "0.89", "1250.00", "33.33", "89.95"])))
        if scenario == "intra_community":
            category, rate = "K", "0.00"
        elif scenario == "reverse_charge":
            category, rate = "AE", "0.00"
        elif scenario == "exempt" and k == 0:
            category, rate = "E", "0.00"
        else:
            category, rate = "S", rates[k % len(rates)]
        lines.append({"id": str(k + 1), "name": name, "quantity": str(qty), "unit_code": unit, "net_price": str(price),
                      "vat_category": category, "vat_rate": rate})
    order = {
        "id": f"order-{i:02d}", "scenario": scenario,
        "invoice": {"number": f"INV-2026-{1000 + i}", "issue_date": issued.isoformat(), "due_date": (issued + timedelta(days=30)).isoformat(),
                    "type_code": "380", "currency": "EUR", "buyer_reference": f"PO-{4700 + i}"},
        "seller": _party(i, "FR", "Seller"), "buyer": _party(50 + i, buyer_country, "Buyer"),
        "payment": {"means_code": "58", "iban": "FR7630006000011234567890189"},
        "lines": lines, "allowances": [], "charges": [],
    }
    if scenario == "intra_community":
        order["delivery"] = {"date": (issued - timedelta(days=20)).isoformat(), "country": "DE"}
    if scenario == "allowances":
        first = lines[0]
        order["allowances"].append({"amount": "15.00", "reason": "Loyalty discount", "vat_category": first["vat_category"], "vat_rate": first["vat_rate"]})
        if i % 2 == 0:
            order["charges"].append({"amount": "9.90", "reason": "Shipping", "vat_category": first["vat_category"], "vat_rate": first["vat_rate"]})
    used = {l["vat_category"] for l in lines}
    order["vat_exemptions"] = {c: {"reason": r, "code": code} for c, (r, code) in EXEMPTIONS.items() if c in used}
    return order


def expected(order: dict) -> dict:
    """The amounts an invoice for this order must carry (EN 16931 arithmetic, amounts rounded half-up to the cent)."""
    line_net = {l["id"]: money(Decimal(l["quantity"]) * Decimal(l["net_price"])) for l in order["lines"]}
    allowances = sum((Decimal(a["amount"]) for a in order["allowances"]), Decimal("0"))
    charges = sum((Decimal(c["amount"]) for c in order["charges"]), Decimal("0"))
    groups: dict[tuple[str, str], Decimal] = {}
    for l in order["lines"]:
        key = (l["vat_category"], l["vat_rate"])
        groups[key] = groups.get(key, Decimal("0")) + line_net[l["id"]]
    for a in order["allowances"]:
        groups[(a["vat_category"], a["vat_rate"])] -= Decimal(a["amount"])
    for c in order["charges"]:
        key = (c["vat_category"], c["vat_rate"])
        groups[key] = groups.get(key, Decimal("0")) + Decimal(c["amount"])
    vat = {f"{cat} {rate}": {"taxable": money(base), "tax": money(base * Decimal(rate) / 100)} for (cat, rate), base in sorted(groups.items())}
    line_total = sum(line_net.values(), Decimal("0"))
    tax_exclusive = line_total - allowances + charges
    tax = sum((v["tax"] for v in vat.values()), Decimal("0"))
    return {"line_net": {k: str(v) for k, v in line_net.items()}, "line_total": str(line_total), "allowances": str(allowances),
            "charges": str(charges), "tax_exclusive": str(tax_exclusive), "tax": str(tax), "tax_inclusive": str(tax_exclusive + tax),
            "payable": str(tax_exclusive + tax), "vat": {k: {"taxable": str(v["taxable"]), "tax": str(v["tax"])} for k, v in vat.items()}}


def load_orders() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(ORDERS_DIR.glob("order-*.json"))]


def write_orders(n: int = 50, seed: int = 2026) -> None:
    rng = random.Random(seed)
    ORDERS_DIR.mkdir(exist_ok=True)
    for i in range(1, n + 1):
        order = make_order(i, rng)
        (ORDERS_DIR / f"{order['id']}.json").write_text(json.dumps(order, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_orders()
    print(f"{len(load_orders())} orders written to {ORDERS_DIR}")
