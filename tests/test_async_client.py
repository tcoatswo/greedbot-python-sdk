"""
Unit tests for AsyncGreedBotClient.
"""

import unittest
from unittest.mock import MagicMock, patch
from greedbot.async_client import AsyncGreedBotClient


class TestAsyncClient(unittest.IsolatedAsyncioTestCase):

    async def test_async_client_init_and_redaction(self):
        client = AsyncGreedBotClient(api_key="secret_key_999")
        self.assertEqual(client.api_key, "secret_key_999")
        repr_str = repr(client)
        self.assertNotIn("secret_key_999", repr_str)
        self.assertIn("<redacted>", repr_str)

    @patch("greedbot.client.GreedBotClient.ping")
    async def test_async_ping(self, mock_ping):
        mock_ping.return_value = "PONG"
        client = AsyncGreedBotClient(api_key="test")
        res = await client.ping()
        self.assertEqual(res, "PONG")

    @patch("greedbot.client.GreedBotClient.get_hub_earnings_expected_move")
    async def test_batch_scan_expected_moves(self, mock_exp):
        mock_exp.side_effect = [
            {"expected_move_pct": 5.0},
            {"expected_move_pct": 8.0},
        ]
        client = AsyncGreedBotClient(api_key="test")
        res = await client.batch_scan_expected_moves(["NVDA", "TSLA"])
        self.assertEqual(len(res), 2)
        self.assertAlmostEqual(res["NVDA"]["expected_move_pct"], 5.0)
        self.assertAlmostEqual(res["TSLA"]["expected_move_pct"], 8.0)


if __name__ == "__main__":
    unittest.main()
