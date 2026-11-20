"""The claims verifier: deterministic, no model, no network (protocol: bench/claims/PROTOCOL.md).

It reads the model's two outputs, the free answer and the boxes, and decides from the contract's rules:
- every quotation is looked up word for word in the contract;
- every fact's source phrase must be in the declaration and backed by the lexicon (lexicon.fr.yaml), with guards
  against negation, doubt and contradiction; a fact that fails becomes `inconnu`, it is never guessed;
- the rules are three-valued: a verdict that an unknown fact could change is `indetermine`, and the facts it hangs on
  become questions;
- the model's verdict must agree with the rules', or a person decides;
- the action is the one the rules allow; the amount is always the rules' (article 8.2), never the model's.

Its checks return Keyross verdicts; the report has the shape of a Keyross report.
"""
from __future__ import annotations

import difflib
import hashlib
import itertools
import re
import unicodedata
from dataclasses import asdict, dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from keyross.core.verdict import Severity, Verdict

HERE = Path(__file__).resolve().parent
CONTRACT = HERE / "contract.fr.yaml"
CASES = HERE / "cases.fr.yaml"
LEXICON = HERE / "lexicon.fr.yaml"
PROMPTS = HERE / "prompts.fr.yaml"

UNKNOWN = "inconnu"
VERDICTS = ("couvert", "non_couvert", "indetermine")
ACTIONS = ("indemniser", "refuser", "demander", "transmettre")
MODES = ("strict", "lenient")


# -- loading -------------------------------------------------------------------------------------------------------

def load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@lru_cache(maxsize=None)
def contract(path: Path = CONTRACT) -> dict[str, Any]:
    return load(path)


@lru_cache(maxsize=None)
def cases(path: Path = CASES) -> list[dict[str, Any]]:
    return load(path)["cases"]


def enum_facts(k: dict[str, Any]) -> dict[str, list[str]]:
    """The facts that take a value from a list, with their values (`inconnu` excluded)."""
    out = {}
    for name, spec in k["facts"].items():
        values = spec.get("values")
        if values is not None:
            out[name] = list(values) if isinstance(values, list) else list(values.keys())
    return out


def number_facts(k: dict[str, Any]) -> list[str]:
    return [name for name, spec in k["facts"].items() if "number" in spec]


# -- the boxes: the canonical facts, defined by the verifier from the contract's vocabulary ----------------------------
#
# The verifier, not the model, decides which boxes exist and which values each may take: they are the `facts` of the
# contract. It imposes them on the model with a strict JSON schema (the model cannot answer outside it), and it is
# the verifier again that keeps or refuses each value the model puts in them (check_fact).

def boxes_schema(k: dict[str, Any]) -> dict[str, Any]:
    """The boxes as a strict JSON schema: for each fact, one value of its list or `inconnu`, and the phrase of the
    declaration that states it; for the value of the item, an amount in euros."""
    props: dict[str, Any] = {}
    for name in k["facts"]:
        if name in number_facts(k):
            props[name] = {"type": "object", "properties": {"connu": {"type": "boolean"}, "montant": {"type": "integer"},
                                                            "phrase": {"type": "string"}},
                           "required": ["connu", "montant", "phrase"], "additionalProperties": False}
        else:
            props[name] = {"type": "object", "properties": {"choix": {"type": "string", "enum": enum_facts(k)[name] + [UNKNOWN]},
                                                            "phrase": {"type": "string"}},
                           "required": ["choix", "phrase"], "additionalProperties": False}
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


def boxes_text(k: dict[str, Any]) -> str:
    """The boxes as the model reads them: each fact, its label, its values. Nothing about the rules that use them."""
    lines = []
    for name, spec in k["facts"].items():
        if "number" in spec:
            lines.append(f"- {name} ({spec['label']}) : un montant en euros, ou inconnu")
            continue
        values = spec["values"]
        shown = [f"{v} ({values[v]['label']})" for v in values] if isinstance(values, dict) else list(values)
        lines.append(f"- {name} ({spec['label']}) : " + ", ".join(shown) + ", ou inconnu")
    return "\n".join(lines)


# -- words ---------------------------------------------------------------------------------------------------------

_QUOTES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "´": "'", "`": "'"})


