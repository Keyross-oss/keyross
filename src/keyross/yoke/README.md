# Yoke — coupling an agent to its gauges

A yoke attaches a harness to Keyross, the way a wheel alignment makes two wheels run parallel: the model and the rules each run straight; the yoke keeps them aligned at every writing tool. `Report.aligned` — green on first pass, the **first-pass rate** — is the metric to watch over time. It runs the installed gauges after every writing tool and returns only the flag and the category to the model.

| Yoke | Harness | How | Status |
|---|---|---|---|
| `yoke/deepagents.py` | Deep Agents / LangChain 1.x (`wrap_tool_call`, `awrap_tool_call`) | `Yoke(gauge="einvoice")` (`KeyrossMiddleware` alias) — reads the written document back through the agent's backend, runs the gauges, restores it on red | shipped — `pip install 'keyross[yoke]'` |
| Claude Code hook | Claude Code (`PostToolUse`) | `keyross check "$FILE" --json` on every file the agent writes — code executed by the harness, not a skill | 0.5 |
| MCP server | any platform | `keyross serve --mcp` — guard mode (called by the platform, invisible to the model) or tool mode (minimal feedback, scrutineering mandatory) | 0.5 |

`keyross yoke <harness>` prints the recipe. The yoke assumes the harness has its own limiters (budgets, protected columns, deletion cap): the yoke measures, it does not bound.

## The Deep Agents yoke

```python
from deepagents import create_deep_agent
from keyross.telemetry import JsonlTelemetry
from keyross.yoke import Yoke

agent = create_deep_agent(model=..., middleware=[Yoke(gauge="einvoice", telemetry=JsonlTelemetry())])
```

- **What it measures**: `write_file` and `edit_file`, plus any custom tool that has action contracts (`@contract("<tool name>")`) and takes a `file_path` argument. A document is measured when a loaded gauge covers it — `.xlsx` / `.csv` by the invariants and sentinels, `.xml` by the adapters. Anything else passes through untouched.
- **How**: before the tool runs, the yoke reads the document through the agent's own backend; after, it reads it again and runs the gauges on a temporary copy. On a red flag it restores the previous content (or deletes a file that did not exist) and answers the model with a `ToolMessage` in error: `red flag: BR-CO-10, BR-CO-13 — the write was reverted; fix and retry`. Only the categories — never the evidence, the rule text or the list of oracles. Yellow and sentinel failures never block; they go to the telemetry.
- **Backends**: the default `StateBackend` needs nothing. With another backend (`FilesystemBackend`, `CompositeBackend`…), pass the same object to the yoke: `Yoke(gauge=..., backend=backend)`.
- **First-pass rate**: with a telemetry, every measured write is a `verification` event (attempt, flag, evidence). `keyross stats` computes, per gauge, the share of documents that were green on their first write. `yoke.stats()` gives the same numbers for one process.

Try it offline — a scripted model writes an invoice with a wrong total, with and without the yoke: `python examples/deepagents/invoice_agent.py`.
