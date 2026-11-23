"""Export a finished run for the claims page, docs/claims/: what the page replays, run by run, and every figure it
shows, computed from the raw results with the report's own functions, so that the page carries no number typed by
hand.

    python -m bench.claims.page bench/claims/results/<run>.jsonl          # writes docs/claims/data/
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

from bench.claims import run as R
from bench.claims import verifier as V

DATA = Path(__file__).resolve().parents[2] / "docs" / "claims" / "data"

# What a clause's rule holds, for the page to show a clause condition by condition.
RULE_KEYS = ("when", "requires", "applies_when", "otherwise", "ceiling", "deductible")

# One sentence of the model's own reasoning, for each claim on which the model alone executed wrong decisions: the page
# quotes it to say why. Chosen by hand from the run, by instruction. A sentence is exported only if it is word for word
# in its run's answer and that answer, executed as it stands, was wrong; a test checks the published data holds them all.
EXCERPTS: dict[str, dict[str, tuple[int, str]]] = {
    "velo-local-commun": {
        "base": (4, "Si le local n'était pas fermé, il n'y a pas eu d'effraction"),
        "reinforced": (1, "Il n'y a pas eu effraction puisque le local était ouvert")},
    "velo-local-commun-antivol": {
        "base": (5, ("La destruction de l'antivol du vélo ne constitue pas une effraction au sens des conditions générales "
                     "(qui se rapporte au local assuré, pas au bien individuel)"))},
    "bougie-table": {
        "base": (2, "il n'y a donc pas d'embrasement ou de combustion avec flammes"),
        "reinforced": (3, ("la bougie a fondu mais il n'y a pas eu de combustion avec flammes décrite par l'assuré ; "
                           "il y a seulement eu de la chaleur"))},
    "velo-cave-retard": {
        "base": (7, ("Le seul point d'attention est le retard dans la déclaration (28 jours au lieu de 8), mais sans "
                     "préjudice démontré pour l'assureur")),
        "reinforced": (7, "Le retard dans la déclaration ne paraît pas causer un préjudice démontré")},
}


def _plain(x: Any) -> Any:
    """YAML dates and tuples, as JSON."""
    if isinstance(x, date):
        return x.isoformat()
    if isinstance(x, dict):
        return {k: _plain(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_plain(v) for v in x]
    return x


def _answer(a: dict[str, Any], lanes: dict[str, Any]) -> dict[str, Any]:
    """One free answer as recorded, and what each lane made of it; the strict report is the trace."""
    return {"text": a["text"], "chunks": a["chunks"], "ms": a["ms"], "first_text_ms": a["first_text_ms"],
            "decision": lanes["off"]["decision"],
            "outcome": {lane: lanes[lane]["grade"]["outcome"] for lane, _ in R.LANES},
            "final": {mode: lanes[mode]["report"]["context"]["final"] for mode in V.MODES},
            "report": lanes["strict"]["report"]}


def runs_of(rows: list[dict[str, Any]], case: str) -> dict[str, Any]:
    out = []
    for r in sorted((r for r in rows if r["case"] == case and "error" not in r), key=lambda r: r["rep"]):
        out.append({"rep": r["rep"], "extract_ms": r["extract"]["ms"], "base": _answer(r["answer"], r["lanes"]),
                    "reinforced": _answer(r["answer_reinforced"], r["lanes_reinforced"])})
    return {"case": case, "runs": out}


def excerpts(rows: list[dict[str, Any]], case: str) -> dict[str, dict[str, Any]]:
    """The chosen sentences of the model for one claim, each kept only if it is word for word in its run's answer and
    that answer, executed as it stands, was wrong."""
    keys = {ins: key for ins, _, key in R.INSTRUCTIONS}
    out = {}
    for ins, (rep, quote) in EXCERPTS.get(case, {}).items():
        r = next((r for r in rows if r["case"] == case and r["rep"] == rep and "error" not in r), None)
        if r is not None and quote in r[keys[ins]]["text"] and R.lanes_of(r, ins)["off"]["grade"]["harmful"]:
            out[ins] = {"rep": rep, "quote": quote}
    return out


def _counts(ok: list[dict[str, Any]], ins: str, lane: str, case: str | None = None) -> dict[str, Any]:
    g = [x[lane]["grade"] for x in R._runs(ok, ins, case)]
    return {"n": len(g), "harmful": sum(x["harmful"] for x in g), "outcomes": dict(Counter(x["outcome"] for x in g))}


def summary(rows: list[dict[str, Any]], source: str) -> dict[str, Any]:
    ok = [r for r in rows if "error" not in r]
    k, cases = V.contract(), V.cases()
    arms = {f"{ins}.{lane}": _counts(ok, ins, lane) for _, _, ins, lane in R.ARMS + R.LENIENT}
    by_case = {c["id"]: {f"{ins}.{lane}": _counts(ok, ins, lane, c["id"]) for _, _, ins, lane in R.ARMS + R.LENIENT}
               for c in cases}
    quotations, unexact, last_line = {}, [], {}
    for ins, _, _ in R.INSTRUCTIONS:
        runs = R._runs(ok, ins)
        quotes = [q for x in runs for q in x["strict"]["report"]["context"]["quotations"]]
        quotations[ins] = {"answers": len(runs), "total": len(quotes), "kinds": dict(Counter(q["kind"] for q in quotes)),
                           "near": sum(bool(q.get("near")) for q in quotes),
                           "answers_not_word_for_word": sum(any(q["kind"] in ("not_found", "wrong_article")
                                                                for q in x["strict"]["report"]["context"]["quotations"])
                                                            for x in runs)}
        last_line[ins] = {"answers": len(runs), "readable": sum(x["off"]["decision"] is not None for x in runs),
                          "exact": sum(bool((x["off"]["decision"] or {}).get("exact")) for x in runs)}
    for r in sorted(ok, key=lambda r: (r["case"], r["rep"])):
        for ins, _, _ in R.INSTRUCTIONS:
            for q in R.lanes_of(r, ins)["strict"]["report"]["context"]["quotations"]:
                if q["kind"] in ("not_found", "wrong_article"):
                    unexact.append({"case": r["case"], "rep": r["rep"], "instruction": ins, **q})
    boxes = {}
    for mode in V.MODES:
        f = [r["lanes"][mode]["facts"] for r in ok]
        boxes[mode] = {"boxes": sum(x["boxes"] for x in f), "proposed_right": sum(x["proposed_right"] for x in f),
                       "kept_right": sum(x["kept_right"] for x in f),
                       "codes": dict(Counter(c["code"] for r in ok for c in r["lanes"][mode]["report"]["context"]["facts"].values()))}
    entries = R.calibration(ok)
    values = [e for e in entries if e["kind"] == "value"]

    def grouped(items: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
        return [{**dict(zip(keys, key)), "count": len(g), "runs": sorted({e["rep"] for e in g})}
                for key, g in R._group(items, *keys)]

    costs = [r["cost_usd"] for r in ok if r.get("cost_usd") is not None]
    expected = {c["id"]: c["expected"]["action"]["type"] for c in cases}
    cost = {}
    for ins, _, _ in R.INSTRUCTIONS:       # the verifier's decisions that are not correct, and what they cost a person
        wrong = [(r["case"], R.lanes_of(r, ins)["strict"]) for r in ok if not R.lanes_of(r, ins)["strict"]["grade"]["correct"]]
        right = sum(lane["report"]["context"]["final"]["type"] == expected[case] == "transmettre" for case, lane in wrong)
        cost[ins] = {"not_correct": len(wrong), "right_transfer_other_verdict": right, "extra_referrals": len(wrong) - right}
    return {
        "run": {"file": source, "runs": len(rows), "errors": len(rows) - len(ok),
                "model": sorted({r["model"] for r in rows}), "commit": sorted({r.get("commit") or "?" for r in rows}),
                "fingerprints": sorted({tuple(v[:12] for v in r["sha256"].values()) for r in rows}),
                "started": min(r["started_at"] for r in rows), "last_started": max(r["started_at"] for r in rows),
                "cost_usd": round(sum(costs), 4), "cost_per_run": round(sum(costs) / len(costs), 5) if costs else None,
                "answer_seconds": {ins: round(sum(r[key]["ms"] for r in ok) / len(ok) / 1000, 1)
                                   for ins, _, key in R.INSTRUCTIONS}},
        "contract": {"id": f"{k['contract']['id']}@{k['contract']['version']}",
                     "clauses": [{"id": c["id"], "type": c["type"], "title": c["title"], "text": " ".join(c["text"].split()),
                                  "rule": {key: c[key] for key in RULE_KEYS if key in c}}
                                 for c in k["clauses"]],
                     "facts": {name: {"label": f["label"], "values": (
                         {v: x["label"] for v, x in f["values"].items()} if isinstance(f.get("values"), dict)
                         else {v: v for v in f.get("values", [])})} for name, f in k["facts"].items()}},
        "cases": [_plain({"id": c["id"], "title": c["title"], "base": bool(c.get("base")), "varies": c.get("varies"),
                          "probe": c.get("probe"), "declaration": " ".join(c["declaration"].split()), "form": c.get("form", {}),
                          "facts": c["facts"], "expected": c["expected"], "excerpts": excerpts(ok, c["id"])}) for c in cases],
        "documents": V.lexicon().documents,
        "arms": arms, "by_case": by_case, "cost": cost, "quotations": quotations, "unexact": unexact,
        "last_line": last_line, "boxes": boxes,
        "journal": {"judged": {m: dict(Counter(e["judged"] for e in values if e["mode"] == m)) for m in V.MODES},
                    "too_strict": grouped([e for e in values if e["judged"] == "too_strict"],
                                          "case", "fact", "proposed", "phrase", "code", "mode"),
                    "too_lenient": grouped([e for e in values if e["judged"] == "too_lenient"],
                                           "case", "fact", "kept", "phrase", "expected", "mode"),
                    "decisions": grouped([e for e in entries if e["kind"] == "decision"],
                                         "case", "instruction", "mode", "decision", "outcome", "harmful", "reason",
                                         "model", "rules", "kept_wrong")},
    }


def export(results: Path, out: Path = DATA) -> list[Path]:
    rows = [json.loads(line) for line in results.read_text(encoding="utf-8").splitlines() if line.strip()]
    out.mkdir(parents=True, exist_ok=True)
    written = [out / "summary.json"]
    written[0].write_text(json.dumps(summary(rows, results.name), ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    for c in V.cases():
        path = out / f"{c['id']}.json"
        path.write_text(json.dumps(runs_of(rows, c["id"]), ensure_ascii=False, separators=(",", ":"), default=str),
                        encoding="utf-8")
        written.append(path)
    return written


def main() -> int:
    p = argparse.ArgumentParser(description="export a finished claims run for docs/claims/")
    p.add_argument("results", type=Path)
    p.add_argument("--out", type=Path, default=DATA)
    args = p.parse_args()
    for path in export(args.results, args.out):
        print(f"{path}  {path.stat().st_size / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
