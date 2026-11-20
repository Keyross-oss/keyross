"""Run the claims benchmark (protocol: bench/claims/PROTOCOL.md): for every case, `--reps` times, the model writes two
free answers, one under the base instruction and one under the reinforced instruction, each streamed and recorded with
its timing; the lane without the verifier executes each answer's last line; the lane with the verifier asks the model
once for the boxes, then checks each answer without a model. Four arms: two instructions, without and with the
verifier. One JSON line per run, then the report.

    python -m bench.claims.run --model scripted --pilot                    # offline dry run: checks the harness, measures nothing
    python -m bench.claims.run --model claude-haiku-4-5 --pilot            # the pilot: the four base cases, twice
    python -m bench.claims.run --model claude-haiku-4-5 --reps 10          # the full run: 12 cases × 10
    python -m bench.claims.run --report bench/claims/results/<run>.jsonl   # the report of a finished run
    python -m bench.claims.run --report <run>.jsonl --reverify             # verified again with today's lexicon, at no cost
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from bench.claims import verifier as V

RESULTS = Path(__file__).resolve().parent / "results"
PILOT = ("velo-local-commun", "bougie-table", "trottinette-garage", "velo-cave-effraction")
# USD per million tokens, input and output: list prices (Anthropic first-party API), for an estimate only
PRICES = {"claude-haiku-4-5": (1.00, 5.00)}
MAX_TOKENS = {"answer": 4000, "extract": 1500}


# -- the two prompts -----------------------------------------------------------------------------------------------------

def contract_text(k: dict[str, Any]) -> str:
    return "\n\n".join(f"Article {c['id']} — {c['title']}\n{c['text']}" for c in k["clauses"])


def form_text(form: dict[str, Any]) -> str:
    def day(d: Any) -> str:
        return d.strftime("%d/%m/%Y") if isinstance(d, date) else str(d)
    return f"Sinistre constaté le : {day(form.get('constat'))}\nDéclaré le : {day(form.get('declaration'))}"


def reinforced(system: str, rule: str) -> str:
    """The base instruction with one rule added after the rule « N’utilise que… », and nothing else changed."""
    lines = system.split("\n")
    at = next(i for i, line in enumerate(lines) if line.startswith("- N’utilise que")) + 1
    return "\n".join(lines[:at] + [rule] + lines[at:])


def prompts(case: dict[str, Any], k: dict[str, Any]) -> dict[str, dict[str, str]]:
    """What the model receives, and nothing else: the contract, the form and the declaration for each free answer,
    under the base instruction and under the reinforced one; the boxes and the declaration for the extraction. Never a
    case's title, probe, trap or expected answer, never a word of the verifier or the lexicon (tests/test_claims.py)."""
    p = V.load(V.PROMPTS)
    form = form_text(case.get("form", {}))
    user = p["answer"]["user"].format(contract=contract_text(k), form=form, declaration=case["declaration"])
    return {"answer": {"system": p["answer"]["system"], "user": user},
            "answer_reinforced": {"system": reinforced(p["answer"]["system"], p["answer"]["reinforced"]), "user": user},
            "extract": {"system": p["extract"]["system"].format(facts=V.boxes_text(k)),
                        "user": p["extract"]["user"].format(declaration=case["declaration"])}}


# -- the model -------------------------------------------------------------------------------------------------------------

def _usage(u: Any) -> dict[str, int]:
    return {"input_tokens": getattr(u, "input_tokens", 0) or 0, "output_tokens": getattr(u, "output_tokens", 0) or 0}


def call_answer(client: Any, model: str, system: str, user: str) -> dict[str, Any]:
    """The free answer, streamed: every piece of text with the milliseconds since the request, for the replay."""
    chunks: list[list[Any]] = []
    t0 = time.perf_counter()
    with client.messages.stream(model=model, max_tokens=MAX_TOKENS["answer"], system=system,
                                messages=[{"role": "user", "content": user}]) as stream:
        for text in stream.text_stream:
            chunks.append([round((time.perf_counter() - t0) * 1000), text])
        final = stream.get_final_message()
    return {"text": "".join(c[1] for c in chunks), "chunks": chunks, "ms": round((time.perf_counter() - t0) * 1000),
            "first_text_ms": chunks[0][0] if chunks else None, "stop_reason": final.stop_reason, "model": final.model,
            "id": final.id, "usage": _usage(final.usage)}