def words(text: str) -> tuple[str, ...]:
    """The words a phrase is matched on: lower case, without accents or punctuation."""
    t = str(text).translate(_QUOTES).replace("œ", "oe").replace("Œ", "oe").replace("æ", "ae")
    t = "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c)).lower()
    return tuple(re.findall(r"[a-z0-9]+", t))


def find(seq: tuple[str, ...], sub: tuple[str, ...]) -> int:
    """The first position of `sub` in `seq`, word for word, or -1."""
    n = len(sub)
    if not n:
        return -1
    for i in range(len(seq) - n + 1):
        if seq[i:i + n] == sub:
            return i
    return -1


def contains(seq: tuple[str, ...], sub: tuple[str, ...]) -> bool:
    return find(seq, sub) >= 0


_AMOUNT = re.compile(r"(\d{1,3}(?:[   .]\d{3})+|\d+)(?:,\d{1,2})?\s*(?:€|euros?\b|eur\b)", re.IGNORECASE)


def amounts(text: str) -> list[int]:
    """The amounts in euros a text states, in whole euros: « 2 400 € » is 2400."""
    return [int(re.sub(r"[   .]", "", m.group(1))) for m in _AMOUNT.finditer(str(text))]


# -- the lexicon: the configuration zone ------------------------------------------------------------------------------

@dataclass(frozen=True)
class Lexicon:
    expressions: dict[str, tuple[tuple[tuple[str, ...], str], ...]]       # fact -> ((words, value), …)
    ambiguous: dict[str, tuple[tuple[tuple[str, ...], frozenset[str]], ...]]   # fact -> ((words, against), …)
    means: dict[str, tuple[tuple[tuple[str, ...], frozenset[str]], ...]]       # fact -> ((words, what it can mean), …)
    negation: frozenset[str]
    doubt: tuple[tuple[str, ...], ...]
    amount_doubt: tuple[tuple[str, ...], ...]
    justified_by: tuple[tuple[str, ...], ...]
    questions: tuple[dict[str, Any], ...]
    documents: dict[str, str]
    version: str
    fingerprint: str


@lru_cache(maxsize=None)
def lexicon(path: Path = LEXICON) -> Lexicon:
    raw = load(path)
    expressions = {fact: tuple((words(e), value) for value, exprs in by_value.items() for e in (exprs or []))
                   for fact, by_value in raw["facts"].items()}
    ambiguous = {fact: tuple((words(e), frozenset(entry["against"])) for entry in entries for e in entry["expressions"])
                 for fact, entries in (raw.get("ambiguous") or {}).items()}
    means = {fact: tuple((words(e), frozenset(entry["means"])) for entry in entries if entry.get("means")
                         for e in entry["expressions"])
             for fact, entries in (raw.get("ambiguous") or {}).items()}
    return Lexicon(expressions=expressions, ambiguous=ambiguous, means=means,
                   negation=frozenset(w for n in raw["negation"] for w in words(n)),
                   doubt=tuple(words(d) for d in raw["doubt"]),
                   amount_doubt=tuple(words(d) for d in raw["valeur"]["doubt"]),
                   justified_by=tuple(words(j) for j in raw["valeur"]["justified_by"]),
                   questions=tuple(raw["questions"]), documents=dict(raw["documents"]),
                   version=str(raw["version"]), fingerprint=sha256(path))


def matches(tokens: tuple[str, ...], entries: tuple[tuple[tuple[str, ...], Any], ...]) -> list[tuple[int, int, Any]]:
    """The expressions found in `tokens`, without overlap, the longest first: [(start, end, payload)]."""
    found = []
    for expr, payload in entries:
        n = len(expr)
        for i in range(len(tokens) - n + 1):
            if tokens[i:i + n] == expr:
                found.append((i, i + n, payload))
    found.sort(key=lambda m: (-(m[1] - m[0]), m[0]))
    taken: set[int] = set()
    kept = []
    for s, e, p in found:
        if taken.isdisjoint(range(s, e)):
            kept.append((s, e, p))
            taken.update(range(s, e))
    return sorted(kept, key=lambda m: m[0])


# -- facts -----------------------------------------------------------------------------------------------------------

