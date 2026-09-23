"""The yoke for Deep Agents / LangChain: couples the agent to its gauges and keeps them aligned — like a wheel alignment:
the model and the rules each run straight; the yoke makes them run parallel.

After every writing tool (`write_file`, `edit_file`), the yoke reads the document back through the agent's own backend,
runs the gauges on it, and on a red flag restores the previous content and returns only the categories — a pit stop.
A delegated run (`task`, a Deep Agents subagent) is measured too: a subagent does not inherit the main agent's middleware,
so the yoke checks every document it returns or writes, and keeps a red one out of the agent's files.
No evidence, no rule text, no list of oracles ever reaches the model. Requires `pip install 'keyross[yoke]'`."""
from __future__ import annotations

import base64
import dataclasses
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Awaitable, Callable

from keyross.core.document import load
from keyross.core.registry import registry
from keyross.core.runner import ADAPTER_SUFFIXES, TABULAR_SUFFIXES, Report, check_file, run_contract, unreadable
from keyross.core.verdict import Status
from keyross.gauges import load_gauge
from keyross.oracles.adapter import adapters

try:
    from langchain.agents.middleware import AgentMiddleware as _Middleware
    from langchain_core.messages import ToolMessage
except ImportError:  # keyross never requires LangChain; the yoke needs it only when an agent uses it
    _Middleware, ToolMessage = object, None  # type: ignore[assignment,misc]

WRITE_TOOLS = ("write_file", "edit_file")
DELEGATE_TOOLS = ("task",)          # Deep Agents' subagents: they do not inherit the main agent's middleware


def _normalize(path: str) -> str | None:
    """The path the writing tool actually writes to: Deep Agents normalizes it ("quote.csv" -> "/quote.csv").
    A path it refuses (traversal, drive letter) is None: the tool fails on its own, there is nothing to measure."""
    try:
        from deepagents.backends.utils import validate_path
    except ImportError:
        return path
    try:
        return validate_path(path)
    except ValueError:
        return None


def _default_backend() -> Any:
    from deepagents.backends import StateBackend   # the default backend of create_deep_agent
    return StateBackend()


