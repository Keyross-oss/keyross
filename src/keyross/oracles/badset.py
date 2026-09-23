"""keyross test: every oracle must catch its bad case from the badset. Tests for the tests."""
from __future__ import annotations

from pathlib import Path

import json

from keyross.core.document import load
from keyross.core.invoice import load_invoice
from keyross.core.registry import registry
from keyross.core.runner import INVOICE_TAG, run
from keyross.oracles.adapter import adapters


def run_badset(badset_dir: str | Path = "badset", gauge: str | None = None, ctx: dict | None = None) -> list[tuple[str, bool, str]]:
    """For each oracle: look for badset/<id>.xlsx|csv (an invoice oracle: badset/<id>.xml, and its order in <id>.order.json);
    the oracle MUST fail on it. For each adapter: one bad case per rule family (badset/<gauge>.<rule>[.<variant>].<ext> must
    raise <rule>). Returns (id, ok, message)."""
    results = []
    d = Path(badset_dir)
    for spec in registry.all(gauge=gauge):
        if spec.kind in ("contract", "adapter"):
            continue
        on_invoice = INVOICE_TAG in spec.tags
        candidates = [d / f"{spec.id}.xml"] if on_invoice else [d / f"{spec.id}.xlsx", d / f"{spec.id}.csv"]
        f = next((c for c in candidates if c.exists()), None)
        if f is None:
            results.append((spec.id, False, "no bad case in the badset — an untested oracle lies one day"))
            continue
        c = dict(ctx or {})
        if on_invoice:
            order = d / f"{spec.id}.order.json"                # the order the invoice must match
            if order.exists():
                c["order"] = json.loads(order.read_text(encoding="utf-8"))
            v = run(load_invoice(f), ids=[spec.id], ctx=c).verdicts[0]
            results.append((spec.id, v.failed, "catches its bad case" if v.failed else f"DOES NOT FAIL on {f.name} — dead oracle or badly built case"))
            continue
        before = d / f"{spec.id}.before.xlsx"           # a conservation sentinel needs a reference document
        if before.exists():
            c["before"] = load(before)
        rep = run(load(f), ids=[spec.id], ctx=c)
        v = rep.verdicts[0]
        results.append((spec.id, v.failed, "catches its bad case" if v.failed else f"DOES NOT FAIL on {f.name} — dead oracle or badly built case"))
    for a in sorted(adapters.values(), key=lambda a: a.id):
        if not gauge or a.gauge == gauge:
            results.extend(a.badset(d))
    return results
