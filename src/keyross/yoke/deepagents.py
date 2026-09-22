"""The yoke for Deep Agents / LangChain (sketch, v0.2): couples the agent to its gauges and keeps them aligned — like a wheel alignment:
the model and the rules each run straight; the yoke makes them run parallel. After every writing tool, run the oracles on the working copy;
hard red → revert and minimal feedback; never any evidence nor the list of oracles reaches the model.
LangChain 1.x signature: wrap_tool_call(request, handler) — verify against the project's pinned version."""
from __future__ import annotations

from typing import Any, Callable

from keyross.core.document import Document
from keyross.core.runner import run, run_contract


class Yoke:  # inherits from AgentMiddleware when deepagents is installed; dependency-free sketch
    def __init__(self, *, gauge: str = "core", write_tools: tuple[str, ...] = ("apply_edits",), snapshot: Callable[[], Document] | None = None,
                 restore: Callable[[Document], None] | None = None, recorder: Any = None, ctx: dict | None = None) -> None:
        self.gauge, self.write_tools, self.snapshot, self.restore, self.recorder, self.ctx = gauge, write_tools, snapshot, restore, recorder, ctx or {}

    def wrap_tool_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        if getattr(request, "tool_name", None) not in self.write_tools or self.snapshot is None:
            return handler(request)
        before = self.snapshot()
        result = handler(request)                     # the edit, on the working copy
        after = self.snapshot()
        args = getattr(request, "args", {}) or {}
        verdicts = run(after, gauge=self.gauge, ctx={**self.ctx, "before": before}).verdicts
        verdicts += run_contract(args.get("action", ""), before, after, args, self.ctx)
        if self.recorder is not None:
            for v in verdicts:
                self.recorder.event(event_type="verification", decision_id=args.get("decision_id", ""), payload=v.to_dict())
        hard = [v for v in verdicts if v.failed and v.severity.value == "hard" and not v.silent]
        if hard and self.restore is not None:
            self.restore(before)                      # revert
            return {"status": "error", "content": f"{hard[0].category}: retry"}   # minimal sufficient feedback
        return result


KeyrossMiddleware = Yoke  # alias kept for readers who expect the LangChain naming