# Why a proposed value is kept, or why it becomes `inconnu`. The three kinds of `inconnu` of the protocol:
#   absent         silent — the model found nothing
#   not recognised not_recognised — the phrase is there, the lexicon does not know it (it feeds the lexicon review)
#   ambiguous      every other refusal code — the phrase is there and says something else, or not clearly
KEPT, SILENT, NOT_RECOGNISED = "kept", "silent", "not_recognised"
REFUSALS = ("no_phrase", "phrase_not_found", "doubt", "other_value", "mixed", "negation", "ambiguous", "contradiction",
            "amount_not_found", "not_justified", NOT_RECOGNISED)


@dataclass
class FactCheck:
    fact: str
    proposed: Any
    phrase: str
    value: Any
    code: str

    @property
    def refused(self) -> bool:
        return self.code not in (KEPT, SILENT)


_CLAUSE_END = re.compile(r"(?<!\d)[.;!?](?!\d)|\n")


def clause_of(declaration: str, phrase: str) -> str:
    """The clause of the declaration that holds the phrase (clauses end at . ; ! ? or a line, not inside a number);
    the phrase itself when it spans more than one."""
    p = words(phrase)
    return next((c for c in _CLAUSE_END.split(declaration) if contains(words(c), p)), phrase)


def check_fact(fact: str, proposed: Any, phrase: str, declaration: str, lex: Lexicon, mode: str = "strict") -> FactCheck:
    """Keep the proposed value only if the declaration backs it; otherwise the fact is `inconnu`."""
    def out(code: str) -> FactCheck:
        return FactCheck(fact, proposed, phrase, proposed if code == KEPT else UNKNOWN, code)

    if proposed == UNKNOWN or proposed is None:
        return FactCheck(fact, UNKNOWN, phrase, UNKNOWN, SILENT)
    p, d = words(phrase), words(declaration)
    if not p:
        return out("no_phrase")
    if not contains(d, p):
        return out("phrase_not_found")
    if any(contains(p, x) for x in lex.doubt):
        return out("doubt")
    if fact == "valeur":
        # The phrase locates the amount; what justifies it, or doubts it, is read in the amount's clause of the
        # declaration: « Facture : 900 € » justifies the phrase « 900 € », « le vélo valait 900 € » does not.
        c = words(clause_of(declaration, phrase))
        if any(contains(c, x) for x in lex.doubt + lex.amount_doubt):
            return out("doubt")
        if amounts(phrase) != [proposed]:
            return out("amount_not_found")
        if not any(contains(c, j) for j in lex.justified_by):
            return out("not_justified")
        return out(KEPT)
    entries = lex.expressions.get(fact, ())
    found = matches(p, entries)
    values = {v for _, _, v in found}
    if len(values) > 1:
        return out("mixed")
    if values and proposed not in values:
        return out("other_value")
    if values:
        support = [(s, e) for s, e, v in found if v == proposed]
        negative = any(t in lex.negation for s, e in support for t in p[s:e])
        outside = [t for i, t in enumerate(p) if not any(s <= i < e for s, e, _ in found)]
        if not negative and any(t in lex.negation for t in outside):
            return out("negation")
    elif mode == "strict":
        return out(NOT_RECOGNISED)
    else:
        if any(t in lex.negation for t in p):
            return out("negation")
        if any(proposed in against for _, _, against in matches(p, lex.ambiguous.get(fact, ()))):
            return out("ambiguous")
    others = {v for _, _, v in matches(d, entries)} - {proposed}
    if others:
        return out("contradiction")
    return out(KEPT)


def check_facts(boxes: dict[str, dict[str, Any]], declaration: str, lex: Lexicon, k: dict[str, Any],
                mode: str = "strict") -> list[FactCheck]:
    """Every box of the model's second answer, checked. A missing box is `inconnu`."""
    out = []
    for fact in list(enum_facts(k)) + number_facts(k):
        box = boxes.get(fact) or {}
        if fact in number_facts(k):
            proposed = box.get("montant") if box.get("connu") else UNKNOWN
        else:
            proposed = box.get("choix", UNKNOWN)
        out.append(check_fact(fact, proposed, box.get("phrase", ""), declaration, lex, mode))
    return out


# -- rules: three-valued ---------------------------------------------------------------------------------------------

