"""A Deep Agent that writes an EN 16931 invoice, with and without the yoke.

Offline by default: a scripted model stands in for the LLM. Its draft invoice has a wrong total (BT-106, the sum of the
line net amounts); it rewrites the invoice only when a tool answers with a red flag. Without the yoke, nothing answers
and the wrong invoice ships. With the yoke, the write is measured by the official EN 16931 rules, reverted, retried.

    pip install 'keyross[einvoice,yoke]'
    python examples/deepagents/invoice_agent.py
    python examples/deepagents/invoice_agent.py --model anthropic:claude-sonnet-5    # a real model (ANTHROPIC_API_KEY)
    keyross stats                                                                     # the first-pass rate, from the telemetry
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from keyross.core.runner import check_file
from keyross.gauges import load_gauge
from keyross.telemetry import JsonlTelemetry
from keyross.yoke import Yoke

ROOT = Path(__file__).resolve().parents[2]
DRAFT = (ROOT / "badset" / "einvoice.br-co-10.xml").read_text(encoding="utf-8")                       # BT-106 = 96.00
CORRECTED = (ROOT / "tests" / "fixtures" / "einvoice" / "facturx-en16931.cii.xml").read_text(encoding="utf-8")  # BT-106 = 95.00
TASK = ("Write the invoice F20260023 for the order in EN 16931 (UN/CEFACT CII) to /invoice.xml with write_file. "
        "If a tool answers with a red flag, correct the listed rules and write the file again.")


class ScriptedModel(BaseChatModel):
    """Stands in for an LLM, offline: writes its draft, and rewrites only after a red flag."""

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedModel":
        return self

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
        tool_results = [m for m in messages if isinstance(m, ToolMessage)]
        if not tool_results:
            content = DRAFT
        elif tool_results[-1].status == "error" and "red flag" in str(tool_results[-1].content):
            content = CORRECTED
        else:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="Invoice written to /invoice.xml."))])
        call = {"name": "write_file", "args": {"file_path": "/invoice.xml", "content": content}, "id": f"call_{len(tool_results) + 1}"}
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="", tool_calls=[call]))])


def run(model: Any, middleware: list[Any]) -> dict[str, Any]:
    agent = create_deep_agent(model=model, middleware=middleware)
    return agent.invoke({"messages": [{"role": "user", "content": TASK}]}, config={"configurable": {"thread_id": "demo"}})


def transcript(out: dict[str, Any]) -> None:
    for m in out["messages"]:
        if isinstance(m, AIMessage) and m.tool_calls:
            for c in m.tool_calls:
                print(f"  agent  -> {c['name']}({c['args'].get('file_path')})")
        elif isinstance(m, ToolMessage):
            print(f"  tool   <- [{m.status}] {m.content}")
        elif isinstance(m, AIMessage):
            print(f"  agent  :  {m.content}")


def shipped(out: dict[str, Any], tmp: Path) -> str:
    """Scrutineering on what the agent delivered: the official rules, replayed outside the agent."""
    data = out.get("files", {}).get("/invoice.xml")
    if data is None:
        return "no invoice delivered"
    text = data.get("content") if isinstance(data, dict) else data
    f = tmp / "invoice.xml"
    f.write_text("\n".join(text) if isinstance(text, list) else text, encoding="utf-8")
    rep = check_file(f, gauge="einvoice")
    reds = ", ".join(v.category for v in rep.hard_failures)
    return f"{rep.flag} flag" + (f" ({reds})" if reds else "")


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--model", help="a real model for init_chat_model, e.g. anthropic:claude-sonnet-5 (default: the offline scripted model)")
    p.add_argument("--telemetry", default=".keyross/events.jsonl")
    args = p.parse_args()
    model = args.model or ScriptedModel()
    load_gauge("einvoice")                     # scrutineering needs the gauge loaded, with or without a yoke
    tmp = Path(".keyross"); tmp.mkdir(exist_ok=True)

    print("WITHOUT A YOKE — nothing measures the output until it ships")
    out = run(model, [])
    transcript(out)
    print(f"  shipped: {shipped(out, tmp)}\n")

    print("WITH A YOKE — every writing tool is measured by the einvoice gauge")
    yoke = Yoke(gauge="einvoice", telemetry=JsonlTelemetry(args.telemetry))
    out = run(model, [yoke])
    transcript(out)
    print(f"  shipped: {shipped(out, tmp)}")
    s = yoke.stats()
    print(f"  first pass: {s['first_pass']} / {s['documents']} document(s) · {s['writes']} write(s) — `keyross stats` reads {args.telemetry}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
