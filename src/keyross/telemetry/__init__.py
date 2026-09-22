"""Telemetry: the events of every run — decisions, verdicts, sealed runs. JSONL locally; ClickHouse in production (the adaptiq repo)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JsonlTelemetry:
    def __init__(self, path: str | Path = ".keyross/events.jsonl") -> None:
        self.path = Path(path); self.path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, **fields: Any) -> None:
        fields.setdefault("at", datetime.now(timezone.utc).isoformat())
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(fields, ensure_ascii=False, default=str) + "\n")