def holds(when: Any, facts: dict[str, Any]) -> bool | None:
    """A clause's condition on the facts: True, False, or None when an unknown fact leaves it open.
    A mapping holds when every fact has one of the listed values; a list of mappings, when any of them holds."""
    if isinstance(when, list):
        rs = [holds(w, facts) for w in when]
        return True if True in rs else (None if None in rs else False)
    rs: list[bool | None] = []
    for name, allowed in when.items():
        allowed = allowed if isinstance(allowed, list) else [allowed]
        value = facts.get(name, UNKNOWN)
        rs.append(None if value == UNKNOWN else value in allowed)
    return False if False in rs else (None if None in rs else True)


def _decide(k: dict[str, Any], facts: dict[str, Any]) -> str:
    """The verdict on facts that are all known: an exclusion that holds wins, then a guarantee that holds."""
    if any(holds(c["when"], facts) for c in k["clauses"] if c["type"] == "exclusion"):
        return "non_couvert"
    return "couvert" if any(holds(c["when"], facts) for c in k["clauses"] if c["type"] == "garantie") else "non_couvert"


def _read_by_rules(k: dict[str, Any]) -> list[str]:
    """The facts the guarantees and exclusions read."""
    def names(when: Any) -> set[str]:
        return set().union(*(names(w) for w in when)) if isinstance(when, list) else set(when)
    read = set().union(*(names(c["when"]) for c in k["clauses"] if c["type"] in ("garantie", "exclusion")))
    return [f for f in enum_facts(k) if f in read]


def rules_verdict(k: dict[str, Any], facts: dict[str, Any],
                  narrow: dict[str, frozenset[str]] | None = None) -> tuple[str, list[str]]:
    """The verdict the rules give, and the unknown facts it hangs on (the decisive ones), by trying every value of
    every unknown fact: a verdict that does not change is known; otherwise it is `indetermine`. `narrow` keeps an
    unknown fact to the values its phrase can still mean; it serves the questions, never the verdict."""
    values = {f: [v for v in vs if not narrow or f not in narrow or v in narrow[f]] for f, vs in enum_facts(k).items()}
    unknown = [f for f in _read_by_rules(k) if facts.get(f, UNKNOWN) == UNKNOWN]
    outcomes = {combo: _decide(k, {**facts, **dict(zip(unknown, combo))})
                for combo in itertools.product(*(values[f] for f in unknown))}
    found = set(outcomes.values())
    if len(found) == 1:
        return found.pop(), []
    decisive = []
    for i, f in enumerate(unknown):
        if any(outcomes[combo[:i] + (alt,) + combo[i + 1:]] != verdict
               for combo, verdict in outcomes.items() for alt in values[f] if alt != combo[i]):
            decisive.append(f)
    return "indetermine", decisive


def clause_status(k: dict[str, Any], facts: dict[str, Any]) -> dict[str, bool | None]:
    """Each guarantee's and exclusion's condition on the facts, three-valued: what the page shows as applied,
    set aside or pending."""
    return {c["id"]: holds(c["when"], facts) for c in k["clauses"] if c["type"] in ("garantie", "exclusion")}


def _clause(k: dict[str, Any], cid: str) -> dict[str, Any]:
    return next(c for c in k["clauses"] if c["id"] == cid)


def amount_due(k: dict[str, Any], facts: dict[str, Any]) -> int | None:
    """Article 8.2: the value, within the ceiling of article 5, minus the deductible of article 8.1, never below 0."""
    value, item = facts.get("valeur", UNKNOWN), facts.get("bien", UNKNOWN)
    if value == UNKNOWN or item == UNKNOWN:
        return None
    ceiling = _clause(k, "5")["ceiling"][item]
    return max(0, min(int(value), ceiling) - _clause(k, "8.1")["deductible"])


def _delay(form: dict[str, Any]) -> int | None:
    seen, declared = form.get("constat"), form.get("declaration")
    if not (isinstance(seen, date) and isinstance(declared, date)):
        return None
    return (declared - seen).days


def rules_action(k: dict[str, Any], facts: dict[str, Any], form: dict[str, Any], verdict: str) -> dict[str, Any]:
    """The action the rules allow for this verdict. Articles 7.1 (the delay), 7.2 (the complaint) and 8.2 (the value)
    gate the payment, never the verdict."""
    documents = []
    if holds(_clause(k, "7.2")["applies_when"], facts) is not False and facts.get("plainte") != "oui":
        documents.append("plainte")
    if facts.get("valeur", UNKNOWN) == UNKNOWN:
        documents.append("valeur")
    if verdict == "indetermine":
        return {"type": "demander", "documents": documents}
    if verdict == "non_couvert":
        return {"type": "refuser"}
    due = amount_due(k, facts)
    delay, limit = _delay(form), _clause(k, "7.1")["requires"]["delai_jours"]["max"]
    if delay is not None and delay > limit:
        return {"type": "transmettre", "because": ["7.1"], "delay_days": delay, "amount_at_most": due}
    if documents:
        return {"type": "demander", "documents": documents, "amount_once_complete": due}
    return {"type": "indemniser", "amount": due}


