# A Deep Agent yoked to the einvoice gauge

`invoice_agent.py` runs the same Deep Agent twice: it writes an EN 16931 invoice (UN/CEFACT CII) to `/invoice.xml`.

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

Offline, a scripted model stands in for the LLM: its draft has a wrong sum of line net amounts (BT-106), and it rewrites the invoice only when a tool answers with a red flag. The rules are the official CEN EN 16931 artefacts, executed unmodified; the model only ever sees the rule ids. With `--model anthropic:claude-sonnet-5` (or any `init_chat_model` string, and its API key), a real model writes the invoice instead.
