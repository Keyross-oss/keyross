# Audit trail — what was verified, and how a third party replays it

"How do you prove what the agent shipped?" Keyross answers with three things a third party can check without trusting the agent or us:

| | What it is | Where |
|---|---|---|
| **The report** | every `keyross check` writes one: the document, the context, every verifier that ran with its version and flag, and each deviation with its evidence | `.keyross/reports/<document>.md` (`report_dir` in `keyross.yaml`) |
| **The lock** | the fingerprint of every oracle and the SHA-256 of every official artefact that ran — "what verified this run?" | `keyross.lock` |
| **The gate** | replays every gauge outside the agent, on a folder of outputs, and returns the verdict as an exit code | `keyross gate <folder>`, or the [GitHub Action](../integrations/github-action/README.md) in CI |

A signed audit receipt (the document's hash, the lock and the verdicts in one file, verifiable offline) is planned; today the report and the lock are the record.

## A real report

The invoice in [`audit-trail/`](audit-trail/) was delivered by an agent in the [e-invoice benchmark](../bench/einvoice/README.md), without the yoke (run `20260923T162255Z`, order-07, repetition 1 — byte for byte the published file). Checked against the official EN 16931 rules alone, it is **green**: it is coherent with itself. Checked with the order it was issued for, it is **red**:

```text
$ keyross check invoice.xml
  ✔ einvoice.schematron        CEN/TC 434 EN 16931 validation artefacts 1.3.16: 0 finding(s) on 0 rule(s)
  ✔ einvoice.delta.order.header ok
  ✘ einvoice.delta.order.lines 2 line deviation(s) from the order  [red]
  ✘ einvoice.delta.order.totals 5 total(s) differ from the order  [red]
  ✘ einvoice.delta.order.vat   2 VAT breakdown deviation(s) from the order  [red]
2 green · 3 red · 0 yellow — red flag — output rejected (exit 2)
```

The agent only ever receives the categories (`order.lines`, `order.totals`, `order.vat`). The report keeps the evidence — [`audit-trail/report.md`](audit-trail/report.md), as written by that run:

```text
### einvoice.delta.order.lines — order.lines
- deviations: [{'line': '3', 'issue': 'net amount', 'expected': '1146.86', 'actual': 1146.81},
               {'line': '5', 'issue': 'net amount', 'expected': '44.98', 'actual': 45.0}]
```

12.75 × 89.95 is 1,146.86; the agent wrote 1,146.81 and carried the error into every total, so the official rules — which check that an invoice is coherent with itself — accept it. Only the order can catch it.

## The lock

[`audit-trail/keyross.lock`](audit-trail/keyross.lock) pins what ran: the two CEN artefacts by SHA-256, and each of the 1,566 oracles by fingerprint and version.

```json
"einvoice.schematron": {
  "artifacts": {
    "rules/cen-1.3.16/EN16931-CII-validation.xslt": "0b234dea2bbfee739b7761e607a992c17fab88773014ef56355b6158cfb1cc53",
    "rules/cen-1.3.16/EN16931-UBL-validation.xslt": "39f9d282867f1a49e7708d9e29a53da89643e1ee56f10cec1ebcf1277595fcbd"
  },
  "offline": true, "tool": "CEN/TC 434 EN 16931 validation artefacts", "version": "1.3.16"
},
"einvoice.br-co-10": { "fingerprint": "8031961bd666", "kind": "adapter", "severity": "hard", "version": "1.3.16" },
"einvoice.delta.order.lines": { "fingerprint": "8ed2c3b266c7", "kind": "invariant", "severity": "hard", "version": 1 }
```

If a rule, an oracle or an artefact changes, `keyross lock --check` fails: a verdict is never silently produced by different rules.

## Replay it

```bash
pip install "keyross[einvoice]"
git clone https://github.com/Keyross-oss/keyross && cd keyross/docs/audit-trail
keyross lock --check        # ✔ pinning respected — the rules installed are the rules that ran
keyross check invoice.xml   # exit 2 — the same three red verdicts, the same evidence in the report
```

`keyross.yaml` in that folder loads the `einvoice` gauge and carries the order in its `context`; remove the order and the same command returns green, as the official rules alone do. No network is used during the check, and no model is in the loop.
