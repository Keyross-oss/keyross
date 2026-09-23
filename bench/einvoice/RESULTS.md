# Results — einvoice benchmark, the full run of 23 September 2026

The pre-registered benchmark ([PROTOCOL.md](PROTOCOL.md)), run once and in full: 50 purchase orders × 2 repetitions × 3 arms, 300 runs of the same Deep Agent on `claude-haiku-4-5`, graded by three judges that are not Keyross. Every number below comes from the run's report ([results/20260923T162255Z-claude-haiku-4-5.md](results/20260923T162255Z-claude-haiku-4-5.md)). The raw data and every delivered invoice are published next to it. The blind human review is pending.

## In short

- **The yoke raises the share of correct invoices.** 50 % without it, 64 % with the official rules (H1, Holm-adjusted p = 0.005), 60 % with the rules and the order (H4, p = 0.021). Between the two yoke arms, no difference that 100 pairs can detect (p = 0.39).
- **Its larger effect is on the invoices that ship wrong without anyone being told.** 50 % without the yoke, 22 % with the rules, 11 % with the rules and the order. Those 11 % are all XML schema violations, the one property no arm's yoke checks, as declared before the run.
- **Nothing the yoke checks shipped.** No fatal CEN rule in either yoke arm (33 % without). No amount that differs from the order in the third arm (26 % without).
- **The price is visible.** 14 % (rules) and 29 % (rules and order) of the invoices are not delivered: the agent used its four writes without passing the checks. Tokens rise by 80 % and 140 %. A check takes about 15 ms.
- **Keyross and the independent validator agree.** They report the same fatal rules on 557 of 557 invoices graded.

## The run

| | |
|---|---|
| Date | 23 September 2026, 16:22–17:14 UTC |
| Code | commit `1855858`: the protocol as frozen after deviation 5 |
| Model | `anthropic:claude-haiku-4-5`, provider defaults, streaming |
| Runs | 300 = 50 orders × 2 repetitions × 3 arms: 100 complete blocks, 0 API errors, no run lost |
| Arms | without the yoke · `Yoke(gauge="einvoice")`, the official rules · `Yoke(gauge="einvoice", ctx={"order": order})`, the rules and the order |
| Limits | 4 writes of the invoice and 12 model calls per run, in every arm |
| Judges | easybill/en16931-validator 0.7.0 (CEN 1.3.16) · the Factur-X 1.09 EN 16931 XSD · the order |
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

H1 and H4 hold at α = 0.05 after Holm's correction. The third comparison is exploratory and shows no difference that 100 pairs can detect.

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

What the yoke checks at every write, as stated in the protocol before the run:

| property (judge) | without yoke | yoke: rules | yoke: rules + order |
|---|---|---|---|
| content — the official CEN rules (validator) | no | yes | yes |
| amounts — the invoice against its order (order judge) | no | no | yes |
| structure — the XML schema (schema judge) | no | no | no |

The rows of *What ships* follow this table. What an arm's yoke checks does not ship: no fatal rule in arms 2 and 3, no order mismatch in arm 3. What it does not check does ship: 11 schema violations in both yoke arms. In arm 3, the order check and the order judge test the same property with separate code, so its zero is by construction. What that arm measures is whether the agent gets there: it does not, in 29 runs of 100.

## Hypotheses

| | declared before the run | result |
|---|---|---|
| H1 | the yoke with the rules increases correct delivered invoices | **supported**: 50 → 64 %, Holm-adjusted p = 0.0052 |
| H2 | risk: the yoke may increase *valid but wrong* invoices | **not observed**: 11 → 11 |
| H3 | sanity: first-write rates agree between the arms | **holds**: first write correct 50 / 51 / 48 %, valid 66 / 70 / 61 % |
| H4 | the yoke with the rules and the order increases correct delivered invoices | **supported**: 50 → 60 %, Holm-adjusted p = 0.021 |
| H5 | risk: the order check may make the agent give up more often | **observed**: not delivered 0 / 14 / 29 % |

## How the yoke gets there

In every arm, most correct invoices are right at the first write (50, 51, 48). The yoke adds rescues, and turns the rest into blocks:

| runs that received at least one red flag | yoke: rules | yoke: rules + order |
|---|---|---|
| runs | 30 | 45 |
| … corrected, then correct | 13 | 12 |
| … not delivered | 14 | 29 |
| … delivered, still not correct (schema, or valid but wrong) | 3 | 4 |

With the categories alone, Haiku fixed 13 of 30 flagged runs with the rules, and 12 of 45 with the rules and the order. Of the 33 runs that received an `order.*` flag, 11 ended correct, 19 were not delivered, and 3 shipped with a schema violation. The minimal feedback gives the category, never the expected amount nor the rule text. It is a design choice, and with a small model its cost is the give-ups.

Red flags returned, by category:
- yoke: rules — BR-IC-12 ×57, BR-CO-10 ×15, BR-IC-11 ×13, BR-S-08 ×12, BR-CO-13 ×4, BR-DEC-23 ×3, then single rules;
- yoke: rules + order — `order.totals` ×79, `order.vat` ×77, BR-IC-12 ×68, `order.lines` ×59, BR-CO-10 ×26, BR-S-08 ×25, BR-CO-13 ×11, BR-IC-11 ×9, then the decimal rules.

Correct invoices per scenario:

