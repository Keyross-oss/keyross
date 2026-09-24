# Benchmark — an invoicing agent, without and with the yoke

Does the yoke change what an agent ships, and at what cost? The same Deep Agent turns a purchase order into an EN 16931 invoice (UN/CEFACT CII, the XML of Factur-X), in three arms: without the yoke; with `Yoke(gauge="einvoice")`, the official rules; and with the official rules and the order, `Yoke(gauge="einvoice", ctx={"order": order})`. Same model, prompt and limits in every arm. **None of the judges is Keyross**, so the yoke is never graded by its own code.

The protocol was written and frozen before the first paid run: [PROTOCOL.md](PROTOCOL.md), with its six dated deviations. This page reports the full run of 23 September 2026 — measured numbers only. Every number here is recomputed from the raw results by the command under *Files*. The blind human review agrees with the three judges on 21 of 21 invoices.

## The run

| | |
|---|---|
| Date | 23 September 2026, 16:22–17:14 UTC |
| Code | commit `1855858`, the protocol as frozen after deviation 5 |
| Model | `anthropic:claude-haiku-4-5`, provider defaults, streaming |
| Runs | 300 = 50 orders × 2 repetitions × 3 arms: 100 complete blocks, 0 API errors, no run lost |
| Limits | 4 writes of the invoice and 12 model calls per run, in every arm |
| Judges | easybill/en16931-validator 0.7.0, image `sha256:e2f84d3d371e95d9eae2da0ccaef5a13bf01f2e58278e9080994ae763d8914dd`, CEN rules 1.3.16 · the Factur-X 1.09 EN 16931 XSD (factur-x 6.8 wheel, `sha256:02b57dd5…`) · the match with the order |
| Cost | 12.57 USD at list prices |

## Primary endpoint — a correct delivered invoice

An invoice is correct when the three judges accept it.

| | without yoke | yoke: rules | yoke: rules + order |
|---|---|---|---|
| correct | 50/100 (50 %, CI 40–60) | 64/100 (64 %, CI 54–73) | 60/100 (60 %, CI 50–69) |

| paired comparison | both correct | only the first | only the second | neither | exact McNemar p | Holm-adjusted p |
|---|---|---|---|---|---|---|
| without yoke → yoke: rules (**H1**) | 47 | 3 | 17 | 33 | 0.0026 | **0.0052** |
| without yoke → yoke: rules + order (**H4**) | 47 | 3 | 13 | 37 | 0.021 | **0.021** |
| yoke: rules → yoke: rules + order (exploratory) | 56 | 8 | 4 | 32 | 0.39 | — |

H1 and H4 hold at α = 0.05 after Holm's correction. The third comparison shows no difference that 100 pairs can detect.

## What ships

| per 100 runs | without yoke | yoke: rules | yoke: rules + order |
|---|---|---|---|
| correct | 50 | 64 | 60 |
| not delivered: blocked, and visible | 0 | 14 | 29 |
| **delivered and not correct: nobody is told** | **50** | **22** | **11** |
| … with a fatal CEN rule (validator) | 33 | 0 | 0 |
| … with an XML schema violation | 26 | 11 | 11 |
| … with an amount that differs from the order | 26 | 11 | 0 |
| … valid but wrong: passes the validator and the schema, differs from the order | 11 | 11 | 0 |

The last four rows overlap, since one invoice can fail several judges; *delivered and not correct* counts each invoice once. It sums up the pre-registered rows; it is not a new endpoint.

What each arm's yoke checks at every write, as declared before the run:

| property (judge) | without yoke | yoke: rules | yoke: rules + order |
|---|---|---|---|
| content — the official CEN rules (validator) | no | yes | yes |
| amounts — the invoice against its order (order judge) | no | no | yes |
| structure — the XML schema (schema judge) | no | no | no |

