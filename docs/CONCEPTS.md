# Concepts — oracles, flags, and the rules the tool enforces

The README gives the three words: **gauge**, **yoke**, **flags**. This page is the reference behind them.

## Three families of oracles

An oracle is one check. A gauge is a set of them.

- **Invariants** — independent of the plan: the total equals the sum of the lines, no priced line disappeared, units belong to the vocabulary. The `core` gauge ships six.
- **Action contracts** — derived from the plan: `@contract("delete_rows")` checks that the action did exactly what it announced, instantiated by the harness with the task's parameters. The agent can only be tested on what it announced.
- **Sentinels** — `@oracle(..., silent=True)`: silent, no feedback to the agent, zero weight. A visible green and a silent red is the signature of a workaround.

An **adapter** is an oracle that runs an official validator unmodified — the CEN rules for EN 16931 in the `einvoice` gauge. A gauge built on adapters is *homologated*.

## Flags

Every verdict carries a flag:

| Flag | Meaning | Exit code |
|---|---|---|
| **green** | the check passed | 0 |
| **yellow** | a soft failure: it signals, it does not block | 1 |
| **red** | a hard failure: it blocks — in the loop the write is reverted, in CI the output is rejected | 2 |
| **black** | raised by scrutineering (`keyross gate`, the gauges replayed outside the agent) when the agent reported green and the gate found red: an integrity incident, the run is quarantined | — |

`hard` / `soft` remain the values in the JSON; the flags are what people read.

## Rules the tool makes impossible to break

- `keyross lint` **refuses** an oracle that imports a model client, the network, or a source of non-determinism.
- Feedback to the agent is **minimal**: the flag and the category of the deviation — never the logic, the threshold, the list of oracles nor the evidence (`Verdict.minimal()`). Red means pit stop: revert and retry.
- An oracle without a bad case in `badset/` fails `keyross test`: an untested test lies one day.
- An oracle that crashes is a hard red: we never guess.

## A skill asks, a gauge measures

![A skill asks, a gauge measures: the rule inside the context vs the gauges outside it, in the harness](skills_vs_gauges.gif)

A skill, a system prompt or a `CLAUDE.md` is text a model reads and may or may not follow. A gauge is code a model never reads: the harness runs it, the verdict is deterministic, and the proof — verdict, lock, report — can be put in front of an auditor. A gauge that ships a prompt file is not a gauge.

## Writing an oracle

An oracle is a **pure** function: `(document, context) -> Verdict`. No state, no side effect, no network, no model. The canonical document exposes rows with stable identifiers (`rid:12`), blocks (priced lines + subtotal) and the recognized columns; invoices have their own canonical model (`Invoice`: header, lines, VAT breakdown, totals). The context carries what the client provides — unit vocabulary, reference document, document type.

```python
from keyross import oracle, Verdict

@oracle("invoices.total.matches", severity="hard")
def total_matches(doc):
    expected = sum(l.amount for l in doc.amount_lines())
    if abs(doc.lines[-1].amount - expected) > 0.01:
        return Verdict.fail("total ≠ sum of lines", "totals.mismatch", expected=expected)
    return Verdict.ok()
```

Every oracle has an **id** (`gauge.subject.property`), a **version**, a **flag on failure** (red blocks, yellow signals — `hard` / `soft` in the code) and a **bad case** in `badset/<id>.xlsx`. See [CONTRIBUTING.md](../CONTRIBUTING.md), [GOVERNANCE.md](../GOVERNANCE.md) and [GAUGES.md](../GAUGES.md).
