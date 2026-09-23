# Benchmark — an invoicing agent, without and with the yoke

Does the yoke change what an agent ships, and at what cost? The same Deep Agent turns a purchase order into an EN 16931 invoice (UN/CEFACT CII, the XML of Factur-X), in three arms: without the yoke; with `Yoke(gauge="einvoice")`, the official rules; and with the official rules and the order, `Yoke(gauge="einvoice", ctx={"order": order})`, whose delta oracles catch an invoice that is valid but bills the wrong amount. Same model, prompt and limits in every arm. **None of the judges is Keyross**, so the yoke is never graded by its own code.

**Status: pre-registered; two pilots run, excluded from the analysis; the full run not yet made.** The protocol — design, endpoints, analysis, human review — is fixed in [PROTOCOL.md](PROTOCOL.md) before the first paid run, and every change since is recorded there with its date and reason (model, harness, worked example, third arm). Every result will be published, favourable or not.

## Design, in short

- **50 purchase orders** (`orders/`, fictitious, seeded), 10 per scenario: domestic, exempt (an exemption reason is due), intra-community supply, reverse charge, document-level allowances and charges. Every task is solvable: the 50 reference invoices pass the three judges.
- **Paired**: each order runs twice in each arm — 100 blocks, 300 runs. Every arm gets the same prompt, which ends with a worked example: an order outside the 50 and the invoice issued for it (`example/`), as a company gives a template.
- **Three judges, independent of Keyross:**
  1. **validator** — easybill/en16931-validator (MIT, Docker, pinned by digest): an independent implementation of the official CEN EN 16931 rules, release 1.3.16. There is one official rule set; this is another implementation of it, not other rules;
  2. **schema** — the official Factur-X 1.09 EN 16931 XSD, which checks the structure the CEN rules do not;
  3. **order** — lines, VAT breakdown and totals against what the order implies. It catches an invoice made valid by bending the order.
- **Correct** = accepted by all three. Primary endpoint: correct delivered invoice, per block — no yoke against each yoke arm, exact McNemar tests, Holm-adjusted; exact counts, Wilson intervals.
- **What the yoke checks, and what it does not**, at every write: the official CEN rules (arms 2 and 3) and the order (arm 3). No arm's yoke checks the XML schema: a schema violation can ship in every arm, and the schema judge counts it (the table in the protocol, printed in every report).
- In the third arm, the yoke and the order judge check the same property with separate code, so a delivered invoice matches the order almost by construction. What that arm measures is whether the agent gets there from the categories alone (`order.lines`, `order.vat`…), within its limits, and at what cost — or gives up.
- Also reported: residual errors in what ships (including *valid but wrong*), the model's first write, not delivered, writes and pit stops, the red flags by category, token and time overhead of the yoke (paired bootstrap), estimated cost, agreement between Keyross and the independent validator and between Keyross' delta oracles and the order judge, results per scenario, and a blind human review of 21 invoices.

A first measurement of the adapter, before any agent run: on 46 invoices (the CEN and Factur-X examples, the 20 bad cases, 20 references), **Keyross and the independent validator report the same fatal rules and warnings on 46 of 46**. CI checks this on every commit.

## Run

```bash
pip install -e ".[einvoice,yoke,bench]"
python -m bench.einvoice.judges --setup          # the schema (pinned); prints the command that starts the validator
docker run -d --name keyross-bench-validator -p 127.0.0.1:8081:8080 -e JAVA_TOOL_OPTIONS=-Xmx512m \
  easybill/en16931-validator@sha256:e2f84d3d371e95d9eae2da0ccaef5a13bf01f2e58278e9080994ae763d8914dd

python -m bench.einvoice.run --model scripted --tasks 10      # offline dry run: checks the harness, measures nothing
python -m bench.einvoice.run --model anthropic:claude-haiku-4-5 --arms with_order --only order-01,order-02,order-03,order-04,order-05   # pilot of the third arm
python -m bench.einvoice.run --model anthropic:claude-haiku-4-5 --reps 2                                            # full run: 300 runs
python -m bench.einvoice.review sample bench/einvoice/results/<run>.jsonl   # the blind review sheet; then fill review.csv
python -m bench.einvoice.review score  bench/einvoice/results/<run>.jsonl   # agreement between the reviewer and the judges
```

A real model needs its provider's credentials (for Anthropic: `ANTHROPIC_API_KEY`). The model is `claude-haiku-4-5` (see the protocol's deviations). Rough cost, from the second pilot's real token use (about 0.03 USD per run without the yoke, 0.05 with it): under 1 USD for the pilot of the third arm, 12–22 USD for the full run. Each run is capped at 4 writes of the invoice and 12 model calls, in every arm.

The offline `scripted` model is built to fail its first write and fix it after a red flag: its numbers are true by construction and say nothing about real agents.
