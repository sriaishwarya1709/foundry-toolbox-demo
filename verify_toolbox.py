"""List what the toolbox MCP endpoint exposes and try a few tool_search queries."""

import asyncio
import os
import sys

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import create_mcp_http_client, streamable_http_client

load_dotenv()
ENDPOINT = os.environ["PROJECT_ENDPOINT"].rstrip("/")
URL = f"{ENDPOINT}/toolboxes/{os.environ['TOOLBOX_NAME']}/mcp?api-version=v1"
QUERIES = sys.argv[1:] or ["weather", "currency exchange", "travel advisory", "public holidays"]


async def main() -> None:
    token = DefaultAzureCredential().get_token("https://ai.azure.com/.default").token
    http = create_mcp_http_client(headers={"Authorization": f"Bearer {token}"})
    async with http, streamable_http_client(URL, http_client=http) as streams:
        read, write = streams[0], streams[1]
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            print(f"tools/list -> {[t.name for t in listed.tools]}")
            for query in QUERIES:
                result = await session.call_tool("tool_search", {"query": query})
                text = " ".join(c.text for c in result.content if c.type == "text")
                print(f"\ntool_search('{query}') error={result.is_error}\n  {text[:400]}")


if __name__ == "__main__":
    asyncio.run(main())
