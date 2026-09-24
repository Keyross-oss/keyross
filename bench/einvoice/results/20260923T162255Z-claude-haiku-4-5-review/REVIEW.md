# Human review — blind

For each invoice, decide whether it is a **correct invoice for its order**: the parties, every line, the VAT breakdown (with the exemption reason where one is due), the totals and the amount due — what a buyer or a tax office would accept. Check against the order, and open the XML when in doubt. Write `correct` or `incorrect` and what is wrong in `review.csv`. Do not open `../20260923T162255Z-claude-haiku-4-5-review-key.json` before you are done.

## invoice-01 — order-25

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1025",
    "issue_date": "2026-09-25",
    "due_date": "2026-10-25",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4725"
  },
  "seller": {
    "name": "Seller 25 SAS",
    "vat_id": "FR25000197975",
    "address": {
      "line": "25 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 75 SAS",
    "vat_id": "FR75000593925",
    "address": {
      "line": "75 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "USB-C dock",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "120.00",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "2",
      "name": "Office chair",
      "quantity": "2",
      "unit_code": "C62",
      "net_price": "7.45",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "3",
      "name": "Printer paper A4",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "1250.00",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "allowances": [
    {
      "amount": "15.00",
      "reason": "Loyalty discount",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "charges": [],
  "vat_exemptions": {}
}
```

**What the invoice says**

- number INV-2026-1025 · issued 2026-09-25 · type 380 · currency EUR
- seller Seller 25 SAS (FR25000197975, FR) · buyer Buyer 75 SAS (FR75000593925, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | USB-C dock | 5.0 | C62 | 120.0 | 600.0 | S 20.0 |
| 2 | Office chair | 2.0 | C62 | 7.45 | 14.9 | S 10.0 |
| 3 | Printer paper A4 | 5.0 | C62 | 1250.0 | 6250.0 | S 20.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| S | 20.0 | 6835.0 | 1367.0 |   |
| S | 10.0 | 14.9 | 1.49 |   |

Totals: lines 6864.9 · allowances 15.0 · charges None · without VAT 6849.9 · VAT 1368.49 · with VAT 8218.39 · due 8218.39

## invoice-02 — order-22

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1022",
    "issue_date": "2026-09-22",
    "due_date": "2026-10-22",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4722"
  },
  "seller": {
    "name": "Seller 22 SAS",
    "vat_id": "FR22000174218",
    "address": {
      "line": "22 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 72 SAS",
    "vat_id": "FR72000570168",
    "address": {
      "line": "72 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Cable, 5 m",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "120.00",
      "vat_category": "E",
      "vat_rate": "0.00"
    },
    {
      "id": "2",
      "name": "Training day",
      "quantity": "12.75",
      "unit_code": "DAY",
      "net_price": "7.45",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "3",
      "name": "Software licence, annual",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "19.99",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "4",
      "name": "Maintenance visit",
      "quantity": "1",
      "unit_code": "C62",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "10.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {
    "E": {
      "reason": "Exempt: medical care",
      "code": "VATEX-EU-132-1C"
    }
  }
}
```

**What the invoice says**

- number INV-2026-1022 · issued 2026-09-22 · type 380 · currency EUR
- seller Seller 22 SAS (FR22000174218, FR) · buyer Buyer 72 SAS (FR72000570168, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Cable, 5 m | 5.0 | C62 | 120.0 | 600.0 | E 0.0 |
| 2 | Training day | 12.75 | DAY | 7.45 | 94.99 | S 10.0 |
| 3 | Software licence, annual | 5.0 | C62 | 19.99 | 99.95 | S 20.0 |
| 4 | Maintenance visit | 1.0 | C62 | 33.33 | 33.33 | S 10.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| E | 0.0 | 600.0 | 0.0 | Exempt: medical care VATEX-EU-132-1C |
| S | 10.0 | 128.32 | 12.83 |   |
| S | 20.0 | 99.95 | 19.99 |   |

Totals: lines 828.27 · allowances None · charges None · without VAT 828.27 · VAT 32.82 · with VAT 861.09 · due 861.09

## invoice-03 — order-07

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1007",
    "issue_date": "2026-09-07",
    "due_date": "2026-10-07",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4707"
  },
  "seller": {
    "name": "Seller 07 SAS",
    "vat_id": "FR07000055433",
    "address": {
      "line": "7 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 57 SAS",
    "vat_id": "FR57000451383",
    "address": {
      "line": "57 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Maintenance visit",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "89.95",
      "vat_category": "E",
      "vat_rate": "0.00"
    },
    {
      "id": "2",
      "name": "Diesel",
      "quantity": "1.5",
      "unit_code": "LTR",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "3",
      "name": "Coffee beans",
      "quantity": "12.75",
      "unit_code": "KGM",
      "net_price": "89.95",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "4",
      "name": "Consulting, senior",
      "quantity": "0.5",
      "unit_code": "HUR",
      "net_price": "0.89",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "5",
      "name": "Consulting, junior",
      "quantity": "0.5",
      "unit_code": "HUR",
      "net_price": "89.95",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {
    "E": {
      "reason": "Exempt: medical care",
      "code": "VATEX-EU-132-1C"
    }
  }
}
```

**What the invoice says**

- number INV-2026-1007 · issued 2026-09-07 · type 380 · currency EUR
- seller Seller 07 SAS (FR07000055433, FR) · buyer Buyer 57 SAS (FR57000451383, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Maintenance visit | 5.0 | C62 | 89.95 | 449.75 | E 0.0 |
| 2 | Diesel | 1.5 | LTR | 33.33 | 50.0 | S 10.0 |
| 3 | Coffee beans | 12.75 | KGM | 89.95 | 1146.86 | S 20.0 |
| 4 | Consulting, senior | 0.5 | HUR | 0.89 | 0.45 | S 10.0 |
| 5 | Consulting, junior | 0.5 | HUR | 89.95 | 44.98 | S 20.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| E | 0.0 | 449.75 | 0.0 | Exempt: medical care VATEX-EU-132-1C |
| S | 10.0 | 50.45 | 5.05 |   |
| S | 20.0 | 1191.84 | 238.37 |   |

Totals: lines 1692.04 · allowances None · charges None · without VAT 1692.04 · VAT 243.42 · with VAT 1935.46 · due 1935.46

## invoice-04 — order-29

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1029",
    "issue_date": "2026-09-29",
    "due_date": "2026-10-29",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4729"
  },
  "seller": {
    "name": "Seller 29 SAS",
    "vat_id": "FR29000229651",
    "address": {
      "line": "29 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 79 GmbH",
    "vat_id": "DE79000625601",
    "address": {
      "line": "79 Example Street",
      "city": "Cologne",
      "postcode": "50667",
      "country": "DE"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "USB-C dock",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "33.33",
      "vat_category": "AE",
      "vat_rate": "0.00"
    },
    {
      "id": "2",
      "name": "Office chair",
      "quantity": "1",
      "unit_code": "C62",
      "net_price": "33.33",
      "vat_category": "AE",
      "vat_rate": "0.00"
    },
    {
      "id": "3",
      "name": "Printer paper A4",
      "quantity": "3",
      "unit_code": "C62",
      "net_price": "120.00",
      "vat_category": "AE",
      "vat_rate": "0.00"
    },
    {
      "id": "4",
      "name": "Cable, 5 m",
      "quantity": "3",
      "unit_code": "C62",
      "net_price": "120.00",
      "vat_category": "AE",
      "vat_rate": "0.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {
    "AE": {
      "reason": "Reverse charge",
      "code": "VATEX-EU-AE"
    }
  }
}
```

**What the invoice says**

- number INV-2026-1029 · issued 2026-09-29 · type 380 · currency EUR
- seller Seller 29 SAS (FR29000229651, FR) · buyer Buyer 79 GmbH (DE79000625601, DE)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | USB-C dock | 5.0 | C62 | 33.33 | 166.65 | AE 0.0 |
| 2 | Office chair | 1.0 | C62 | 33.33 | 33.33 | AE 0.0 |
| 3 | Printer paper A4 | 3.0 | C62 | 120.0 | 360.0 | AE 0.0 |
| 4 | Cable, 5 m | 3.0 | C62 | 120.0 | 360.0 | AE 0.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| AE | 0.0 | 919.98 | 0.0 | Reverse charge VATEX-EU-AE |

Totals: lines 919.98 · allowances 0.0 · charges None · without VAT 919.98 · VAT 0.0 · with VAT 919.98 · due 919.98

## invoice-05 — order-30

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1030",
    "issue_date": "2026-09-30",
    "due_date": "2026-10-30",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4730"
  },
  "seller": {
    "name": "Seller 30 SAS",
    "vat_id": "FR30000237570",
    "address": {
      "line": "30 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 80 SAS",
    "vat_id": "FR80000633520",
    "address": {
      "line": "80 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Cable, 5 m",
      "quantity": "3",
      "unit_code": "C62",
      "net_price": "89.95",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "2",
      "name": "Training day",
      "quantity": "0.5",
      "unit_code": "DAY",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "3",
      "name": "Software licence, annual",
      "quantity": "3",
      "unit_code": "C62",
      "net_price": "89.95",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "allowances": [
    {
      "amount": "15.00",
      "reason": "Loyalty discount",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "charges": [
    {
      "amount": "9.90",
      "reason": "Shipping",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "vat_exemptions": {}
}
```

**What the invoice says**

- number INV-2026-1030 · issued 2026-09-30 · type 380 · currency EUR
- seller Seller 30 SAS (FR30000237570, FR) · buyer Buyer 80 SAS (FR80000633520, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Cable, 5 m | 3.0 | C62 | 89.95 | 269.85 | S 20.0 |
| 2 | Training day | 0.5 | DAY | 33.33 | 16.665 | S 20.0 |
| 3 | Software licence, annual | 3.0 | C62 | 89.95 | 269.85 | S 20.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| S | 20.0 | 551.265 | 110.253 |   |

Totals: lines 556.365 · allowances 15.0 · charges 9.9 · without VAT 551.265 · VAT 110.253 · with VAT 661.518 · due 661.518

## invoice-06 — order-07

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1007",
    "issue_date": "2026-09-07",
    "due_date": "2026-10-07",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4707"
  },
  "seller": {
    "name": "Seller 07 SAS",
    "vat_id": "FR07000055433",
    "address": {
      "line": "7 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 57 SAS",
    "vat_id": "FR57000451383",
    "address": {
      "line": "57 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Maintenance visit",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "89.95",
      "vat_category": "E",
      "vat_rate": "0.00"
    },
    {
      "id": "2",
      "name": "Diesel",
      "quantity": "1.5",
      "unit_code": "LTR",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "3",
      "name": "Coffee beans",
      "quantity": "12.75",
      "unit_code": "KGM",
      "net_price": "89.95",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "4",
      "name": "Consulting, senior",
      "quantity": "0.5",
      "unit_code": "HUR",
      "net_price": "0.89",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "5",
      "name": "Consulting, junior",
      "quantity": "0.5",
      "unit_code": "HUR",
      "net_price": "89.95",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {
    "E": {
      "reason": "Exempt: medical care",
      "code": "VATEX-EU-132-1C"
    }
  }
}
```

**What the invoice says**

- number INV-2026-1007 · issued 2026-09-07 · type 380 · currency EUR
- seller Seller 07 SAS (FR07000055433, FR) · buyer Buyer 57 SAS (FR57000451383, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Maintenance visit | 5.0 | C62 | 89.95 | 449.75 | E 0.0 |
| 2 | Diesel | 1.5 | LTR | 33.33 | 50.0 | S 10.0 |
| 3 | Coffee beans | 12.75 | KGM | 89.95 | 1146.81 | S 20.0 |
| 4 | Consulting, senior | 0.5 | HUR | 0.89 | 0.45 | S 10.0 |
| 5 | Consulting, junior | 0.5 | HUR | 89.95 | 45.0 | S 20.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| E | 0.0 | 449.75 | 0.0 | Exempt: medical care VATEX-EU-132-1C |
| S | 10.0 | 50.45 | 5.05 |   |
| S | 20.0 | 1191.81 | 238.36 |   |

Totals: lines 1692.01 · allowances None · charges None · without VAT 1692.01 · VAT 243.41 · with VAT 1935.42 · due 1935.42

## invoice-07 — order-42

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1042",
    "issue_date": "2026-10-12",
    "due_date": "2026-11-11",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4742"
  },
  "seller": {
    "name": "Seller 42 SAS",
    "vat_id": "FR42000332598",
    "address": {
      "line": "42 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 92 SAS",
    "vat_id": "FR92000728548",
    "address": {
      "line": "92 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Cable, 5 m",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "49.90",
      "vat_category": "E",
      "vat_rate": "0.00"
    },
    {
      "id": "2",
      "name": "Training day",
      "quantity": "7",
      "unit_code": "DAY",
      "net_price": "0.89",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "3",
      "name": "Software licence, annual",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "0.89",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {
    "E": {
      "reason": "Exempt: medical care",
      "code": "VATEX-EU-132-1C"
    }
  }
}
```

**What the invoice says**

- number INV-2026-1042 · issued 2026-10-12 · type 380 · currency EUR
- seller Seller 42 SAS (FR42000332598, FR) · buyer Buyer 92 SAS (FR92000728548, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Cable, 5 m | 5.0 | C62 | 49.9 | 249.5 | E 0.0 |
| 2 | Training day | 7.0 | DAY | 0.89 | 6.23 | S 20.0 |
| 3 | Software licence, annual | 5.0 | C62 | 0.89 | 4.45 | S 20.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| E | 0.0 | 249.5 | 0.0 | Exempt: medical care VATEX-EU-132-1C |
| S | 20.0 | 10.68 | 2.14 |   |

Totals: lines 260.18 · allowances None · charges None · without VAT 260.18 · VAT 2.14 · with VAT 262.32 · due 262.32

## invoice-08 — order-13

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1013",
    "issue_date": "2026-09-13",
    "due_date": "2026-10-13",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4713"
  },
  "seller": {
    "name": "Seller 13 SAS",
    "vat_id": "FR13000102947",
    "address": {
      "line": "13 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 63 GmbH",
    "vat_id": "DE63000498897",
    "address": {
      "line": "63 Example Street",
      "city": "Cologne",
      "postcode": "50667",
      "country": "DE"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "USB-C dock",
      "quantity": "12",
      "unit_code": "C62",
      "net_price": "89.95",
      "vat_category": "K",
      "vat_rate": "0.00"
    },
    {
      "id": "2",
      "name": "Office chair",
      "quantity": "3",
      "unit_code": "C62",
      "net_price": "7.45",
      "vat_category": "K",
      "vat_rate": "0.00"
    },
    {
      "id": "3",
      "name": "Printer paper A4",
      "quantity": "3",
      "unit_code": "C62",
      "net_price": "89.95",
      "vat_category": "K",
      "vat_rate": "0.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "delivery": {
    "date": "2026-08-24",
    "country": "DE"
  },
  "vat_exemptions": {
    "K": {
      "reason": "Intra-community supply",
      "code": "VATEX-EU-IC"
    }
  }
}
```

**What the invoice says**

- number INV-2026-1013 · issued 2026-09-13 · type 380 · currency EUR
- seller Seller 13 SAS (FR13000102947, FR) · buyer Buyer 63 GmbH (DE63000498897, DE)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | USB-C dock | 12.0 | C62 | 89.95 | 1079.4 | K 0.0 |
| 2 | Office chair | 3.0 | C62 | 7.45 | 22.35 | K 0.0 |
| 3 | Printer paper A4 | 3.0 | C62 | 89.95 | 269.85 | K 0.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| K | 0.0 | 1371.6 | 0.0 | Intra-community supply VATEX-EU-IC |

Totals: lines 1371.6 · allowances None · charges None · without VAT 1371.6 · VAT 0.0 · with VAT 1371.6 · due 1371.6

## invoice-09 — order-26

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1026",
    "issue_date": "2026-09-26",
    "due_date": "2026-10-26",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4726"
  },
  "seller": {
    "name": "Seller 26 SAS",
    "vat_id": "FR26000205894",
    "address": {
      "line": "26 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 76 SAS",
    "vat_id": "FR76000601844",
    "address": {
      "line": "76 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Cable, 5 m",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "7.45",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "2",
      "name": "Training day",
      "quantity": "1.5",
      "unit_code": "DAY",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "3",
      "name": "Software licence, annual",
      "quantity": "1",
      "unit_code": "C62",
      "net_price": "7.45",
      "vat_category": "S",
      "vat_rate": "5.50"
    },
    {
      "id": "4",
      "name": "Maintenance visit",
      "quantity": "2",
      "unit_code": "C62",
      "net_price": "19.99",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "5",
      "name": "Diesel",
      "quantity": "12.75",
      "unit_code": "LTR",
      "net_price": "19.99",
      "vat_category": "S",
      "vat_rate": "10.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {}
}
```

**What the invoice says**

- number INV-2026-1026 · issued 2026-09-26 · type 380 · currency EUR
- seller Seller 26 SAS (FR26000205894, FR) · buyer Buyer 76 SAS (FR76000601844, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Cable, 5 m | 5.0 | C62 | 7.45 | 37.25 | S 20.0 |
| 2 | Training day | 1.5 | DAY | 33.33 | 50.0 | S 10.0 |
| 3 | Software licence, annual | 1.0 | C62 | 7.45 | 7.45 | S 5.5 |
| 4 | Maintenance visit | 2.0 | C62 | 19.99 | 39.98 | S 20.0 |
| 5 | Diesel | 12.75 | LTR | 19.99 | 254.87 | S 10.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| S | 20.0 | 77.23 | 15.45 |   |
| S | 10.0 | 304.87 | 30.49 |   |
| S | 5.5 | 7.45 | 0.41 |   |

Totals: lines 389.55 · allowances None · charges None · without VAT 389.55 · VAT 46.35 · with VAT 435.9 · due 435.9

## invoice-10 — order-13

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1013",
    "issue_date": "2026-09-13",
    "due_date": "2026-10-13",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4713"
  },
  "seller": {
    "name": "Seller 13 SAS",
    "vat_id": "FR13000102947",
    "address": {
      "line": "13 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 63 GmbH",
    "vat_id": "DE63000498897",
    "address": {
      "line": "63 Example Street",
      "city": "Cologne",
      "postcode": "50667",
      "country": "DE"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "USB-C dock",
      "quantity": "12",
      "unit_code": "C62",
      "net_price": "89.95",
      "vat_category": "K",
      "vat_rate": "0.00"
    },
    {
      "id": "2",
      "name": "Office chair",
      "quantity": "3",
      "unit_code": "C62",
      "net_price": "7.45",
      "vat_category": "K",
      "vat_rate": "0.00"
    },
    {
      "id": "3",
      "name": "Printer paper A4",
      "quantity": "3",
      "unit_code": "C62",
      "net_price": "89.95",
      "vat_category": "K",
      "vat_rate": "0.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "delivery": {
    "date": "2026-08-24",
    "country": "DE"
  },
  "vat_exemptions": {
    "K": {
      "reason": "Intra-community supply",
      "code": "VATEX-EU-IC"
    }
  }
}
```

**What the invoice says**

- number INV-2026-1013 · issued 2026-09-13 · type 380 · currency EUR
- seller Seller 13 SAS (FR13000102947, FR) · buyer Buyer 63 GmbH (DE63000498897, DE)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | USB-C dock | 12.0 | C62 | 89.95 | 1079.4 | K 0.0 |
| 2 | Office chair | 3.0 | C62 | 7.45 | 22.35 | K 0.0 |
| 3 | Printer paper A4 | 3.0 | C62 | 89.95 | 269.85 | K 0.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| K | 0.0 | 1371.6 | 0.0 | Intra-community supply VATEX-EU-IC |

Totals: lines 1371.6 · allowances None · charges None · without VAT 1371.6 · VAT 0.0 · with VAT 1371.6 · due 1371.6

## invoice-11 — order-06

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1006",
    "issue_date": "2026-09-06",
    "due_date": "2026-10-06",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4706"
  },
  "seller": {
    "name": "Seller 06 SAS",
    "vat_id": "FR06000047514",
    "address": {
      "line": "6 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 56 SAS",
    "vat_id": "FR56000443464",
    "address": {
      "line": "56 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Cable, 5 m",
      "quantity": "1",
      "unit_code": "C62",
      "net_price": "1250.00",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "2",
      "name": "Training day",
      "quantity": "7",
      "unit_code": "DAY",
      "net_price": "89.95",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "3",
      "name": "Software licence, annual",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "49.90",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {}
}
```

**What the invoice says**

- number INV-2026-1006 · issued 2026-09-06 · type 380 · currency EUR
- seller Seller 06 SAS (FR06000047514, FR) · buyer Buyer 56 SAS (FR56000443464, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Cable, 5 m | 1.0 | C62 | 1250.0 | 1250.0 | S 20.0 |
| 2 | Training day | 7.0 | DAY | 89.95 | 629.65 | S 20.0 |
| 3 | Software licence, annual | 5.0 | C62 | 49.9 | 249.5 | S 20.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| S | 20.0 | 2129.15 | 425.83 |   |

Totals: lines 2129.15 · allowances None · charges None · without VAT 2129.15 · VAT 425.83 · with VAT 2554.98 · due 2554.98

## invoice-12 — order-46

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1046",
    "issue_date": "2026-10-16",
    "due_date": "2026-11-15",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4746"
  },
  "seller": {
    "name": "Seller 46 SAS",
    "vat_id": "FR46000364274",
    "address": {
      "line": "46 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 96 SAS",
    "vat_id": "FR96000760224",
    "address": {
      "line": "96 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Cable, 5 m",
      "quantity": "1",
      "unit_code": "C62",
      "net_price": "19.99",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "2",
      "name": "Training day",
      "quantity": "2.25",
      "unit_code": "DAY",
      "net_price": "1250.00",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "3",
      "name": "Software licence, annual",
      "quantity": "12",
      "unit_code": "C62",
      "net_price": "0.89",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "4",
      "name": "Maintenance visit",
      "quantity": "1",
      "unit_code": "C62",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "10.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {}
}
```

**What the invoice says**

- number INV-2026-1046 · issued 2026-10-16 · type 380 · currency EUR
- seller Seller 46 SAS (FR46000364274, FR) · buyer Buyer 96 SAS (FR96000760224, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Cable, 5 m | 1.0 | C62 | 19.99 | 19.99 | S 20.0 |
| 2 | Training day | 2.25 | DAY | 1250.0 | 2812.5 | S 10.0 |
| 3 | Software licence, annual | 12.0 | C62 | 0.89 | 10.68 | S 20.0 |
| 4 | Maintenance visit | 1.0 | C62 | 33.33 | 33.33 | S 10.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| S | 20.0 | 30.67 | 6.13 |   |
| S | 10.0 | 2845.83 | 284.58 |   |

Totals: lines 2876.5 · allowances None · charges None · without VAT 2876.5 · VAT 290.71 · with VAT 3167.21 · due 3167.21

## invoice-13 — order-06

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1006",
    "issue_date": "2026-09-06",
    "due_date": "2026-10-06",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4706"
  },
  "seller": {
    "name": "Seller 06 SAS",
    "vat_id": "FR06000047514",
    "address": {
      "line": "6 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 56 SAS",
    "vat_id": "FR56000443464",
    "address": {
      "line": "56 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Cable, 5 m",
      "quantity": "1",
      "unit_code": "C62",
      "net_price": "1250.00",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "2",
      "name": "Training day",
      "quantity": "7",
      "unit_code": "DAY",
      "net_price": "89.95",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "3",
      "name": "Software licence, annual",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "49.90",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {}
}
```

**What the invoice says**

- number INV-2026-1006 · issued 2026-09-06 · type 380 · currency EUR
- seller Seller 06 SAS (FR06000047514, FR) · buyer Buyer 56 SAS (FR56000443464, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Cable, 5 m | 1.0 | C62 | 1250.0 | 1250.0 | S 20.0 |
| 2 | Training day | 7.0 | DAY | 89.95 | 629.65 | S 20.0 |
| 3 | Software licence, annual | 5.0 | C62 | 49.9 | 249.5 | S 20.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| S | 20.0 | 2129.15 | 425.83 |   |

Totals: lines 2129.15 · allowances None · charges None · without VAT 2129.15 · VAT 425.83 · with VAT 2554.98 · due 2554.98

## invoice-14 — order-26

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1026",
    "issue_date": "2026-09-26",
    "due_date": "2026-10-26",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4726"
  },
  "seller": {
    "name": "Seller 26 SAS",
    "vat_id": "FR26000205894",
    "address": {
      "line": "26 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 76 SAS",
    "vat_id": "FR76000601844",
    "address": {
      "line": "76 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Cable, 5 m",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "7.45",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "2",
      "name": "Training day",
      "quantity": "1.5",
      "unit_code": "DAY",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "3",
      "name": "Software licence, annual",
      "quantity": "1",
      "unit_code": "C62",
      "net_price": "7.45",
      "vat_category": "S",
      "vat_rate": "5.50"
    },
    {
      "id": "4",
      "name": "Maintenance visit",
      "quantity": "2",
      "unit_code": "C62",
      "net_price": "19.99",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "5",
      "name": "Diesel",
      "quantity": "12.75",
      "unit_code": "LTR",
      "net_price": "19.99",
      "vat_category": "S",
      "vat_rate": "10.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {}
}
```

**What the invoice says**

- number INV-2026-1026 · issued 2026-09-26 · type 380 · currency EUR
- seller Seller 26 SAS (FR26000205894, FR) · buyer Buyer 76 SAS (FR76000601844, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Cable, 5 m | 5.0 | C62 | 7.45 | 37.5 | S 20.0 |
| 2 | Training day | 1.5 | DAY | 33.33 | 50.0 | S 10.0 |
| 3 | Software licence, annual | 1.0 | C62 | 7.45 | 7.45 | S 5.5 |
| 4 | Maintenance visit | 2.0 | C62 | 19.99 | 39.98 | S 20.0 |
| 5 | Diesel | 12.75 | LTR | 19.99 | 254.87 | S 10.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| S | 20.0 | 77.48 | 15.5 |   |
| S | 10.0 | 304.87 | 30.49 |   |
| S | 5.5 | 7.45 | 0.41 |   |

Totals: lines 389.8 · allowances None · charges None · without VAT 389.8 · VAT 46.4 · with VAT 436.2 · due 436.2

## invoice-15 — order-01

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1001",
    "issue_date": "2026-09-01",
    "due_date": "2026-10-01",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4701"
  },
  "seller": {
    "name": "Seller 01 SAS",
    "vat_id": "FR01000007919",
    "address": {
      "line": "1 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 51 SAS",
    "vat_id": "FR51000403869",
    "address": {
      "line": "51 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "USB-C dock",
      "quantity": "1",
      "unit_code": "C62",
      "net_price": "1250.00",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "2",
      "name": "Office chair",
      "quantity": "12",
      "unit_code": "C62",
      "net_price": "49.90",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "3",
      "name": "Printer paper A4",
      "quantity": "2",
      "unit_code": "C62",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {}
}
```

**What the invoice says**

- number INV-2026-1001 · issued 2026-09-01 · type 380 · currency EUR
- seller Seller 01 SAS (FR01000007919, FR) · buyer Buyer 51 SAS (FR51000403869, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | USB-C dock | 1.0 | C62 | 1250.0 | 1250.0 | S 20.0 |
| 2 | Office chair | 12.0 | C62 | 49.9 | 598.8 | S 10.0 |
| 3 | Printer paper A4 | 2.0 | C62 | 33.33 | 66.66 | S 20.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| S | 20.0 | 1316.66 | 263.33 |   |
| S | 10.0 | 598.8 | 59.88 |   |

Totals: lines 1915.46 · allowances None · charges None · without VAT 1915.46 · VAT 323.21 · with VAT 2238.67 · due 2238.67

## invoice-16 — order-45

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1045",
    "issue_date": "2026-10-15",
    "due_date": "2026-11-14",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4745"
  },
  "seller": {
    "name": "Seller 45 SAS",
    "vat_id": "FR45000356355",
    "address": {
      "line": "45 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 95 SAS",
    "vat_id": "FR95000752305",
    "address": {
      "line": "95 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "USB-C dock",
      "quantity": "1",
      "unit_code": "C62",
      "net_price": "120.00",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "2",
      "name": "Office chair",
      "quantity": "12",
      "unit_code": "C62",
      "net_price": "49.90",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "allowances": [
    {
      "amount": "15.00",
      "reason": "Loyalty discount",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "charges": [],
  "vat_exemptions": {}
}
```

**What the invoice says**

- number INV-2026-1045 · issued 2026-10-15 · type 380 · currency EUR
- seller Seller 45 SAS (FR45000356355, FR) · buyer Buyer 95 SAS (FR95000752305, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | USB-C dock | 1.0 | C62 | 120.0 | 120.0 | S 20.0 |
| 2 | Office chair | 12.0 | C62 | 49.9 | 598.8 | S 20.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| S | 20.0 | 703.8 | 140.76 |   |

Totals: lines 718.8 · allowances 15.0 · charges None · without VAT 703.8 · VAT 140.76 · with VAT 844.56 · due 844.56

## invoice-17 — order-25

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1025",
    "issue_date": "2026-09-25",
    "due_date": "2026-10-25",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4725"
  },
  "seller": {
    "name": "Seller 25 SAS",
    "vat_id": "FR25000197975",
    "address": {
      "line": "25 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 75 SAS",
    "vat_id": "FR75000593925",
    "address": {
      "line": "75 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "USB-C dock",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "120.00",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "2",
      "name": "Office chair",
      "quantity": "2",
      "unit_code": "C62",
      "net_price": "7.45",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "3",
      "name": "Printer paper A4",
      "quantity": "5",
      "unit_code": "C62",
      "net_price": "1250.00",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "allowances": [
    {
      "amount": "15.00",
      "reason": "Loyalty discount",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "charges": [],
  "vat_exemptions": {}
}
```

**What the invoice says**

- number INV-2026-1025 · issued 2026-09-25 · type 380 · currency EUR
- seller Seller 25 SAS (FR25000197975, FR) · buyer Buyer 75 SAS (FR75000593925, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | USB-C dock | 5.0 | C62 | 120.0 | 600.0 | S 20.0 |
| 2 | Office chair | 2.0 | C62 | 7.45 | 14.9 | S 10.0 |
| 3 | Printer paper A4 | 5.0 | C62 | 1250.0 | 6250.0 | S 20.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| S | 20.0 | 6835.0 | 1367.0 |   |
| S | 10.0 | 14.9 | 1.49 |   |

Totals: lines 6864.9 · allowances 15.0 · charges None · without VAT 6849.9 · VAT 1368.49 · with VAT 8218.39 · due 8218.39

## invoice-18 — order-21

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1021",
    "issue_date": "2026-09-21",
    "due_date": "2026-10-21",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4721"
  },
  "seller": {
    "name": "Seller 21 SAS",
    "vat_id": "FR21000166299",
    "address": {
      "line": "21 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 71 SAS",
    "vat_id": "FR71000562249",
    "address": {
      "line": "71 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "USB-C dock",
      "quantity": "12",
      "unit_code": "C62",
      "net_price": "0.89",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "2",
      "name": "Office chair",
      "quantity": "12",
      "unit_code": "C62",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "20.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {}
}
```

**What the invoice says**

- number INV-2026-1021 · issued 2026-09-21 · type 380 · currency EUR
- seller Seller 21 SAS (FR21000166299, FR) · buyer Buyer 71 SAS (FR71000562249, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | USB-C dock | 12.0 | C62 | 0.89 | 10.68 | S 20.0 |
| 2 | Office chair | 12.0 | C62 | 33.33 | 399.96 | S 20.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| S | 20.0 | 410.64 | 82.13 |   |

Totals: lines 410.64 · allowances None · charges None · without VAT 410.64 · VAT 82.13 · with VAT 492.77 · due 492.77

## invoice-19 — order-47

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1047",
    "issue_date": "2026-10-17",
    "due_date": "2026-11-16",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4747"
  },
  "seller": {
    "name": "Seller 47 SAS",
    "vat_id": "FR47000372193",
    "address": {
      "line": "47 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 97 SAS",
    "vat_id": "FR97000768143",
    "address": {
      "line": "97 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Maintenance visit",
      "quantity": "12",
      "unit_code": "C62",
      "net_price": "120.00",
      "vat_category": "E",
      "vat_rate": "0.00"
    },
    {
      "id": "2",
      "name": "Diesel",
      "quantity": "7",
      "unit_code": "LTR",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "3",
      "name": "Coffee beans",
      "quantity": "0.5",
      "unit_code": "KGM",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "5.50"
    },
    {
      "id": "4",
      "name": "Consulting, senior",
      "quantity": "2.25",
      "unit_code": "HUR",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "20.00"
    },
    {
      "id": "5",
      "name": "Consulting, junior",
      "quantity": "2.25",
      "unit_code": "HUR",
      "net_price": "120.00",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "6",
      "name": "Laptop stand",
      "quantity": "2",
      "unit_code": "C62",
      "net_price": "19.99",
      "vat_category": "S",
      "vat_rate": "5.50"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {
    "E": {
      "reason": "Exempt: medical care",
      "code": "VATEX-EU-132-1C"
    }
  }
}
```

**What the invoice says**

- number INV-2026-1047 · issued 2026-10-17 · type 380 · currency EUR
- seller Seller 47 SAS (FR47000372193, FR) · buyer Buyer 97 SAS (FR97000768143, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Maintenance visit | 12.0 | C62 | 120.0 | 1440.0 | E 0.0 |
| 2 | Diesel | 7.0 | LTR | 33.33 | 233.31 | S 10.0 |
| 3 | Coffee beans | 0.5 | KGM | 33.33 | 16.67 | S 5.5 |
| 4 | Consulting, senior | 2.25 | HUR | 33.33 | 74.99 | S 20.0 |
| 5 | Consulting, junior | 2.25 | HUR | 120.0 | 270.0 | S 10.0 |
| 6 | Laptop stand | 2.0 | C62 | 19.99 | 39.98 | S 5.5 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| E | 0.0 | 1440.0 | 0.0 | Exempt: medical care VATEX-EU-132-1C |
| S | 5.5 | 56.65 | 3.12 |   |
| S | 10.0 | 503.31 | 50.33 |   |
| S | 20.0 | 74.99 | 15.0 |   |

Totals: lines 2074.95 · allowances None · charges None · without VAT 2074.95 · VAT 68.45 · with VAT 2143.4 · due 2143.4

## invoice-20 — order-32

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1032",
    "issue_date": "2026-10-02",
    "due_date": "2026-11-01",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4732"
  },
  "seller": {
    "name": "Seller 32 SAS",
    "vat_id": "FR32000253408",
    "address": {
      "line": "32 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 82 SAS",
    "vat_id": "FR82000649358",
    "address": {
      "line": "82 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Consulting, senior",
      "quantity": "2.25",
      "unit_code": "HUR",
      "net_price": "19.99",
      "vat_category": "E",
      "vat_rate": "0.00"
    },
    {
      "id": "2",
      "name": "Consulting, junior",
      "quantity": "1.5",
      "unit_code": "HUR",
      "net_price": "89.95",
      "vat_category": "S",
      "vat_rate": "10.00"
    },
    {
      "id": "3",
      "name": "Laptop stand",
      "quantity": "3",
      "unit_code": "C62",
      "net_price": "33.33",
      "vat_category": "S",
      "vat_rate": "5.50"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {
    "E": {
      "reason": "Exempt: medical care",
      "code": "VATEX-EU-132-1C"
    }
  }
}
```

**What the invoice says**

- number INV-2026-1032 · issued 2026-10-02 · type 380 · currency EUR
- seller Seller 32 SAS (FR32000253408, FR) · buyer Buyer 82 SAS (FR82000649358, FR)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Consulting, senior | 2.25 | HUR | 19.99 | 44.98 | E 0.0 |
| 2 | Consulting, junior | 1.5 | HUR | 89.95 | 134.93 | S 10.0 |
| 3 | Laptop stand | 3.0 | C62 | 33.33 | 99.99 | S 5.5 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| E | 0.0 | 44.98 | 0.0 | Exempt: medical care VATEX-EU-132-1C |
| S | 10.0 | 134.93 | 13.49 |   |
| S | 5.5 | 99.99 | 5.5 |   |

Totals: lines 279.9 · allowances None · charges None · without VAT 279.9 · VAT 18.99 · with VAT 298.89 · due 298.89

## invoice-21 — order-19

**The order**

```json
{
  "invoice": {
    "number": "INV-2026-1019",
    "issue_date": "2026-09-19",
    "due_date": "2026-10-19",
    "type_code": "380",
    "currency": "EUR",
    "buyer_reference": "PO-4719"
  },
  "seller": {
    "name": "Seller 19 SAS",
    "vat_id": "FR19000150461",
    "address": {
      "line": "19 Example Street",
      "city": "Lille",
      "postcode": "59000",
      "country": "FR"
    }
  },
  "buyer": {
    "name": "Buyer 69 GmbH",
    "vat_id": "DE69000546411",
    "address": {
      "line": "69 Example Street",
      "city": "Cologne",
      "postcode": "50667",
      "country": "DE"
    }
  },
  "payment": {
    "means_code": "58",
    "iban": "FR7630006000011234567890189"
  },
  "lines": [
    {
      "id": "1",
      "name": "Maintenance visit",
      "quantity": "3",
      "unit_code": "C62",
      "net_price": "120.00",
      "vat_category": "AE",
      "vat_rate": "0.00"
    },
    {
      "id": "2",
      "name": "Diesel",
      "quantity": "1.5",
      "unit_code": "LTR",
      "net_price": "1250.00",
      "vat_category": "AE",
      "vat_rate": "0.00"
    },
    {
      "id": "3",
      "name": "Coffee beans",
      "quantity": "12.75",
      "unit_code": "KGM",
      "net_price": "89.95",
      "vat_category": "AE",
      "vat_rate": "0.00"
    },
    {
      "id": "4",
      "name": "Consulting, senior",
      "quantity": "2.25",
      "unit_code": "HUR",
      "net_price": "7.45",
      "vat_category": "AE",
      "vat_rate": "0.00"
    },
    {
      "id": "5",
      "name": "Consulting, junior",
      "quantity": "0.5",
      "unit_code": "HUR",
      "net_price": "120.00",
      "vat_category": "AE",
      "vat_rate": "0.00"
    }
  ],
  "allowances": [],
  "charges": [],
  "vat_exemptions": {
    "AE": {
      "reason": "Reverse charge",
      "code": "VATEX-EU-AE"
    }
  }
}
```

**What the invoice says**

- number INV-2026-1019 · issued 2026-09-19 · type 380 · currency EUR
- seller Seller 19 SAS (FR19000150461, FR) · buyer Buyer 69 GmbH (DE69000546411, DE)

| line | item | quantity | unit | net price | net amount | VAT |
|---|---|---|---|---|---|---|
| 1 | Maintenance visit | 3.0 | C62 | 120.0 | 360.0 | AE 0.0 |
| 2 | Diesel | 1.5 | LTR | 1250.0 | 1875.0 | AE 0.0 |
| 3 | Coffee beans | 12.75 | KGM | 89.95 | 1146.81 | AE 0.0 |
| 4 | Consulting, senior | 2.25 | HUR | 7.45 | 16.76 | AE 0.0 |
| 5 | Consulting, junior | 0.5 | HUR | 120.0 | 60.0 | AE 0.0 |

| VAT category | rate | taxable | tax | exemption |
|---|---|---|---|---|
| AE | 0.0 | 3458.57 | 0.0 | Reverse charge VATEX-EU-AE |

Totals: lines 3458.57 · allowances 0.0 · charges None · without VAT 3458.57 · VAT 0.0 · with VAT 3458.57 · due 3458.57
