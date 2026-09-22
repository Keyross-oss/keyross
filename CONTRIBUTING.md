# Contributing — writing an oracle

The mission of this repository: gather and create, in the open, the oracles that make agent deployments reliable — horizontal gauges and sector gauges. Not sure where to start? [GAUGES.md](GAUGES.md) lists the good first oracles.

A contribution = **one oracle and its bad case**. Nothing more is required for a first step.

1. `keyross init` in an empty folder, or clone this repository.
2. Write the oracle in `oracles/<gauge>.py` — a pure function `(doc, ctx) -> Verdict`, an id `gauge.subject.property`, a flag on failure (red = `hard`, yellow = `soft`), a one-sentence docstring saying what it verifies.
3. Build its bad case: `badset/<oracle_id>.xlsx` — a deliberately wrong file the oracle **must** catch. For a conservation sentinel, add `badset/<oracle_id>.before.xlsx`.
4. `keyross test` green, `keyross lint` green, `keyross lock`.
5. Sign off your commits (`git commit -s` — Developer Certificate of Origin; no CLA to sign).
6. Open the PR with, in the description: what the oracle verifies, why this severity, and a real (anonymized) case where it would have helped.

Refused without discussion: an oracle that imports a model or the network; an oracle without a bad case; an oracle that leaks evidence into `minimal()`; an oracle whose verdict depends on the clock or on randomness; **a "gauge" made of prompts, skills or instructions to a model** — a gauge is code and official verifiers, never text a model reads.

A sector gauge (`gauges/<sector>/`) is welcome if it brings at least five oracles, their badset, and one page saying which documents they apply to. It is credited to its author.