def questions(decisive: list[str], lex: Lexicon) -> list[str]:
    """One question per group of decisive facts, in the lexicon's order."""
    return [q["text"] for q in lex.questions if set(q["facts"]) & set(decisive)]


def what_it_can_mean(declaration: str, lex: Lexicon) -> dict[str, frozenset[str]]:
    """For each fact, the values an ambiguous phrase of the declaration can still mean (« a disparu »: vol, perte)."""
    d = words(declaration)
    out: dict[str, frozenset[str]] = {}
    for fact, entries in lex.means.items():
        for _, _, meant in matches(d, entries):
            out[fact] = out.get(fact, meant) & meant
    return out


def to_ask(k: dict[str, Any], facts: dict[str, Any], declaration: str, lex: Lexicon) -> list[str]:
    """The decisive facts to ask about: those an answer could still turn, given what the declaration can mean."""
    verdict, decisive = rules_verdict(k, facts)
    if verdict != "indetermine":
        return []
    _, narrowed = rules_verdict(k, facts, what_it_can_mean(declaration, lex))
    return narrowed or decisive


# -- the free answer ---------------------------------------------------------------------------------------------------

_LAST = re.compile(r"VERDICT\s*:\s*(?P<verdict>[^\n·|/;]+?)\s*(?P<sep>·|\||/|;|—|–|-|\n)\s*ACTION\s*:\s*(?P<action>[^\n]+)",
                   re.IGNORECASE)
_VERDICT_AT = re.compile(r"VERDICT\s*:", re.IGNORECASE)


def parse_decision(text: str) -> dict[str, Any] | None:
    """The decision line, read by code: {verdict, action, amount, exact}, or None when it cannot be read. The last
    « VERDICT : … ACTION : … » of the answer is read; a note after it does not hide it. `exact` says whether the line
    has exactly the instructed form, last, with nothing added. An action with two amounts is not read: which one?"""
    if not text:
        return None
    for start in reversed([m.start() for m in _VERDICT_AT.finditer(text)]):
        tail = re.sub(r"[*_`]", "", text[start:])
        m = _LAST.match(tail)
        if not m:
            continue
        v = words(m["verdict"])
        verdict = {("couvert",): "couvert", ("non", "couvert"): "non_couvert", ("indetermine",): "indetermine"}.get(v)
        a = words(m["action"])
        if verdict is None or not a or a[0] not in ACTIONS:
            return None
        decision: dict[str, Any] = {"verdict": verdict, "action": a[0]}
        if a[0] == "indemniser":
            found = amounts(m["action"])
            if len(found) != 1:
                return None
            decision["amount"] = found[0]
        decision["exact"] = (m["sep"] == "·" and words(_AMOUNT.sub(" ", m["action"])) == (a[0],)
                             and not tail[m.end():].strip())
        return decision
    return None


_CITED = re.compile(r"«\s*(.+?)\s*»", re.DOTALL)
# A quotation is attributed to an article only when the article opens it: « l’article 7.2 précise : « … » »,
# « selon l’article 4.2, « … » », « (art. 8.1) « … » ». An article named earlier in the sentence attributes nothing.
_ARTICLE_BEFORE = re.compile(r"art(?:icle)?s?\.?\s*(\d+(?:\.\d+)?)\s*[),]?\s*(?:(?:dit|précise|prévoit|stipule|indique|"
                             r"énonce|dispose|mentionne|définit|ajoute)\s*(?:que\s*)?)?[:(]?\s*$", re.IGNORECASE)
NEAR = 0.8   # a quotation not found word for word, but this close to a passage, is a paraphrase in quotes
_DOTTED = re.compile(r"(?<![\d.])(\d\.\d)(?![\d])")
_SINGLE = re.compile(r"\bart(?:icle)?s?\.?\s*(\d)(?![\d.])", re.IGNORECASE)


