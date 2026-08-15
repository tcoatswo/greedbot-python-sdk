"""
Unit tests for the new quantitative strategies:
Trend Following, Mean Reversion, Stat Arb Pairs, Market Making, and Markowitz.
"""

import unittest
from greedbot.models import Side
from greedbot.strategies import (
    MarketMakerStrategy,
    MarkowitzAllocationStrategy,
    MeanReversionStrategy,
    StatArbPairsStrategy,
    TrendFollowingStrategy,
)


class TestNewStrategies(unittest.TestCase):

    def test_trend_following_strategy(self):
        strat = TrendFollowingStrategy(ticker="NVDA", short_window=5, long_window=10)
        uptrend = [100.0 + i * 2.0 for i in range(20)]
        res = strat.run(capital_usd=10000.0, prices=uptrend)
        self.assertIn("nvda", res.target_dollars)
        self.assertTrue(res.target_dollars["nvda"] > 0)
        self.assertEqual(len(res.intents), 1)
        self.assertEqual(res.intents[0].side, Side.BUY)

    def test_mean_reversion_strategy(self):
        strat = MeanReversionStrategy(ticker="SPY", window=10, z_threshold=2.0)
        oversold = [100.0] * 10 + [75.0]
        res = strat.run(capital_usd=10000.0, prices=oversold)
        self.assertIn("spy", res.target_dollars)
        self.assertTrue(res.target_dollars["spy"] > 0)
        self.assertEqual(res.intents[0].side, Side.BUY)

    def test_stat_arb_pairs_strategy(self):
        strat = StatArbPairsStrategy(ticker_a="SPY", ticker_b="QQQ", lookback_window=10, z_threshold=1.5)
        prices_b = [100.0 + i for i in range(15)]
        prices_a = [100.0 + i for i in range(15)]
        prices_a[-1] = 140.0  # Asset A spikes -> Short A, Long B

        res = strat.run(capital_usd=10000.0, prices_a=prices_a, prices_b=prices_b)
        self.assertEqual(len(res.intents), 2)
        sides = {i.ticker: i.side for i in res.intents}
        self.assertEqual(sides["spy"], Side.SHORT_SELL)
        self.assertEqual(sides["qqq"], Side.BUY)

    def test_market_maker_strategy(self):
        strat = MarketMakerStrategy(ticker="NVDA", quote_size_usd=1000.0)
        res = strat.run(capital_usd=10000.0, mid_price=100.0, inventory_q=0.0, volatility_sigma=0.02)
        self.assertEqual(len(res.intents), 2)
        sides = [i.side for i in res.intents]
        self.assertIn(Side.BUY, sides)
        self.assertIn(Side.SHORT_SELL, sides)
        self.assertTrue(res.intents[0].limit < 100.0)  # Bid limit < mid
        self.assertTrue(res.intents[1].limit > 100.0)  # Ask limit > mid

    def test_markowitz_allocation_strategy(self):
        strat = MarkowitzAllocationStrategy(assets=["SPY", "TLT", "GLD"], mode="tangency")
        res = strat.run(capital_usd=50000.0)
        self.assertEqual(len(res.target_dollars), 3)
        total_alloc = sum(res.target_dollars.values())
        self.assertAlmostEqual(total_alloc, 50000.0, delta=10.0)


if __name__ == "__main__":
    unittest.main()