class Yoke(_Middleware):  # type: ignore[misc,valid-type]
    """`create_deep_agent(..., middleware=[Yoke(gauge="einvoice")])`.

    gauge        the gauge to measure with (`None`: every loaded gauge); it is loaded if needed
    backend      the agent's backend — pass the one given to create_deep_agent (default: StateBackend, as Deep Agents);
                 for a plain LangChain agent whose tools write to disk: LocalFiles(root)
    write_tools  the tools that write documents; a custom tool is measured too if it takes `path_arg`, and its
                 action contracts (`@contract("<tool name>")`) run on the before / after documents
    delegate_tools  the tools that hand work to a subagent (`task`): what the subagent wrote is measured when it returns
    ctx          the gauges' context (unit vocabulary, reference data)
    telemetry    an object with `.event(**fields)` (e.g. JsonlTelemetry) — where the first-pass rate is computed from
    """

    def __init__(self, *, gauge: str | None = None, backend: Any = None, write_tools: tuple[str, ...] = WRITE_TOOLS,
                 path_arg: str = "file_path", ctx: dict[str, Any] | None = None, telemetry: Any = None,
                 delegate_tools: tuple[str, ...] = DELEGATE_TOOLS) -> None:
        if _Middleware is not object:
            super().__init__()
        if gauge:
            load_gauge(gauge)
        self.gauge, self.write_tools, self.path_arg = gauge, tuple(write_tools), path_arg
        self.delegate_tools = tuple(delegate_tools)
        self._backend = backend
        self.ctx, self.telemetry = dict(ctx or {}), telemetry
        self._attempts: dict[tuple[str, str], int] = {}
        self._first: dict[tuple[str, str], bool] = {}

    @property
    def backend(self) -> Any:
        if self._backend is None:
            self._backend = _default_backend()
        return self._backend

    # -- the loop -------------------------------------------------------------------------------------------------

    def wrap_tool_call(self, request: Any, handler: Callable[[Any], Any]) -> Any:
        if request.tool_call.get("name") in self.delegate_tools:
            before = self._snapshot()
            result = handler(request)
            return self._after_delegation(request, before, result, self._snapshot())
        path = self._target(request)
        if path is None:
            return handler(request)
        before = self._read(path)
        result = handler(request)
        if _tool_failed(result):
            return result                                  # nothing was written: nothing to measure
        report = self._measure(request, path, before, self._read(path))
        if report.hard_failures:
            self._restore(path, before)
            return self._pit_stop(request, report)
        return result

    async def awrap_tool_call(self, request: Any, handler: Callable[[Any], Awaitable[Any]]) -> Any:
        if request.tool_call.get("name") in self.delegate_tools:
            before = self._snapshot()
            result = await handler(request)
            return self._after_delegation(request, before, result, self._snapshot())
        path = self._target(request)
        if path is None:
            return await handler(request)
        before = await self._aread(path)
        result = await handler(request)
        if _tool_failed(result):
            return result
        report = self._measure(request, path, before, await self._aread(path))
        if report.hard_failures:
            await self._arestore(path, before)
            return self._pit_stop(request, report)
        return result

    # -- what is measured -----------------------------------------------------------------------------------------

    def _target(self, request: Any) -> str | None:
        """The document this tool call writes, if a loaded gauge can measure it."""
        call = request.tool_call
        path = (call.get("args") or {}).get(self.path_arg)
        known = call.get("name") in self.write_tools or bool(registry.contracts_for(call.get("name", "")))
        if not known or not isinstance(path, str):
            return None
        normalize = getattr(self.backend, "normalize", None)     # LocalFiles knows its own paths; Deep Agents' rule otherwise
        path = normalize(path) if callable(normalize) else _normalize(path)
        return path if path is not None and self._covers(path) else None

    def _covers(self, path: str) -> bool:
        suffix = PurePosixPath(path).suffix.lower()
        if suffix in ADAPTER_SUFFIXES:
            return any(a.accepts(path) for a in adapters.values() if self.gauge in (None, a.gauge))
        if suffix in TABULAR_SUFFIXES:
            return any(s.kind in ("invariant", "sentinel") for s in registry.all(gauge=self.gauge))
        return False

    def _measure(self, request: Any, path: str, before: bytes | None, after: bytes | None) -> Report:
        """Run the gauges on the written document (materialized in a temporary folder, never in the agent's files)."""
        call = request.tool_call
        name = PurePosixPath(path).name
        with tempfile.TemporaryDirectory(prefix="keyross-yoke-", ignore_cleanup_errors=True) as tmp:
            after_file = Path(tmp) / name
            after_file.write_bytes(after or b"")
            before_file = None
            if before is not None and PurePosixPath(path).suffix.lower() in TABULAR_SUFFIXES:
                (Path(tmp) / "before").mkdir()
                before_file = Path(tmp) / "before" / name
                before_file.write_bytes(before)
            try:
                report = check_file(after_file, gauge=self.gauge, ctx=self.ctx, before=before_file)
                contracts = registry.contracts_for(call.get("name", ""))
                if contracts and before_file is not None:
                    report.verdicts += run_contract(call["name"], load(before_file), load(after_file), call.get("args") or {}, self.ctx)
            except (ValueError, OSError) as e:
                report = unreadable(path, str(e))
        report.document = path
        self._record(request, path, report)
        return report

    def _after_delegation(self, request: Any, before: dict[str, bytes], result: Any, after: dict[str, bytes]) -> Any:
        """What a delegated run wrote: the files it returns in its Command (a Deep Agents subagent works on its own copy of
        the state, merged back after the tool) and the files it wrote straight to a shared backend (a disk). A red document
        is kept out of the agent's files — as if it had not been written — and the agent gets the red flag."""
        reds, measured = [], set()
        update = getattr(result, "update", None)
        files = update.get("files") if isinstance(update, dict) else None
        if isinstance(files, dict):
            kept = dict(files)
            for path, data in files.items():
                if data is None or not isinstance(path, str) or not self._covers(path):
                    continue
                content = _file_bytes(data)
                if content is None or content == before.get(path):
                    continue
                measured.add(path)
                report = self._measure(request, path, before.get(path), content)
                if report.hard_failures:
                    del kept[path]                              # never merged: the agent's files keep what they had
                    reds.append(report)
            update = {**update, "files": kept}
        for path, content in after.items():                     # a shared disk: the subagent already wrote there
            if path in measured or content == before.get(path):
                continue
            report = self._measure(request, path, before.get(path), content)
            if report.hard_failures:
                self._restore(path, before.get(path))
                reds.append(report)
        if not reds:
            return result
        message = self._pit_stop(request, *reds)
        if isinstance(getattr(result, "update", None), dict):
            return dataclasses.replace(result, update={**update, "messages": [message]})
        return message

    def _snapshot(self) -> dict[str, bytes]:
        """The documents a loaded gauge covers, as the agent's backend holds them now."""
        glob = getattr(self.backend, "glob", None)
        if not callable(glob):
            return {}
        found = getattr(glob("*", "/"), "matches", None) or []             # a bare pattern matches at any depth
        paths = sorted({m["path"] for m in found if isinstance(m, dict) and isinstance(m.get("path"), str) and self._covers(m["path"])})
        return {r.path: r.content for r in self.backend.download_files(paths) if r.content is not None} if paths else {}

    def _pit_stop(self, request: Any, *reports: Report) -> Any:
        """Minimal feedback: the flag and the categories of the red verdicts — nothing else reaches the model."""
        categories = list(dict.fromkeys(v.category for report in reports for v in report.hard_failures))
        call = request.tool_call
        return ToolMessage(content=f"red flag: {', '.join(categories)} — the write was reverted; fix and retry",
                           tool_call_id=call["id"], name=call["name"], status="error")

    # -- the agent's files, through its own backend -----------------------------------------------------------------

    def _read(self, path: str) -> bytes | None:
        return self.backend.download_files([path])[0].content

    async def _aread(self, path: str) -> bytes | None:
        return (await self.backend.adownload_files([path]))[0].content

    def _restore(self, path: str, before: bytes | None) -> None:
        if before is None:
            self.backend.delete(path)
        else:
            self.backend.upload_files([(path, before)])

    async def _arestore(self, path: str, before: bytes | None) -> None:
        if before is None:
            await self.backend.adelete(path)
        else:
            await self.backend.aupload_files([(path, before)])

    # -- the first-pass rate ----------------------------------------------------------------------------------------

    def _record(self, request: Any, path: str, report: Report) -> None:
        thread = str(((getattr(request.runtime, "config", None) or {}).get("configurable") or {}).get("thread_id", ""))
        key = (thread, path)
        attempt = self._attempts[key] = self._attempts.get(key, 0) + 1
        if attempt == 1:
            self._first[key] = report.aligned
        if self.telemetry is not None:
            call = request.tool_call
            self.telemetry.event(
                event_type="verification", decision_id=call.get("id", ""), tool=call.get("name", ""), thread_id=thread,
                document=path, gauge=self.gauge or "*", attempt=attempt, flag=report.flag, aligned=report.aligned,
                reverted=bool(report.hard_failures), duration_ms=report.duration_ms,
                verdicts=[v.to_dict() for v in report.verdicts if v.status == Status.FAIL])

    def stats(self) -> dict[str, Any]:
        """Documents written, first-pass rate (green on the first write, no retry), pit stops."""
        documents = len(self._first)
        return {"documents": documents, "first_pass": sum(self._first.values()),
                "first_pass_rate": round(sum(self._first.values()) / documents, 3) if documents else None,
                "writes": sum(self._attempts.values())}


def _file_bytes(data: Any) -> bytes | None:
    """The bytes of a Deep Agents file entry (text, or base64 for a binary file)."""
    try:
        from deepagents.backends.utils import file_data_to_string
    except ImportError:
        return None
    text = file_data_to_string(data)
    return text.encode("utf-8") if data.get("encoding", "utf-8") == "utf-8" else base64.standard_b64decode(text)


def _tool_failed(result: Any) -> bool:
    return getattr(result, "status", None) == "error"


KeyrossMiddleware = Yoke  # alias kept for readers who expect the LangChain naming
