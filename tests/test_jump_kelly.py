"""
Unit tests for Merton Jump-Diffusion Kelly Engine in GreedBot SDK.
"""

import unittest
import numpy as np
from greedbot.quant.jump_kelly import MertonJumpKellySizer, compute_jump_kelly

class TestMertonJumpKelly(unittest.TestCase):
    def test_compute_jump_kelly_shape_and_bounds(self):
        S = np.array([100.0, 100.0, 100.0])
        O = np.array([2.5, 1.2, 0.5])
        delta = np.array([0.45, 0.25, 0.10])
        gamma = np.array([0.04, 0.03, 0.015])
        theta = np.array([-0.05, -0.03, -0.01])
        sigma = np.array([0.30, 0.35, 0.40])

        f_stars = compute_jump_kelly(
            S=S, O=O, delta=delta, gamma=gamma, theta=theta, sigma=sigma,
            mu=0.05, lambda_jump=1.5, mu_J=0.10, sigma_J=0.20, gamma_penalty=1.5
        )

        self.assertEqual(len(f_stars), 3)
        for f in f_stars:
            self.assertTrue(0.0 <= f <= 1.0)

    def test_merton_jump_kelly_sizer_class(self):
        sizer = MertonJumpKellySizer(mu=0.05, lambda_jump=1.5, mu_J=0.10, sigma_J=0.20, gamma_penalty=1.5)
        res = sizer.size_contract(
            stock_price=100.0,
            option_price=1.20,
            delta=0.25,
            gamma=0.03,
            theta=-0.03,
            iv=0.35,
            capital_usd=20000.0,
            max_risk_cap_pct=0.25
        )

        self.assertIn("f_star", res)
        self.assertIn("target_risk_dollars", res)
        self.assertGreater(res["target_risk_dollars"], 0)
        self.assertLessEqual(res["target_risk_dollars"], 20000.0 * 0.25)

if __name__ == "__main__":
    unittest.main()
