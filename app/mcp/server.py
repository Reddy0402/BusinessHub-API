"""MCP server initialization and transport/mount integration.

Creates the official MCP Python SDK (v2) MCPServer instance, registers all
BusinessHub MCP tools, and exposes a Starlette ASGI app using the
streamable-http transport. The app is designed to be mounted into the
existing FastAPI application at /mcp.

The MCP StreamableHTTP session manager's lifecycle is driven by ``mcp_lifespan``,
which must be used as the FastAPI application lifespan.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.mcp.tools import (
    businesshub_health,
    breakdown_task,
    create_task,
    delete_task,
    get_ai_insights,
    get_analytics,
    get_business_info,
    get_task,
    list_subtasks,
    list_tasks,
    parse_task,
    update_task,
)

# ---------------------------------------------------------------------------
# MCP server instance (v2 MCPServer, not the removed v1 FastMCP)
# ---------------------------------------------------------------------------

mcp_server = MCPServer(
    name="businesshub",
    title="BusinessHub MCP",
    instructions=(
        "MCP interface to the BusinessHub task manager. Tools call the existing "
        "BusinessHub store/service layer backed by Supabase PostgreSQL. "
        "Read tools: businesshub_health, list_tasks, get_task, list_subtasks, "
        "get_analytics, get_business_info. "
        "Write tools: create_task, update_task, delete_task, parse_task, "
        "get_ai_insights, breakdown_task."
    ),
    version="1.0.0",
)

# --- Read-only tools ---
mcp_server.add_tool(businesshub_health)
mcp_server.add_tool(list_tasks)
mcp_server.add_tool(get_task)
mcp_server.add_tool(list_subtasks)
mcp_server.add_tool(get_analytics)
mcp_server.add_tool(get_business_info)

# --- Write tools (modify persistent Supabase data) ---
mcp_server.add_tool(create_task)
mcp_server.add_tool(update_task)
mcp_server.add_tool(delete_task)
mcp_server.add_tool(parse_task)
mcp_server.add_tool(get_ai_insights)
mcp_server.add_tool(breakdown_task)

# ---------------------------------------------------------------------------
# Streamable HTTP transport (Starlette ASGI app)
# ---------------------------------------------------------------------------

# streamable_http_app() lazily creates the StreamableHTTPSessionManager and
# a Starlette app whose routes serve POST/GET/DELETE at the mount path.
# The internal path is "/" so that mounting this app at "/mcp" exposes the
# MCP endpoint at "/mcp" (not "/mcp/mcp").
#
# DNS rebinding protection is disabled for this first prototype so the MCP
# endpoint works on localhost, in the test client, and on the production
# Railway domain without host-specific configuration. Authentication and
# transport security can be enabled later by supplying a
# `TransportSecuritySettings` here (the SDK supports bearer-token auth and
# allowed-host lists).
mcp_app = mcp_server.streamable_http_app(
    streamable_http_path="/",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

# The session manager is created by streamable_http_app(); access it to drive
# its lifecycle from the FastAPI lifespan.
session_manager: Any = mcp_server.session_manager


@asynccontextmanager
async def mcp_lifespan(app: FastAPI):
    """FastAPI lifespan that starts/stops the MCP session manager.

    The mounted MCP Starlette app also carries a lifespan
    (lambda app: session_manager.run()), but Starlette does not automatically
    propagate lifespan events to mounted sub-apps, so this lifespan is the
    single place that runs session_manager.run() — exactly once.
    """
    async with session_manager.run():
        yield


__all__ = ["mcp_server", "mcp_app", "mcp_lifespan"]
