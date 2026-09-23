"""The yoke in a real Deep Agents loop, offline: a scripted model stands in for the LLM."""
import asyncio
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("deepagents")

from deepagents import create_deep_agent  # noqa: E402
from deepagents.backends import FilesystemBackend  # noqa: E402
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel  # noqa: E402
from langchain_core.messages import AIMessage, ToolMessage  # noqa: E402

from keyross.telemetry import JsonlTelemetry, first_pass, read_events  # noqa: E402
from keyross.yoke import Yoke  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GOOD = "ref;designation;unit;qty;unit_price;amount\n1.1;Excavation;m3;10;25;250\n1.2;Backfill;m3;4;12.5;50\n;Total lot 1;;;;300\n"
BAD = GOOD.replace(";300\n", ";295\n")                         # the subtotal no longer matches its lines
saxon = pytest.mark.skipif(__import__("importlib").util.find_spec("saxonche") is None, reason="pip install 'keyross[einvoice]'")


class Scripted(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def write(path, content, n):
    return AIMessage(content="", tool_calls=[{"name": "write_file", "args": {"file_path": path, "content": content}, "id": f"w{n}"}])


def run(calls, yoke, backend=None, thread="t"):
    agent = create_deep_agent(model=Scripted(responses=[*calls, AIMessage(content="done")]), middleware=[yoke], backend=backend)
    return agent.invoke({"messages": [{"role": "user", "content": "go"}]}, config={"configurable": {"thread_id": thread}})


def files(out):
    return {p: (d["content"] if isinstance(d, dict) else d) for p, d in out.get("files", {}).items()}


def tool_messages(out):
    return [m for m in out["messages"] if isinstance(m, ToolMessage)]


def test_red_write_is_reverted_and_only_the_category_reaches_the_model():
    out = run([write("/quote.csv", BAD, 1), write("/quote.csv", GOOD, 2)], Yoke(gauge="core"))
    red, green = tool_messages(out)
    assert red.status == "error" and red.content == "red flag: totals.mismatch — the write was reverted; fix and retry"
    assert green.status == "success" and files(out)["/quote.csv"] == GOOD
    for leak in ("295", "300", "expected", "rid:", "core.totals"):       # no evidence, no oracle id, no threshold
        assert leak not in red.content


def test_red_edit_restores_the_previous_content():
    edit = AIMessage(content="", tool_calls=[{"name": "edit_file", "id": "e1",
                                              "args": {"file_path": "/quote.csv", "old_string": ";300", "new_string": ";295"}}])
    out = run([write("/quote.csv", GOOD, 1), edit], Yoke(gauge="core"))
    assert [m.status for m in tool_messages(out)] == ["success", "error"]
    assert files(out)["/quote.csv"] == GOOD                                 # restored, not deleted


def test_relative_path_is_measured_where_the_tool_writes_it():
    out = run([write("quote.csv", BAD, 1)], Yoke(gauge="core"))            # Deep Agents writes it to /quote.csv
    assert tool_messages(out)[0].status == "error" and "/quote.csv" not in files(out)


def test_filesystem_backend_is_reverted_on_disk(tmp_path):
    backend = FilesystemBackend(root_dir=tmp_path, virtual_mode=True)
    out = run([write("/quote.csv", BAD, 1)], Yoke(gauge="core", backend=backend), backend=backend)
    assert tool_messages(out)[0].status == "error" and not (tmp_path / "quote.csv").exists()
    run([write("/quote.csv", GOOD, 1)], Yoke(gauge="core", backend=backend), backend=backend)
    assert (tmp_path / "quote.csv").read_text(encoding="utf-8") == GOOD


def test_documents_no_gauge_measures_pass_through(tmp_path):
    telemetry = JsonlTelemetry(tmp_path / "events.jsonl")
    out = run([write("/notes.md", "anything", 1), write("/order.xml", "<x/>", 2)], Yoke(gauge="core", telemetry=telemetry))
    assert [m.status for m in tool_messages(out)] == ["success", "success"] and read_events(telemetry.path) == []


def test_a_failing_tool_is_not_measured(tmp_path):
    telemetry = JsonlTelemetry(tmp_path / "events.jsonl")
    out = run([write("../escape.csv", BAD, 1)], Yoke(gauge="core", telemetry=telemetry))
    assert tool_messages(out)[0].status == "error" and "red flag" not in tool_messages(out)[0].content
    assert read_events(telemetry.path) == []


def test_async_loop():
    agent = create_deep_agent(model=Scripted(responses=[write("/quote.csv", BAD, 1), write("/quote.csv", GOOD, 2), AIMessage(content="done")]),
                              middleware=[Yoke(gauge="core")])
    out = asyncio.run(agent.ainvoke({"messages": [{"role": "user", "content": "go"}]}, config={"configurable": {"thread_id": "a"}}))
    assert [m.status for m in tool_messages(out)] == ["error", "success"] and files(out)["/quote.csv"] == GOOD


def test_first_pass_rate_from_the_telemetry(tmp_path):
    telemetry = JsonlTelemetry(tmp_path / "events.jsonl")
    yoke = Yoke(gauge="core", telemetry=telemetry)
    run([write("/a.csv", BAD, 1), write("/a.csv", GOOD, 2), write("/b.csv", GOOD, 3)], yoke)
    assert yoke.stats() == {"documents": 2, "first_pass": 1, "first_pass_rate": 0.5, "writes": 3}
    assert first_pass(read_events(telemetry.path))["core"] == {"documents": 2, "first_pass": 1, "first_pass_rate": 0.5,
                                                                "writes": 3, "pit_stops": 1}
    red = next(e for e in read_events(telemetry.path) if e["reverted"])
    assert red["verdicts"][0]["evidence"]["errors"][0]["expected"] == 300.0    # the evidence goes to the telemetry, not the model


@saxon
def test_einvoice_yoke_runs_the_official_rules():
    draft = (ROOT / "badset" / "einvoice.br-co-10.xml").read_text(encoding="utf-8")
    right = (ROOT / "tests" / "fixtures" / "einvoice" / "facturx-en16931.cii.xml").read_text(encoding="utf-8")
    out = run([write("/invoice.xml", draft, 1), write("/invoice.xml", right, 2)], Yoke(gauge="einvoice"))
    red, green = tool_messages(out)
    assert red.content == "red flag: BR-CO-10, BR-CO-13 — the write was reverted; fix and retry"
    assert "/*:" not in red.content and "Sum of" not in red.content          # no XPath, no assertion text
    assert green.status == "success" and files(out)["/invoice.xml"] == right


@saxon
def test_saxon_survives_the_agent_threads():
    """saxonche objects created on a worker thread and freed on the main thread crashed the process at exit."""
    code = ("import threading, keyross.gauges.einvoice as g\n"
            "from keyross.core.runner import check_file\n"
            "f = 'badset/einvoice.br-29.xml'\n"
            "t = threading.Thread(target=lambda: check_file(f, gauge='einvoice')); t.start(); t.join()\n"
            "assert check_file(f, gauge='einvoice').hard_failures\n")
    proc = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, timeout=120,
                          env={**__import__("os").environ, "PYTHONPATH": str(ROOT / "src")})
    assert proc.returncode == 0, proc.stderr[-2000:]


