"""
Unit tests for Trade Journal synchronization and plan management.
"""

import unittest
from unittest.mock import MagicMock
from greedbot.client import GreedBotClient
from greedbot.journal import TradeJournal
from greedbot.models import BotRunResult, OrderIntent, Side


class TestTradeJournal(unittest.TestCase):

    def setUp(self):
        self.mock_client = MagicMock(spec=GreedBotClient)
        self.journal = TradeJournal(self.mock_client)

    def test_record_plan(self):
        self.mock_client.create_log.return_value = {"id": "plan_abc123"}
        plan_id = self.journal.record_plan(
            ticker="NVDA",
            direction="long",
            entry=120.0,
            stop=110.0,
            target=135.0,
        )
        self.assertEqual(plan_id, "plan_abc123")
        self.mock_client.create_log.assert_called_once()

    def test_open_close_cancel_trade(self):
        self.mock_client.open_log.return_value = {"status": "open"}
        self.mock_client.close_log.return_value = {"status": "closed"}
        self.mock_client.cancel_log.return_value = {"status": "canceled"}

        open_res = self.journal.open_trade("plan_1", entry_price=120.5)
        self.assertEqual(open_res["status"], "open")

        close_res = self.journal.close_trade("plan_1", exit_price=135.0, net_pnl=1450.0)
        self.assertEqual(close_res["status"], "closed")

        cancel_res = self.journal.cancel_trade("plan_2")
        self.assertEqual(cancel_res["status"], "canceled")

    def test_sync_bot_result(self):
        self.mock_client.create_log.side_effect = [{"id": "p1"}, {"id": "p2"}]
        bot_result = BotRunResult(
            trades=[],
            summary={},
            target_dollars={"nvda": 5000.0, "tsla": 5000.0},
            intents=[
                OrderIntent(ticker="nvda", side=Side.BUY, dollars=5000.0),
                OrderIntent(ticker="tsla", side=Side.SHORT_SELL, dollars=5000.0),
            ]
        )
        plan_ids = self.journal.sync_bot_result(bot_result)
        self.assertEqual(plan_ids, ["p1", "p2"])
        self.assertEqual(self.mock_client.create_log.call_count, 2)


if __name__ == "__main__":
    unittest.main()
