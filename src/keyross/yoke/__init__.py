"""The yoke: what couples an agent to its gauges — a middleware, a hook, an MCP server. Code the model never reads.

from keyross.yoke import Yoke
agent = create_deep_agent(..., middleware=[Yoke(gauge="core")])
"""
from keyross.yoke.deepagents import Yoke, KeyrossMiddleware

__all__ = ["Yoke", "KeyrossMiddleware"]
