"""
Kelly Criterion Position Sizing Engine
--------------------------------------
Calculates optimal bet sizing fractions to maximize long-term compound growth rate
under discrete payoff and continuous lognormal dynamics.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional


class KellyPositionSizer:
    """
    Kelly Criterion Position Sizer.
    
    Formulas:
        Discrete Payoffs:
            f* = (p * (b + 1) - 1) / b
            where:
                p = win probability (0.0 to 1.0)
                b = payoff ratio (average win / average loss)
                
        Continuous / Gaussian Returns:
            f* = (mu - r) / sigma^2
            where:
                mu    = expected asset return
                r     = risk-free rate
                sigma = return volatility (std dev)
                
        Fractional Kelly:
            f_applied = f* * fraction (e.g., fraction=0.5 for Half-Kelly)
    """

    def __init__(self, default_fraction: float = 0.50, max_allocation: float = 0.25):
        if default_fraction <= 0.0 or default_fraction > 1.0:
            raise ValueError(f"default_fraction must be in (0.0, 1.0], got {default_fraction}")
        self.default_fraction = default_fraction
        self.max_allocation = max_allocation

    @staticmethod
    def discrete_kelly(win_rate: float, win_loss_ratio: float) -> float:
        """
        Compute theoretical unconstrained discrete Kelly fraction.
        f* = (p * (b + 1) - 1) / b
        """
        p = float(win_rate)
        b = float(win_loss_ratio)

        if not (0.0 <= p <= 1.0):
            raise ValueError(f"win_rate must be between 0.0 and 1.0, got {p}")
        if b <= 0.0:
            raise ValueError(f"win_loss_ratio must be > 0, got {b}")

        f_star = (p * (b + 1.0) - 1.0) / b
        return float(f_star)

    @staticmethod
    def continuous_kelly(expected_return: float, volatility: float, risk_free_rate: float = 0.0) -> float:
        """
        Compute continuous Gaussian Kelly fraction.
        f* = (mu - r) / sigma^2
        """
        sigma2 = float(volatility) ** 2
        if sigma2 < 1e-9:
            raise ValueError("volatility cannot be near zero")
        excess_return = float(expected_return) - float(risk_free_rate)
        return excess_return / sigma2

    def size_position(
        self,
        capital_usd: float,
        win_rate: float,
        win_loss_ratio: float,
        fraction: Optional[float] = None,
        max_cap: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Calculates actionable dollar allocation and risk budget.
        """
        frac = self.default_fraction if fraction is None else fraction
        cap = self.max_allocation if max_cap is None else max_cap

        f_star = self.discrete_kelly(win_rate, win_loss_ratio)
        has_edge = f_star > 0.0

        if has_edge:
            raw_fraction = f_star * frac
            applied_fraction = max(0.0, min(raw_fraction, cap))
        else:
            raw_fraction = 0.0
            applied_fraction = 0.0

        target_dollars = round(capital_usd * applied_fraction, 2)

        return {
            "has_positive_edge": has_edge,
            "full_kelly_f_star": round(f_star, 4),
            "fraction_applied": frac,
            "applied_kelly_fraction": round(applied_fraction, 4),
            "capital_usd": capital_usd,
            "target_dollars": target_dollars,
            "max_cap_applied": cap,
        }
