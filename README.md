# Keyross — a compiler and a registry of gauges for your agent's documents

> Your agent already knows how to read, plan and edit. What it lacks is a **compiler**: something deterministic that says whether what it produced is right — after every action, in seconds, with no model in the verification loop.
>
> **Gauges measure. The yoke couples your agent to them. Scrutineering decides.**
>
> *In 2026, agents learned to compile their plans. Nobody compiles their outputs.*

![keyross in five minutes](docs/demo.gif)

## Why this repository exists

To **make agents accountable to the compilers that official documents already have — and to write the ones they don't.** Official standards ship their own validators (the CEN Schematron for EN 16931 e-invoices, the ESAs' rules for the DORA register); Keyross never rewrites them. A gauge wraps the official validator as an oracle — pinned, executed by the harness, minimal feedback to the agent, replayed at the gate — and adds the delta the standard cannot know: cross-document consistency, your reference data, the contracts of the agent's own actions. Every team deploying an agent has written a few of these checks by hand, once, in a hurry. Here they are versioned, tested against their bad case, and shared. See [GAUGES.md](GAUGES.md) for the gauges, their order, and the good first contributions.

**Think pre-commit, for agent outputs.** pre-commit wrote no linter; it put every linter in one place, pinned, with one config and one command. Keyross puts every oracle an agent must satisfy in one place: official validators adapted (each gauge's `adapters/`), your own oracles added (`oracles/`), one verdict contract, one lock, one gate, one report, one exit code.

Where it plugs in: your CI (`keyross gate`), your agent loop (the Deep Agents / LangChain middleware, the **Claude Code hook and plugin**), or any harness through the **MCP server** — so every invoice, spreadsheet, CSV or YAML an agent writes is compiled where the developer already works.

## Five minutes

```bash
pip install keyross
keyross init                  # keyross.yaml, oracles/, badset/
keyross check quote.xlsx      # run the core gauge on one output → green / yellow / red, exit 0 / 1 / 2
keyross check invoice.xml     # an EN 16931 invoice (UBL / CII) → the official CEN rules — pip install "keyross[einvoice]"
keyross test                  # does every oracle catch its bad case? (tests for the tests)
keyross lint                  # refuse any oracle that calls a model or the network
keyross lock                  # pin the oracles: the answer to "what verified this run?"
keyross doctor .              # is the agent ready for a cluster? (v0.1: static checks)
```

An oracle is eight lines — a pure function, a verdict, evidence:

```python
from keyross import oracle, Verdict

@oracle("invoices.total.matches", severity="hard")
def total_matches(doc):
    expected = sum(l.amount for l in doc.amount_lines())
    if abs(doc.lines[-1].amount - expected) > 0.01:
        return Verdict.fail("total ≠ sum of lines", "totals.mismatch", expected=expected)
    return Verdict.ok()
```

## What it is, in three words

| Word | Definition | Analogy with code |
|---|---|---|
| **Gauge** | The installable instrument: a versioned, calibrated set of oracles — deterministic checks, red or green, with evidence — for one document family. Official validators adapted (*homologated*), your own oracles added. Written by humans, never learned. | the compiler, the type checker, the test suite |
| **Yoke** | What couples your agent to its gauges: a middleware in the loop, a Claude Code hook, an MCP server. The model never reads it; it only gets a flag and a category back. | the test runner wired into the build |
| **Scrutineering** | Every gauge replayed on what leaves the system, **outside the agent**, from a fresh sandbox, with an exit code. Nothing ships without its green. | CI |

Claude Code is reliable because code has a compiler, tests and CI. Your business documents — quotes, invoices, claims, KYC files — have none of that. Keyross writes it. → [MANIFESTO.md](MANIFESTO.md)

## The registry

Aggregating every document oracle into installable instruments is the product. Rules live in **gauges** — versioned, tested against their bad set, signed, updated from one place — and a gauge knows the revision of the standard it implements and the date it applies.

```bash
keyross gauges                 # installed gauges vs the registry
keyross add einvoice         # install a gauge, pin it in keyross.lock
keyross update                # upgrade within the ranges of keyross.yaml, re-run the badsets      (0.3)
keyross outdated              # are we on the latest rules?
keyross audit                 # what verified what: gauges, versions, checksums, effective dates      (0.3)
```

Think Semgrep's rule registry, for documents: an open engine, open gauges for official standards (adapted, never rewritten), sector and governance gauges maintained as the regulations move. Format: [docs/spec/gauge.md](docs/spec/gauge.md).

## A gauge is not a skill, a prompt or an instruction file

A Claude Code skill, a system prompt, a `CLAUDE.md`: text that a model reads and may or may not follow. A gauge is the opposite: **code that a model never reads**. *A skill asks. A gauge measures.*

![A skill asks, a gauge measures: the rule inside the context vs the gauges outside it, in the harness](docs/skills_vs_gauges.gif)

| | A skill / prompt | A gauge |
|---|---|---|
| What it is | text, instructions to a model | code: pure-function oracles, adapters that execute official validators, bad cases that test them |
| Who runs it | the model, at its discretion | the harness, the CI, the gate — never the model |
| Result | a behaviour, probabilistic | a verdict, deterministic: the same document gives the same red or green, forever |
| On a rule of the standard | "please respect BR-CO-10" | the official EN 16931 Schematron, pinned by release and checksum, executed |
| Can the agent see it? | yes, it is in its context | no — not in the prompt, not in the tool list; it receives a flag + a category |
| Proof | none | the verdict, the lock, the report, the seal |

`keyross lint` refuses a gauge that imports a model client or the network; a gauge that ships a prompt file is not a gauge. This is the whole point: verification you can put in front of an auditor is code with published rules, not a wish addressed to a model.

## The yoke

The yoke is what couples your agent to its gauges — and the one line that changes an agent from *hoping* to *measuring*:

```python
from keyross.yoke import Yoke
agent = create_deep_agent(..., middleware=[Yoke(gauge="einvoice")])   # Deep Agents / LangGraph
```

Think of a wheel alignment. The model runs straight; the rules run straight; without a yoke they do not run *parallel*, and the output drifts a little at every step — until an error ships with a confident sentence. The yoke measures after every writing tool: snapshot → tool → gauges → flag. Red means revert and retry (a pit stop, if you like) — and only the category comes back, nothing else. Green means continue. Over time the **first-pass rate** — green without a retry — is the health of the whole system: a falling rate means the model, the data or the rules drifted.

![Without a yoke the output drifts until it ships; with a yoke every writing tool pulls it back — first-pass rate, measured](docs/yoke.gif)

The yoke measures; it does not bound. Budgets, protected columns and deletion caps stay in your harness (its limiters). Three yokes exist or are planned: the Deep Agents / LangGraph middleware, the Claude Code `PostToolUse` hook, the MCP server (guard mode) — `keyross yoke <harness>` prints the recipe.

Try it offline: `python examples/deepagents/invoice_agent.py` runs the same agent without and with the yoke — a wrong total ships, then is caught, reverted and fixed. With a telemetry, `keyross stats` prints the first-pass rate.

## Where the gauges run

![One run: the agent writes, the compiler runs the gauges, red flag → pit stop, green → scrutineering ships](docs/loop.gif)

![Your gauges, one compiler, three doors](docs/overview.png)

Three yokes — **in the loop** (the Deep Agents / LangGraph middleware, the Claude Code hook), **as a service** (MCP, called by the platform) — and **scrutineering** (`keyross gate` in CI, no agent needed): the same gauges, the same lock, the same flags. The full picture, with the guard and tool modes of MCP and what comes out of every door: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Three families of oracles

- **Invariants** — independent of the plan: the total equals the sum of the lines, no priced line disappeared, units belong to the vocabulary. The `core` gauge ships six.
- **Action contracts** — derived from the plan: `@contract("delete_rows")` checks that the action did exactly what it announced, instantiated by the harness with the task's parameters. The agent can only be tested on what it announced.
- **Sentinels** — `@oracle(..., silent=True)`: silent, no feedback to the agent, zero weight. A visible green and a silent red is the signature of a workaround.

## Flags

Every verdict carries a flag: **green** (ok), **yellow** (soft failure — signals, exit 1), **red** (hard failure — blocks, exit 2). Scrutineering raises the **black** flag when the agent reported green and the gate found red: an integrity incident, the run is quarantined. `hard` / `soft` remain the values in the JSON; the flags are what people read.

## Rules the tool makes impossible to break

- `keyross lint` **refuses** an oracle that imports a model client, the network, or a source of non-determinism.
- Feedback to the agent is **minimal**: the flag and the category of the deviation — never the logic, the threshold, the list of oracles nor the evidence (`Verdict.minimal()`). Red means pit stop: revert and retry.
- An oracle without a bad case in `badset/` fails `keyross test`: an untested test lies one day.
- An oracle that crashes is a hard red: we never guess.

## Plugging it into a stack

| Level | How | Time |
|---|---|---|
| 0 — scrutineering in CI | `keyross gate outputs/ --fail-on hard` — every gauge replayed outside the agent, an exit code, like pytest | 10 min |
| 1 — the yoke, in the loop | `Yoke(gauge="core")` for Deep Agents / LangChain: measures after every writing tool, pit stop on red, minimal feedback — `pip install 'keyross[yoke]'`. For Claude Code, a **hook** (`PostToolUse`) runs `keyross check` on files the agent writes — code executed by the harness, not a skill the model reads. `keyross yoke <harness>` prints the recipe | 1 h |
| 2 — the yoke, as a service | `keyross serve --mcp`: guard mode, called by the platform and invisible to the model; or tool mode with minimal feedback *(v0.5)* | 1 h |
| 3 — the audit | `keyross audit`: the nine-section report and the governance gauge on the telemetry *(0.3)* | 1 day |

Nothing requires an account, a cloud, a cluster or a change to your agent to start. Everything runs locally.

## Writing an oracle

An oracle is a **pure** function: `(document, context) -> Verdict`. No state, no side effect, no network, no model. The canonical document exposes rows with stable identifiers (`rid:12`), blocks (priced lines + subtotal) and the recognized columns. The context carries what the client provides — unit vocabulary, reference document, document type.

Every oracle has an **id** (`gauge.subject.property`), a **version**, a **flag on failure** (red blocks, yellow signals — `hard` / `soft` in the code) and a **bad case** in `badset/<id>.xlsx`. See [CONTRIBUTING.md](CONTRIBUTING.md), [GOVERNANCE.md](GOVERNANCE.md) and [GAUGES.md](GAUGES.md).

## Status and roadmap

`0.1` — check, core gauge, test, lint, lock, report, static doctor, `gauges` / `add` / `outdated` / `yoke` on built-in gauges, and the homologated [`einvoice`](src/keyross/gauges/einvoice/README.md) gauge (the official CEN EN 16931 artefacts 1.3.16, executed unmodified), the Deep Agents yoke and `keyross stats` (first-pass rate) · `0.2` — `einvoice` delta oracles and Factur-X PDF · `0.3` — gauges from git, `update` / `audit`, the seal, doctor on images · `0.4` — signed gauges, doctor on a throwaway cluster (kind), CI action, boxed demo · `0.5` — the MCP yoke, the Claude Code hook and plugin · then `dora.register`, `aiact.annex4`, `governance`.

This repository verifies itself: its CI runs `keyross test`, `keyross lint` and `keyross lock --check` on every commit.

*Version française : [README.fr.md](README.fr.md) · [MANIFESTO.fr.md](MANIFESTO.fr.md)*

## License

[Apache-2.0](LICENSE). The engine and the public gauges are open; contributions under the Developer Certificate of Origin (`git commit -s`), no CLA. Sector gauges written on a mission belong to the client unless generalized and contributed back.
