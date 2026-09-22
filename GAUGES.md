# Gauges — the registry

*A gauge is the installable instrument: a versioned, calibrated set of oracles for one document family. Official validators adapted (homologated), your own oracles added. Gauges measure; the yoke couples your agent to them; scrutineering decides.*

`keyross gauges` · `keyross add <gauge>@<version>` · `keyross outdated` · `keyross update` (0.3). Every gauge is a versioned, signed unit with its own badset and a changelog that cites the revision of the standard behind each version. Format: [docs/spec/gauge.md](docs/spec/gauge.md).

The goal of this repository is to **make agents accountable to the compilers that official documents already have — and to write the ones they don't**. Official standards ship their own validators (the CEN Schematron for EN 16931 invoices, the ESAs' validation rules for the DORA register): we do not rewrite those rules. A gauge **wraps the official validator as an oracle** — pinned by release and checksum, executed by the harness, minimal feedback to the agent, replayed at the gate — and adds the **delta oracles** the standard cannot know: cross-document consistency, the client's reference data, the action contracts of the agent. Pick one below, or propose yours.

**Rule of the house: if a public validator exists, the gauge adapts it; it never reimplements it.** A verdict that disagrees with the official validator is a bug in the gauge.

**A gauge is code, not a skill or a prompt.** It contains oracles (pure functions), adapters that execute official validators pinned by version and checksum, and the bad cases that test them. Nothing in a gauge is ever read by a model; the model only receives a flag and a category. A gauge that ships a prompt file, a `CLAUDE.md` or instructions to a model is not a gauge and is not merged.

## Gauges, in order of priority

| # | Gauge | Status | What it compiles | Rules | Deadline / driver | Owner |
|---|---|---|---|---|---|---|
| 1 | `core` | **shipped (0.1)** | the universal invariants of priced documents: schema, totals, duplicates, unit vocabulary, numbering, conservation (sentinel); `delete_rows` contract | ours | — | maintainers |
| 2 | `einvoice` | **adapter shipped (0.1.0)** — delta oracles next | electronic invoices — EN 16931 (Factur-X, UBL, CII), Peppol BIS Billing. **Adapter** (shipped): runs the official CEN validation artefacts 1.3.16 unmodified (Saxon-HE, offline) as one oracle per rule id — 1,562 ids, BR-*, BR-CO-*, BR-CL-*, syntax rules — pinned by release + SHA-256, one bad case per rule family; **delta oracles**: invoice vs order / delivery, supplier and contract reference data, agent action contracts | official validators exist (ConnectingEurope/eInvoicing-EN16931, KoSIT, phive, easybill, Klarfakt) — reused, never rewritten | e-invoicing mandatory in several member states; France rolling out since September 2026 | wanted — good first gauge |
| 3 | `dora.register` | planned | the DORA Register of Information (xBRL-CSV, 15 templates). **Adapter**: the ESAs' published validation rules and the open validators (DORA ROI Validator — Python, MIT; `dora-lei-check` for LEI status); **delta oracles**: register vs the contracts and the localisation table actually held by the entity, third parties called by agents vs third parties declared | official rules + open validators exist — reused | annual submission by every EU financial entity | Keyross |
| 4 | `aiact.annex4` | planned | the EU AI Act technical documentation (Annex IV). Scaffolds exist (`plusultra-tools/ai-act-conformity-pack`); the Keyross oracle is the part nobody has: **consistency of the documentation with the actual traces** of the telemetry (versions, human oversight, logging, third parties) | EU regulation | 2 December 2027 | Keyross |
| 5 | `governance` | planned | the behavioural evidence read from the telemetry: pinned versions, decision linkage, gate executed, human oversight, masked egress, third parties declared, retention, incident timeline, sentinel coverage, policy promotion, canary alive, registry complete. Complementary to the governance planes that enforce *permissions* and keep *audit chains* (Agent Governance Toolkit, Regulus, air-adk-trust): they say who may call what; these oracles say whether the outputs were verified and how | ours | audits (DORA, AI Act) | maintainers |
| 6 | `security` | planned | OWASP-style checks on the loop: tool order respected, footprint bounded, no secret in outputs or logs, egress to declared hosts only, injection markers in inputs | ours | — | wanted |
| — | `construction.quotes` | calibration field | bills of quantities and quotes (DCE / devis) — the first real field, used to calibrate `core`; not a headline gauge | ours | — | Keyross |

## Good first contributions

**For `einvoice` — the adapter, not the rules.** The BR-* rules already exist as official Schematron; do not rewrite them.

- ~~`einvoice.schematron`~~ and ~~the UBL / CII loaders to the canonical `Invoice`~~ — shipped in 0.1.0 ([gauge README](src/keyross/gauges/einvoice/README.md))
- `einvoice.facturx.pdf` — extract the CII XML embedded in a Factur-X PDF, offline, then run the same adapter
- `einvoice.delta.order_match` — invoice lines vs the purchase order (quantities, prices, references) — a delta oracle the standard cannot know
- `einvoice.delta.supplier_reference` — seller identifiers vs the client's supplier master data
- `einvoice.contract.issue_invoice` — the action contract of an agent that issues an invoice: what it announced is what was written

**Generic, useful today**

- `core.amount.sign` — no negative amount unless the document type allows credit lines
- `core.line.qty_pu_amount` — every priced line has all three of qty, unit price, amount, or none
- `core.dates.ordered` — issue date ≤ due date; no future date beyond a tolerance

Open an issue with the **New oracle** template; the bad case is half of the work.

## Where the gauges plug in

- **Level 0** — `keyross gate` in CI, on the files your systems already produce.
- **Level 1** — inside the loop: the Deep Agents / LangChain middleware; the **Claude Code hook** (`PostToolUse`) and the **Claude Code plugin**, so every invoice, spreadsheet, CSV or YAML an agent writes is compiled where the developer already works.
- **Level 2** — as a service: the MCP server (`keyross serve --mcp`), callable from any harness (Claude, Codex, Deep Agents, platforms).
