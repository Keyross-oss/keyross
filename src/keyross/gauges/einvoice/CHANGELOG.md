# Changelog — gauge einvoice

## 0.2.0 (23 September 2026)
- delta oracles — the invoice against the order it is issued for (`ctx["order"]`): `einvoice.delta.order.header` (number, currency), `.lines` (every line once; quantity, net price, VAT category and rate; net amount = quantity × net price), `.vat` (breakdown per category and rate: taxable amount, VAT amount), `.totals` (lines, allowances, charges, without VAT, VAT, with VAT, amount due) — EN 16931 arithmetic, half-up to the cent. They catch what the official rules cannot: an invoice coherent with itself that bills the wrong amounts (a 1-cent VAT error sits inside BR-CO-17's tolerance)
- one bad case each (`badset/einvoice.delta.order.*.xml` and its order)

## 0.1.0 (22 September 2026)
- CEN/TC 434 EN 16931 validation artefacts **1.3.16** (April 2026), UBL and CII, vendored unmodified and pinned by SHA-256; executed offline by Saxon-HE (saxonche)
- 1,562 rule ids registered from the artefacts and pinned in the lock; fatal → red, warning → yellow
- bad set: 20 corrupted public Factur-X examples, one or more per rule family (19 families)
