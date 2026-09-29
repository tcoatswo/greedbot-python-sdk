"""
Unit tests for MACDCrossover signal generator.
"""

import unittest
from greedbot.signals import MACDCrossover, SignalDirection


class TestMACDSignal(unittest.TestCase):

    def test_macd_initialization_and_validation(self):
        gen = MACDCrossover(fast_period=12, slow_period=26, signal_period=9)
        self.assertEqual(gen.fast_period, 12)
        self.assertEqual(gen.slow_period, 26)
        self.assertEqual(gen.signal_period, 9)

        # fast_period must be < slow_period
        with self.assertRaises(ValueError):
            MACDCrossover(fast_period=26, slow_period=12)

        with self.assertRaises(ValueError):
            MACDCrossover(signal_period=1)

    def test_macd_calculation_and_crossover_signals(self):
        gen = MACDCrossover(fast_period=5, slow_period=10, signal_period=4)

        # Downtrend followed by sharp upward reversal creates bullish cross
        reversal_prices = [100.0 - i * 1.5 for i in range(25)] + [100.0 - 37.5 + i * 4.0 for i in range(15)]
        sig = gen.generate("AAPL", reversal_prices)

        self.assertIn("macd", sig.indicator_values)
        self.assertIn("signal_line", sig.indicator_values)
        self.assertIn("histogram", sig.indicator_values)
        self.assertEqual(sig.ticker, "AAPL")
        self.assertEqual(sig.direction, SignalDirection.LONG)
        self.assertTrue(sig.is_bullish)

    def test_macd_bearish_crossover(self):
        gen = MACDCrossover(fast_period=5, slow_period=10, signal_period=4)

        # Uptrend followed by sharp drop creates bearish cross
        drop_prices = [50.0 + i * 2.0 for i in range(25)] + [100.0 - i * 5.0 for i in range(15)]
        sig = gen.generate("TSLA", drop_prices)

        self.assertEqual(sig.direction, SignalDirection.SHORT)
        self.assertTrue(sig.is_bearish)

    def test_macd_insufficient_history(self):
        gen = MACDCrossover(fast_period=12, slow_period=26, signal_period=9)
        with self.assertRaises(ValueError):
            gen.calculate_macd([100.0] * 30)


if __name__ == "__main__":
    unittest.main()
