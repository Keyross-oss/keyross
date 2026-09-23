# Benchmark — an invoicing agent, without and with the yoke

Does the yoke change what an agent ships, and at what cost? The same Deep Agent turns a purchase order into an EN 16931 invoice (UN/CEFACT CII, the XML of Factur-X), with and without `Yoke(gauge="einvoice")`. Same model, prompt and limits. **None of the judges is Keyross**, so the yoke is never graded by its own code.

**Status: pre-registered, not yet run on a real model.** The protocol — design, endpoints, analysis, human review — is fixed in [PROTOCOL.md](PROTOCOL.md) before the first paid run. Every result will be published, favourable or not.

## Design, in short

- **50 purchase orders** (`orders/`, fictitious, seeded), 10 per scenario: domestic, exempt (an exemption reason is due), intra-community supply, reverse charge, document-level allowances and charges. Every task is solvable: the 50 reference invoices pass the three judges.
- **Paired**: each order runs twice in each arm — 100 pairs.
- **Three judges, independent of Keyross:**
  1. **validator** — easybill/en16931-validator (MIT, Docker, pinned by digest): an independent implementation of the official CEN EN 16931 rules, release 1.3.16. There is one official rule set; this is another implementation of it, not other rules;
  2. **schema** — the official Factur-X 1.09 EN 16931 XSD, which checks the structure the CEN rules do not;
  3. **order** — lines, VAT breakdown and totals against what the order implies. It catches an invoice made valid by bending the order.
- **Correct** = accepted by all three. Primary endpoint: correct delivered invoice, per pair — exact McNemar test, exact counts, Wilson intervals.
- Also reported: residual errors in what ships (including *valid but wrong*), the model's first write, not delivered, writes and pit stops, token and time overhead of the yoke (paired bootstrap), estimated cost, agreement between Keyross and the independent validator, results per scenario, and a blind human review of 20 invoices.

A first measurement of the adapter, before any agent run: on 46 invoices (the CEN and Factur-X examples, the 20 bad cases, 20 references), **Keyross and the independent validator report the same fatal rules and warnings on 46 of 46**. CI checks this on every commit.

## Run

```bash
pip install -e ".[einvoice,yoke,bench]"
python -m bench.einvoice.judges --setup          # the schema (pinned); prints the command that starts the validator
docker run -d --name keyross-bench-validator -p 127.0.0.1:8081:8080 -e JAVA_TOOL_OPTIONS=-Xmx512m \
  easybill/en16931-validator@sha256:e2f84d3d371e95d9eae2da0ccaef5a13bf01f2e58278e9080994ae763d8914dd

python -m bench.einvoice.run --model scripted --tasks 10      # offline dry run: checks the harness, measures nothing
python -m bench.einvoice.run --model anthropic:claude-haiku-4-5 --only order-01,order-02,order-03,order-04,order-05   # pilot
python -m bench.einvoice.run --model anthropic:claude-haiku-4-5 --reps 2                                            # full run: 200 runs
python -m bench.einvoice.review sample bench/einvoice/results/<run>.jsonl   # the blind review sheet; then fill review.csv
python -m bench.einvoice.review score  bench/einvoice/results/<run>.jsonl   # agreement between the reviewer and the judges
```

A real model needs its provider's credentials (for Anthropic: `ANTHROPIC_API_KEY`). The model is `claude-haiku-4-5` (see the protocol's deviations). Rough cost: 1–2 USD for the pilot, 15–30 USD for the full run; the pilot measures the real token use first. Each run is capped at 4 writes of the invoice and 12 model calls, in both arms.

The offline `scripted` model is built to fail its first write and fix it after a red flag: its numbers are true by construction and say nothing about real agents.
