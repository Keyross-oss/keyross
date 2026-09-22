"""The runner: executes oracles on a document, returns a report and an exit code. Run by the harness, never by the model."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from keyross.core.document import Document
from keyross.core.registry import registry, OracleSpec
from keyross.core.verdict import Verdict, Status, Severity

EXIT_OK, EXIT_SOFT, EXIT_HARD = 0, 1, 2


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
    """Run invariants and sentinels (not contracts: they need before / after / params)."""
    ctx = ctx or {}
    t0 = time.perf_counter()
    specs = [s for s in registry.all() if s.kind in ("invariant", "sentinel")]
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
        v = Verdict.fail(f"no loaded gauge validates {path}", "document.unsupported")
        v.oracle_id = "keyross.check"
        report.verdicts.append(v)
    report.duration_ms = round((time.perf_counter() - t0) * 1000)
    return report


def run_contract(action: str, before: Document, after: Document, params: dict[str, Any], ctx: dict[str, Any] | None = None) -> list[Verdict]:
    """Instantiate the contracts of an action with the task's parameters — the harness calls this, never the LLM."""
    ctx = ctx or {}
    return [_apply(spec, (before, after, params), ctx) for spec in registry.contracts_for(action)]
