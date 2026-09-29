"""
Unit tests for RiskParityOptimizer (Inverse Volatility & Equal Risk Contribution).
"""

import unittest
import numpy as np
from greedbot.quant import RiskParityOptimizer


class TestRiskParityOptimizer(unittest.TestCase):

    def setUp(self):
        self.optimizer = RiskParityOptimizer(max_iterations=100, tolerance=1e-6)
        self.tickers = ["SPY", "TLT", "GLD"]

        # Synthetic returns with distinct volatilities:
        # SPY: vol ~ 0.015, TLT: vol ~ 0.008, GLD: vol ~ 0.010
        np.random.seed(42)
        n_days = 250
        r_spy = np.random.normal(0.0004, 0.015, n_days)
        r_tlt = np.random.normal(0.0002, 0.008, n_days)
        r_gld = np.random.normal(0.0003, 0.010, n_days)
        self.returns = np.column_stack([r_spy, r_tlt, r_gld])

    def test_inverse_volatility_optimization(self):
        res = self.optimizer.optimize_inverse_volatility(self.returns, self.tickers)
        weights = res["weights"]

        # Sum of weights should be 1.0
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=3)

        # Asset with lowest volatility (TLT) must have highest allocation in inverse-vol
        self.assertTrue(weights["TLT"] > weights["SPY"])
        self.assertTrue(weights["TLT"] > weights["GLD"])
        self.assertEqual(res["strategy"], "INVERSE_VOLATILITY")
        self.assertTrue(res["annualized_volatility"] > 0)

    def test_equal_risk_contribution_optimization(self):
        res = self.optimizer.optimize_equal_risk_contribution(self.returns, self.tickers)
        weights = res["weights"]
        rc_pct = res["risk_contributions_pct"]

        self.assertAlmostEqual(sum(weights.values()), 1.0, places=3)
        self.assertEqual(res["strategy"], "EQUAL_RISK_CONTRIBUTION")

        # In true ERC, each of the 3 assets should contribute ~ 33.3% of total risk
        for ticker in self.tickers:
            self.assertAlmostEqual(rc_pct[ticker], 100.0 / 3.0, delta=1.5)

    def test_dimension_mismatch_raises(self):
        with self.assertRaises(ValueError):
            self.optimizer.optimize_inverse_volatility(self.returns, ["SPY", "TLT"])  # 2 tickers for 3 assets

        with self.assertRaises(ValueError):
            self.optimizer.optimize_equal_risk_contribution(self.returns, ["SPY", "TLT"])


if __name__ == "__main__":
    unittest.main()
