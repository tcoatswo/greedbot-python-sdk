"""
Unit tests for RSIMeanReversion signal generator.
"""

import unittest
from greedbot.signals import RSIMeanReversion, SignalDirection


class TestRSISignal(unittest.TestCase):

    def test_rsi_initialization_and_validation(self):
        gen = RSIMeanReversion(period=14, oversold_threshold=30.0, overbought_threshold=70.0)
        self.assertEqual(gen.period, 14)
        self.assertEqual(gen.oversold_threshold, 30.0)
        self.assertEqual(gen.overbought_threshold, 70.0)

        # Invalid period
        with self.assertRaises(ValueError):
            RSIMeanReversion(period=1)

        # Invalid threshold ordering
        with self.assertRaises(ValueError):
            RSIMeanReversion(oversold_threshold=80.0, overbought_threshold=20.0)

    def test_rsi_calculation_all_gains(self):
        gen = RSIMeanReversion(period=5)
        strictly_rising = [100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0]
        stats = gen.calculate_rsi(strictly_rising)
        self.assertEqual(stats["rsi"], 100.0)
        self.assertEqual(stats["avg_loss"], 0.0)

    def test_rsi_signals_oversold_and_overbought(self):
        gen = RSIMeanReversion(period=14, oversold_threshold=30.0, overbought_threshold=70.0)

        # Sharp decline produces oversold (RSI < 30) -> LONG
        declining_prices = [150.0 - (i * 3.0) for i in range(25)]
        sig_long = gen.generate("NVDA", declining_prices)
        self.assertEqual(sig_long.direction, SignalDirection.LONG)
        self.assertTrue(sig_long.is_bullish)
        self.assertTrue(sig_long.indicator_values["rsi"] < 30.0)
        self.assertTrue(sig_long.strength >= 0.5)

        # Sharp rally produces overbought (RSI > 70) -> SHORT
        rallying_prices = [50.0 + (i * 3.5) for i in range(25)]
        sig_short = gen.generate("NVDA", rallying_prices)
        self.assertEqual(sig_short.direction, SignalDirection.SHORT)
        self.assertTrue(sig_short.is_bearish)
        self.assertTrue(sig_short.indicator_values["rsi"] > 70.0)

        # Flat / sideways produces FLAT signal
        flat_prices = [100.0 + ((i % 2) * 0.1) for i in range(25)]
        sig_flat = gen.generate("NVDA", flat_prices)
        self.assertEqual(sig_flat.direction, SignalDirection.FLAT)
        self.assertTrue(sig_flat.is_flat)

    def test_rsi_insufficient_history(self):
        gen = RSIMeanReversion(period=14)
        with self.assertRaises(ValueError):
            gen.calculate_rsi([100.0, 101.0, 102.0])


if __name__ == "__main__":
    unittest.main()
