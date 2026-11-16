"""BusinessHub MCP server module.

Mounts the official MCP Python SDK (v2) into the existing FastAPI application
at /mcp, exposing BusinessHub task management, analytics and AI capabilities
as MCP tools that call the existing business/data layer (store.py) backed by
Supabase PostgreSQL via SQLAlchemy.
"""

from app.mcp.server import mcp_app, mcp_server

__all__ = ["mcp_app", "mcp_server"]
