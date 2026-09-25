## What this PR adds

- [ ] one oracle (id: `…`) and its bad case in the gauge's `badset/`, or
- [ ] a gauge (`gauges/<name>/`) with at least five oracles and their badset, or
- [ ] a fix / a doc change

## Checklist — the gate of this repository

- [ ] `pytest -q` green
- [ ] `keyross test` green (every oracle catches its bad case)
- [ ] `keyross lint` green (no model, no network, no clock, no randomness in an oracle)
- [ ] `keyross lock` regenerated and committed
- [ ] CHANGELOG.md updated
- [ ] commits signed off (DCO: `git commit -s`)

## Why this severity, and a real case

<!-- one paragraph: what the oracle protects against, an anonymized case where it would have helped -->
