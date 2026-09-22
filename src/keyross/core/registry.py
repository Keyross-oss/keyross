"""The registry: every oracle has an identity, a version, a severity. Declared, never discovered by accident."""
from __future__ import annotations

import hashlib
import inspect
from dataclasses import dataclass, field
from typing import Callable

from keyross.core.verdict import Verdict, Severity

OracleFn = Callable[..., Verdict]


@dataclass
class OracleSpec:
    id: str
    fn: OracleFn
    version: int = 1
    severity: Severity = Severity.HARD
    silent: bool = False              # sentinel
    kind: str = "invariant"           # invariant | contract | sentinel
    action: str | None = None         # for a contract: the action it verifies
    doc: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def fingerprint(self) -> str:
        """Code fingerprint: changes when the oracle changes. This is what the lock pins."""
        try:
            src = inspect.getsource(self.fn)
        except OSError:
            src = self.fn.__name__
        return hashlib.sha1(src.encode()).hexdigest()[:12]


class Registry:
    def __init__(self) -> None:
        self._oracles: dict[str, OracleSpec] = {}

    def add(self, spec: OracleSpec) -> None:
        if spec.id in self._oracles:
            raise ValueError(f"oracle already declared: {spec.id}")
        self._oracles[spec.id] = spec

    def get(self, oracle_id: str) -> OracleSpec:
        return self._oracles[oracle_id]

    def all(self, kind: str | None = None, gauge: str | None = None) -> list[OracleSpec]:
        out = list(self._oracles.values())
        if kind:
            out = [o for o in out if o.kind == kind]
        if gauge:
            out = [o for o in out if o.id.startswith(gauge + ".")]
        return sorted(out, key=lambda o: o.id)

    def contracts_for(self, action: str) -> list[OracleSpec]:
        return [o for o in self._oracles.values() if o.kind == "contract" and o.action == action]

    def clear(self) -> None:
        self._oracles.clear()


registry = Registry()


def oracle(id: str, *, severity: str | Severity = "hard", version: int = 1, silent: bool = False, tags: list[str] | None = None):
    """Declare an invariant: (document, context) -> Verdict. Pure, deterministic, no network, no model."""
    def deco(fn: OracleFn) -> OracleFn:
        registry.add(OracleSpec(id=id, fn=fn, version=version, severity=Severity(severity), silent=silent,
                                kind="sentinel" if silent else "invariant", doc=(fn.__doc__ or "").strip(), tags=tags or []))
        fn.__keyross__ = registry.get(id)  # type: ignore[attr-defined]
        return fn
    return deco


def contract(action: str, *, id: str | None = None, severity: str | Severity = "hard", version: int = 1):
    """Declare an action contract: (before, after, params) -> Verdict. Instantiated by the harness with the plan's parameters."""
    def deco(fn: OracleFn) -> OracleFn:
        oid = id or f"contract.{action}"
        registry.add(OracleSpec(id=oid, fn=fn, version=version, severity=Severity(severity), kind="contract", action=action,
                                doc=(fn.__doc__ or "").strip()))
        fn.__keyross__ = registry.get(oid)  # type: ignore[attr-defined]
        return fn
    return deco
