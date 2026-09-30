import unittest
from unittest.mock import patch

import anyio
from mcp import Client

from server import mcp


class McpProtocolTests(unittest.TestCase):
    def test_registered_tool_can_be_called_through_mcp_client(self):
        async def call_tool():
            async with Client(mcp) as client:
                return await client.call_tool("get_staff_count", {})

        with patch("server.staff_count", return_value={"staff_count": 10}):
            result = anyio.run(call_tool)

        self.assertFalse(result.is_error)
        self.assertEqual(result.structured_content, {"staff_count": 10})


if __name__ == "__main__":
    unittest.main()