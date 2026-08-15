"""
Statistical Arbitrage & Cointegration Pairs Trading Signal Generator
--------------------------------------------------------------------
Calculates dynamic Ordinary Least Squares (OLS) hedge ratios, cointegrated spreads,
and rolling spread Z-scores for market-neutral pairs trading.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence, Tuple
import numpy as np

from .base import Signal, SignalDirection, SignalGenerator


class StatisticalArbitrageSpread(SignalGenerator):
    """
    Statistical Arbitrage Pairs Trading Generator.
    
    Formulas:
        OLS Hedge Ratio: beta = Cov(ln P_A, ln P_B) / Var(ln P_B)
        Spread Series:   S_t = ln(P_A_t) - beta * ln(P_B_t) - alpha
        Spread Z-Score:  Z_t = (S_t - mu_S) / sigma_S
        
    Logic:
        When Z_t > +z_threshold: Short Asset A, Long Asset B (Spread expected to collapse)
        When Z_t < -z_threshold: Long Asset A, Short Asset B (Spread expected to expand)
        When |Z_t| <= exit_z:    Close / Revert to FLAT
    """

    def __init__(
        self,
        ticker_a: str,
        ticker_b: str,
        lookback_window: int = 60,
        z_threshold: float = 2.0,
        exit_z: float = 0.5,
    ):
        if lookback_window <= 2:
            raise ValueError(f"lookback_window must be > 2, got {lookback_window}")
        self.ticker_a = ticker_a.upper().strip()
        self.ticker_b = ticker_b.upper().strip()
        self.lookback_window = lookback_window
        self.z_threshold = z_threshold
        self.exit_z = exit_z

    @property
    def name(self) -> str:
        return f"stat_arb_{self.ticker_a}_{self.ticker_b}"

    def calculate_ols_spread(
        self, prices_a: Sequence[float], prices_b: Sequence[float]
    ) -> Dict[str, Any]:
        n = min(len(prices_a), len(prices_b))
        if n < self.lookback_window:
            raise ValueError(f"Need at least {self.lookback_window} bars, got {n}")

        y = np.log(np.array(prices_a[-self.lookback_window:], dtype=float))
        x = np.log(np.array(prices_b[-self.lookback_window:], dtype=float))

        # OLS regression of y on x: y = alpha + beta * x
        var_x = float(np.var(x, ddof=1))
        if var_x < 1e-9:
            beta = 1.0
            alpha = float(np.mean(y) - np.mean(x))
        else:
            cov_xy = float(np.cov(x, y)[0, 1])
            beta = cov_xy / var_x
            alpha = float(np.mean(y) - (beta * np.mean(x)))

        spread = y - (beta * x) - alpha
        mu_s = float(np.mean(spread))
        sigma_s = float(np.std(spread, ddof=1))
        curr_spread = float(spread[-1])
        z_score = float((curr_spread - mu_s) / sigma_s) if sigma_s > 1e-9 else 0.0

        return {
            "beta": beta,
            "alpha": alpha,
            "current_spread": curr_spread,
            "spread_mean": mu_s,
            "spread_std": sigma_s,
            "z_score": z_score,
            "price_a": float(prices_a[-1]),
            "price_b": float(prices_b[-1]),
        }

    def generate(self, prices_a: Sequence[float], prices_b: Sequence[float]) -> Tuple[Signal, Signal]:
        """
        Generates paired signals for Asset A and Asset B.
        """
        stats = self.calculate_ols_spread(prices_a, prices_b)
        z = stats["z_score"]
        beta = stats["beta"]

        if z > self.z_threshold:
            # Spread too high -> Short A, Long B
            dir_a = SignalDirection.SHORT
            dir_b = SignalDirection.LONG
            strength = min(1.0, (z - self.z_threshold) + 0.5)
        elif z < -self.z_threshold:
            # Spread too low -> Long A, Short B
            dir_a = SignalDirection.LONG
            dir_b = SignalDirection.SHORT
            strength = min(1.0, (abs(z) - self.z_threshold) + 0.5)
        else:
            dir_a = SignalDirection.FLAT
            dir_b = SignalDirection.FLAT
            strength = 0.0

        sig_a = Signal(
            ticker=self.ticker_a,
            direction=dir_a,
            strength=strength,
            price=stats["price_a"],
            indicator_values={"spread_z": round(z, 4), "beta": round(beta, 4)},
            metadata={"pair": f"{self.ticker_a}/{self.ticker_b}", "role": "asset_a"},
        )

        sig_b = Signal(
            ticker=self.ticker_b,
            direction=dir_b,
            strength=strength,
            price=stats["price_b"],
            indicator_values={"spread_z": round(z, 4), "beta": round(beta, 4)},
            metadata={"pair": f"{self.ticker_a}/{self.ticker_b}", "role": "asset_b"},
        )

        return sig_a, sig_b
