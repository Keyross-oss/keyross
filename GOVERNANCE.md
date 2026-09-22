# Governance — how oracles get in, and how they stay honest

## Mission

Keyross is the **open home of oracles for agents in production**: horizontal gauges (structure, governance, security) and sector gauges (quotes, invoices, insurance claims, KYC files…), so that any team deploying an agent can compile its outputs before shipping — and prove it.

## Roles

- **Maintainers** review and merge; they own the core gauges and the release cadence. Today: Wassim Amri (Keyross).
- **Gauge owners** own a sector gauge: they approve its oracles, keep its badset alive, answer its calibration issues. A gauge is credited to its owner.
- **Contributors** propose oracles, gauges, fixes. One oracle and its bad case is a complete contribution.

## What gets merged

An oracle is merged when it is deterministic (`keyross lint`), catches its bad case (`keyross test`), returns minimal feedback, has an id, a version, a severity and a one-sentence docstring, and comes with one real (anonymized) case. Severity is argued, not asserted.

An oracle is **never** merged if it calls a model or the network, depends on the clock or on randomness, leaks evidence to the agent, or has no bad case. A gauge is **never** merged if it contains prompts, skills or instruction files for a model: gauges are compilers with official verifiers, not text.

## Versioning

Oracles are versioned individually (`version=`) and pinned by fingerprint in `keyross.lock`. Changing an oracle's logic bumps its version; a run always knows which version verified it. Gauges follow semantic versioning; the engine follows semantic versioning with `0.x` until the verdict and lock formats are frozen (target: 1.0).

## Calibration

A false positive or a false negative is filed as a calibration issue against an oracle id and version, with the (anonymized) document. The gauge owner decides: fix the oracle (new version), change its severity, or add a case to the badset. An oracle that never turns red in the badset is retired, not kept.

## Licensing and contributions

The engine and the public gauges are Apache-2.0. Contributions are accepted under the Developer Certificate of Origin (`git commit -s`): you certify that you have the right to submit the code under this license. No CLA.

Sector gauges written for a client on a mission belong to that client unless generalized and contributed back with their agreement.
