"""keyross.lock: the pinned oracles — id, version, code fingerprint. The answer to "what verified this run?"."""
from __future__ import annotations

import json
from pathlib import Path

from keyross.core.registry import registry


def write(path: str | Path = "keyross.lock") -> dict:
    data = {"oracles": {s.id: {"version": s.version, "fingerprint": s.fingerprint, "severity": s.severity.value, "kind": s.kind}
                        for s in registry.all()}}
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return data


def check(path: str | Path = "keyross.lock") -> list[str]:
    """Return the differences between the lock and the loaded oracles. Empty = pinning respected."""
    p = Path(path)
    if not p.exists():
        return ["keyross.lock missing — run `keyross lock`"]
    locked = json.loads(p.read_text(encoding="utf-8")).get("oracles", {})
    diffs = []
    for s in registry.all():
        L = locked.get(s.id)
        if L is None:
            diffs.append(f"{s.id}: not in lock")
        elif L["version"] != s.version or L["fingerprint"] != s.fingerprint:
            diffs.append(f"{s.id}: locked v{L['version']}/{L['fingerprint']}, loaded v{s.version}/{s.fingerprint}")
    for oid in locked:
        if oid not in {s.id for s in registry.all()}:
            diffs.append(f"{oid}: in lock, not loaded")
    return diffs
