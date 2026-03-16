"""Allow running as: python -m atlassian_mcp"""

from atlassian_mcp.server import main

if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
