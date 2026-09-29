"""
Unit tests for extended RiskLimits: short caps, pre-trade order firewall, and drawdown circuit breaker.
"""

import unittest
from greedbot.models import OrderIntent, Side
from greedbot.risk import RiskLimits


class TestRiskLimitsExtended(unittest.TestCase):

    def test_short_fraction_validation(self):
        limits = RiskLimits(
            max_gross_fraction=0.30,
            per_name_cap_fraction=0.10,
            max_short_fraction=0.08,
        )
        limits.validate()

        # Valid targets with short
        valid_targets = {"nvda": 500.0, "tsla": -300.0}
        limits.validate_targets(equity_usd=10000.0, target_dollars=valid_targets)

        # Target violating short cap (1000 > 10000 * 0.08 = 800)
        invalid_short = {"nvda": 500.0, "tsla": -900.0}
        with self.assertRaises(ValueError) as ctx:
            limits.validate_targets(equity_usd=10000.0, target_dollars=invalid_short)
        self.assertIn("short cap violated", str(ctx.exception))

    def test_pre_trade_order_intent_firewall(self):
        limits = RiskLimits(
            max_gross_fraction=0.20,      # $2,000 max gross
            per_name_cap_fraction=0.10,   # $1,000 max per asset
            max_short_fraction=0.05,      # $500 max short
        )
        equity = 10000.0
        current_positions = {"nvda": 0.0, "tsla": 0.0}
        prices = {"nvda": 100.0, "tsla": 200.0}

        # Safe orders: Buy $800 of NVDA
        safe_orders = [OrderIntent(ticker="nvda", side=Side.BUY, dollars=800.0)]
        limits.validate_order_intents(equity, current_positions, prices, safe_orders)

        # Order that breaches per-name cap: Buy $1200 of NVDA (> $1000)
        per_name_breach = [OrderIntent(ticker="nvda", side=Side.BUY, dollars=1200.0)]
        with self.assertRaises(ValueError) as ctx:
            limits.validate_order_intents(equity, current_positions, prices, per_name_breach)
        self.assertIn("per-name cap violated", str(ctx.exception))

        # Order that breaches short cap: Short $600 of TSLA (> $500)
        short_breach = [OrderIntent(ticker="tsla", side=Side.SHORT_SELL, dollars=600.0)]
        with self.assertRaises(ValueError) as ctx:
            limits.validate_order_intents(equity, current_positions, prices, short_breach)
        self.assertIn("short cap violated", str(ctx.exception))

        # Order that breaches gross cap: Buy $1000 of NVDA + Short $400 of TSLA + Buy $800 of AAPL
        gross_breach = [
            OrderIntent(ticker="nvda", side=Side.BUY, dollars=950.0),
            OrderIntent(ticker="tsla", side=Side.BUY, dollars=950.0),
            OrderIntent(ticker="aapl", side=Side.BUY, dollars=950.0),
        ]
        with self.assertRaises(ValueError) as ctx:
            limits.validate_order_intents(
                equity, current_positions, {"nvda": 100.0, "tsla": 200.0, "aapl": 150.0}, gross_breach
            )
        self.assertIn("gross cap violated", str(ctx.exception))

    def test_drawdown_circuit_breaker(self):
        limits = RiskLimits(max_drawdown_stop_pct=15.0)

        # 10% drawdown -> not triggered
        self.assertFalse(limits.is_circuit_breaker_triggered(peak_equity=10000.0, current_equity=9000.0))

        # 15% drawdown -> triggered
        self.assertTrue(limits.is_circuit_breaker_triggered(peak_equity=10000.0, current_equity=8500.0))

        # 20% drawdown -> triggered
        self.assertTrue(limits.is_circuit_breaker_triggered(peak_equity=10000.0, current_equity=8000.0))


if __name__ == "__main__":
    unittest.main()
