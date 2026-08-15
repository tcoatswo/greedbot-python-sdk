"""
Unit tests for Signal Generation modules.
"""

import unittest
from greedbot.signals import (
    AvellanedaStoikovMarketMaker,
    BollingerMeanReversion,
    MovingAverageCrossover,
    SignalDirection,
    StatisticalArbitrageSpread,
    TimeSeriesMomentum,
)


class TestSignals(unittest.TestCase):

    def test_moving_average_crossover(self):
        gen = MovingAverageCrossover(short_window=5, long_window=10)
        self.assertEqual(gen.short_window, 5)
        self.assertEqual(gen.long_window, 10)

        # Bullish upward trend
        uptrend = [10.0 + i * 2.0 for i in range(20)]
        sig_bull = gen.generate("NVDA", uptrend)
        self.assertEqual(sig_bull.direction, SignalDirection.LONG)
        self.assertTrue(sig_bull.is_bullish)

        # Bearish downward trend
        downtrend = [50.0 - i * 2.0 for i in range(20)]
        sig_bear = gen.generate("NVDA", downtrend)
        self.assertEqual(sig_bear.direction, SignalDirection.SHORT)
        self.assertTrue(sig_bear.is_bearish)

    def test_timeseries_momentum(self):
        gen = TimeSeriesMomentum(lookback_k=5, require_acceleration=False)
        uptrend = [100.0, 102.0, 104.0, 106.0, 108.0, 112.0, 115.0]
        sig = gen.generate("AAPL", uptrend)
        self.assertEqual(sig.direction, SignalDirection.LONG)
        self.assertTrue(sig.indicator_values["momentum_pct"] > 0)

    def test_bollinger_mean_reversion(self):
        gen = BollingerMeanReversion(window=10, z_threshold=2.0)
        flat_then_spike = [100.0] * 10
        flat_then_spike.append(120.0)  # Massive spike above upper band
        sig_overbought = gen.generate("SPY", flat_then_spike)
        self.assertEqual(sig_overbought.direction, SignalDirection.SHORT)
        self.assertTrue(sig_overbought.indicator_values["z_score"] > 2.0)

        flat_then_drop = [100.0] * 10
        flat_then_drop.append(80.0)  # Massive drop below lower band
        sig_oversold = gen.generate("SPY", flat_then_drop)
        self.assertEqual(sig_oversold.direction, SignalDirection.LONG)
        self.assertTrue(sig_oversold.indicator_values["z_score"] < -2.0)

    def test_statistical_arbitrage_pairs(self):
        gen = StatisticalArbitrageSpread(ticker_a="SPY", ticker_b="QQQ", lookback_window=10, z_threshold=1.5)
        # Synthetic cointegrated series where A diverges upward at the end
        prices_b = [100.0 + i for i in range(15)]
        prices_a = [100.0 + i for i in range(15)]
        prices_a[-1] = 140.0  # Asset A spiked

        sig_a, sig_b = gen.generate(prices_a, prices_b)
        self.assertEqual(sig_a.direction, SignalDirection.SHORT)
        self.assertEqual(sig_b.direction, SignalDirection.LONG)

    def test_avellaneda_stoikov_market_maker(self):
        mm = AvellanedaStoikovMarketMaker(gamma=0.1, k=1.5, precision=4)

        # 1. Neutral inventory
        q_neutral = mm.calculate_quotes(mid_price=100.0, inventory_q=0.0, volatility_sigma=0.02)
        self.assertAlmostEqual(q_neutral["reservation_price"], 100.0)
        self.assertTrue(q_neutral["bid_price"] < 100.0)
        self.assertTrue(q_neutral["ask_price"] > 100.0)

        # 2. Long inventory skew (reservation price must drop)
        q_long = mm.calculate_quotes(mid_price=100.0, inventory_q=500.0, volatility_sigma=0.02)
        self.assertTrue(q_long["reservation_price"] < 100.0)
        self.assertTrue(q_long["bid_price"] < q_neutral["bid_price"])
        self.assertTrue(q_long["ask_price"] < q_neutral["ask_price"])

        # 3. Short inventory skew (reservation price must rise)
        q_short = mm.calculate_quotes(mid_price=100.0, inventory_q=-500.0, volatility_sigma=0.02)
        self.assertTrue(q_short["reservation_price"] > 100.0)
        self.assertTrue(q_short["bid_price"] > q_neutral["bid_price"])
        self.assertTrue(q_short["ask_price"] > q_neutral["ask_price"])


if __name__ == "__main__":
    unittest.main()