What an arm's yoke checks does not ship; what it does not check does. In arm 3 the order check and the order judge test the same property with separate code, so its zero is by construction: what that arm measures is whether the agent gets there — it does not, in 29 runs of 100.

## Hypotheses, declared before the run

| | hypothesis | result |
|---|---|---|
| H1 | the yoke with the rules increases correct delivered invoices | **supported**: 50 → 64 %, Holm-adjusted p = 0.0052 |
| H2 | risk: the yoke may increase *valid but wrong* invoices | **not observed**: 11 → 11 |
| H3 | sanity: first-write rates agree between the arms | **holds**: first write correct 50 / 51 / 48 %, valid 66 / 70 / 61 % |
| H4 | the yoke with the rules and the order increases correct delivered invoices | **supported**: 50 → 60 %, Holm-adjusted p = 0.021 |
| H5 | risk: the order check may make the agent give up more often | **observed**: not delivered 0 / 14 / 29 % |

## Rescues, and how they relate to the paired table

A **rescue** is counted within one arm: a run that received at least one red flag and ended correct.

| within the arm | yoke: rules | yoke: rules + order |
|---|---|---|
| runs with at least one red flag | 30 | 45 |
| … corrected, then correct (a rescue) | 13 | 12 |
| … not delivered | 14 | 29 |
| … delivered, still not correct | 3 | 4 |

The paired table above counts something else: blocks won and lost *between* arms (17 won and 3 lost for the rules, 13 and 3 for the rules and the order). A block can be won without a rescue, because the model samples its first write independently in each arm: a first write right in the yoked arm and wrong in the other counts as won. The net gain (+14 and +10 correct) is the rescues (13 and 12) plus the difference in first writes (51 − 50 = +1 and 48 − 50 = −2).

With the categories alone, of the 33 runs that received an `order.*` flag, 11 ended correct, 19 were not delivered and 3 shipped with a schema violation.

## Correct invoices per scenario

| scenario | without yoke | yoke: rules | yoke: rules + order |
|---|---|---|---|
| domestic | 14/20 | 16/20 | 17/20 |
| exempt | 13/20 | 16/20 | 16/20 |
| reverse charge | 14/20 | 18/20 | 17/20 |
| allowances and charges | 9/20 | 9/20 | 9/20 |
| intra-community supply | 0/20 | 5/20 | 1/20 |

Both weak scenarios need something the worked example in the prompt does not show (it is a domestic invoice, with no delivery data and no charge):
- **intra-community supply** — the deliver-to country (BT-80, rule BR-IC-12) is rarely written where the rules expect it. BR-IC-12 is the most frequent official-rule red flag (57 and 68 times); 29 of the 43 give-ups are intra-community; without the yoke, all 20 of these invoices ship with fatal rules;
- **allowances and charges** — when the order has a shipping charge, the charge total is written out of place in the XML in 9 of 10 runs, in every arm: no arm checks the schema.

Red flags returned, by category: rules — BR-IC-12 ×57, BR-CO-10 ×15, BR-IC-11 ×13, BR-S-08 ×12, BR-CO-13 ×4, BR-DEC-23 ×3, then single rules; rules + order — `order.totals` ×79, `order.vat` ×77, BR-IC-12 ×68, `order.lines` ×59, BR-CO-10 ×26, BR-S-08 ×25, BR-CO-13 ×11, BR-IC-11 ×9, then the decimal rules.

## Cost

| per run | without yoke | yoke: rules | yoke: rules + order |
|---|---|---|---|
| writes | 1.0 | 1.7 | 2.1 |
| tokens | 23,523 | 42,420 | 56,537 |
| seconds | 23.9 | 41.7 | 55.2 |
| cost, USD at list prices | 0.025 | 0.043 | 0.057 |
| yoke checks | — | 1.7 | 2.1 |
| yoke check time, per run | — | 26.1 ms | 33.2 ms |
| **yoke check time, per check** | — | **15.2 ms** (median 14.9) | **15.6 ms** (median 14.4) |

