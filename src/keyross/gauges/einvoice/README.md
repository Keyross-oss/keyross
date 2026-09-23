# Gauge `einvoice` — EN 16931 e-invoices

The official CEN/TC 434 validation artefacts for EN 16931, executed as published. **No rule is rewritten.** A verdict that differs from the official validator is a bug in the adapter.

| | |
|---|---|
| Documents | UBL 2.1 Invoice / CreditNote, UN/CEFACT CII D16B (the XML of Factur-X / ZUGFeRD) |
| Rules | CEN validation artefacts **1.3.16** ([release](https://github.com/ConnectingEurope/eInvoicing-EN16931/releases/tag/validation-1.3.16)) — 1,562 rule ids, 19 families |
| Engine | Saxon-HE through `saxonche` (the artefacts are XSLT 2.0) — `pip install 'keyross[einvoice]'` |
| Network | none: the check runs offline, and a document that declares a DOCTYPE is refused |
| Not checked | **the XML schema** — which element, where, in which order. The CEN rules assume a schema-valid document: validate against the syntax's schema as well. The schema step is planned |

```bash
keyross add einvoice && keyross lock
keyross check invoice.xml          # exit 0 green · 1 yellow (a CEN warning) · 2 red (a CEN fatal)
```

## How it works

- `rules/cen-1.3.16/` holds the two XSLT files CEN compiles from its Schematron, byte for byte. `gauge.yaml` pins their SHA-256. The adapter checks both files before every run; if one differs, nothing runs and the verdict is red (`adapter.pin_mismatch`).
- **One registry entry per rule id**, read from the assertions of those same files: `einvoice.br-co-10`, `einvoice.ubl-cr-005`… The version is the release (`1.3.16`). `fatal` maps to red, `warning` to yellow. `keyross.lock` pins every entry and the adapter pin, so a new release shows up in `keyross lock --check`.
- A rule that exists in both syntaxes with different flags (BR-51: fatal in CII, warning in UBL) is registered with the stricter flag. At check time, the flag always follows the artifact that actually ran.
- **Minimal feedback**: the category is the rule id (`BR-CO-10`). The XPath location, the assertion test and the assertion text go into `evidence` for the report. They never go into `minimal()`.
- `keyross.core.invoice` loads the same files into the canonical `Invoice` model (header, lines, totals, VAT breakdown) for delta oracles. The official rules never depend on it.

## Delta oracles — the invoice against its order

The official rules check that an invoice is coherent with itself. It can be coherent and still bill the wrong quantity, price or amount: the benchmark's pilot saw `12.75 × 89.95` written `1146.81` and carried into every total, and a VAT amount one cent off — inside the tolerance of BR-CO-17. Four delta oracles compare the invoice with the order it is issued for:

| Oracle | Category | Checks |
|---|---|---|
| `einvoice.delta.order.header` | `order.header` | invoice number and currency |
| `einvoice.delta.order.lines` | `order.lines` | every order line invoiced once: quantity, net price, VAT category and rate, net amount = quantity × net price |
| `einvoice.delta.order.vat` | `order.vat` | one breakdown per VAT category and rate: taxable amount (lines − allowances + charges), VAT amount (taxable × rate) |
| `einvoice.delta.order.totals` | `order.totals` | lines, allowances, charges, without VAT, VAT, with VAT, amount due |

Amounts follow EN 16931 arithmetic, rounded half-up to the cent. The order comes from the context — the harness gives it, not the model: `Yoke(gauge="einvoice", ctx={"order": order})`, or `check_file(path, gauge="einvoice", ctx={"order": order})`. Without an order, the delta oracles skip. The agent only ever gets the categories, never the expected amounts.

The order format:

```json
{
  "invoice": {"number": "INV-2026-0901", "currency": "EUR"},
  "lines": [{"id": "1", "quantity": "3", "net_price": "49.90", "vat_category": "S", "vat_rate": "20.00"}],
  "allowances": [{"amount": "10.00", "vat_category": "S", "vat_rate": "20.00"}],
  "charges": []
}
```

## Bad set

At least one bad case per rule family. Each case is a public Factur-X example with one deliberate corruption. `keyross test` fails if a family has no case, or if a case does not raise its rule.

| Case | Source | Corruption |
|---|---|---|
| `einvoice.br-29` | CII | a date: invoicing period end date (BT-74) moved before its start date |
| `einvoice.br-co-10` | CII | a total: sum of line net amounts (BT-106) 95.00 → 96.00 |
| `einvoice.br-co-15.ubl` | UBL | a total: invoice total with VAT (BT-112) → 9999.99 |
| `einvoice.br-s-05` | CII | a rate: standard-rated line (S) with a 0.00 % rate |
| `einvoice.br-e-05` | CII | a rate: exempt line (E) with a 10.00 % rate |
| `einvoice.br-ae-05` | CII | a rate: reverse-charge line (AE) with a 10.00 % rate |
| `einvoice.br-g-05` | CII | a rate: export line (G) with a 10.00 % rate |
| `einvoice.br-z-10` | CII | exempt line and breakdown recoded zero-rated (Z), exemption reason left in place |
| `einvoice.br-ic-08` | CII | exempt line and breakdown recoded intra-community (K): the K taxable amount no longer matches its lines |
| `einvoice.br-o-05` | CII | exempt line recoded not subject to VAT (O) while still carrying a rate |
| `einvoice.br-af-05` | CII | exempt line recoded IGIC (L) with a 0.00 % rate |
| `einvoice.br-ag-10` | CII | exempt breakdown recoded IPSI (M), exemption reason left in place |
| `einvoice.br-b-01` | CII | split payment (B) on an invoice outside Italy |
| `einvoice.br-cl-04` | CII | a code: invoice currency (BT-5) EUR → EUX, not in ISO 4217 |
| `einvoice.br-dec-18` | CII | an amount: amount due (BT-115) with three decimals |
| `einvoice.cii-sr-002` | CII | syntax: `TestIndicator` added |
| `einvoice.cii-dt-001` | CII | data type: `schemeName` attribute on the invoice number |
| `einvoice.ubl-cr-005` | UBL | syntax: `UUID` added |
| `einvoice.ubl-dt-08` | UBL | data type: `schemeName` attribute on the invoice number |
| `einvoice.ubl-sr-01` | UBL | syntax: contract reference (BT-12) duplicated |

Sources: `tests/fixtures/xml/factur-x-en16931.xml` (CII) and `ubl-21-en16931.xml` (UBL) from [akretion/factur-x](https://github.com/akretion/factur-x), BSD licence, XML comments removed. The clean originals are in `tests/fixtures/einvoice/`, next to four CEN examples. Every clean file is green; the tests check this.

## Not yet

The XML schema step, before the CEN rules (Saxon-HE does not validate XML schemas: it needs a second engine); other delta oracles (supplier master data, the `issue_invoice` contract); extracting the XML from a Factur-X PDF; the national extensions (XRechnung CIUS, the French CTC rules), each of which will be its own pinned adapter.

## Licences

The vendored CEN artefacts are licensed under the **EUPL-1.2** (`rules/cen-1.3.16/LICENSE.txt`) and are redistributed unmodified. The rest of the gauge is Apache-2.0.
