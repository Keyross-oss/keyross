# Compilable AI Workflows — a manifesto
### *Compile the output, not just the plan*

v0.1 · September 2026 · Wassim Amri — Keyross

## 1. The observation

Claude Code is reliable. Not because its model is better — because code has a **compiler**, **tests** and **CI**: free, deterministic, immediate oracles that say, after every action, whether the result is right. Coding agents inherited forty years of verification tooling without having to write any of it.

Business agents have none of it. A quote, an invoice, an insurance claim, a KYC file has no compiler and no tests. So we verify with the model itself — a probabilistic judge grading a probabilistic producer — and we are surprised it does not hold in production.

In 2026, agents learned to compile their plans: an intent becomes a deterministic, replayable, auditable execution plan. That is the right half. **Nobody compiles their outputs.** This manifesto is the other half.

## 2. The definition

A **domain compiler** is a deterministic program that takes a business artifact and its reference data, and returns a structured verdict with evidence. It has four components:

- the **schema** — the types: a quantity is a number, a unit belongs to a vocabulary;
- the **invariants** — what is true whatever the plan: the total equals the sum of the lines, no priced line disappears;
- the **action contracts** — what is true if the action did what it announced, instantiated with the plan's parameters;
- the **reference data** — the *linker*: the price list, the nomenclature, the lexicon, provided by the client.

It has two passes: the first **compiles the plan** (the pre-conditions, before anything is touched), the second **compiles the output** (the post-conditions and the invariants, after every action and at the gate). A workflow is **compilable** when its outputs have a compiler.

What it is not: an LLM-as-a-judge, a decision rules engine, a compiled workflow — nor a skill, a prompt or an instruction file: a compiler is code a model never reads, with rules the model never sees. It compiles the document, the way gcc compiles code; the agent is the developer.

## 3. The ten principles

1. **Deterministic or nothing.** An oracle is right or wrong; it does not think. A probabilistic verifier is named as such and is never the reward function.
2. **Written by humans, never learned.** An oracle that learns is no longer an oracle. The oracle suite improves by versions, after human review, from evidence-backed proposals.
3. **Invisible to the agent, executed by the harness.** The oracle is not in the prompt, not in the tool list, not in a readable file. The model never reports a green, so it cannot fabricate one.
4. **Minimal sufficient feedback.** The agent receives red or green and the category of the deviation — enough to correct, not enough to work around.
5. **Replayed outside the agent.** The gate replays the full suite from a fresh environment. Agent green and gate red: an integrity incident, not a grade.
6. **Redundant, with sentinels.** The same property seen by several independent oracles; silent, zero-weight oracles that sign a workaround.
7. **Tested itself.** Every oracle has its bad case; an oracle that never turns red anymore is dead, not good.
8. **Versioned, pinned, logged.** Every run knows which oracles verified it. That is the proof for the audit.
9. **Written before the first agent.** Without a compiler, no loop can be reliable — nor learn. The first question of any agent project: *what is your compiler?*
10. **Open.** The verdict format, the registry and the lifecycle are public; sector gauges are the accumulation of real fields.

## 4. The minimal architecture

A registry of versioned oracles, packaged as gauges and installable from one place · a runner that executes them and returns a report and an exit code · a gate that replays everything outside the agent · a lock that pins · a calibration that, later, confronts the oracles with ground truth. Three exposures: a library, a command line, an MCP server any harness can call.

Its relation to learning: the compiler is the reward function. The policy learns — which action to prefer among those allowed. The compiler, never.

## 5. The conditions of a compilable domain

A structured or structurable artifact on which closed operations exist · a cheap structural oracle — a compiler — that exists or can be written · nameable actions, to derive contracts · a sandbox and a diff attributable to a task · a high cost of error · a rare but existing ground truth, to calibrate · and stationarity: rules that change in years, not weeks.

## 6. The lifecycle

Propose (a human, or the agent with its cases) → review → approve → version → pin → calibrate → retire. The client owns its oracles; the engine and the generalized gauges stay open.

## 7. What exists, and where this sits

Agents compile their plans (Compiled AI, agent compilers); regulated platforms compile policies into deterministic checks, closed-source; reliability tools evaluate with generic judges; verification layers for code exist for code. This manifesto occupies the empty square: **the compiler of the business artifact — open, sector-specific, calibrated, with a gate.**

## 8. What this manifesto asks

Write the compiler before the agent. Publish your invariants. Contribute a gauge.

*Apache-2.0 — keyross.*