def quotations(text: str, k: dict[str, Any], declaration: str, form_text: str = "") -> list[dict[str, Any]]:
    """Every « … » of the free answer: found in a clause, word for word (case, accents and punctuation aside), or
    not. A quotation of the declaration or the form is not a quotation of the contract, even adapted (« […] » or a
    word put in brackets, a few words changed); under four words that match nothing, it is a word in quotes, not a
    citation. Brackets never hide a word from the contract's check: only « […] » marks a cut there."""
    clauses = [(c["id"], words(c["text"])) for c in k["clauses"]]
    elsewhere = words(declaration) + ("|",) + words(form_text)
    out = []
    for m in _CITED.finditer(text):
        quote = m.group(1)
        parts = [words(x) for x in re.split(r"…|\.\.\.|\[\s*…?\s*\]", quote) if words(x)]
        if not parts:
            continue
        cut = [words(x) for x in re.split(r"…|\.\.\.|\[[^\]]*\]", quote) if words(x)]      # the claimant's words, edited
        edited = sum(map(len, cut)) >= 0.75 * sum(map(len, parts))      # brackets hold a word or two, not the quotation
        before = _ARTICLE_BEFORE.search(text[max(0, m.start() - 60):m.start()])
        named = before.group(1) if before else None
        found = [cid for cid, ws in clauses if _in_order(ws, parts)]
        if found:
            kind = "exact" if named is None or named in found else "wrong_article"
        elif edited and all(contains(elsewhere, x) for x in cut):
            kind = "declaration"
        elif sum(len(x) for x in parts) < 4:
            kind = "word"
        elif edited and _closest([w for x in cut for w in x], [("declaration", elsewhere)])[1] >= NEAR:
            kind = "declaration"
        else:
            kind = "not_found"
        q = {"text": quote, "article_named": named, "found_in": found, "kind": kind}
        if kind == "not_found":
            q["closest"], q["similarity"] = _closest([w for x in parts for w in x], clauses)
            q["near"] = q["similarity"] >= NEAR
        out.append(q)
    return out


def _closest(quote: list[str], clauses: list[tuple[str, tuple[str, ...]]]) -> tuple[str | None, float]:
    """The clause whose passage is closest to a quotation that is not in the contract, and how close (0 to 1)."""
    best: tuple[str | None, float] = (None, 0.0)
    n = len(quote)
    for cid, ws in clauses:
        for i in range(max(1, len(ws) - n + 1)):
            ratio = difflib.SequenceMatcher(None, quote, list(ws[i:i + n])).ratio()
            if ratio > best[1]:
                best = (cid, round(ratio, 2))
    return best


def _in_order(ws: tuple[str, ...], parts: list[tuple[str, ...]]) -> bool:
    i = 0
    for x in parts:
        j = find(ws[i:], x)
        if j < 0:
            return False
        i += j + len(x)
    return True


def articles_named(text: str, k: dict[str, Any]) -> list[str]:
    """The articles the free answer names: « 4.2 », « article 6.3 », « art. 5 »."""
    ids = {c["id"] for c in k["clauses"]}
    named = {m.group(1) for m in _DOTTED.finditer(text)} | {m.group(1) for m in _SINGLE.finditer(text)}
    return sorted(named & ids, key=lambda x: [int(p) for p in x.split(".")])


# -- the verifier ------------------------------------------------------------------------------------------------------

ORACLES = {"cit": "claims.citations.exact", "src": "claims.facts.sourced", "facts": "claims.facts.complete",
           "rul": "claims.rules.verdict", "act": "claims.action.allowed"}
SEVERITY = {"cit": Severity.SOFT, "src": Severity.SOFT, "facts": Severity.HARD, "rul": Severity.HARD, "act": Severity.HARD}


def _verdict(check: str, v: Verdict) -> dict[str, Any]:
    v.oracle_id, v.version, v.severity = ORACLES[check], 1, SEVERITY[check]
    return v.to_dict()


def same_action(a: dict[str, Any] | None, b: dict[str, Any]) -> bool:
    if a is None:
        return False
    return a.get("action", a.get("type")) == b["type"] and (b["type"] != "indemniser" or a.get("amount") == b.get("amount"))


