"""
Unit tests for RiskLimits and portfolio validation.
"""

import math
import unittest
from greedbot.risk import RiskLimits


class TestRiskLimits(unittest.TestCase):

    def test_valid_limits_and_targets(self):
        limits = RiskLimits(max_gross_fraction=0.20, per_name_cap_fraction=0.05)
        limits.validate()

        equity = 10000.0
        targets = {"xlk": 400.0, "xle": -400.0}
        # Gross = $800 <= $2,000; Per-name = $400 <= $500
        limits.validate_targets(equity, targets)

    def test_per_name_cap_violation(self):
        limits = RiskLimits(max_gross_fraction=0.20, per_name_cap_fraction=0.05)
        equity = 10000.0
        # Target for xlk = $600 > $500 (5%)
        targets = {"xlk": 600.0, "xle": 200.0}
        with self.assertRaises(ValueError) as ctx:
            limits.validate_targets(equity, targets)
        self.assertIn("per-name cap violated", str(ctx.exception))

    def test_gross_cap_violation(self):
        limits = RiskLimits(max_gross_fraction=0.20, per_name_cap_fraction=0.05)
        equity = 10000.0
        # 5 names * $500 = $2,500 > $2,000 (20%)
        targets = {
            "xlk": 500.0,
            "xle": 500.0,
            "xlf": 500.0,
            "xlv": 500.0,
            "xly": 500.0,
        }
        with self.assertRaises(ValueError) as ctx:
            limits.validate_targets(equity, targets)
        self.assertIn("gross cap violated", str(ctx.exception))

    def test_invalid_limit_fractions(self):
        bad_cases = [
            (float("nan"), 0.05),
            (0.20, float("nan")),
            (float("inf"), 0.05),
            (0.20, -0.05),
            (0.0, 0.05),
            (11.0, 0.05),
            (0.20, 1.5),
        ]
        for gross, per_name in bad_cases:
            limits = RiskLimits(max_gross_fraction=gross, per_name_cap_fraction=per_name)
            with self.assertRaises(ValueError):
                limits.validate()


if __name__ == "__main__":
    unittest.main()