| scenario | without yoke | yoke: rules | yoke: rules + order |
|---|---|---|---|
| domestic | 14/20 | 16/20 | 17/20 |
| exempt | 13/20 | 16/20 | 16/20 |
| reverse charge | 14/20 | 18/20 | 17/20 |
| allowances and charges | 9/20 | 9/20 | 9/20 |
| intra-community supply | 0/20 | 5/20 | 1/20 |

Two scenarios hold most failures. Both need something the worked example in the prompt does not show: it is a domestic invoice, with no delivery data and no charge.
- **Intra-community supply.** The invoice must give the country the goods were delivered to (BT-80, rule BR-IC-12). Haiku rarely writes it where the rules expect it. BR-IC-12 is the most frequent CEN red flag in both yoke arms, and 29 of the 43 give-ups are intra-community. Without the yoke, no intra-community invoice is correct: they all ship with fatal rules.
- **Allowances and charges.** When the order has a shipping charge, the charge total is written out of place in the XML. That is 9 schema violations in each arm, identical because no yoke checks the schema.

## Cost

| per run | without yoke | yoke: rules | yoke: rules + order |
|---|---|---|---|
| writes | 1.0 | 1.7 | 2.1 |
| tokens | 23,523 | 42,420 | 56,537 |
| seconds | 23.9 | 41.7 | 55.2 |
| cost, USD at list prices | 0.025 | 0.043 | 0.057 |
| yoke check time | — | 26 ms (1.7 checks) | 33 ms (2.1 checks) |

Paired overhead against no yoke, with 95 % bootstrap intervals:
- rules: +18,896 tokens (+12,205 to +26,255, +80 %), +17.7 s (+11.5 to +24.5), +0.018 USD per invoice;
- rules and order: +33,013 tokens (+24,338 to +42,168, +140 %), +31.2 s (+23.3 to +39.6), +0.032 USD per invoice.

The checks themselves take about 15 ms each. The overhead is the model writing again.

## Keyross against the judges

- **Against the independent validator:** the same fatal rules on 557 of 557 invoices graded, every delivered invoice and every first write. The gauge runs the official rules as the validator does.
- **Keyross' delta oracles against the order judge:** the same verdict on 547 of 557. The 10 differences are one case. Orders 03, 24 and 30 each have a line whose exact amount has a third decimal of 5 (1.5 × 89.95 = 134.925; 0.5 × 33.33 = 16.665). Invoices that left such an amount unrounded differ from the order by exactly half a cent. The order judge's tolerance (0.005, as registered) accepts that; the delta oracle does not. All 10 invoices fail the CEN decimal rules (BR-DEC), so none of them is correct and no endpoint changes. The judge stays as registered; the two tolerances will be aligned in the next version.

## What these results do not show

- **Reading.** The agent receives a structured order, whose correct invoice can be computed, and that is what makes 300 invoices gradable. In practice the input is an email or a PDF. This benchmark measures writing the invoice, not reading the order: it is the easiest version of the task. The next step is a version where the agent gets the same orders as emails or PDFs, with the same answer key and the same judges.
- **Other models and settings.** There is one model (Haiku 4.5), one prompt with one worked example, and four writes per run. A stronger model, a richer example or more writes would change the give-up rate.
- **The XML schema.** No arm's yoke checks it, and 11 % of invoices ship with a schema violation in both yoke arms. The schema step is planned for the `einvoice` gauge.
- **Arm 3's zero.** Its order check and the order judge test the same property, so its 0 % of wrong amounts is by construction, as stated before the run.
- **Tasks seen in the pilots.** The pilots ran on order-01 to order-05, which are among the 50 tasks. They informed deviations 2 to 5, all of which are general: none is specific to an order.
- **Parties, dates, payment details.** No automated judge compares them with the order; the human review reads them.
- **Interim looks.** Two descriptive looks were taken during the run, at the owner's request: after 20 orders, and after 57 blocks. No test was run and nothing changed (protocol, deviation 6).

## Human review — pending

21 delivered invoices, 7 per arm, were drawn with `random.Random(2027)` and renamed so the arm is hidden (`review.py sample`). The reviewer's verdicts and their agreement with the three judges will be added here, with every disagreement.

## Next

- A more precise minimal feedback, naming the line and the field but never the expected value, to cut the give-ups; measured with this benchmark.
- The XML schema step in the `einvoice` gauge, before the CEN rules.
- The benchmark with messy input: the same orders, as emails or PDFs.
- One tolerance, half a cent, for the order judge and the delta oracles.

## Files and reproduction

- [PROTOCOL.md](PROTOCOL.md): the pre-registered protocol and its deviations
- [results/20260923T162255Z-claude-haiku-4-5.jsonl](results/20260923T162255Z-claude-haiku-4-5.jsonl): one JSON line per run
- [results/20260923T162255Z-claude-haiku-4-5.md](results/20260923T162255Z-claude-haiku-4-5.md): the report, as the run printed it
- [results/20260923T162255Z-claude-haiku-4-5/](results/20260923T162255Z-claude-haiku-4-5/): the 257 delivered invoices, named `<order>-<arm>-<repetition>.xml`

```bash
python -m bench.einvoice.run --report bench/einvoice/results/20260923T162255Z-claude-haiku-4-5.jsonl   # the report, again
python -m bench.einvoice.run --model anthropic:claude-haiku-4-5 --reps 2                                 # a new run, about 13 USD
```