def call_extract(client: Any, model: str, system: str, user: str, k: dict[str, Any]) -> dict[str, Any]:
    """The boxes, under a strict JSON schema: the format cannot fail, so no format retry exists."""
    t0 = time.perf_counter()
    msg = client.messages.create(model=model, max_tokens=MAX_TOKENS["extract"], system=system,
                                 messages=[{"role": "user", "content": user}],
                                 output_config={"format": {"type": "json_schema", "schema": V.boxes_schema(k)}})
    text = next((b.text for b in msg.content if b.type == "text"), "")
    try:
        boxes = json.loads(text)
    except json.JSONDecodeError:
        boxes = {}
    return {"json": text, "boxes": boxes, "ms": round((time.perf_counter() - t0) * 1000), "stop_reason": msg.stop_reason,
            "model": msg.model, "id": msg.id, "usage": _usage(msg.usage)}


DRY_RUN = ("> **Dry run.** The model is a scripted stand-in that makes the mock-up's mistakes on purpose, to check that "
           "the harness records, reads and verifies them. These figures measure nothing and are never published; "
           "a measured run uses the real model, which nothing steers.")


class Scripted:
    """An offline stand-in for the model, for the dry run only, never in a measured run: it answers each case from its
    expected result, with the mistakes of the mock-up planted on the four base cases (an invented quotation and a
    payment, a missing last line, boxes filled by inference, a forgotten deductible); under the reinforced instruction,
    only the forgotten deductible is left. It checks the harness; it measures nothing."""

    def __init__(self, case: dict[str, Any], k: dict[str, Any]) -> None:
        self.case, self.k = case, k

    def answer(self, reinforced: bool = False) -> dict[str, Any]:
        e, cid = self.case["expected"], self.case["id"]
        verdict = {"couvert": "couvert", "non_couvert": "non couvert", "indetermine": "indéterminé"}[e["verdict"]]
        action = e["action"]["type"] + (f" {e['action']['amount']} €" if e["action"]["type"] == "indemniser" else "")
        first = next(c for c in self.k["clauses"] if c["id"] == (e["because"] or ["8.1"])[0])
        text = f"La déclaration est lue avec le contrat. L’article {first['id']} dit « {first['text']} »\n"
        if cid == "velo-local-commun" and not reinforced:
            text += "L’article 4.2 précise : « Le vol des vélos est garanti en tout lieu. »\nVERDICT : couvert · ACTION : indemniser 450 €"
        elif cid == "bougie-table" and not reinforced:
            text += "La bougie a abîmé la table : le sinistre semble couvert, sous réserve."
        elif cid == "trottinette-garage" and not reinforced:
            text += "Une disparition dans le garage du logement est un vol.\nVERDICT : couvert · ACTION : indemniser 370 €"
        elif cid == "velo-cave-effraction":
            text += "Vol avec effraction dans un local assuré.\nVERDICT : couvert · ACTION : indemniser 900 €"
        else:
            text += f"VERDICT : {verdict} · ACTION : {action}"
        chunks, t = [], 400
        for piece in text.split(" "):
            chunks.append([t, piece + " "])
            t += 35
        return {"text": "".join(c[1] for c in chunks).rstrip(), "chunks": chunks, "ms": t, "first_text_ms": 400,
                "stop_reason": "end_turn", "model": "scripted", "id": "", "usage": {"input_tokens": 0, "output_tokens": 0}}

    def extract(self) -> dict[str, Any]:
        boxes: dict[str, Any] = {}
        for name, x in self.case["facts"].items():
            if name in V.number_facts(self.k):
                known = x["value"] != V.UNKNOWN
                boxes[name] = {"connu": known, "montant": x["value"] if known else 0, "phrase": x.get("source", "")}
            else:
                boxes[name] = {"choix": x["value"], "phrase": x.get("source", "")}
        if self.case["id"] == "trottinette-garage":
            boxes["evenement"] = {"choix": "vol", "phrase": "a disparu"}
            boxes["lieu"] = {"choix": "dependance_privative", "phrase": "garage de la résidence"}
        return {"json": json.dumps(boxes, ensure_ascii=False), "boxes": boxes, "ms": 300, "stop_reason": "end_turn",
                "model": "scripted", "id": "", "usage": {"input_tokens": 0, "output_tokens": 0}}


def _api_key() -> str | None:
    """The key from the environment; otherwise typed in, hidden, for this run only: it is never written nor printed,
    and it stays out of the shell's history, whatever the shell."""
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return None                                      # the SDK reads it from the environment
    if not (sys.stdin.isatty() and sys.stdout.isatty()):     # on Windows the null device passes for a terminal: ask both
        sys.exit("No API key: set ANTHROPIC_API_KEY, or run this command in a terminal to type the key")
    import getpass
    key = getpass.getpass("Anthropic API key (hidden: nothing shows while you paste it), then Enter: ").strip()
    if not key:
        sys.exit("No API key given: nothing was run.")
    return key


