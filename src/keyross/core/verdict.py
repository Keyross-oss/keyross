"""The verdict: what an oracle returns, and nothing else. Serializable, readable, never carries a secret value."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class Status(str, Enum):
    OK = "ok"
    FAIL = "fail"
    SKIP = "skip"        # the oracle does not apply to this document (not an error)


class Severity(str, Enum):
    HARD = "hard"        # blocks: the output cannot be delivered
    SOFT = "soft"        # signals: negative reward, no blocking


@dataclass
class Verdict:
    status: Status
    message: str = ""
    category: str = ""                      # the category of the deviation — this is ALL the agent ever receives
    evidence: dict[str, Any] = field(default_factory=dict)   # proof: rows, expected, actual — never shown to the agent
    oracle_id: str = ""
    version: int | str = 0
    severity: Severity = Severity.HARD
    silent: bool = False                    # sentinel: no feedback to the agent, zero weight

    @classmethod
    def ok(cls, message: str = "ok", **evidence: Any) -> "Verdict":
        return cls(Status.OK, message, evidence=evidence)

    @classmethod
    def fail(cls, message: str, category: str = "", **evidence: Any) -> "Verdict":
        return cls(Status.FAIL, message, category=category or message.split(":")[0], evidence=evidence)

    @classmethod
    def skip(cls, message: str = "") -> "Verdict":
        return cls(Status.SKIP, message)

    @property
    def failed(self) -> bool:
        return self.status == Status.FAIL

    @property
    def flag(self) -> str:
        """The flag: green (ok / skip), yellow (soft failure), red (hard failure). Black is a run-level flag raised by scrutineering."""
        if not self.failed:
            return "green"
        return "red" if self.severity == Severity.HARD else "yellow"

    def minimal(self) -> dict[str, Any]:
        """The minimal sufficient feedback: the flag + the category. No logic, no threshold, no list, no evidence."""
        return {"status": self.status.value, "flag": self.flag, "category": self.category if self.failed else ""}

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["severity"] = self.severity.value
        d["flag"] = self.flag
        return d
