"""Adapters: run an official validator (Schematron, published rules, a linter) as oracles inside a gauge — never reimplement it. A gauge built this way is homologated.

The adapter contract, in one sentence: an adapter is pinned (tool version + artifact checksum), runs offline,
maps every finding of the external tool to a Verdict (rule id → oracle id, tool severity → hard / soft),
and registers those verdicts under the same lock, gate, minimal feedback and report as any other oracle.
Like pre-commit for linters: one config, one lock, many tools, one exit code."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from keyross.core.registry import registry, OracleSpec
from keyross.core.verdict import Verdict, Severity, Status


@dataclass
class AdapterPin:
    """What the lock records for an adapter: the tool, its version, the checksum of the rule artifacts it runs."""
    tool: str                 # e.g. "akretion/factur-x", "kosit/validator", "dora-roi-validator"
    version: str              # the tool or artifact release, e.g. "EN16931 1.3.13"
    artifact_sha256: str = "" # checksum of the rule artifacts (Schematron, XSLT, schema) actually executed
    offline: bool = True      # an adapter that needs the network at check time is not deterministic — refused


@dataclass
class Finding:
    """One finding of the external tool, before it becomes a Verdict."""
    rule_id: str              # e.g. "BR-CO-10"
    severity: str             # the tool's own vocabulary: fatal / error / warning / info
    message: str
    location: str = ""        # XPath, row, field — evidence, never returned to the agent
    extra: dict[str, Any] = field(default_factory=dict)


class ExternalValidatorAdapter:
    """Subclass this to wrap a validator. Implement `pin()` and `findings(document)`; everything else is shared."""

    gauge: str = "external"
    severity_map: dict[str, Severity] = {"fatal": Severity.HARD, "error": Severity.HARD, "warning": Severity.SOFT, "info": Severity.SOFT}

    def pin(self) -> AdapterPin:
        raise NotImplementedError

    def findings(self, document: Any) -> Iterable[Finding]:
        """Run the tool offline on the document (a path or a canonical document) and yield its findings."""
        raise NotImplementedError

    def oracle_id(self, rule_id: str) -> str:
        return f"{self.gauge}.{rule_id.lower().replace('_', '-')}"

    def verdicts(self, document: Any) -> list[Verdict]:
        p = self.pin()
        if not p.offline:
            return [Verdict.fail("adapter needs the network at check time — refused", "adapter.not_offline", oracle_id=f"{self.gauge}.adapter")]
        out: list[Verdict] = []
        for f in self.findings(document):
            sev = self.severity_map.get(f.severity.lower(), Severity.SOFT)
            v = Verdict.fail(f"{f.rule_id}: {f.message}", category=f.rule_id, location=f.location, **f.extra)
            v.oracle_id, v.severity = self.oracle_id(f.rule_id), sev
            v.version = 0
            v.evidence["pin"] = {"tool": p.tool, "version": p.version, "artifact_sha256": p.artifact_sha256}
            out.append(v)
        if not out:
            out.append(Verdict(Status.OK, f"{p.tool} {p.version}: no finding", oracle_id=f"{self.gauge}.adapter"))
        return out

    def register(self, rule_ids: Iterable[str]) -> None:
        """Declare one registry entry per rule id, so the lock pins the rules the adapter is expected to run."""
        p = self.pin()
        for rid in rule_ids:
            oid = self.oracle_id(rid)
            spec = OracleSpec(id=oid, fn=lambda doc, _rid=rid: Verdict.skip(f"{_rid}: evaluated by adapter"), version=0,
                              severity=Severity.HARD, kind="adapter", doc=f"{p.tool} {p.version} — rule {rid}")
            try:
                registry.add(spec)
            except ValueError:
                pass
