"""Adapters: run an official validator (Schematron, published rules, a linter) as oracles inside a gauge — never reimplement it. A gauge built this way is homologated.

The adapter contract, in one sentence: an adapter is pinned (tool version + artifact checksum), runs offline,
maps every finding of the external tool to a Verdict (rule id → oracle id and category, tool severity → hard / soft),
and registers those verdicts under the same lock, scrutineering, minimal feedback and report as any other oracle.
Like pre-commit for linters: one config, one lock, many tools, one exit code."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable

from keyross.core.registry import registry, OracleSpec
from keyross.core.verdict import Verdict, Severity, Status


@dataclass
class AdapterPin:
    """What the lock records for an adapter: the tool, its version, the checksum of the rule artifacts it runs."""
    tool: str                 # e.g. "CEN/TC 434 EN 16931 validation artefacts"
    version: str              # the tool or artifact release, e.g. "1.3.16"
    artifact_sha256: str = "" # checksum of the rule artifacts actually executed (several files: see `digest`)
    offline: bool = True      # an adapter that needs the network at check time is not deterministic — refused
    artifacts: dict[str, str] = field(default_factory=dict)   # artifact path -> SHA-256, each verified before it runs

    @staticmethod
    def digest(artifacts: dict[str, str]) -> str:
        """One checksum for several artifacts: the SHA-256 of their sorted `sha256  path` manifest."""
        manifest = "".join(f"{sha}  {name}\n" for name, sha in sorted(artifacts.items()))
        return hashlib.sha256(manifest.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Rule:
    """One rule the adapter runs, as declared by the artifact itself (never retyped by hand)."""
    id: str                   # e.g. "BR-CO-10"
    severity: str             # the tool's own vocabulary: fatal / error / warning / info
    text: str = ""


@dataclass
class Finding:
    """One finding of the external tool, before it becomes a Verdict."""
    rule_id: str              # e.g. "BR-CO-10"
    severity: str             # the tool's own vocabulary: fatal / error / warning / info
    message: str
    location: str = ""        # XPath, row, field — evidence, never returned to the agent
    extra: dict[str, Any] = field(default_factory=dict)


class AdapterError(Exception):
    """The adapter refuses to give a verdict (pin mismatch, network needed, unreadable document): a hard red, never a guess."""

    def __init__(self, message: str, category: str) -> None:
        super().__init__(message)
        self.category = category


adapters: dict[str, "ExternalValidatorAdapter"] = {}


def family(rule_id: str) -> str:
    """The rule family: the rule id without its number — BR-CO-10 → BR-CO, BR-01 → BR, UBL-CR-005 → UBL-CR."""
    return re.sub(r"-\d+[a-z]?$", "", rule_id)


class ExternalValidatorAdapter:
    """Subclass this to wrap a validator. Implement `pin()`, `rules()`, `accepts(path)` and `findings(document)`; the rest is shared."""

    id: str = "external.adapter"
    gauge: str = "external"
    severity_map: dict[str, Severity] = {"fatal": Severity.HARD, "error": Severity.HARD, "warning": Severity.SOFT, "info": Severity.SOFT}

    def pin(self) -> AdapterPin:
        raise NotImplementedError

    def rules(self) -> Iterable[Rule]:
        """The rules of the pinned artifacts, read from the artifacts themselves."""
        raise NotImplementedError

    def accepts(self, path: str | Path) -> bool:
        """Whether this adapter validates this kind of document."""
        return False

    def findings(self, document: Any) -> Iterable[Finding]:
        """Run the tool offline on the document (a path or a canonical document) and yield its findings."""
        raise NotImplementedError

    def oracle_id(self, rule_id: str) -> str:
        return f"{self.gauge}.{rule_id.lower().replace('_', '-')}"

    def severity(self, tool_severity: str) -> Severity:
        return self.severity_map.get(tool_severity.lower(), Severity.HARD)   # an unknown severity blocks: we never guess

    def _refusal(self, message: str, category: str, **evidence: Any) -> list[Verdict]:
        v = Verdict.fail(message, category, **evidence)
        v.oracle_id, v.severity = self.id, Severity.HARD
        return [v]

    def verdicts(self, document: Any) -> list[Verdict]:
        """One verdict per failed rule (category = the rule id, locations in evidence), plus one green verdict for the adapter run."""
        p = self.pin()
        if not p.offline:
            return self._refusal("adapter needs the network at check time — refused", "adapter.not_offline")
        try:
            found = list(self.findings(document))
        except AdapterError as e:
            return self._refusal(str(e), e.category, pin=p.to_dict())
        except Exception as e:  # an adapter that crashes is a hard red, like an oracle that crashes
            return self._refusal(f"adapter error: {type(e).__name__}", "oracle.error", error=str(e))
        by_rule: dict[str, list[Finding]] = {}
        for f in found:
            by_rule.setdefault(f.rule_id, []).append(f)
        pin = {"tool": p.tool, "version": p.version, "artifact_sha256": p.artifact_sha256}
        out: list[Verdict] = []
        for rule_id, fs in sorted(by_rule.items()):
            severity = Severity.HARD if any(self.severity(f.severity) == Severity.HARD for f in fs) else Severity.SOFT
            v = Verdict.fail(fs[0].message, category=rule_id, rule=rule_id, text=fs[0].message,
                             occurrences=[{"location": f.location, **f.extra} for f in fs], pin=pin)
            v.oracle_id, v.severity, v.version = self.oracle_id(rule_id), severity, p.version
            out.append(v)
        summary = Verdict(Status.OK, f"{p.tool} {p.version}: {len(found)} finding(s) on {len(by_rule)} rule(s)", oracle_id=self.id,
                          evidence={"pin": pin})
        summary.version = p.version
        return out + [summary]

    def register(self) -> None:
        """Declare the adapter and one registry entry per rule id, so the lock pins the rules the adapter runs.
        A rule present in several artifacts takes its strictest severity; at check time the flag follows the executed artifact."""
        p = self.pin()
        adapters[self.id] = self
        try:
            rules = list(self.rules())
        except AdapterError:   # a missing or tampered artifact registers nothing: verdicts() refuses it, `lock --check` shows the gap
            rules = []
        merged: dict[str, Rule] = {}
        for r in rules:
            known = merged.get(r.id)
            if known is None or (self.severity(r.severity) == Severity.HARD and self.severity(known.severity) != Severity.HARD):
                merged[r.id] = r
        for rid, r in sorted(merged.items()):
            spec = OracleSpec(id=self.oracle_id(rid), fn=_evaluated_by_adapter, version=p.version, severity=self.severity(r.severity),
                              kind="adapter", doc=r.text, pinned=f"{rid}|{r.severity}|{p.artifact_sha256}")
            try:
                registry.add(spec)
            except ValueError:
                pass

    def rule_ids(self) -> set[str]:
        return {s.id for s in registry.all(kind="adapter", gauge=self.gauge)}

    def badset(self, badset_dir: str | Path | list[Path]) -> list[tuple[str, bool, str]]:
        """`<gauge>.<rule>[.<variant>].<ext>` must raise <rule>; every rule family must have at least one bad case. Several
        dirs (the project's badset, the gauge's own): a file name found in an earlier dir hides the same name in a later one."""
        dirs = [Path(d) for d in badset_dir] if isinstance(badset_dir, list) else [Path(badset_dir)]
        results, covered, seen = [], set(), set()
        known = self.rule_ids()
        own = [s.id for s in registry.all(gauge=self.gauge) if s.kind != "adapter"]   # the gauge's other oracles have bad cases too
        for f in sorted((f for d in dirs for f in d.glob(f"{self.gauge}.*")), key=lambda f: f.name):
            if f.name in seen or not self.accepts(f) or any(f.name.startswith(oid + ".") for oid in own):
                continue
            seen.add(f.name)
            oid = f"{self.gauge}.{f.name[len(self.gauge) + 1:].split('.')[0]}"
            if oid not in known:
                results.append((oid, False, f"{f.name}: no such rule in {self.pin().tool} {self.pin().version}"))
                continue
            failed = {v.oracle_id for v in self.verdicts(f) if v.failed}
            ok = oid in failed
            if ok:
                covered.add(family(registry.get(oid).pinned.split("|")[0]))
            results.append((oid, ok, f"catches its bad case ({f.name})" if ok else f"DOES NOT FAIL on {f.name} — {sorted(failed) or 'no finding'}"))
        families = {family(registry.get(oid).pinned.split("|")[0]) for oid in known}
        for fam in sorted(families - covered):
            results.append((f"{self.gauge}.{fam.lower()}-*", False, "no bad case for this rule family — an untested family lies one day"))
        return results


def _evaluated_by_adapter(doc: Any) -> Verdict:
    """Registry placeholder: an adapter rule is evaluated by its adapter, never called as a Python oracle."""
    return Verdict.skip("evaluated by its adapter")
