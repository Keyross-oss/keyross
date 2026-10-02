# Specification — a gauge (v0.1)

A gauge is the installable instrument: a versioned, calibrated set of oracles for one document family — signed, once signing ships. It is what `keyross add` adds to a project and `keyross outdated` compares with the registry. A gauge built on official validators is *homologated*.

## Layout

```
gauge-einvoice/
  gauge.yaml            # the manifest
  oracles/*.py         # invariants, contracts, sentinels (@oracle, @contract)
  adapters/*.py        # existing validators wrapped as oracles (ExternalValidatorAdapter)
  rules/<release>/     # the validator's artifacts, vendored unmodified, with their licence
  badset/*.xlsx|xml    # one bad case per oracle; for an adapter, one per rule family
  CHANGELOG.md         # every version cites the revision of the standard that motivates it
  README.md            # which documents, which rules, what is delta
```

## What a gauge may and may not contain

May: Python oracles (pure functions), adapters executing an external validator (pinned, offline), rule artifacts (Schematron, XSLT, schemas, reference vocabularies) with their checksums, bad cases, documentation, a changelog.

May not: prompts, skills, `CLAUDE.md`-style instruction files, model calls, network calls at check time, anything a model is expected to read. `keyross lint` enforces the code side; the review enforces the rest. A gauge is a compiler with official verifiers — not a way to ask a model to behave.

## gauge.yaml

The manifest of the shipped `einvoice` gauge ([src/keyross/gauges/einvoice/gauge.yaml](../../src/keyross/gauges/einvoice/gauge.yaml)), shortened:

```yaml
name: einvoice
version: 0.2.0                       # semantic versioning
description: EN 16931 e-invoices — the official CEN Schematron, executed as published; delta oracles, the invoice against its order
documents: [invoice.ubl, invoice.cii]
owner: keyross                       # credited owner; gauges written on a mission belong to the client
license: Apache-2.0                  # the vendored CEN artifacts keep their own licence (EUPL-1.2)
requires: { keyross: ">=0.1,<1" }
adapters:
  - id: einvoice.schematron
    tool: CEN/TC 434 EN 16931 validation artefacts
    version: "1.3.16"                # the release; every rule registered from it carries this version
    engine: Saxon-HE via saxonche (XSLT 2.0)
    offline: true                    # false = refused
    syntaxes: { cii: rules/cen-1.3.16/EN16931-CII-validation.xslt, ubl: rules/cen-1.3.16/EN16931-UBL-validation.xslt }
    artifacts:                       # SHA-256 of each file executed, verified before every run
      rules/cen-1.3.16/EN16931-CII-validation.xslt: "0b234dea…"
      rules/cen-1.3.16/EN16931-UBL-validation.xslt: "39f9d282…"
oracles:                             # declared, so the lock can pin them before they run
  - { id: einvoice.delta.order.lines, severity: hard, version: 1 }
  - { id: einvoice.delta.order.totals, severity: hard, version: 1 }    # and order.header, order.vat
regulatory:                          # which revision of the standard the rules implement — part of the package
  - { standard: "EN 16931-1:2017+A1:2019", revision: "CEN validation artefacts 1.3.16" }
signature: sigstore                  # planned: the gauge is signed; keyross verifies before installing
```

## Commands

| Command | Does | Status |
|---|---|---|
| `keyross gauges` | the gauges of the registry index: installed, available or planned | shipped |
| `keyross add einvoice` | adds a gauge of the index to `keyross.yaml`; `keyross lock` then pins it | shipped for the built-in gauges; packages from this repository's index in 0.2 |
| `keyross outdated` | lists gauges whose installed version is behind the registry — the answer to "are we on the latest rules?" | shipped |
| `keyross update` | upgrades gauges within the ranges of `keyross.yaml`, re-runs `keyross test` on their badsets, rewrites the lock | planned |
| `keyross audit` | what verified what: gauges, versions, artifact checksums, signatures, effective dates | planned |

## Registry

v1: the gauges ship inside the package, listed in an index ([src/keyross/gauges/index.json](../../src/keyross/gauges/index.json): name, latest version, source, licence, owner, status). The planned packages will live in this repository's `packages/`; `keyross add` copies them from 0.2. No server.
v2 (planned): an OCI registry (as Conftest bundles), private registries for a client's own gauges, signatures verified at install.
