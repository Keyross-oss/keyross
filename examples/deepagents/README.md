# A Deep Agent yoked to the einvoice gauge

`invoice_agent.py` runs the same Deep Agent twice: it writes an EN 16931 invoice (UN/CEFACT CII) to `/invoice.xml`. Its draft gets a total wrong; the official EN 16931 rules catch it at the write, the yoke restores the file, and the agent fixes it. The idea in one picture: [an example, one e-invoice](../../README.md#an-example-one-e-invoice).

```bash
pip install 'keyross[einvoice,yoke]'
python examples/deepagents/invoice_agent.py        # offline, no API key
keyross stats                                      # first-pass rate, from .keyross/events.jsonl
```

```
WITHOUT A YOKE — nothing measures the output until it ships
  agent  -> write_file(/invoice.xml)
  tool   <- [success] Updated file /invoice.xml
  agent  :  Invoice written to /invoice.xml.
  shipped: red flag (BR-CO-10, BR-CO-13)

WITH A YOKE — every writing tool is measured by the einvoice gauge
  agent  -> write_file(/invoice.xml)
  tool   <- [error] red flag: BR-CO-10, BR-CO-13 — the write was reverted; fix and retry
  agent  -> write_file(/invoice.xml)
  tool   <- [success] Updated file /invoice.xml
  agent  :  Invoice written to /invoice.xml.
  shipped: green flag
```

**Reading the output.** `BR-CO-10` is the official rule *the sum of the invoice lines equals the line total (BT-106)*; `BR-CO-13` follows from it: *the total without VAT equals the line total minus allowances plus charges (BT-109)*. Without the yoke, nothing answers the agent: the wrong invoice ships, and only a check after the fact (scrutineering) sees the red flag. With the yoke, the write is measured at once, reverted, and the agent receives only the rule ids — never the rule text or the evidence.

Offline, a scripted model stands in for the LLM: its draft has a wrong sum of line net amounts (BT-106), and it rewrites the invoice only when a tool answers with a red flag. The rules are the official CEN EN 16931 artefacts, executed unmodified; the model only ever sees the rule ids. With `--model anthropic:claude-sonnet-5` (or any `init_chat_model` string, and its API key), a real model writes the invoice instead.

**Demo or benchmark?** This demo shows the mechanism on one invoice, with a model scripted to make one mistake. [bench/einvoice](../../bench/einvoice/README.md) measures the effect: the same kind of agent on 20 orders, with a real model, graded outside the agent.

Use it in your own agent:

```python
from keyross.yoke import Yoke
agent = create_deep_agent(model=..., middleware=[Yoke(gauge="einvoice")])
```
