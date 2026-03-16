"""
Atlassian MCP Server

Provides Jira and Confluence tools for Claude Desktop and Claude Code.

Usage:
  Claude Desktop (claude_desktop_config.json):
    {
      "mcpServers": {
        "atlassian-mcp-server": {
          "command": "uv",
          "args": ["run", "--directory", "/path/to/atlassian-mcp-server", "python", "-m", "atlassian_mcp.server"]
        }
      }
    }

  Claude Code:
    claude mcp add atlassian-mcp-server -- uv run --directory /path/to/atlassian-mcp-server python -m atlassian_mcp.server
"""

import asyncio

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from atlassian_mcp.tools import confluence as confluence_tools
from atlassian_mcp.tools import jira as jira_tools

server = Server("atlassian-mcp-server", version="0.1.0")

# Collect all tools from each module
ALL_TOOLS = jira_tools.TOOLS + confluence_tools.TOOLS

# Map tool names to their module handlers
TOOL_HANDLERS: dict[str, object] = {}
for tool in jira_tools.TOOLS:
    TOOL_HANDLERS[tool.name] = jira_tools.handle_tool
for tool in confluence_tools.TOOLS:
    TOOL_HANDLERS[tool.name] = confluence_tools.handle_tool


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return ALL_TOOLS


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    handler = TOOL_HANDLERS.get(name)
    if handler is None:
        result = f'{{"error": "Unknown tool: {name}"}}'
    else:
        result = await handler(name, arguments)

    return [types.TextContent(type="text", text=result)]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
