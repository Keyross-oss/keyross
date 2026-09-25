"""keyross test: every oracle must catch its bad case from the badset. Tests for the tests.

A gauge ships its bad cases in its own package (`<gauge>/badset/`, docs/spec/gauge.md), so `keyross test` checks an installed
gauge in any project; the project's `badset/` holds the bad cases of its own oracles and is looked at first."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from keyross.core.document import load
from keyross.core.invoice import load_invoice
from keyross.core.registry import registry
from keyross.core.runner import INVOICE_TAG, run
from keyross.oracles.adapter import adapters


def badset_dirs(badset_dir: str | Path = "badset", gauges: list[str] | None = None) -> list[Path]:
    """Where bad cases are looked for: the project's badset, then the badset each loaded gauge ships in its package."""
    names = list(gauges or []) + sorted({n.split(".")[2] for n in sys.modules if n.startswith("keyross.gauges.") and n.count(".") == 2})
    dirs = [Path(badset_dir)]
    for name in dict.fromkeys(names):
        module = sys.modules.get(name if "." in name else f"keyross.gauges.{name}")
        if module is not None and getattr(module, "__file__", None):
            dirs.append(Path(module.__file__).parent / "badset")
    return [d for d in dict.fromkeys(dirs) if d.is_dir()]


def _find(dirs: list[Path], names: list[str]) -> Path | None:
    return next((d / n for d in dirs for n in names if (d / n).exists()), None)


def run_badset(badset_dir: str | Path = "badset", gauge: str | None = None, ctx: dict | None = None,
               gauges: list[str] | None = None) -> list[tuple[str, bool, str]]:
    """For each oracle: look for <id>.xlsx|csv (an invoice oracle: <id>.xml, and its order in <id>.order.json) in the badset
    dirs; the oracle MUST fail on it. For each adapter: one bad case per rule family (<gauge>.<rule>[.<variant>].<ext> must
    raise <rule>). Returns (id, ok, message)."""
    results = []
    dirs = badset_dirs(badset_dir, gauges)
    for spec in registry.all(gauge=gauge):
        if spec.kind in ("contract", "adapter"):
            continue
        on_invoice = INVOICE_TAG in spec.tags
        f = _find(dirs, [f"{spec.id}.xml"] if on_invoice else [f"{spec.id}.xlsx", f"{spec.id}.csv"])
        if f is None:
            results.append((spec.id, False, "no bad case in the badset — an untested oracle lies one day"))
            continue
        c = dict(ctx or {})
        if on_invoice:
            order = f.parent / f"{spec.id}.order.json"          # the order the invoice must match
            if order.exists():
                c["order"] = json.loads(order.read_text(encoding="utf-8"))
            v = run(load_invoice(f), ids=[spec.id], ctx=c).verdicts[0]
            results.append((spec.id, v.failed, "catches its bad case" if v.failed else f"DOES NOT FAIL on {f.name} — dead oracle or badly built case"))
            continue
        before = f.parent / f"{spec.id}.before.xlsx"           # a conservation sentinel needs a reference document
        if before.exists():
            c["before"] = load(before)
        rep = run(load(f), ids=[spec.id], ctx=c)
        v = rep.verdicts[0]
        results.append((spec.id, v.failed, "catches its bad case" if v.failed else f"DOES NOT FAIL on {f.name} — dead oracle or badly built case"))
    for a in sorted(adapters.values(), key=lambda a: a.id):
        if not gauge or a.gauge == gauge:
            results.extend(a.badset(dirs))
    return results
