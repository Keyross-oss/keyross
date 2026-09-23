# Architecture — where the gauges run

![Full architecture: registry → installed gauges → three doors → outputs](architecture.png)

**The registry** (`keyross gauges · add · outdated`; `update` in 0.3) holds the gauges: `core`, `einvoice` (the official CEN EN 16931 artefacts, run unmodified; delta oracles in 0.2), `dora.register`, `governance`, and yours. **Installed gauges** are pinned in `keyross.lock` — ids, versions, checksums of the official artifacts — and deployed where the documents are: your machine, your CI, your cluster. Never a SaaS that receives files.

## Three doors — two yokes and scrutineering

![One run: the agent writes, the compiler runs the gauges, red flag → pit stop, green → scrutineering ships](loop.gif)

1. **The yoke, inside the harness.** The model plans and writes on the working copy without ever seeing the gauges — not in the prompt, not in the tool list. `Yoke` (alias `KeyrossMiddleware`; `wrap_tool_call`, around the writing tool) runs the gauges on what was written: invariants, contracts, sentinels, official validators. Red → revert and minimal feedback (the categories — rule ids — only); green → continue. Shipped for Deep Agents and LangChain agents. With Claude Code (0.5), a `PostToolUse` hook will run `keyross check` on the file the agent wrote: code executed by the harness, not a skill the model reads.
2. **The yoke, as a service — MCP** *(planned, 0.5)*. `keyross serve --mcp`, deployed at the client, offline. *Guard mode*: called by the platform's control layer, invisible to the model — the normal mode. *Tool mode*: `verify` visible to the model, minimal feedback only, the gate stays mandatory — acceptable when the platform cannot host a guard. Consumers: the Claude platform, Codex, Deep Agents, agent platforms, ERPs, e-invoicing platforms (OEM).
3. **Scrutineering — the gate.** `keyross gate outputs/` in CI, in a pipeline or as a Kubernetes Job replays every gauge on what leaves, outside the agent — exit 0 / 1 / 2. Agent green and gate red is an integrity incident: the run is quarantined. The door that needs no agent.

## What comes out — the same contract from every door

The **verdict** (status, category, evidence, `oracle_id@version`, severity; `minimal()` for the agent) · **keyross.lock** (what verified this run: gauges, versions, checksums of official artifacts) · the **report** (human-readable: scope, verifiers, deviations with evidence, integrity, recommendations that name the oracle that will measure them) · the **seal** (0.3: hash of the document + lock + verdicts, signed — the attestation, verifiable offline) · the **telemetry** (JSONL locally, ClickHouse in production — the events that audits and learning read).

Formats: [spec/verdict.md](spec/verdict.md) · [spec/lock.md](spec/lock.md) · [spec/gauge.md](spec/gauge.md) · adapters: [../src/keyross/oracles/adapter.py](../src/keyross/oracles/adapter.py) · yoke: [../src/keyross/yoke/README.md](../src/keyross/yoke/README.md).
