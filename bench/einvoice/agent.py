"""The invoicing agent under test: a Deep Agent that turns a purchase order into an EN 16931 invoice (CII) at /invoice.xml.

Both arms get the same model, the same prompt and the same limits; the only difference is the yoke. The limits cap the cost
of a run: at most `max_writes` writes of the invoice and `max_model_calls` model calls."""
from __future__ import annotations

import json
from typing import Any

from deepagents import create_deep_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from keyross.yoke import Yoke

from bench.einvoice.reference import to_cii

INVOICE_PATH = "/invoice.xml"
SYSTEM_PROMPT = (
    "You are the invoicing agent of a company. You receive a purchase order as JSON. Issue its invoice as an EN 16931 "
    "electronic invoice in UN/CEFACT Cross Industry Invoice syntax (CII D16B — the XML of Factur-X, profile EN 16931) and "
    f"save it with write_file to {INVOICE_PATH}. Compute every amount from the order: line net amounts, document-level "
    "allowances and charges, the VAT breakdown per category and rate, and the totals. When a tool answers with a red flag, "
    "the listed EN 16931 rules failed: correct them and write the file again. When the invoice is saved, answer DONE.")


def task_message(order: dict) -> str:
    """What the agent receives: the order, without the benchmark's own labels."""
    data = {k: v for k, v in order.items() if k not in ("id", "scenario")}
    return "Invoice this order:\n```json\n" + json.dumps(data, indent=2, ensure_ascii=False) + "\n```"


def build_agent(model: Any, *, yoke: bool, telemetry: Any = None, max_writes: int = 4, max_model_calls: int = 12) -> Any:
    middleware: list[Any] = [ToolCallLimitMiddleware(tool_name="write_file", run_limit=max_writes),
                             ModelCallLimitMiddleware(run_limit=max_model_calls, exit_behavior="end")]
    if yoke:
        middleware.append(Yoke(gauge="einvoice", telemetry=telemetry))
    return create_deep_agent(model=model, system_prompt=SYSTEM_PROMPT, middleware=middleware)


class ScriptedInvoiceModel(BaseChatModel):
    """Offline stand-in for an LLM, to check the harness at zero cost: its first invoice has a wrong sum of line net
    amounts (BT-106); it writes the reference invoice only after a red flag."""

    order: dict

    def bind_tools(self, tools: Any, **kwargs: Any) -> "ScriptedInvoiceModel":
        return self

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def _generate(self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
        results = [m for m in messages if isinstance(m, ToolMessage)]
        if not results:
            content = to_cii(self.order, line_total_shift="1.00")
        elif results[-1].status == "error" and "red flag" in str(results[-1].content):
            content = to_cii(self.order)
        else:
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content="DONE"))])
        call = {"name": "write_file", "args": {"file_path": INVOICE_PATH, "content": content}, "id": f"call_{len(results) + 1}"}
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content="", tool_calls=[call]))])