def _client(key: str | None = None) -> Any:
    import anthropic
    return anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()


def _cost(model: str, *usages: dict[str, int]) -> float | None:
    price = PRICES.get(model)
    if price is None:
        return None
    return round(sum(u["input_tokens"] * price[0] + u["output_tokens"] * price[1] for u in usages) / 1e6, 5)


# -- one run ---------------------------------------------------------------------------------------------------------------

def lanes(case: dict[str, Any], answer: str, boxes: dict[str, Any], k: dict[str, Any]) -> dict[str, Any]:
    """Both lanes from the same outputs: the model alone, then the verified lane in both lexicon modes."""
    alone = V.parse_decision(answer)
    out: dict[str, Any] = {"off": {"decision": alone, "grade": V.grade(case["expected"], alone)}}
    for mode in V.MODES:
        report = V.verify(case, answer, boxes, mode=mode, k=k, form_text=form_text(case.get("form", {})))
        out[mode] = {"report": report, "grade": V.grade(case["expected"], report["context"]["final"]),
                     "facts": V.facts_against(case["facts"], report)}
    return out


def run_one(model: str, case: dict[str, Any], rep: int, commit: str, client: Any = None) -> dict[str, Any]:
    k = V.contract()
    record: dict[str, Any] = {"model": model, "case": case["id"], "rep": rep, "commit": commit,
                              "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                              "sha256": {"contract": V.sha256(V.CONTRACT), "cases": V.sha256(V.CASES),
                                         "lexicon": V.sha256(V.LEXICON), "prompts": V.sha256(V.PROMPTS)}}
    p = prompts(case, k)
    try:
        if model == "scripted":
            s = Scripted(case, k)
            answer, answer_r, boxes = s.answer(), s.answer(reinforced=True), s.extract()
        else:
            answer = call_answer(client, model, p["answer"]["system"], p["answer"]["user"])
            answer_r = call_answer(client, model, p["answer_reinforced"]["system"], p["answer_reinforced"]["user"])
            boxes = call_extract(client, model, p["extract"]["system"], p["extract"]["user"], k)
    except Exception as e:  # noqa: BLE001 — an API error is recorded, the benchmark goes on
        return {**record, "error": f"{type(e).__name__}: {str(e)[:300]}"}
    record.update({"prompts": p, "answer": answer, "answer_reinforced": answer_r, "extract": boxes,
                   "lanes": lanes(case, answer["text"], boxes["boxes"], k),
                   "lanes_reinforced": lanes(case, answer_r["text"], boxes["boxes"], k),
                   "cost_usd": _cost(model, answer["usage"], answer_r["usage"], boxes["usage"])})
    return record


def _commit() -> str:
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "bench/claims"], capture_output=True, text=True,
                               check=True).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


# -- the report -------------------------------------------------------------------------------------------------------------

OUTCOMES = (("correct", "correct decision"), ("wrong_payment", "payment that should not be made"),
            ("wrong_amount", "payment of a wrong amount"), ("wrong_refusal", "refusal that should not be made"),
            ("unjustified_referral", "referral to a person, though the rules decide"),
            ("mismatch", "other mismatch"), ("illegible", "last line unreadable: nothing done"))
SHORT = {"correct": "correct", "wrong_payment": "payment", "wrong_amount": "amount", "wrong_refusal": "refusal",
         "unjustified_referral": "referral", "mismatch": "other", "illegible": "unreadable"}
LANES = (("off", "model alone"), ("strict", "verified, strict lexicon"), ("lenient", "verified, lenient lexicon"))
INSTRUCTIONS = (("base", "base instruction", "answer"), ("reinforced", "reinforced instruction", "answer_reinforced"))
# The four arms, read top to bottom: the model alone, then with the verifier; under each, the base instruction first.
# Name, short name, instruction, lane.
ARMS = (("model alone, base instruction", "alone · base", "base", "off"),
        ("model alone, reinforced instruction", "alone · reinforced", "reinforced", "off"),
        ("with the verifier, base instruction", "verifier · base", "base", "strict"),
        ("with the verifier, reinforced instruction", "verifier · reinforced", "reinforced", "strict"))
LENIENT = (("with the verifier, base instruction", "verifier · base", "base", "lenient"),
           ("with the verifier, reinforced instruction", "verifier · reinforced", "reinforced", "lenient"))


def lanes_of(r: dict[str, Any], instruction: str) -> dict[str, Any] | None:
    """A run's lanes under one instruction; None for a run recorded before the reinforced instruction existed."""
    return r.get("lanes") if instruction == "base" else r.get("lanes_reinforced")


