# Keyross report — invoice.xml
_2026-10-02 11:34 UTC · 307 ms · exit 2_

## 1. Scope
- document: `invoice.xml`
- context: `{'order': {'invoice': {'number': 'INV-2026-1007', 'issue_date': '2026-09-07', 'due_date': '2026-10-07', 'type_code': '380', 'currency': 'EUR', 'buyer_reference': 'PO-4707'}, 'lines': [{'id': '1', 'name': 'Maintenance visit', 'quantity': '5', 'unit_code': 'C62', 'net_price': '89.95', 'vat_category': 'E', 'vat_rate': '0.00'}, {'id': '2', 'name': 'Diesel', 'quantity': '1.5', 'unit_code': 'LTR', 'net_price': '33.33', 'vat_category': 'S', 'vat_rate': '10.00'}, {'id': '3', 'name': 'Coffee beans', 'quantity': '12.75', 'unit_code': 'KGM', 'net_price': '89.95', 'vat_category': 'S', 'vat_rate': '20.00'}, {'id': '4', 'name': 'Consulting, senior', 'quantity': '0.5', 'unit_code': 'HUR', 'net_price': '0.89', 'vat_category': 'S', 'vat_rate': '10.00'}, {'id': '5', 'name': 'Consulting, junior', 'quantity': '0.5', 'unit_code': 'HUR', 'net_price': '89.95', 'vat_category': 'S', 'vat_rate': '20.00'}], 'allowances': [], 'charges': []}}`

## 3. Verifiers
| oracle | version | flag | status | message |
|---|---|---|---|---|
| einvoice.schematron | 1.3.16 | green | ok | CEN/TC 434 EN 16931 validation artefacts 1.3.16: 0 finding(s) on 0 rule(s) |
| einvoice.delta.order.header | 1 | green | ok | ok |
| einvoice.delta.order.lines | 1 | red | fail | 2 line deviation(s) from the order |
| einvoice.delta.order.totals | 1 | red | fail | 5 total(s) differ from the order |
| einvoice.delta.order.vat | 1 | red | fail | 2 VAT breakdown deviation(s) from the order |

## 4. Deviations — evidence
### einvoice.delta.order.lines — order.lines
- **deviations**: `[{'line': '3', 'issue': 'net amount', 'expected': '1146.86', 'actual': 1146.81}, {'line': '5', 'issue': 'net amount', 'expected': '44.98', 'actual': 45.0}]`
### einvoice.delta.order.totals — order.totals
- **deviations**: `[{'total': 'line total', 'expected': '1692.04', 'actual': 1692.01}, {'total': 'total without VAT', 'expected': '1692.04', 'actual': 1692.01}, {'total': 'VAT total', 'expected': '243.42', 'actual': 243.41}, {'total': 'total with VAT', 'expected': '1935.46', 'actual': 1935.42}, {'total': 'amount due', 'expected': '1935.46', 'actual': 1935.42}]`
### einvoice.delta.order.vat — order.vat
- **deviations**: `[{'vat': 'S 20.00', 'issue': 'taxable amount', 'expected': '1191.84', 'actual': 1191.81}, {'vat': 'S 20.00', 'issue': 'VAT amount', 'expected': '238.37', 'actual': 238.36}]`

## 8. Integrity
- run flag: red
- red sentinels: 0

## 9. Recommendations
- (to complete: every recommendation names the oracle that will measure it)