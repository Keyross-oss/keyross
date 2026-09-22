"""keyross test: every oracle must catch its bad case from the badset. Tests for the tests."""
from __future__ import annotations

from pathlib import Path

from keyross.core.document import load
from keyross.core.registry import registry
from keyross.core.runner import run


def run_badset(badset_dir: str | Path = "badset", gauge: str | None = None, ctx: dict | None = None) -> list[tuple[str, bool, str]]:
    """For each oracle: look for badset/<id>.xlsx|csv; the oracle MUST fail on it. Returns (id, ok, message)."""
    results = []
    d = Path(badset_dir)
    for spec in registry.all(gauge=gauge):
        if spec.kind == "contract":
            continue
        candidates = [d / f"{spec.id}.xlsx", d / f"{spec.id}.csv"]
        f = next((c for c in candidates if c.exists()), None)
        if f is None:
            results.append((spec.id, False, "no bad case in the badset — an untested oracle lies one day"))
            continue
        c = dict(ctx or {})
        before = d / f"{spec.id}.before.xlsx"           # a conservation sentinel needs a reference document
        if before.exists():
            c["before"] = load(before)
        rep = run(load(f), ids=[spec.id], ctx=c)
        v = rep.verdicts[0]
        results.append((spec.id, v.failed, "catches its bad case" if v.failed else f"DOES NOT FAIL on {f.name} — dead oracle or badly built case"))
    return results
