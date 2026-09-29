"""
Unit tests for extended PaperBroker methods: portfolio_value, unrealized_pnl, stop triggers, and close_all.
"""

import unittest
from greedbot.broker import PaperBroker
from greedbot.models import OrderIntent, Side


class TestPaperBrokerExtended(unittest.TestCase):

    def test_portfolio_value_and_positions(self):
        broker = PaperBroker(cash_usd=10000.0)
        self.assertTrue(broker.is_flat())
        self.assertEqual(broker.get_position("NVDA"), 0.0)

        # Execute Buy of NVDA ($2000 at $100 -> 20 shares)
        intents = [OrderIntent(ticker="NVDA", side=Side.BUY, dollars=2000.0)]
        fills = broker.execute(intents, prices={"NVDA": 100.0})
        self.assertEqual(len(fills), 1)

        self.assertFalse(broker.is_flat())
        self.assertFalse(broker.is_flat("NVDA"))
        self.assertTrue(broker.is_flat("TSLA"))
        self.assertAlmostEqual(broker.get_position("NVDA"), 20.0)
        self.assertAlmostEqual(broker.cash, 8000.0)

        # Mark to market at $110: 8000 cash + 20 * 110 = 10,200 total equity
        val = broker.portfolio_value(prices={"NVDA": 110.0})
        self.assertAlmostEqual(val, 10200.0)

        # Unrealized PnL: (110 - 100) * 20 = +$200
        pnl = broker.unrealized_pnl(prices={"NVDA": 110.0}, cost_bases={"nvda": 100.0})
        self.assertAlmostEqual(pnl["nvda"], 200.0)

    def test_stop_trigger_checking(self):
        broker = PaperBroker(cash_usd=10000.0)
        # Open Long NVDA (10 shares at $100)
        broker.execute([OrderIntent(ticker="NVDA", side=Side.BUY, dollars=1000.0)], {"NVDA": 100.0})
        # Open Short TSLA (10 shares at $200)
        broker.execute([OrderIntent(ticker="TSLA", side=Side.SHORT_SELL, dollars=2000.0)], {"TSLA": 200.0})

        # No stops breached
        normal_prices = {"NVDA": 102.0, "TSLA": 195.0}
        stops = {"NVDA": 95.0, "TSLA": 210.0}
        triggered = broker.check_stop_triggers(normal_prices, stops)
        self.assertEqual(len(triggered), 0)

        # Breached: NVDA drops to $94 (below 95 stop), TSLA rises to $212 (above 210 stop)
        breach_prices = {"NVDA": 94.0, "TSLA": 212.0}
        triggered = broker.check_stop_triggers(breach_prices, stops)
        self.assertEqual(len(triggered), 2)

        sides = {t.ticker: t.side for t in triggered}
        self.assertEqual(sides["nvda"], Side.SELL)
        self.assertEqual(sides["tsla"], Side.BUY_TO_COVER)

    def test_close_all_intents(self):
        broker = PaperBroker(cash_usd=10000.0)
        broker.execute([
            OrderIntent(ticker="AAPL", side=Side.BUY, dollars=1000.0),
            OrderIntent(ticker="MSFT", side=Side.SHORT_SELL, dollars=1000.0),
        ], {"AAPL": 100.0, "MSFT": 200.0})

        close_intents = broker.close_all_intents(prices={"AAPL": 105.0, "MSFT": 190.0})
        self.assertEqual(len(close_intents), 2)

        # Executing the close intents should flatten the book
        broker.execute(close_intents, prices={"AAPL": 105.0, "MSFT": 190.0})
        self.assertTrue(broker.is_flat())


if __name__ == "__main__":
    unittest.main()
