"""keyross.lock: the pinned oracles — id, version, code fingerprint. The answer to "what verified this run?"."""
from __future__ import annotations

import json
from pathlib import Path

from keyross.core.registry import registry
from keyross.oracles.adapter import adapters


def _adapter_pins() -> dict:
    return {a.id: {k: v for k, v in a.pin().to_dict().items() if k != "artifacts"} | {"artifacts": dict(sorted(a.pin().artifacts.items()))}
            for a in adapters.values()}


def write(path: str | Path = "keyross.lock") -> dict:
    data = {"oracles": {s.id: {"version": s.version, "fingerprint": s.fingerprint, "severity": s.severity.value, "kind": s.kind}
                        for s in registry.all()}}
    if adapters:
        data["adapters"] = _adapter_pins()
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return data


def check(path: str | Path = "keyross.lock") -> list[str]:
    """Return the differences between the lock and the loaded oracles. Empty = pinning respected."""
    p = Path(path)
    if not p.exists():
        return ["keyross.lock missing — run `keyross lock`"]
    data = json.loads(p.read_text(encoding="utf-8"))
    locked = data.get("oracles", {})
    diffs = []
    locked_adapters, loaded_adapters = data.get("adapters", {}), _adapter_pins()
    for aid, pin in loaded_adapters.items():
        L = locked_adapters.get(aid)
        if L is None:
            diffs.append(f"{aid}: adapter not in lock")
        elif (L.get("version"), L.get("artifact_sha256")) != (pin["version"], pin["artifact_sha256"]):
            diffs.append(f"{aid}: locked {L.get('version')}/{str(L.get('artifact_sha256'))[:12]}, loaded {pin['version']}/{pin['artifact_sha256'][:12]}")
    for aid in locked_adapters:
        if aid not in loaded_adapters:
            diffs.append(f"{aid}: adapter in lock, not loaded")
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