def _runs(ok: list[dict[str, Any]], instruction: str, case: str | None = None) -> list[dict[str, Any]]:
    found = (lanes_of(r, instruction) for r in ok if case is None or r["case"] == case)
    return [x for x in found if x]


def _decision(lanes_: dict[str, Any], lane: str) -> str:
    d = lanes_[lane]["decision"] if lane == "off" else lanes_[lane]["report"]["context"]["final"]
    return "—" if d is None else (d.get("action") or d.get("type")) + (f" {d['amount']} €" if d.get("amount") is not None else "")


def headline(ok: list[dict[str, Any]], arms: tuple[tuple[str, str, str, str], ...]) -> list[str]:
    """One row per arm: the primary endpoint first, then the correct decisions and the verifier's cost."""
    out = ["| | wrong decisions executed | correct decisions | sent to a person, though the rules decide |", "|---|---|---|---|"]
    for name, _, ins, lane in arms:
        g = [x[lane]["grade"] for x in _runs(ok, ins)]
        if not g:
            out.append(f"| {name} | not run | not run | not run |")
            continue
        n = len(g)
        out.append(f"| {name} | **{sum(x['harmful'] for x in g)}/{n}** | {sum(x['outcome'] == 'correct' for x in g)}/{n} | "
                   f"{sum(x['outcome'] == 'unjustified_referral' for x in g)}/{n} |")
    return out


def by_case(ok: list[dict[str, Any]], arms: tuple[tuple[str, str, str, str], ...]) -> list[str]:
    """Each case on one row, its four arms side by side: the correct decisions out of its runs, the others by kind."""
    out = ["| case | expected | " + " | ".join(short for _, short, _, _ in arms) + " |", "|---" * (len(arms) + 2) + "|"]
    for case in V.cases():
        if not any(r["case"] == case["id"] for r in ok):
            continue
        e, cells = case["expected"], []
        for _, _, ins, lane in arms:
            g = Counter(x[lane]["grade"]["outcome"] for x in _runs(ok, ins, case["id"]))
            wrong = ", ".join(f"{SHORT[o]} {v}" for o, v in g.most_common() if o != "correct")
            cells.append("—" if not g else f"{g['correct']}/{sum(g.values())}" + (f" ({wrong})" if wrong else ""))
        amount = e["action"].get("amount")
        out.append(f"| {case['id']} | {e['verdict']} · {e['action']['type']}" + (f" {amount} €" if amount is not None else "")
                   + " | " + " | ".join(cells) + " |")
    return out


# -- the verifier's journal, judged against the labels ---------------------------------------------------------------------

JUDGED = (("too_strict", "refused, though the declaration states it: a wording the lexicon lacks"),
          ("too_lenient", "kept, though the declaration does not state it"),
          ("right_to_refuse", "refused, rightly: the declaration does not state it"),
          ("missed", "left unknown by the model, though the declaration states it"))


def judge_value(f: dict[str, Any], want: Any) -> str | None:
    """One box as the verifier left it, against its label; None when there is nothing to review."""
    if f["code"] == V.SILENT:
        return "missed" if want != V.UNKNOWN else None
    if f["code"] == V.KEPT:
        return "too_lenient" if f["value"] != want else None
    return "too_strict" if f["proposed"] == want else "right_to_refuse"


def _excerpt(text: str) -> str:
    """The model's last paragraph before its decision line: the reason it gives, for the review."""
    lines = [m.start() for m in re.finditer(r"VERDICT\s*:", text, re.IGNORECASE)]
    head = re.sub(r"[*#]+", "", text[:lines[-1]] if lines else text)        # the answer's Markdown, not its words
    paragraphs = [p.strip(" -\n") for p in re.split(r"\n\s*\n", head) if p.strip(" -\n")]
    last = " ".join(paragraphs[-1].split()) if paragraphs else ""
    return last if len(last) <= 400 else last[:399] + "…"


