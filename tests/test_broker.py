"""
Unit tests for PaperBroker execution, batch atomicity, limits, and position lifecycle.
"""

import unittest
from greedbot.broker import PaperBroker
from greedbot.models import OrderIntent, Side


class TestPaperBroker(unittest.TestCase):

    def test_market_buys_and_limits(self):
        broker = PaperBroker(cash_usd=10000.0, fee_per_fill=1.0)
        prices = {"nvda": 100.0}

        intents = [
            OrderIntent(ticker="nvda", side=Side.BUY, dollars=1000.0),  # Marketable -> fills
            OrderIntent(ticker="nvda", side=Side.BUY, dollars=1000.0, limit=90.0),  # Limit below price -> rests
        ]
        fills = broker.execute(intents, prices=prices)
        self.assertEqual(len(fills), 1)
        self.assertAlmostEqual(fills[0].quantity, 10.0)
        self.assertAlmostEqual(broker.cash, 8999.0)  # $10,000 - $1,000 - $1 fee
        self.assertAlmostEqual(broker.positions["nvda"], 10.0)

    def test_sell_limit_at_or_better(self):
        broker = PaperBroker(cash_usd=10000.0, fee_per_fill=0.0)
        prices = {"nvda": 100.0}

        # First buy 10 shares
        broker.execute([OrderIntent(ticker="nvda", side=Side.BUY, dollars=1000.0)], prices=prices)

        # Sell with limit 100.0 (matches price)
        fills = broker.execute(
            [OrderIntent(ticker="nvda", side=Side.SELL, dollars=500.0, limit=100.0)],
            prices=prices,
        )
        self.assertEqual(len(fills), 1)
        self.assertAlmostEqual(broker.positions["nvda"], 5.0)

    def test_short_selling_and_covering(self):
        broker = PaperBroker(cash_usd=10000.0, fee_per_fill=0.0)
        prices = {"xle": 50.0}

        # Open short 10 shares ($500)
        fills = broker.execute([OrderIntent(ticker="xle", side=Side.SHORT_SELL, dollars=500.0)], prices=prices)
        self.assertEqual(len(fills), 1)
        self.assertAlmostEqual(broker.positions["xle"], -10.0)
        self.assertAlmostEqual(broker.cash, 10500.0)

        # Cover short
        broker.execute([OrderIntent(ticker="xle", side=Side.BUY_TO_COVER, dollars=500.0)], prices=prices)
        self.assertNotIn("xle", broker.positions)
        self.assertAlmostEqual(broker.cash, 10000.0)

    def test_over_close_rejection_and_batch_atomicity(self):
        broker = PaperBroker(cash_usd=10000.0, fee_per_fill=0.0)
        prices = {"nvda": 100.0}

        # Long 10 shares ($1,000)
        broker.execute([OrderIntent(ticker="nvda", side=Side.BUY, dollars=1000.0)], prices=prices)

        # Attempt to sell 15 shares ($1,500) against 10 shares held -> must reject
        with self.assertRaises(ValueError) as ctx:
            broker.execute([OrderIntent(ticker="nvda", side=Side.SELL, dollars=1500.0)], prices=prices)
        self.assertIn("Sell is reduce/close-only", str(ctx.exception))

        # Ensure state is unchanged (atomic rollback)
        self.assertAlmostEqual(broker.positions["nvda"], 10.0)
        self.assertAlmostEqual(broker.cash, 9000.0)

    def test_cover_while_flat_rejected(self):
        broker = PaperBroker(cash_usd=10000.0, fee_per_fill=0.0)
        prices = {"nvda": 100.0}

        # Attempt to cover while having no short position
        with self.assertRaises(ValueError) as ctx:
            broker.execute([OrderIntent(ticker="nvda", side=Side.BUY_TO_COVER, dollars=500.0)], prices=prices)
        self.assertIn("BuyToCover is reduce/close-only", str(ctx.exception))

    def test_overdraft_rejection_and_atomic_rollback(self):
        broker = PaperBroker(cash_usd=100.0, fee_per_fill=1.0)
        prices = {"nvda": 10.0, "amd": 10.0}

        # First intent would pass ($50), second would overdraw ($60 + $2 fees > $100)
        batch = [
            OrderIntent(ticker="nvda", side=Side.BUY, dollars=50.0),
            OrderIntent(ticker="amd", side=Side.BUY, dollars=60.0),
        ]
        with self.assertRaises(ValueError) as ctx:
            broker.execute(batch, prices=prices)
        self.assertIn("insufficient cash", str(ctx.exception))

        # Ensure complete rollback
        self.assertAlmostEqual(broker.cash, 100.0)
        self.assertEqual(len(broker.positions), 0)


if __name__ == "__main__":
    unittest.main()
