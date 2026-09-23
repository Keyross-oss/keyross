# Benchmark — an invoicing agent, without and with the yoke

Does the yoke change what an agent ships? The same Deep Agent turns a purchase order into an EN 16931 invoice (UN/CEFACT CII, the XML of Factur-X), twice per task: once without the yoke, once with `Yoke(gauge="einvoice")`. Same model, same prompt, same limits. Two graders, both outside the agent, decide.

**Status: harness ready, not yet run on a real model.** No result below is a measurement until a run with a real model is published here.

## Tasks

20 purchase orders (`orders/*.json`), fictitious and deterministic (`python -m bench.einvoice.orders` regenerates them), with rising difficulty:

| scenario | orders | what makes it hard |
|---|---|---|
| domestic | 1–8 | one to three VAT rates, 1–5 lines, quantity × price that needs rounding |
| exempt | 9–11 | an exempt line: the VAT breakdown needs an exemption reason and code |
| intra_community | 12–14 | intra-community supply: seller and buyer VAT identifiers, delivery date and country, exemption reason |
| reverse_charge | 15–16 | reverse charge: both VAT identifiers, exemption reason, 0 % rate |
| allowances | 17–20 | document-level allowances and charges, which move the VAT basis |

Every task is solvable: `reference.py` writes a reference invoice for each order, and all 20 are valid for the official rules and match their order (`python -m bench.einvoice.grade`; also a test).

## Grading

- **valid** — the official CEN EN 16931 validation artefacts (1.3.16) find no fatal rule in the delivered invoice;
- **right** — the delivered invoice matches the order: lines (quantity, price, net amount, VAT category and rate), VAT breakdown per category and rate, totals;
- **correct** — valid **and** right. The second grader matters: an agent can make an invoice valid by bending the order (changing a price so the totals add up). The yoke only runs the first grader, so "right" is measured by something the yoke never sees.

Also recorded: first write valid (the model's own first attempt), writes and pit stops per run, tokens, estimated cost at list prices, time.

## Limits (both arms)

At most 4 writes of the invoice and 12 model calls per run (`ToolCallLimitMiddleware`, `ModelCallLimitMiddleware`) — they bound the cost of a run that would loop.

## Run

```bash
pip install -e ".[einvoice,yoke]"
python -m bench.einvoice.run --model scripted                                   # offline dry run: checks the harness, measures nothing
python -m bench.einvoice.run --model anthropic:claude-sonnet-5 --only order-02,order-10,order-13,order-15,order-18   # pilot: one task per scenario
python -m bench.einvoice.run --model anthropic:claude-sonnet-5 --reps 3         # full run: 20 tasks × 2 arms × 3
python -m bench.einvoice.run --report bench/einvoice/results/<run>.jsonl       # report of a finished run
```

A real model needs its provider's credentials (for Anthropic: `ANTHROPIC_API_KEY`, or a profile from `ant auth login`). Rough cost with `claude-sonnet-5`: a few dollars for the pilot, 15–35 USD for the full run — the pilot measures the real token use first.

The offline `scripted` model is built to fail its first write and fix it after a red flag: its numbers (0 % correct without the yoke, 100 % with) are true by construction and say nothing about real agents.