def test_plain_langchain_agent_with_its_own_disk_tool(tmp_path):
    """No Deep Agents: a LangChain create_agent whose own tool writes to disk, yoked through LocalFiles."""
    from langchain.agents import create_agent
    from langchain_core.tools import tool
    from keyross.yoke import LocalFiles

    @tool
    def save_quote(file_path: str, content: str) -> str:
        """Save a quote as CSV."""
        (tmp_path / file_path).write_text(content, encoding="utf-8")
        return f"saved {file_path}"

    def call(content, n):
        return AIMessage(content="", tool_calls=[{"name": "save_quote", "args": {"file_path": "quote.csv", "content": content}, "id": f"s{n}"}])

    yoke = Yoke(gauge="core", backend=LocalFiles(tmp_path), write_tools=("save_quote",))
    agent = create_agent(model=Scripted(responses=[call(BAD, 1), call(GOOD, 2), AIMessage(content="done")]), tools=[save_quote], middleware=[yoke])
    out = agent.invoke({"messages": [{"role": "user", "content": "go"}]})
    assert [m.status for m in tool_messages(out)] == ["error", "success"]
    assert (tmp_path / "quote.csv").read_text(encoding="utf-8") == GOOD


def test_local_files_refuses_paths_outside_its_root(tmp_path):
    from keyross.yoke import LocalFiles
    files = LocalFiles(tmp_path / "out")
    assert files.normalize("invoice.xml") == files.normalize("/invoice.xml") == "/invoice.xml"
    assert files.normalize("../secret.csv") is None and files.normalize(str(tmp_path / "elsewhere.csv")) is None
    assert files.normalize(str(tmp_path / "out" / "sub" / "a.csv")) == "/sub/a.csv"