The per-run check time is the per-check time times the number of checks in the run (172 and 213 checks in all). Paired overhead against no yoke, with 95 % bootstrap intervals: rules +18,896 tokens (+12,205 to +26,255, +80 %), +17.7 s (+11.5 to +24.5), +0.018 USD per invoice; rules and order +33,013 tokens (+24,338 to +42,168, +140 %), +31.2 s (+23.3 to +39.6), +0.032 USD. The overhead is the model writing again, not the checks.

## Keyross against the judges

- **Against the independent validator:** the same fatal rules on **557 of 557** invoices graded (every delivered invoice and every first write).
- **Keyross' delta oracles against the order judge:** the same verdict on **547 of 557**. The 10 differences are one case: orders 03, 24 and 30 each have a line whose exact amount has a third decimal of 5 (1.5 × 89.95 = 134.925; 0.5 × 33.33 = 16.665). An invoice that leaves such an amount unrounded differs from the order by exactly half a cent: the order judge's tolerance (0.005, `<=`, as registered) accepts it, the delta oracle does not. All 10 invoices fail the CEN decimal rules (BR-DEC), so none of them is correct and no endpoint changes. The registered judge stays as it is for this run; the calibration is [issue #1](https://github.com/Keyross-oss/keyross/issues/1).

## What these results do not show

- **Reading.** The agent receives a structured order, whose correct invoice can be computed — that is what makes 300 invoices gradable. In practice the input is an email or a PDF: this benchmark measures writing the invoice, not reading the order, and is the easiest version of the task.
- **Other models and settings.** One model, one prompt with one worked example, four writes per run.
- **The XML schema.** No arm's yoke checks it; 11 % of invoices ship with a schema violation in both yoked arms.
- **Arm 3's zero.** Its order check and the order judge test the same property; its 0 % of wrong amounts is by construction (stated before the run).
- **Tasks seen in the pilots.** The pilots ran on order-01 to order-05, among the 50 tasks; they informed deviations 2 to 5, all general.
- **Parties, dates, payment details.** No automated judge compares them with the order; the human review read them on 21 invoices.
- **Interim looks.** Two descriptive looks during the run, at the owner's request; no test, nothing changed (deviation 6).

## Next measurements

- **The XML schema step** in the `einvoice` gauge, run again on this benchmark: the 11 % should move from *shipped wrong* to *blocked* or *correct*. A target, not a result.
- **Sharper minimal feedback** — the line and the field that failed, never the expected value — to reduce give-ups.
- **Messy input** — the same orders as emails or PDFs, with the same answer key and the same judges.
- **One tolerance** for the order judge and the delta oracles ([issue #1](https://github.com/Keyross-oss/keyross/issues/1)).

## Human review — blind, 21 of 21 agree

21 delivered invoices, 7 per arm, were drawn with `random.Random(2027)` and renamed so the arm was hidden (`review.py sample`). On 24 September 2026 the reviewer, the project's owner, compared each with its order, blind to the arm, and wrote `correct` or `incorrect` with what is wrong. The notes were written in French and are published translated.

| | without yoke | yoke: rules | yoke: rules + order |
|---|---|---|---|
| the reviewer agrees with the three judges | 7/7 | 7/7 | 7/7 |
| incorrect, for the judges and for the reviewer | 3 | 1 | 0 |

No disagreement. The four incorrect invoices, as the reviewer found them:
- invoice-06 (no yoke): 12.75 × 89.95 written 1,146.81 and 0.5 × 89.95 written 45.00, carried into the totals — valid but wrong;
- invoice-14 (no yoke): 5 × 7.45 written 37.50, carried into the VAT and the totals — valid but wrong;
- invoice-21 (yoke with the rules only): 12.75 × 89.95 written 1,146.81 — valid but wrong, which the official rules cannot see;
- invoice-05 (no yoke): amounts left unrounded (0.5 × 33.33 = 16.665). The validator rejects it, so it is incorrect for the three judges together; but it is one of the 10 half-cent cases, where the order judge alone accepts the amounts and Keyross' delta oracles refuse them. The reviewer read the amounts as wrong — evidence for the stricter tolerance ([issue #1](https://github.com/Keyross-oss/keyross/issues/1)).

What the review cannot tell: it reads what the invoice says, not its XML structure. The one schema-invalid invoice of the sample also breaks the official rules, so no invoice in it fails on the schema alone, and the review does not test the schema judge. The reviewer knows the study's aims; only the arm was hidden.

Files: [REVIEW.md](results/20260923T162255Z-claude-haiku-4-5-review/REVIEW.md) (the sheet), [review.csv](results/20260923T162255Z-claude-haiku-4-5-review/review.csv) (the verdicts), [SCORE.md](results/20260923T162255Z-claude-haiku-4-5-review/SCORE.md), the key [20260923T162255Z-claude-haiku-4-5-review-key.json](results/20260923T162255Z-claude-haiku-4-5-review-key.json).

## Design, in short

- **50 purchase orders** (`orders/`, fictitious, seeded), 10 per scenario. Every task is solvable: the 50 reference invoices pass the three judges.
- **Paired**: each order runs twice in each arm — 100 blocks, 300 runs. Every arm gets the same prompt, which ends with a worked example (`example/`).
- **Three judges, independent of Keyross**: the easybill validator, an independent implementation of the one official CEN rule set; the Factur-X XSD, which checks the structure the CEN rules do not; the order match.
- Before any agent run, on 46 invoices (CEN and Factur-X examples, bad cases, references), Keyross and the independent validator reported the same fatal rules and warnings on 46 of 46. CI checks this on every commit.

## Files and recomputing

- [PROTOCOL.md](PROTOCOL.md) — the pre-registered protocol and its deviations
- [results/20260923T162255Z-claude-haiku-4-5.jsonl](results/20260923T162255Z-claude-haiku-4-5.jsonl) — one JSON line per run
- [results/20260923T162255Z-claude-haiku-4-5.md](results/20260923T162255Z-claude-haiku-4-5.md) — the report as the run printed it
- [results/20260923T162255Z-claude-haiku-4-5/](results/20260923T162255Z-claude-haiku-4-5/) — the 257 delivered invoices, `<order>-<arm>-<repetition>.xml`

```bash
pip install -e ".[einvoice,yoke,bench]"
python -m bench.einvoice.run --report bench/einvoice/results/20260923T162255Z-claude-haiku-4-5.jsonl   # every number on this page
```

The report command also prints the per-check time and the rescue table, which the run's original report did not include yet.

## Run it again

```bash
python -m bench.einvoice.judges --setup          # the schema (pinned); prints the command that starts the validator
docker run -d --name keyross-bench-validator -p 127.0.0.1:8081:8080 -e JAVA_TOOL_OPTIONS=-Xmx512m \
  easybill/en16931-validator@sha256:e2f84d3d371e95d9eae2da0ccaef5a13bf01f2e58278e9080994ae763d8914dd

python -m bench.einvoice.run --model scripted --tasks 10                   # offline dry run: checks the harness, measures nothing
python -m bench.einvoice.run --model anthropic:claude-haiku-4-5 --reps 2   # the full run: 300 runs, about 13 USD
python -m bench.einvoice.review sample bench/einvoice/results/<run>.jsonl  # the blind review sheet; then fill review.csv
python -m bench.einvoice.review score  bench/einvoice/results/<run>.jsonl  # agreement between the reviewer and the judges
```

A real model needs its provider's credentials (for Anthropic: `ANTHROPIC_API_KEY`). The offline `scripted` model is built to fail its first write and fix it after a red flag: its numbers are true by construction and say nothing about real agents.
