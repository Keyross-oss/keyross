"""Telemetry: the events of every run — decisions, verdicts, sealed runs. JSONL locally; ClickHouse in production."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_PATH = ".keyross/events.jsonl"


class JsonlTelemetry:
    def __init__(self, path: str | Path = DEFAULT_PATH) -> None:
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, **fields: Any) -> None:
        fields.setdefault("at", datetime.now(timezone.utc).isoformat())
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(fields, ensure_ascii=False, default=str) + "\n")


def read_events(path: str | Path = DEFAULT_PATH) -> list[dict[str, Any]]:
    p = Path(path)
    if not p.exists():
        return []
    return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


def first_pass(events: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per gauge, from the yoke's verification events: documents written, first pass (green on the first write, no retry),
    first-pass rate, writes, pit stops. A falling rate means the model, the data or the rules drifted."""
    firsts: dict[tuple[str, str, str], bool] = {}
    counts: dict[str, dict[str, int]] = {}
    for e in events:
        if e.get("event_type") != "verification":
            continue
        gauge = str(e.get("gauge", "*"))
        c = counts.setdefault(gauge, {"writes": 0, "pit_stops": 0})
        c["writes"] += 1
        c["pit_stops"] += bool(e.get("reverted"))
        if e.get("attempt") == 1:
            firsts[(gauge, str(e.get("thread_id", "")), str(e.get("document", "")))] = bool(e.get("aligned"))
    out: dict[str, dict[str, Any]] = {}
    for gauge, c in sorted(counts.items()):
        docs = [ok for (g, _, _), ok in firsts.items() if g == gauge]
        out[gauge] = {"documents": len(docs), "first_pass": sum(docs),
                      "first_pass_rate": round(sum(docs) / len(docs), 3) if docs else None, **c}
    return out