def verify(case: dict[str, Any], answer: str, boxes: dict[str, Any], *, mode: str = "strict",
           k: dict[str, Any] | None = None, lex: Lexicon | None = None, form_text: str = "") -> dict[str, Any]:
    """The verified lane for one run: the checks, then the final decision. Deterministic: the same inputs give the
    same report, so a recorded run can be verified again under another lexicon or mode at no cost."""
    k = k or contract()
    lex = lex or lexicon()
    declaration, form = case["declaration"], case.get("form", {})
    model = parse_decision(answer)
    checked = check_facts(boxes, declaration, lex, k, mode)
    facts = {c.fact: c.value for c in checked}
    verdict, _ = rules_verdict(k, facts)
    decisive = to_ask(k, facts, declaration, lex)
    allowed = rules_action(k, facts, form, verdict)
    if verdict == "indetermine":
        final = {"verdict": "indetermine", **allowed, "reason": "unknown_fact"}
    elif model is None or model["verdict"] != verdict:
        final = {"verdict": "indetermine", "type": "transmettre", "reason": "disagreement"}
    else:
        final = {"verdict": verdict, **allowed, "reason": "agreement"}
    quotes = quotations(answer, k, declaration, form_text)
    named = articles_named(answer, k)
    status = clause_status(k, facts)
    unread = [cid for cid, s in status.items() if s is not False and cid not in named]
    if final["verdict"] == "couvert" and "8.1" not in named:
        unread.append("8.1")

    verdicts = []
    bad = [q for q in quotes if q["kind"] in ("not_found", "wrong_article")]
    verdicts.append(_verdict("cit", Verdict.fail(f"{len(bad)} quotation(s) not in the contract as quoted", "citation.not_found",
                                                 quotes=bad) if bad else Verdict.ok(f"{len(quotes)} quotation(s) checked")))
    refused = [c for c in checked if c.refused]
    verdicts.append(_verdict("src", Verdict.fail(f"{len(refused)} box(es) refused, now unknown", "fact.not_supported",
                                                 refused=[asdict(c) for c in refused]) if refused
                             else Verdict.ok("every value has its phrase, and the lexicon backs it")))
    verdicts.append(_verdict("facts", Verdict.fail(f"the verdict hangs on {', '.join(decisive)}", "fact.unknown",
                                                   decisive=decisive) if decisive
                             else Verdict.ok("no unknown fact changes the verdict")))
    if verdict == "indetermine":
        rul = Verdict.fail("the rules cannot conclude", "rules.unknown", rules=verdict)
    elif model is None:
        rul = Verdict.fail("the model's last line cannot be read", "rules.no_proposal", rules=verdict)
    elif model["verdict"] != verdict:
        rul = Verdict.fail(f"model {model['verdict']} ≠ rules {verdict}", "rules.disagreement", rules=verdict, model=model["verdict"])
    else:
        rul = Verdict.ok(f"model = rules = {verdict}")
    verdicts.append(_verdict("rul", rul))
    if same_action(model, final):
        act = Verdict.ok("the model's action is the one the contract allows")
    elif model is not None and model["action"] == "indemniser" and final["type"] == "indemniser":
        act = Verdict.fail(f"amount {model['amount']} € set aside: the rules give {final['amount']} €", "action.amount",
                           proposed=model, allowed=final)
    elif model is not None and model["action"] == "indemniser":
        act = Verdict.fail(f"payment of {model.get('amount')} € blocked", "action.blocked", proposed=model, allowed=final)
    else:
        act = Verdict.fail("the model's action is replaced by the one the contract allows", "action.replaced",
                           proposed=model, allowed=final)
    verdicts.append(_verdict("act", act))
    hard = any(v["status"] == "fail" and v["severity"] == "hard" for v in verdicts)
    soft = any(v["status"] == "fail" for v in verdicts)
    report = {
        "document": case["id"], "exit_code": 1 if hard else 0, "flag": "red" if hard else ("yellow" if soft else "green"),
        "context": {"mode": mode, "contract": f"{k['contract']['id']}@{k['contract']['version']}",
                    "contract_sha256": sha256(CONTRACT), "lexicon": lex.version, "lexicon_sha256": lex.fingerprint,
                    "model_proposal": model, "facts": {c.fact: asdict(c) for c in checked},
                    "rules_verdict": verdict, "decisive": decisive, "clauses": status, "articles_named": named,
                    "unread": unread, "quotations": quotes, "questions": questions(decisive, lex) if verdict == "indetermine" else [],
                    "final": final},
        "verdicts": verdicts,
    }
    report["context"]["journal"] = journal(report, k, lex)
    return report


