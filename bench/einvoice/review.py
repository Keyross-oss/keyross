"""The human review (PROTOCOL.md): at least 20 delivered invoices, the same number per arm — 7 per arm for three arms (21),
10 per arm for two — drawn with random.Random(2027) and renamed so the arm is hidden. The sheet shows the order and what the
invoice says — never the expected amounts nor any judge's verdict.

    python -m bench.einvoice.review sample bench/einvoice/results/<run>.jsonl    # writes results/<run>-review/
    python -m bench.einvoice.review score  bench/einvoice/results/<run>.jsonl    # after review.csv is filled in
"""
from __future__ import annotations

import csv
import json
import math
import random
import sys
from pathlib import Path

from keyross.core.invoice import load_invoice

from bench.einvoice.agent import ARMS, task_message
from bench.einvoice.orders import load_orders

SEED, REVIEWED = 2027, 20            # at least 20 invoices, the same number per arm (protocol, deviation 4)


def _rows(results: Path) -> list[dict]:
    rows = [json.loads(l) for l in results.read_text(encoding="utf-8").splitlines() if l.strip()]
    latest = {(r["task"], r["arm"], r["rep"]): r for r in rows if "error" not in r}      # a retry replaces its failed run
    return [latest[k] for k in sorted(latest)]


def _render(xml: Path) -> str:
    """What the invoice says, as read from its XML — no expected value, no verdict."""
    try:
        inv = load_invoice(xml)
    except Exception as e:  # noqa: BLE001 — an unreadable invoice is shown as such
        return f"*The XML could not be read ({type(e).__name__}); open the file.*"
    t = inv.totals
    out = [f"- number {inv.number} · issued {inv.issue_date} · type {inv.type_code} · currency {inv.currency}",
           f"- seller {inv.seller.name} ({inv.seller.vat_id}, {inv.seller.country}) · buyer {inv.buyer.name} ({inv.buyer.vat_id}, {inv.buyer.country})",
           "", "| line | item | quantity | unit | net price | net amount | VAT |", "|---|---|---|---|---|---|---|"]
    out += [f"| {l.number} | {l.designation} | {l.qty} | {l.unit} | {l.unit_price} | {l.amount} | {l.vat_category} {l.vat_rate} |" for l in inv.lines]
    out += ["", "| VAT category | rate | taxable | tax | exemption |", "|---|---|---|---|---|"]
    out += [f"| {b.category} | {b.rate} | {b.taxable_amount} | {b.tax_amount} | {b.exemption_reason or ''} {b.exemption_code or ''} |" for b in inv.vat]
    out += ["", f"Totals: lines {t.line_net} · allowances {t.allowances} · charges {t.charges} · without VAT {t.tax_exclusive} · "
                f"VAT {t.tax} · with VAT {t.tax_inclusive} · due {t.payable}"]
    return "\n".join(out)


def sample(results: Path) -> Path:
    rows = [r for r in _rows(results) if r.get("delivered")]
    rng = random.Random(SEED)
    arms = [arm for arm in ARMS if any(r["arm"] == arm for r in rows)]
    per_arm = math.ceil(REVIEWED / len(arms)) if arms else 0
    picked = []
    for arm in arms:
        pool = [r for r in rows if r["arm"] == arm]
        picked += rng.sample(pool, min(per_arm, len(pool)))
    rng.shuffle(picked)
    invoices = results.parent / results.stem
    folder = results.parent / f"{results.stem}-review"
    folder.mkdir(exist_ok=True)
    orders = {o["id"]: o for o in load_orders()}
    key, sheet = {}, ["# Human review — blind", "",
                      "For each invoice, decide whether it is a **correct invoice for its order**: the parties, every line, the VAT "
                      "breakdown (with the exemption reason where one is due), the totals and the amount due — what a buyer or a tax "
                      "office would accept. Check against the order, and open the XML when in doubt. Write `correct` or `incorrect` "
                      "and what is wrong in `review.csv`. Do not open `../" + f"{results.stem}-review-key.json` before you are done.", ""]
    for i, r in enumerate(picked, start=1):
        name = f"invoice-{i:02d}"
        xml = invoices / f"{r['task']}-{r['arm']}-{r['rep']}.xml"
        (folder / f"{name}.xml").write_bytes(xml.read_bytes())
        key[name] = {"task": r["task"], "arm": r["arm"], "rep": r["rep"], "correct": r["correct"]}
        sheet += [f"## {name} — {r['task']}", "", "**The order**", "", task_message(orders[r["task"]]).split("\n", 1)[1], "",
                  "**What the invoice says**", "", _render(folder / f"{name}.xml"), ""]
    (folder / "REVIEW.md").write_text("\n".join(sheet), encoding="utf-8")
    with open(folder / "review.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["invoice", "verdict", "what is wrong"])
        w.writerows([[name, "", ""] for name in key])
    (results.parent / f"{results.stem}-review-key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    return folder


def score(results: Path) -> str:
    folder = results.parent / f"{results.stem}-review"
    key = json.loads((results.parent / f"{results.stem}-review-key.json").read_text(encoding="utf-8"))
    with open(folder / "review.csv", newline="", encoding="utf-8") as f:
        human = {row["invoice"]: row for row in csv.DictReader(f)}
    done = {n: h for n, h in human.items() if h["verdict"].strip().lower() in ("correct", "incorrect")}
    agree = [n for n, h in done.items() if (h["verdict"].strip().lower() == "correct") == key[n]["correct"]]
    per_arm = [f"{ARMS[arm]} {sum(1 for n in agree if key[n]['arm'] == arm)}/{sum(1 for n in done if key[n]['arm'] == arm)}"
               for arm in ARMS if any(key[n]["arm"] == arm for n in done)]
    lines = ["# Human review — agreement with the automated judges", "",
             f"{len(done)}/{len(key)} invoices reviewed · the human verdict agrees with the three judges on {len(agree)}/{len(done)}"
             + (f" ({', '.join(per_arm)})" if per_arm else "") + ".", ""]
    for n in sorted(set(done) - set(agree)):
        k, h = key[n], done[n]
        lines.append(f"- {n} ({k['task']}, {ARMS[k['arm']]}, rep {k['rep']}): judges say {'correct' if k['correct'] else 'incorrect'}, "
                     f"the reviewer says {h['verdict'].strip()} — {h['what is wrong'].strip()}")
    text = "\n".join(lines) + "\n"
    (folder / "SCORE.md").write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    command, path = sys.argv[1], Path(sys.argv[2])
    print(sample(path) if command == "sample" else score(path))
