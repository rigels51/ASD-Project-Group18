import unittest

import anyio
from mcp import Client

from rag_server import mcp


class RagMcpServerTests(unittest.TestCase):
    def test_rag_mcp_exposes_three_lab_tools(self):
        async def list_tools():
            async with Client(mcp) as client:
                return await client.list_tools()

        result = anyio.run(list_tools)
        names = {tool.name for tool in result.tools}

        self.assertEqual(names, {"refresh_corpus", "retrieve_context", "answer_question"})


if __name__ == "__main__":
    unittest.main()