# -- the journal: what the verifier writes down for a person -------------------------------------------------------------

def refusal_clauses(k: dict[str, Any], status: dict[str, bool | None]) -> list[str]:
    """Why the rules refuse: the exclusions that hold; when none does, the guarantees, which then all fail."""
    kind = {c["id"]: c["type"] for c in k["clauses"]}
    held = [cid for cid, s in status.items() if s is True and kind[cid] == "exclusion"]
    return held or [cid for cid, s in status.items() if s is False and kind[cid] == "garantie"]


def journal(report: dict[str, Any], k: dict[str, Any], lex: Lexicon) -> list[dict[str, Any]]:
    """What the verifier writes down for a person to review, from its own report and with no expected answer: each
    value it refused and why, each value the lenient mode kept with no listed expression, the unknown facts that
    decide, a model that disagrees with the rules, and each refusal of a claim with the clauses that make it. Its
    limits and its edge cases, kept on purpose: an entry is a wording the lexicon lacks, a mistake to correct, or a
    case for a person; together they are the list that calibrates the lexicon."""
    ctx, out = report["context"], []
    for f in ctx["facts"].values():
        if f["code"] not in (KEPT, SILENT):
            out.append({"event": "value_refused", "fact": f["fact"], "proposed": f["proposed"], "phrase": f["phrase"],
                        "code": f["code"], "decisive": f["fact"] in ctx["decisive"]})
        elif f["code"] == KEPT and f["fact"] in lex.expressions and f["value"] not in {
                v for _, _, v in matches(words(f["phrase"]), lex.expressions[f["fact"]])}:
            out.append({"event": "value_kept_unlisted", "fact": f["fact"], "value": f["value"], "phrase": f["phrase"]})
    final = ctx["final"]
    if final["reason"] == "unknown_fact":
        out.append({"event": "unknown_decisive", "facts": ctx["decisive"], "questions": ctx["questions"]})
    elif final["reason"] == "disagreement":
        out.append({"event": "disagreement", "model": (ctx["model_proposal"] or {}).get("verdict"),
                    "rules": ctx["rules_verdict"]})
    if final.get("type") == "refuser":
        out.append({"event": "refusal", "clauses": refusal_clauses(k, ctx["clauses"])})
    return out


# -- grading against the expected answers ---------------------------------------------------------------------------------

def grade(expected: dict[str, Any], decision: dict[str, Any] | None) -> dict[str, Any]:
    """One lane's decision against the answer written before the run: correct, or which error."""
    if decision is None:
        return {"correct": False, "outcome": "illegible", "harmful": False}
    act = decision.get("action", decision.get("type"))
    exp_act, exp_amount = expected["action"]["type"], expected["action"].get("amount")
    verdict_ok = decision["verdict"] == expected["verdict"]
    action_ok = act == exp_act and (exp_act != "indemniser" or decision.get("amount") == exp_amount)
    if verdict_ok and action_ok:
        outcome = "correct"
    elif act == "indemniser":
        outcome = "wrong_amount" if exp_act == "indemniser" else "wrong_payment"
    elif act == "refuser":
        outcome = "wrong_refusal"
    elif exp_act in ("indemniser", "refuser"):
        outcome = "unjustified_referral"
    else:
        outcome = "mismatch"
    return {"correct": outcome == "correct", "outcome": outcome,
            "harmful": outcome in ("wrong_payment", "wrong_amount", "wrong_refusal"),
            "verdict_ok": verdict_ok, "action_ok": action_ok}


def facts_against(expected_facts: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """The boxes against the expected ones, `inconnu` included: as the model proposed them, and as the verifier kept them."""
    got = report["context"]["facts"]
    names = [f for f in expected_facts if f in got]
    proposed = {f: got[f]["proposed"] == expected_facts[f]["value"] for f in names}
    kept = {f: got[f]["value"] == expected_facts[f]["value"] for f in names}
    return {"proposed_right": sum(proposed.values()), "kept_right": sum(kept.values()), "boxes": len(names),
            "proposed_wrong": sorted(f for f, ok in proposed.items() if not ok),
            "kept_wrong": sorted(f for f, ok in kept.items() if not ok)}
