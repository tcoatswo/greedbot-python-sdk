"""
Unit tests for BacktestEngine and PerformanceMetrics.
"""

import unittest
from greedbot.backtest import BacktestEngine, PerformanceMetrics
from greedbot.signals import MovingAverageCrossover


class TestBacktest(unittest.TestCase):

    def test_performance_metrics_calculation(self):
        equity_curve = [10000.0, 10200.0, 10500.0, 10300.0, 10800.0]
        trades = [
            {"type": "SELL", "pnl": 200.0},
            {"type": "SELL", "pnl": 300.0},
            {"type": "SELL", "pnl": -200.0},
            {"type": "SELL", "pnl": 500.0},
        ]
        metrics = PerformanceMetrics.calculate(equity_curve, trades, bars_per_year=252)

        self.assertEqual(metrics.initial_capital, 10000.0)
        self.assertEqual(metrics.final_equity, 10800.0)
        self.assertAlmostEqual(metrics.net_profit, 800.0)
        self.assertAlmostEqual(metrics.total_return_pct, 8.0)
        self.assertEqual(metrics.total_trades, 4)
        self.assertEqual(metrics.winning_trades, 3)
        self.assertEqual(metrics.losing_trades, 1)
        self.assertAlmostEqual(metrics.win_rate_pct, 75.0)
        self.assertTrue(metrics.profit_factor > 1.0)
        self.assertTrue(len(metrics.generate_tear_sheet()) > 0)

    def test_backtest_engine_execution(self):
        engine = BacktestEngine(
            initial_capital=10000.0,
            slippage_bps=0.0,
            fee_per_trade=0.0,
        )
        gen = MovingAverageCrossover(short_window=5, long_window=10)
        uptrend_prices = [100.0 + i * 2.0 for i in range(30)]

        res = engine.run_signal_series(
            ticker="NVDA",
            prices=uptrend_prices,
            signal_generator=gen,
            min_warmup_bars=10,
            allocation_fraction=0.50,
        )

        self.assertTrue(len(res.equity_curve) > 0)
        self.assertTrue(res.metrics.final_equity > res.metrics.initial_capital)
        self.assertTrue(len(res.trades) > 0)


if __name__ == "__main__":
    unittest.main()
