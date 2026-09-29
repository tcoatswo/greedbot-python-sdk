"""
Unit tests for extended BacktestEngine and PerformanceMetrics features:
- Short position execution and covering P&L accounting
- VaR and CVaR calculations
- Benchmark comparison (Alpha, Beta, Information Ratio)
- Drawdown series
"""

import unittest
from greedbot.backtest import BacktestEngine, PerformanceMetrics
from greedbot.signals import Signal, SignalDirection, SignalGenerator


class StaticSignal(SignalGenerator):
    def __init__(self, direction: SignalDirection):
        self._dir = direction

    @property
    def name(self) -> str:
        return "static_signal"

    def generate(self, ticker: str, prices):
        return Signal(ticker=ticker, direction=self._dir)


class AlternatingSignal(SignalGenerator):
    """Generates SHORT for first half, then LONG for second half to test covering."""
    def __init__(self, switch_at: int):
        self.switch_at = switch_at
        self.call_count = 0

    @property
    def name(self) -> str:
        return "alternating_signal"

    def generate(self, ticker: str, prices):
        self.call_count += 1
        if self.call_count < self.switch_at:
            return Signal(ticker=ticker, direction=SignalDirection.SHORT)
        else:
            return Signal(ticker=ticker, direction=SignalDirection.FLAT)


class TestBacktestExtended(unittest.TestCase):

    def test_short_accounting_no_double_counting(self):
        engine = BacktestEngine(
            initial_capital=10000.0,
            slippage_bps=0.0,
            fee_per_trade=0.0,
        )
        # 15 bars: starts at 100, drops to 80 (profitable short), then stays flat
        # Price drops from 100 to 80
        prices = [100.0] * 5 + [90.0, 85.0, 80.0, 80.0, 80.0, 80.0]
        sig = AlternatingSignal(switch_at=2)

        res = engine.run_signal_series(
            ticker="TSLA",
            prices=prices,
            signal_generator=sig,
            min_warmup_bars=3,
            allocation_fraction=0.50,
        )

        # Since it was shorted at ~100 and closed around ~85, profit should be positive,
        # but final equity MUST be reasonable (e.g. around ~$10,750, NOT double-counted $15,000+)
        self.assertTrue(res.metrics.final_equity > 10000.0)
        self.assertTrue(res.metrics.final_equity < 12000.0)
        self.assertAlmostEqual(res.metrics.final_equity, 10000.0 + res.metrics.net_profit, places=2)

    def test_var_and_cvar_metrics(self):
        # Equity curve with some losses
        equity_curve = [10000.0, 9900.0, 9700.0, 9800.0, 9600.0, 9900.0, 10200.0]
        metrics = PerformanceMetrics.calculate(
            equity_curve=equity_curve,
            trades=[{"type": "SELL", "pnl": 200.0}],
        )

        self.assertTrue(metrics.var_95_pct >= 0.0)
        self.assertTrue(metrics.var_99_pct >= metrics.var_95_pct)
        self.assertTrue(metrics.cvar_95_pct >= metrics.var_95_pct)
        self.assertTrue(len(metrics.drawdown_series) == len(equity_curve))

    def test_benchmark_relative_metrics(self):
        strat_equity = [10000.0, 10200.0, 10400.0, 10600.0, 10800.0]
        bench_prices = [100.0, 101.0, 102.0, 102.5, 103.0]

        metrics = PerformanceMetrics.calculate(
            equity_curve=strat_equity,
            trades=[{"type": "SELL", "pnl": 800.0}],
            benchmark_prices=bench_prices,
        )

        self.assertIsNotNone(metrics.benchmark_total_return_pct)
        self.assertAlmostEqual(metrics.benchmark_total_return_pct, 3.0, places=1)
        self.assertIsNotNone(metrics.beta)
        self.assertIsNotNone(metrics.alpha)
        self.assertIsNotNone(metrics.information_ratio)
        self.assertTrue(metrics.alpha > 0)  # Strategy beat benchmark return (8% vs 3%)

        sheet = metrics.generate_tear_sheet()
        self.assertIn("Benchmark Total Return", sheet)
        self.assertIn("Beta", sheet)
        self.assertIn("Jensen's Alpha", sheet)


if __name__ == "__main__":
    unittest.main()
