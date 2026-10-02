# Gauges — the registry

*A gauge is the unit: a versioned set of oracles for one document family, tested against its bad cases and pinned by the lock. Official rules run unmodified; your own checks are added. Gauges measure; the yoke couples your agent to them; flags decide what ships.*

`keyross gauges` · `keyross add <gauge>` · `keyross outdated`. Format: [docs/spec/gauge.md](docs/spec/gauge.md).

Two homes. **Built-in gauges** ship inside the `keyross` package (`core`, `einvoice`). **Packages** will live in `packages/<name>/` in this repository, and `keyross add` will copy them into yours from this repository's index (0.2): you read the code, you own it, the lock pins it.

**Rule of the house: if a public validator exists, the gauge runs it; it never reimplements it.** A verdict that disagrees with the official validator is a bug in the gauge. Then the gauge adds the **delta oracles** the standard cannot know: your reference data, consistency across documents, the contracts of the agent's actions.

**A gauge is code, not a skill or a prompt.** It contains oracles (pure functions), adapters that execute official validators pinned by version and checksum, and the bad cases that test them. Nothing in a gauge is ever read by a model; the model only receives a flag and a category. A gauge that ships a prompt file, a `CLAUDE.md` or instructions to a model is not merged.

## On the shelf

| Gauge | Status | What it checks | Rules |
|---|---|---|---|
| `core` | **shipped** | priced tables (quotes, bills of quantities, any priced sheet): schema, totals, duplicates, unit vocabulary, numbering, conservation (a sentinel); the `delete_rows` contract | ours |
| `einvoice` | **shipped** (gauge 0.2.0) | EN 16931 electronic invoices (UBL, CII — the XML of Factur-X): the official CEN validation artefacts 1.3.16 run unmodified, one oracle per rule id (1,562), offline, pinned by SHA-256; delta oracles that check the invoice against its order. Measured in a [pre-registered benchmark](bench/einvoice/README.md) | official, never rewritten |
| `rules` | planned | your `AGENTS.md` / `CLAUDE.md` rules — scope, file size, tests, dependencies, public API, secrets — run on the diff, with git as the only truth | yours, in ten lines |
| `payments` | planned | a payment run checked against what the run cannot rewrite: the supplier master data, the open invoices, the IBAN checksum, sanctions lists, the bank calendar | ISO 13616, ISO 20022, official lists |

The same list is in the registry index (`src/keyross/gauges/index.json`), which `keyross gauges` reads. Nothing planned is announced as shipped; a planned gauge appears here when its first version is in this repository with its bad cases.

**Want a verifier that is not here?** Tell us the document your agent got wrong, and where the truth lives: open a discussion in the **Wanted verifier** category.

## Good first contributions

**For `einvoice` — the gauge, never the rules.** The BR-* rules already exist as official Schematron; do not rewrite them.

- ~~`einvoice.schematron`~~, ~~the UBL / CII loaders~~ — shipped in 0.1.0; ~~`einvoice.delta.order_match`~~ — shipped in gauge 0.2.0 as `einvoice.delta.order.header`, `.lines`, `.vat`, `.totals` ([gauge README](src/keyross/gauges/einvoice/README.md))
- `einvoice.dates.ordered` — the payment due date (BT-9) is not before the issue date (BT-2): no EN 16931 rule checks it. Load BT-9 in the UBL and CII loaders, write the oracle, add one bad invoice
- `einvoice.facturx.pdf` — extract the CII XML embedded in a Factur-X PDF, offline, then run the same adapter
- `einvoice.delta.supplier_reference` — seller identifiers against the client's supplier master data
- `einvoice.contract.issue_invoice` — the action contract of an agent that issues an invoice: what it announced is what was written

**For `core` — needs real documents first.** `core.amount.sign` (a negative amount is legitimate on a discount or a credit line) and `core.line.qty_pu_amount` (lump-sum and "for the record" lines carry no unit price) only make sense once calibrated on real priced tables; bring a few anonymised ones with the proposal.

Open an issue with the **New oracle** template; the bad case is half of the work.

## Where the gauges plug in

- **In CI** — `keyross gate` on a folder of outputs, or the [GitHub Action](integrations/github-action/README.md) (shipped). A `pre-commit` hook is planned.
- **In the loop** — the [yoke](src/keyross/yoke/README.md) for Deep Agents and LangChain (shipped): every write is measured, a red write is reverted, the agent gets the rule ids. Native hooks for Claude Code, Codex CLI and Gemini CLI are planned.
- **As a service** — an MCP server, later.
