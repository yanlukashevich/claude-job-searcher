r"""Stage 2: talk to server.py over real MCP stdio -- handshake, tools/list, tools/call.

Run:  .venv\Scripts\python.exe tools\mcp_webfile\02_server_test.py

This is exactly what Claude Code's client does, minus the model. If this passes, the only
thing left is `claude mcp add`. Chrome must be open on test_form.html.
"""

import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).resolve().parent
CV = HERE.parents[1] / "src/CV_PDF/CV_Yan_Lukashevich_universal/CV_Yan_Lukashevich.pdf"


def text_of(result):
    return "\n".join(c.text for c in result.content if getattr(c, "text", None))


async def main():
    params = StdioServerParameters(command=sys.executable, args=[str(HERE / "server.py")])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            init = await session.initialize()
            print(f"handshake   {init.server_info.name} (protocol {init.protocol_version})")

            listed = await session.list_tools()
            print(f"tools/list  {len(listed.tools)}")
            for t in listed.tools:
                schema = t.input_schema
                props = schema.get("properties", {})
                required = set(schema.get("required", []))
                args = ", ".join(f"{n}{'' if n in required else '?'}:{p.get('type')}"
                                 for n, p in props.items())
                print(f"   {t.name}({args})")

            print("\ntools/call find_file_inputs")
            r = await session.call_tool("find_file_inputs", {"url_contains": "test_form.html"})
            print(text_of(r))

            print("\ntools/call attach_file  (iframe input, nth=2)")
            r = await session.call_tool("attach_file", {
                "file_path": str(CV), "url_contains": "test_form.html", "nth": 2})
            print(text_of(r))

            print("\ntools/call attach_file  (bad path -> must be an ERROR string, not a crash)")
            r = await session.call_tool("attach_file", {
                "file_path": "C:/nope.pdf", "url_contains": "test_form.html"})
            print(f"isError={r.is_error}  {text_of(r)}")

            print("\ntools/call attach_file  (missing required arg -> schema must reject)")
            r = await session.call_tool("attach_file", {"file_path": str(CV)})
            print(f"isError={r.is_error}  {text_of(r)[:120]}")


if __name__ == "__main__":
    if not CV.is_file():
        sys.exit(f"test CV not found: {CV}")
    asyncio.run(main())
