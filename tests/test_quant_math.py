"""
Unit tests for Quantitative Risk & Portfolio Math (Kelly, Markowitz).
"""

import unittest
import numpy as np
from greedbot.quant import KellyPositionSizer, MeanVarianceOptimizer


class TestQuantMath(unittest.TestCase):

    def test_discrete_kelly_formula(self):
        # p = 0.6, b = 2.0 -> f* = (0.6 * 3 - 1) / 2 = 0.8 / 2 = 0.40
        f_star = KellyPositionSizer.discrete_kelly(win_rate=0.60, win_loss_ratio=2.0)
        self.assertAlmostEqual(f_star, 0.40)

        # Negative edge case: p = 0.4, b = 1.0 -> f* = (0.4 * 2 - 1) / 1 = -0.20
        f_star_neg = KellyPositionSizer.discrete_kelly(win_rate=0.40, win_loss_ratio=1.0)
        self.assertAlmostEqual(f_star_neg, -0.20)

    def test_kelly_position_sizing(self):
        sizer = KellyPositionSizer(default_fraction=0.50, max_allocation=0.25)
        res = sizer.size_position(
            capital_usd=10000.0,
            win_rate=0.60,
            win_loss_ratio=2.0,
        )
        # f* = 0.40, Half-Kelly = 0.20 -> $2,000
        self.assertTrue(res["has_positive_edge"])
        self.assertAlmostEqual(res["applied_kelly_fraction"], 0.20)
        self.assertAlmostEqual(res["target_dollars"], 2000.0)

    def test_continuous_kelly(self):
        # mu = 0.12, r = 0.04, sigma = 0.20 -> f* = (0.12 - 0.04) / 0.04 = 2.0
        f_cont = KellyPositionSizer.continuous_kelly(expected_return=0.12, volatility=0.20, risk_free_rate=0.04)
        self.assertAlmostEqual(f_cont, 2.0)

    def test_markowitz_optimizer_gmv_and_tangency(self):
        optimizer = MeanVarianceOptimizer(risk_free_rate=0.04)
        tickers = ["SPY", "TLT", "GLD"]

        # Synthetic returns
        np.random.seed(42)
        returns = np.random.normal(0.0005, 0.01, size=(50, 3))

        # 1. GMV Optimization
        gmv = optimizer.optimize_gmv(returns, tickers, long_only=True)
        weights_gmv = list(gmv["weights"].values())
        self.assertAlmostEqual(sum(weights_gmv), 1.0, places=3)
        self.assertTrue(all(w >= 0.0 for w in weights_gmv))

        # 2. Tangency Optimization
        tan = optimizer.optimize_tangency(returns, tickers, long_only=True)
        weights_tan = list(tan["weights"].values())
        self.assertAlmostEqual(sum(weights_tan), 1.0, places=3)
        self.assertTrue(all(w >= 0.0 for w in weights_tan))


if __name__ == "__main__":
    unittest.main()
