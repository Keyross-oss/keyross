# Yoke — coupling an agent to its gauges

A yoke attaches a harness to Keyross. It runs the installed gauges after every writing tool and returns only the flag and the category to the model.

| Yoke | Harness | How | Status |
|---|---|---|---|
| `yoke/deepagents.py` | Deep Agents / LangChain (`wrap_tool_call`) | `KeyrossMiddleware(gauge="core")` — snapshot, run, revert on red | sketch (0.2) |
| Claude Code hook | Claude Code (`PostToolUse`) | `keyross check "$FILE" --json` on every file the agent writes — code executed by the harness, not a skill | 0.5 |
| MCP server | any platform | `keyross serve --mcp` — guard mode (called by the platform, invisible to the model) or tool mode (minimal feedback, scrutineering mandatory) | 0.5 |

`keyross yoke <harness>` prints the recipe. The yoke assumes the harness has its own limiters (budgets, protected columns, deletion cap): the yoke measures, it does not bound.
