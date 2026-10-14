"""MCP Client có Authentication — kết nối tới auth_server.py qua HTTP.

Client tạo HTTP client bằng create_mcp_http_client(headers=...) của MCP SDK
(đúng thư viện HTTP mà SDK dùng bên dưới, kèm timeout khuyến nghị). Header
Authorization được gắn vào mọi request HTTP (POST, GET, DELETE) tới server.

Cách chạy (cần auth_server.py đang chạy ở terminal khác):
    cd 03-production
    python auth_server.py            # terminal 1
    python auth_client.py            # terminal 2
"""

from __future__ import annotations

import asyncio

import os

from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

SERVER_URL = "http://localhost:8000/mcp"
TOKEN = os.environ.get("MCP_AUTH_TOKEN", "dev-token-abc123")


async def main() -> None:
    http_client = create_mcp_http_client(
        headers={"Authorization": f"Bearer {TOKEN}"},
    )

    async with http_client:
        async with streamable_http_client(SERVER_URL, http_client=http_client) as (
            read,
            write,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()

                tools = await session.list_tools()
                print("Tools (có auth):")
                for t in tools.tools:
                    print(f"  - {t.name}: {t.description}")

                result = await session.call_tool("get_weather", {"city": "Hanoi"})
                print(f"\nKết quả: {result.content[0].text}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except BaseException as exc:
        # MCP transports use task groups, so an HTTP 401 may be wrapped in an
        # ExceptionGroup.  Keep the negative-auth demo readable while still
        # returning a non-zero exit code.
        current = exc
        while isinstance(current, BaseExceptionGroup) and current.exceptions:
            current = current.exceptions[0]
        print(f"Kết nối bị từ chối: {current}")
        raise SystemExit(1)
