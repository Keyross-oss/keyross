"""The report: human-readable, generated locally. The nine sections will come from the Loop Store; here, the sections of one run."""
from __future__ import annotations

from datetime import datetime, timezone

from keyross.core.runner import Report
from keyross.core.verdict import Status

SYMBOL = {Status.OK: "✔", Status.FAIL: "✘", Status.SKIP: "◦"}


def terminal(rep: Report, verbose: bool = False) -> str:
    out = [f"keyross check {rep.document}"]
    for v in rep.verdicts:
        if v.silent and not verbose:
            continue                                   # sentinels only show in verbose mode (never to the agent)
        sev = f"[{v.flag}]" if v.failed else ""
        tag = " (sentinel)" if v.silent else ""
        out.append(f"  {SYMBOL[v.status]} {v.oracle_id:<26} {v.message}{tag}  {sev}")
        if verbose and v.failed and v.evidence:
            for k, val in list(v.evidence.items())[:3]:
                out.append(f"      {k}: {str(val)[:160]}")
    ok = sum(1 for v in rep.verdicts if v.status == Status.OK)
    red, yellow = len(rep.hard_failures), len(rep.soft_failures)
    verdict = "red flag — output rejected (exit 2)" if red else ("yellow flag — output accepted with warnings (exit 1)" if yellow else "green flag — output accepted (exit 0)")
    out.append(f"{ok} green · {red} red · {yellow} yellow — {verdict}")
    if rep.sentinel_failures:
        out.append(f"! {len(rep.sentinel_failures)} red sentinel(s) — logged, not returned to the agent")
    return "\n".join(out)


def markdown(rep: Report) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Keyross report — {rep.document}", f"_{now} · {rep.duration_ms} ms · exit {rep.exit_code}_", "",
             "## 1. Scope", f"- document: `{rep.document}`", f"- context: `{ {k: v for k, v in rep.context.items() if k != 'before'} }`", "",
             "## 3. Verifiers", "| oracle | version | flag | status | message |", "|---|---|---|---|---|"]
    for v in rep.verdicts:
        lines.append(f"| {v.oracle_id} | {v.version} | {v.flag}{' · sentinel' if v.silent else ''} | {v.status.value} | {v.message} |")
    lines += ["", "## 4. Deviations — evidence"]
    for v in rep.verdicts:
        if v.failed:
            lines.append(f"### {v.oracle_id} — {v.category}")
            for k, val in v.evidence.items():
                lines.append(f"- **{k}**: `{str(val)[:400]}`")
    lines += ["", "## 8. Integrity", f"- run flag: {rep.flag}", f"- red sentinels: {len(rep.sentinel_failures)}", "",
              "## 9. Recommendations", "- (to complete: every recommendation names the oracle that will measure it)"]
    return "\n".join(lines)
