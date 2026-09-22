# Specification — a gauge (v0.1)

A gauge is the installable instrument: a versioned, signed, calibrated set of oracles for one document family. It is what `keyross add` installs and `keyross update` keeps current. A gauge built on official validators is *homologated*.

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

```yaml
name: einvoice
version: 1.2.0                       # semantic versioning
description: EN 16931 e-invoices — official Schematron adapted, delta oracles added
documents: [invoice.ubl, invoice.cii, facturx.pdf]
owner: keyross                       # credited owner; gauges written on a mission belong to the client
license: Apache-2.0                  # or a commercial license id
requires: { keyross: ">=0.2,<1" }
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
  - { id: einvoice.delta.order_match, severity: hard, version: 2 }
  - { id: einvoice.delta.supplier_reference, severity: soft, version: 1 }
regulatory:                          # when the rules apply — part of the package
  - { standard: "EN 16931", revision: "2017+A1", effective: "2026-09-01", scope: "FR B2B reception" }
signature: sigstore                  # the gauge is signed; keyross verifies before installing (0.4)
```

## Commands

| Command | Does |
|---|---|
| `keyross add einvoice@1.2` | resolves the gauge in the registry index, installs it, adds it to `keyross.yaml`, pins it in `keyross.lock` |
| `keyross update` | upgrades gauges within the ranges of `keyross.yaml`, re-runs `keyross test` on their badsets, rewrites the lock |
| `keyross outdated` | lists gauges whose installed version is behind the registry — the answer to "are we on the latest rules?" |
| `keyross audit` | what verified what: gauges, versions, artifact checksums, signatures, effective dates |

## Registry

v1: a git repository per gauge and an index (`gauges/index.json`: name, versions, source, checksums). No server.
v2: an OCI registry (as Conftest bundles), private registries for a client's own gauges, signatures verified at install.