def calibration(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The verifier's journal, judged entry by entry against the labels written before the run: each box it refused,
    or kept against them; each of its decisions that differs from the expected answer; and each refusal of a claim in
    every arm, made or expected, with its articles. One entry per line: the list a person reviews, one by one, and the
    lexicon's calibration list."""
    k, by_id, out = V.contract(), {c["id"]: c for c in V.cases()}, []
    for r in sorted((r for r in rows if "error" not in r), key=lambda r: (r["case"], r["rep"])):
        case, at = by_id[r["case"]], {"case": r["case"], "rep": r["rep"]}
        labels = {f: x["value"] for f, x in case["facts"].items()}
        expected_refusal = case["expected"]["action"]["type"] == "refuser"
        for mode in V.MODES:                       # one extraction per run: the same boxes under both instructions
            for f in r["lanes"][mode]["report"]["context"]["facts"].values():
                judged = judge_value(f, labels.get(f["fact"]))
                if judged:
                    out.append({**at, "kind": "value", "mode": mode, "fact": f["fact"], "proposed": f["proposed"],
                                "phrase": f["phrase"], "code": f["code"], "kept": f["value"],
                                "expected": labels.get(f["fact"]), "judged": judged})
        for ins, _, key in INSTRUCTIONS:
            lanes_ = lanes_of(r, ins)
            if not lanes_:
                continue
            for lane, _ in LANES:
                g = lanes_[lane]["grade"]
                ctx = lanes_[lane if lane != "off" else "strict"]["report"]["context"]
                d = lanes_[lane]["decision"] if lane == "off" else ctx["final"]
                act = None if d is None else (d.get("action") or d.get("type"))
                if lane != "off" and not g["correct"]:
                    out.append({**at, "kind": "decision", "instruction": ins, "mode": lane, "outcome": g["outcome"],
                                "harmful": g["harmful"], "decision": _decision(lanes_, lane), "reason": d["reason"],
                                "model": (ctx["model_proposal"] or {}).get("verdict"), "rules": ctx["rules_verdict"],
                                "decisive": ctx["decisive"], "kept_wrong": lanes_[lane]["facts"]["kept_wrong"]})
                if act == "refuser" or expected_refusal:
                    entry = {**at, "kind": "refusal", "instruction": ins, "lane": lane, "made": act == "refuser",
                             "expected": expected_refusal, "outcome": g["outcome"],
                             "judged": ("right" if expected_refusal else "wrong") if act == "refuser" else "missed",
                             "expected_clauses": V.refusal_clauses(k, V.clause_status(k, labels)) if expected_refusal else []}
                    if lane == "off":
                        entry.update(articles_named=ctx["articles_named"], excerpt=_excerpt(r[key]["text"]))
                    elif act == "refuser":
                        entry["clauses"] = V.refusal_clauses(k, ctx["clauses"])
                    out.append(entry)
    return out


def _runs_of(group: list[dict[str, Any]]) -> str:
    reps = sorted({e["rep"] for e in group})
    return f"{len(group)}× (run{'s' if len(reps) > 1 else ''} {', '.join(map(str, reps))})"


def _group(entries: list[dict[str, Any]], *keys: str) -> list[tuple[tuple[Any, ...], list[dict[str, Any]]]]:
    groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
    for e in entries:
        groups.setdefault(tuple(json.dumps(e.get(x), ensure_ascii=False, default=str) for x in keys), []).append(e)
    return [(tuple(json.loads(x) for x in key), g) for key, g in groups.items()]


def journal_section(entries: list[dict[str, Any]]) -> list[str]:
    """The journal in the report: its limits shown, grouped where the verifier repeats itself, one by one where the
    model speaks."""
    values = [e for e in entries if e["kind"] == "value"]
    out = ["## The verifier's journal", "",
           ("What the verifier wrote down in these runs, judged against the labels written before the run: its limits and "
            "its edge cases, kept on purpose. A value refused though the declaration states it is a wording the lexicon "
            "lacks: it goes to the calibration list. The whole journal, one entry per line, goes with the results."), "",
           "| the boxes, as the verifier left them | strict | lenient |", "|---|---|---|"]
    for key, name in JUDGED:
        out.append(f"| {name} | " + " | ".join(str(sum(e["judged"] == key and e["mode"] == m for e in values))
                                               for m in V.MODES) + " |")
    out += ["", "### The calibration list", ""]
    strict = [e for e in values if e["judged"] == "too_strict"]
    out += [f"- {case} · `{fact} = {value}` from « {phrase} » · {code}, {mode} · {_runs_of(g)}"
            for (case, fact, value, phrase, code, mode), g in _group(strict, "case", "fact", "proposed", "phrase", "code", "mode")
            ] or ["None in these runs: every stated fact the model filled in was recognised."]
    out += ["", "### Kept against the labels", ""]
    lenient = [e for e in values if e["judged"] == "too_lenient"]
    out += [f"- {case} · `{fact} = {value}` from « {phrase} », where the label says `{want}` · {mode} · {_runs_of(g)}"
            for (case, fact, value, phrase, want, mode), g in _group(lenient, "case", "fact", "kept", "phrase", "expected", "mode")
            ] or ["None in these runs."]
    out += ["", "### The verifier's decisions that differ from the expected answer", ""]
    wrong = [e for e in entries if e["kind"] == "decision"]
    out += [f"- {case} · {ins} instruction · {mode} · {decision} ({outcome}{', executed' if harmful else ''}) · "
            f"{reason}: model {model}, rules {rules}" + (f"; boxes kept wrong: {', '.join(kw)}" if kw else "") + f" · {_runs_of(g)}"
            for (case, ins, mode, decision, outcome, harmful, reason, model, rules, kw), g in _group(
                wrong, "case", "instruction", "mode", "decision", "outcome", "harmful", "reason", "model", "rules", "kept_wrong")
            ] or ["None in these runs."]
    refusals = [e for e in entries if e["kind"] == "refusal"]
    out += ["", "### Refusals, one by one", "", "By the model alone, each with the reason it gave:", ""]
    alone = [e for e in refusals if e["lane"] == "off"]
    out += [f"- {e['case']}, run {e['rep']}, {e['instruction']} instruction · "
            + ("refused" if e["made"] else f"not refused ({e['outcome']})") + f" · {e['judged']}"
            + (f" (expected under {', '.join(e['expected_clauses'])})" if e["expected"] else "")
            + f" · articles named: {', '.join(e['articles_named']) or 'none'}" + (f" — « {e['excerpt']} »" if e["made"] else "")
            for e in alone] or ["None in these runs."]
    out += ["", "By the verifier:", ""]
    verified = [e for e in refusals if e["lane"] != "off"]
    out += [f"- {case} · {ins} instruction · {lane} · " + (f"refused under {', '.join(cl)}" if made else f"not refused ({outcome})")
            + f" · {judged}" + (f" (expected under {', '.join(ecl)})" if ecl else "") + f" · {_runs_of(g)}"
            for (case, ins, lane, made, cl, outcome, judged, ecl), g in _group(
                verified, "case", "instruction", "lane", "made", "clauses", "outcome", "judged", "expected_clauses")
            ] or ["None in these runs."]
    return out + [""]


def report(rows: list[dict[str, Any]], title: str) -> str:
    ok = [r for r in rows if "error" not in r]
    out = [f"# Claims benchmark — {title}", "",
           (f"{len(rows)} runs · {len(rows) - len(ok)} API error(s) · model {', '.join(sorted({r['model'] for r in rows}))} · "
            f"commit {', '.join(sorted({r.get('commit') or '?' for r in rows}))} · contract "
            f"{', '.join(sorted({r['sha256']['contract'][:12] for r in rows}))} · lexicon "
            f"{', '.join(sorted({r['sha256']['lexicon'][:12] for r in rows}))} · prompts "
            f"{', '.join(sorted({r['sha256']['prompts'][:12] for r in rows}))}"), ""]
    if any(r["model"] == "scripted" for r in rows):
        out += [DRY_RUN, ""]
    changed = sorted({r["sha256"]["contract"][:12] for r in rows if r.get("contract_changed")})
    if changed:
        out += [(f"> **The contract changed since this run** (recorded {', '.join(changed)}, now {V.sha256(V.CONTRACT)[:12]}): "
                 "the quotations and the rules are checked against today's text, not the one the model read."), ""]
    if not ok:
        return "\n".join(out + ["No run to report."]) + "\n"
    if not _runs(ok, "reinforced"):
        out += ["> **Recorded before the reinforced instruction existed:** its arms read « not run ».", ""]
    arms = tuple(a for a in ARMS if _runs(ok, a[2]))
    out += ["## The four arms", "",
            ("Two instructions, without and with the verifier (strict lexicon). A wrong decision executed is a payment that "
             "should not be made, a payment of a wrong amount, or a refusal that should not be made. The two arms of an "
             "instruction read the same answer."), ""]
    out += headline(ok, ARMS) + ["", "## Outcomes in detail", "",
                                 "| outcome | " + " | ".join(short for _, short, _, _ in arms) + " |", "|---" * (len(arms) + 1) + "|"]
    for key, name in OUTCOMES:
        out.append(f"| {name} | " + " | ".join(
            f"{sum(x[lane]['grade']['outcome'] == key for x in _runs(ok, ins))}/{len(_runs(ok, ins))}" for _, _, ins, lane in arms) + " |")
    out += ["", "## By case", "", "Correct decisions out of the runs of each case, the others by kind.", ""] + by_case(ok, arms)
    out += ["", "## The lenient lexicon", "",
            ("The same outputs, verified with the lenient lexicon: a value is also kept when no listed expression backs it, "
             "unless a negation, a doubt or an ambiguous expression listed against it is there."), ""]
    out += headline(ok, LENIENT) + [""] + journal_section(calibration(ok)) + ["## Quotations", ""]
    for ins, name, _ in INSTRUCTIONS:
        runs = _runs(ok, ins)
        if not runs:
            continue
        quotes = [q for x in runs for q in x["strict"]["report"]["context"]["quotations"]]
        kinds = Counter(q["kind"] for q in quotes)
        near = sum(bool(q.get("near")) for q in quotes)
        answers_bad = sum(any(q["kind"] in ("not_found", "wrong_article") for q in x["strict"]["report"]["context"]["quotations"])
                          for x in runs)
        out += [(f"**{name.capitalize()}.** {len(quotes)} quotation(s) in {len(runs)} answers: {kinds['exact']} found word "
                 f"for word, {kinds['not_found']} not in the contract ({near} of them close to a passage: a paraphrase in "
                 f"quotes; the others invented), {kinds['wrong_article']} under the wrong article, {kinds['declaration']} of "
                 f"the declaration, {kinds['word']} single word(s). Answers with at least one quotation not in the contract "
                 f"as quoted: {answers_bad}/{len(runs)}."), ""]
    out += ["## The last line (decision D3)", ""]
    for ins, name, _ in INSTRUCTIONS:
        runs = _runs(ok, ins)
        if runs:
            readable = sum(x["off"]["decision"] is not None for x in runs)
            exact = sum(bool((x["off"]["decision"] or {}).get("exact")) for x in runs)
            out.append(f"- {name.capitalize()}: readable {readable}/{len(runs)}; exactly in the instructed form {exact}/{len(runs)}.")
    out += ["", "No run was retried for its format.", ""]
    for mode in V.MODES:
        f = [r["lanes"][mode]["facts"] for r in ok]
        boxes = sum(x["boxes"] for x in f)
        codes = Counter(c["code"] for r in ok for c in r["lanes"][mode]["report"]["context"]["facts"].values())
        out += [f"## Boxes, {mode} lexicon", "",
                f"As the model filled them: {sum(x['proposed_right'] for x in f)}/{boxes} right; as the verifier kept them: "
                f"{sum(x['kept_right'] for x in f)}/{boxes} right (`inconnu` included). Codes: "
                + ", ".join(f"{c} ×{v}" for c, v in codes.most_common()) + "."
                + (" One extraction per run serves both instructions: it reads neither answer." if mode == V.MODES[0] else ""), ""]
    costs = [r["cost_usd"] for r in ok if r.get("cost_usd") is not None]
    secs = {name: [r[key]["ms"] / 1000 for r in ok if key in r] for _, name, key in INSTRUCTIONS}
    out += ["## Cost and time", "",
            (f"{sum(costs):.4f} USD in all at list prices, {sum(costs) / len(costs):.5f} per run (all its calls). " if costs else "")
            + "Free answer, on average: " + ", ".join(f"{name} {sum(s) / len(s):.1f} s" for name, s in secs.items() if s) + ".",
            "", "## Runs", ""]
    for r in sorted(ok, key=lambda r: (r["case"], r["rep"])):
        parts = [f"{ins}: " + " · ".join(f"{lane} {_decision(x, lane)} ({x[lane]['grade']['outcome']})" for lane, _ in LANES)
                 for ins, _, _ in INSTRUCTIONS if (x := lanes_of(r, ins))]
        out.append(f"- {r['case']} rep {r['rep']} — " + " | ".join(parts))
    for r in rows:
        if "error" in r:
            out.append(f"- {r['case']} rep {r['rep']} — error: {r['error']}")
    return "\n".join(out + boxes_by_run(ok)) + "\n"


def boxes_by_run(ok: list[dict[str, Any]]) -> list[str]:
    """The canonicalisation, run by run: what the model put in each box, the phrase it gave, what the verifier kept and
    why. Every box the model filled for a short run (the pilot); only the refused ones for a long run."""
    detail = len(ok) <= 16
    out = ["", "## The boxes, run by run (strict lexicon)", "",
           "What the model put in each box, the phrase of the declaration it gave, and what the verifier kept. "
           + ("Every box the model filled is shown, and every box it left unknown is listed." if detail
              else "Only the boxes the verifier refused are shown.")]
    for r in sorted(ok, key=lambda r: (r["case"], r["rep"])):
        facts = r["lanes"]["strict"]["report"]["context"]["facts"].values()
        shown = [f for f in facts if f["code"] != V.SILENT] if detail else [f for f in facts if f["code"] not in (V.KEPT, V.SILENT)]
        if not shown:
            continue
        out += ["", f"**{r['case']}, rep {r['rep']}**", "", "| box | the model's value | its phrase | kept | why |", "|---|---|---|---|---|"]
        for f in shown:
            phrase = f"« {f['phrase']} »".replace("|", "\\|") if f["phrase"] else "—"
            out.append(f"| {f['fact']} | {f['proposed']} | {phrase} | {f['value']} | {f['code']} |")
        if detail:
            silent = [f["fact"] for f in facts if f["code"] == V.SILENT]
            if silent:
                out += ["", "Unknown for the model: " + ", ".join(silent) + "."]
    return out


def write_journal(rows: list[dict[str, Any]], path: Path) -> Path:
    """The judged journal, one entry per line, next to the results it was read from."""
    path.write_text("".join(json.dumps(e, ensure_ascii=False, default=str) + "\n" for e in calibration(rows)), encoding="utf-8")
    return path


def reverify(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The recorded outputs, verified again with today's contract, lexicon and verifier: no model call."""
    k, by_id, now = V.contract(), {c["id"]: c for c in V.cases()}, V.sha256(V.CONTRACT)
    for r in rows:
        if "error" not in r:
            case, boxes = by_id[r["case"]], r["extract"]["boxes"]
            r["lanes"] = lanes(case, r["answer"]["text"], boxes, k)
            if "answer_reinforced" in r:
                r["lanes_reinforced"] = lanes(case, r["answer_reinforced"]["text"], boxes, k)
            r["contract_changed"] = r["sha256"]["contract"] != now
            r["sha256"] = {**r["sha256"], "lexicon": V.sha256(V.LEXICON)}
    return rows


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description="claims benchmark: two instructions, each answer without and with the verifier")
    p.add_argument("--model", default="scripted", help="scripted (offline) or a Claude model id, e.g. claude-haiku-4-5")
    p.add_argument("--pilot", action="store_true", help=f"the pilot: {', '.join(PILOT)}, twice")
    p.add_argument("--only", default="", help="only these cases, e.g. velo-local-commun,bougie-table")
    p.add_argument("--reps", type=int, default=1)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--report", type=Path, help="print the report of a results file and exit")
    p.add_argument("--reverify", action="store_true", help="with --report: verify the recorded outputs again first")
    p.add_argument("--journal", action="store_true", help="with --report: also write the judged journal next to the results")
    args = p.parse_args()
    if args.report:
        rows = [json.loads(line) for line in args.report.read_text(encoding="utf-8").splitlines() if line.strip()]
        rows = reverify(rows) if args.reverify else rows
        print(report(rows, args.report.name + (" (verified again)" if args.reverify else "")))
        if args.journal:
            path = write_journal(rows, args.report.with_suffix(".journal.jsonl"))
            print(f"journal: {path}")
        return 0
    key = None if args.model == "scripted" else _api_key()
    chosen = V.cases()
    wanted = set(PILOT) if args.pilot else set(filter(None, args.only.split(",")))
    if wanted:
        chosen = [c for c in chosen if c["id"] in wanted]
    reps = 2 if args.pilot else args.reps
    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    kind = "pilot" if args.pilot else "run"
    out = RESULTS / f"{stamp}-{kind}-{args.model}.jsonl"
    commit = _commit()
    client = None if args.model == "scripted" else _client(key)
    jobs = [(c, rep) for rep in range(1, reps + 1) for c in chosen]
    print(f"{len(jobs)} runs · {args.model} · commit {commit} · results: {out}")
    if args.model == "scripted":
        print(DRY_RUN.replace("> ", "").replace("**", ""))
    if commit.endswith("-dirty") and args.model != "scripted":
        print("warning: bench/claims has uncommitted changes — the protocol wants the cases, the prompts and the lexicon committed first")
    rows, failed = [], []
    with ThreadPoolExecutor(max_workers=args.workers) as pool, open(out, "a", encoding="utf-8") as f:
        for (case, rep), r in zip(jobs, pool.map(lambda j: run_one(args.model, j[0], j[1], commit, client), jobs)):
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n"); f.flush()
            rows.append(r)
            if "error" in r:
                failed.append((case, rep))
                print(f"  {case['id']} rep {rep}: error {r['error']}")
            else:
                print(f"  {case['id']} rep {rep}: " + " | ".join(
                    f"{ins} " + " · ".join(f"{lane} {r[key][lane]['grade']['outcome']}" for lane, _ in LANES)
                    for ins, key in (("base", "lanes"), ("reinforced", "lanes_reinforced")))
                    + (f" · ${r['cost_usd']}" if r.get("cost_usd") else ""))
        for case, rep in failed:                         # protocol: an API error is run again once, at the end
            r = {**run_one(args.model, case, rep, commit, client), "retry": True}
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n"); f.flush()
            rows = [x for x in rows if not (x["case"] == case["id"] and x["rep"] == rep)] + [r]
    text = report(rows, out.name)
    out.with_suffix(".md").write_text(text, encoding="utf-8")
    print("\n" + text + f"\njournal: {write_journal(rows, out.with_suffix('.journal.jsonl'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
