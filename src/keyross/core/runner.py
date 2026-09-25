"""The runner: executes oracles on a document, returns a report and an exit code. Run by the harness, never by the model."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from keyross.core.document import Document, load
from keyross.core.invoice import Invoice, load_invoice
from keyross.core.registry import registry, OracleSpec
from keyross.core.verdict import Verdict, Status, Severity

EXIT_OK, EXIT_SOFT, EXIT_HARD = 0, 1, 2
TABULAR_SUFFIXES = (".xlsx", ".xlsm", ".csv")   # read by the tabular loader, checked by invariants and sentinels
ADAPTER_SUFFIXES = (".xml",)                     # checked by adapters (official validators), then by the invoice oracles
INVOICE_TAG = "invoice"                          # an oracle with this tag reads the canonical Invoice, not a table


@dataclass
class Report:
    document: str
    verdicts: list[Verdict] = field(default_factory=list)
    duration_ms: int = 0
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def hard_failures(self) -> list[Verdict]:
        return [v for v in self.verdicts if v.failed and v.severity == Severity.HARD and not v.silent]

    @property
    def soft_failures(self) -> list[Verdict]:
        return [v for v in self.verdicts if v.failed and v.severity == Severity.SOFT and not v.silent]

    @property
    def sentinel_failures(self) -> list[Verdict]:
        """Red sentinels: never returned to the agent, only logged — the signature of a workaround."""
        return [v for v in self.verdicts if v.failed and v.silent]

    @property
    def flag(self) -> str:
        """The run's flag: red if any hard failure, yellow if only soft ones, green otherwise. Black is raised by scrutineering
        when the agent reported green and the gate found red (see gate.scrutineering)."""
        return "red" if self.hard_failures else ("yellow" if self.soft_failures else "green")

    @property
    def aligned(self) -> bool:
        """First pass: green with no retry. Tracked over time, the first-pass rate is the health of the yoke:
        a falling rate means the model, the data or the rules drifted. (Not "alignment": that word belongs to model safety.)"""
        return self.flag == "green"

    @property
    def exit_code(self) -> int:
        if self.hard_failures:
            return EXIT_HARD
        if self.soft_failures:
            return EXIT_SOFT
        return EXIT_OK

    def minimal(self) -> list[dict[str, Any]]:
        """What the agent receives: flag + category, no sentinels, no evidence."""
        return [v.minimal() for v in self.verdicts if not v.silent and v.status != Status.SKIP]

    def to_dict(self) -> dict[str, Any]:
        return {"document": self.document, "duration_ms": self.duration_ms, "exit_code": self.exit_code, "flag": self.flag,
                "context": self.context, "verdicts": [v.to_dict() for v in self.verdicts]}


def _apply(spec: OracleSpec, args: tuple, ctx: dict[str, Any]) -> Verdict:
    try:
        v = spec.fn(*args, ctx) if _wants_ctx(spec) else spec.fn(*args)
    except Exception as e:  # an oracle that crashes is a hard red: we never guess
        v = Verdict.fail(f"oracle error: {type(e).__name__}", category="oracle.error", error=str(e))
    v.oracle_id, v.version, v.severity, v.silent = spec.id, spec.version, spec.severity, spec.silent
    return v


def _wants_ctx(spec: OracleSpec) -> bool:
    import inspect
    n = len(inspect.signature(spec.fn).parameters)
    return (spec.kind != "contract" and n >= 2) or (spec.kind == "contract" and n >= 4)


def run(doc: Document, *, gauge: str | None = None, ids: list[str] | None = None, ctx: dict[str, Any] | None = None) -> Report:
    """Run invariants and sentinels (not contracts: they need before / after / params) — those written for this kind of
    document: an Invoice gets the oracles tagged "invoice", a table the others."""
    ctx = ctx or {}
    t0 = time.perf_counter()
    on_invoice = isinstance(doc, Invoice)
    specs = [s for s in registry.all() if s.kind in ("invariant", "sentinel") and (INVOICE_TAG in s.tags) == on_invoice]
    if gauge:
        specs = [s for s in specs if s.id.startswith(gauge + ".")]
    if ids:
        specs = [s for s in specs if s.id in ids]
    report = Report(document=doc.path, context=ctx)
    for spec in specs:
        report.verdicts.append(_apply(spec, (doc,), ctx))
    report.duration_ms = round((time.perf_counter() - t0) * 1000)
    return report


def run_adapters(path: str, *, gauge: str | None = None, only: list[str] | None = None, ctx: dict[str, Any] | None = None) -> Report:
    """Run the registered adapters that accept this document (an official validator, pinned, offline). No adapter = hard red."""
    from keyross.oracles.adapter import adapters
    t0 = time.perf_counter()
    report = Report(document=str(path), context=ctx or {})
    for a in sorted(adapters.values(), key=lambda a: a.id):
        if (gauge and a.gauge != gauge) or (only and a.id not in only) or not a.accepts(path):
            continue
        report.verdicts.extend(a.verdicts(path))
    if not report.verdicts:
        hint = " — an EN 16931 invoice? keyross add einvoice" if Path(path).suffix.lower() == ".xml" else ""
        v = Verdict.fail(f"no loaded gauge validates {Path(path).name}{hint}", "document.unsupported")
        v.oracle_id = "keyross.check"
        report.verdicts.append(v)
    report.duration_ms = round((time.perf_counter() - t0) * 1000)
    return report


def check_file(path: str | Path, *, gauge: str | None = None, ctx: dict[str, Any] | None = None, only: list[str] | None = None,
               before: str | Path | Document | None = None) -> Report:
    """One document through the loaded gauges — the same verdicts whether the CLI, scrutineering or a yoke asks.
    Tabular documents go to the invariants and sentinels (`before` is the reference of a conservation sentinel), XML to the
    adapters. Raises ValueError when the tabular loader cannot read the document."""
    if Path(path).suffix.lower() in ADAPTER_SUFFIXES:
        report = run_adapters(str(path), gauge=gauge, only=only, ctx=ctx)
        if any(INVOICE_TAG in s.tags and s.kind in ("invariant", "sentinel") for s in registry.all(gauge=gauge)):
            try:
                invoice = load_invoice(path)
            except (ValueError, OSError, SyntaxError):  # unreadable or not an invoice: the adapters' verdict already says so
                return report
            extra = run(invoice, gauge=gauge, ctx=ctx)
            report.verdicts += extra.verdicts
            report.duration_ms += extra.duration_ms
        return report
    c = dict(ctx or {})
    if before is not None:
        c["before"] = before if isinstance(before, Document) else load(before)
    return run(load(path), gauge=gauge, ctx=c)


def unreadable(document: str, error: str) -> Report:
    """A document nothing can verify is a hard red, never a pass: the report of an output the loader could not read."""
    v = Verdict.fail(f"unreadable document: {error}", "document.unreadable")
    v.oracle_id = "keyross.check"
    return Report(document=document, verdicts=[v])


def run_contract(action: str, before: Document, after: Document, params: dict[str, Any], ctx: dict[str, Any] | None = None) -> list[Verdict]:
    """Instantiate the contracts of an action with the task's parameters — the harness calls this, never the LLM."""
    ctx = ctx or {}
    return [_apply(spec, (before, after, params), ctx) for spec in registry.contracts_for(action)]
