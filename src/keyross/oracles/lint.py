"""keyross lint: an oracle that calls a model or the network is refused. Deterministic or nothing."""
from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN = {"openai", "anthropic", "langchain", "langgraph", "deepagents", "litellm", "requests", "httpx", "aiohttp",
             "urllib", "socket", "random", "time", "datetime"}   # time / datetime / random: no non-determinism inside an oracle


def lint_file(path: str | Path) -> list[str]:
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                root = a.name.split(".")[0]
                if root in FORBIDDEN:
                    problems.append(f"{path}:{node.lineno} forbidden import in an oracle: {a.name}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in FORBIDDEN:
                problems.append(f"{path}:{node.lineno} forbidden import in an oracle: {node.module}")
    return problems


def lint_dir(path: str | Path) -> list[str]:
    out = []
    for f in sorted(Path(path).rglob("*.py")):
        out.extend(lint_file(f))
    return out
