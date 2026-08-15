"""
Unit tests for GreedBot HTTP Client, Auth, Retries, and Spend Caps.
"""

import unittest
from unittest.mock import MagicMock, patch
import requests
from greedbot.client import (
    GreedBotClient,
    GreedBotAPIError,
    GreedBotSpendCapError,
    DEFAULT_BASE_URL,
)


class TestGreedBotClient(unittest.TestCase):

    def test_client_initialization_and_redaction(self):
        client = GreedBotClient(api_key="secret_key_12345")
        self.assertEqual(client.api_key, "secret_key_12345")
        self.assertEqual(client.base_url, DEFAULT_BASE_URL)

        # Ensure key is not leaked in __repr__
        repr_str = repr(client)
        self.assertNotIn("secret_key_12345", repr_str)
        self.assertIn("<redacted>", repr_str)

        # Ensure x-api-key header is set
        self.assertEqual(client.session.headers.get("x-api-key"), "secret_key_12345")

    def test_client_from_env(self):
        with patch.dict("os.environ", {"GREEDBOT_API_KEY": "env_key_abc", "GREEDBOT_API_BASE": "https://custom.greedbot.com"}):
            client = GreedBotClient.from_env()
            self.assertEqual(client.api_key, "env_key_abc")
            self.assertEqual(client.base_url, "https://custom.greedbot.com")

    def test_client_from_env_missing_raises(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                GreedBotClient.from_env()

    @patch.object(requests.Session, "request")
    def test_ping_endpoint(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = "PONG"
        mock_request.return_value = mock_resp

        client = GreedBotClient(api_key="test")
        res = client.ping()
        self.assertEqual(res, "PONG")

    @patch.object(requests.Session, "request")
    def test_spend_cap_error_402(self, mock_request):
        mock_resp = MagicMock()
        mock_resp.status_code = 402
        mock_resp.text = "Monthly spend cap exceeded"
        mock_request.return_value = mock_resp

        client = GreedBotClient(api_key="test")
        with self.assertRaises(GreedBotSpendCapError):
            client.get_targets(["NVDA"])

    @patch.object(requests.Session, "request")
    def test_rate_limit_429_retries(self, mock_request):
        # 429 once with Retry-After: 0, then 200
        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.headers = {"Retry-After": "0"}

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {"id": "receipt_123"}

        mock_request.side_effect = [resp_429, resp_200]

        client = GreedBotClient(api_key="test")
        resp = client._request_with_retry("POST", "/api/v1/targets/receipt", json={})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(mock_request.call_count, 2)


if __name__ == "__main__":
    unittest.main()
