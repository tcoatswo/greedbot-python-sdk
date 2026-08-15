"""
Unit tests for WebhookDispatcher.
"""

import unittest
from unittest.mock import MagicMock, patch
from greedbot.alerts import WebhookDispatcher
from greedbot.models import OrderIntent, Side, SlotInfo


class TestAlerts(unittest.TestCase):

    @patch("requests.post")
    def test_discord_trade_alert(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 204
        mock_post.return_value = mock_resp

        dispatcher = WebhookDispatcher(discord_url="https://discord.com/api/webhooks/test")
        intent = OrderIntent(ticker="NVDA", side=Side.BUY, dollars=5000.0, limit=120.0)

        results = dispatcher.send_trade_alert(intent, current_price=119.50)
        self.assertTrue(results["discord"])
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_slack_bake_alert(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        dispatcher = WebhookDispatcher(slack_url="https://hooks.slack.com/services/test")
        slot = SlotInfo(
            year=2026,
            refresh_n=140,
            interval="day",
            quote_type="equity",
            effective_at="2026-07-25T00:00:00Z",
            effective_until="2026-07-28T00:00:00Z",
        )
        results = dispatcher.send_bake_alert(hub_name="ideas", slot=slot)
        self.assertTrue(results["slack"])
        mock_post.assert_called_once()


if __name__ == "__main__":
    unittest.main()
