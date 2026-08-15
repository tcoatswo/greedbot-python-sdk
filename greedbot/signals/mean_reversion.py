"""
Mean Reversion Signal Generators
--------------------------------
Implements Bollinger Bands, Rolling Mean & Standard Deviation, and Z-Score statistics.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence
import numpy as np

from .base import Signal, SignalDirection, SignalGenerator


class BollingerMeanReversion(SignalGenerator):
    """
    Bollinger Bands and Rolling Z-Score Mean Reversion Signal Generator.
    
    Formulas:
        Rolling Mean: mu_t = SMA_n(P_t)
        Rolling Std:  sigma_t = sqrt( (1/n) * sum((P_{t-i} - mu_t)^2) )
        Z-Score:      Z_t = (P_t - mu_t) / sigma_t
        
    Logic:
        SHORT when Z_t > z_threshold (e.g., +2.0, Statistically Overbought)
        LONG  when Z_t < -z_threshold (e.g., -2.0, Statistically Oversold)
        FLAT  when -z_threshold <= Z_t <= z_threshold
    """

    def __init__(self, window: int = 20, z_threshold: float = 2.0, num_std: float = 2.0):
        if window <= 1:
            raise ValueError(f"window must be > 1, got {window}")
        if z_threshold <= 0:
            raise ValueError(f"z_threshold must be > 0, got {z_threshold}")
        self.window = window
        self.z_threshold = z_threshold
        self.num_std = num_std

    @property
    def name(self) -> str:
        return f"bollinger_zscore_w{self.window}_z{self.z_threshold}"

    def calculate_stats(self, prices: Sequence[float]) -> Dict[str, float]:
        if len(prices) < self.window:
            raise ValueError(f"Need at least {self.window} bars, got {len(prices)}")
        subset = np.array(prices[-self.window:], dtype=float)
        mu = float(np.mean(subset))
        sigma = float(np.std(subset, ddof=0))
        p_t = float(subset[-1])
        z_score = float((p_t - mu) / sigma) if sigma > 1e-9 else 0.0

        upper_band = mu + (self.num_std * sigma)
        lower_band = mu - (self.num_std * sigma)

        return {
            "current_price": p_t,
            "mean": mu,
            "std": sigma,
            "z_score": z_score,
            "upper_band": upper_band,
            "lower_band": lower_band,
        }

    def generate(self, ticker: str, prices: Sequence[float]) -> Signal:
        stats = self.calculate_stats(prices)
        z = stats["z_score"]

        if z > self.z_threshold:
            # Overbought -> Short
            direction = SignalDirection.SHORT
            strength = min(1.0, (z - self.z_threshold) + 0.5)
        elif z < -self.z_threshold:
            # Oversold -> Long
            direction = SignalDirection.LONG
            strength = min(1.0, (abs(z) - self.z_threshold) + 0.5)
        else:
            direction = SignalDirection.FLAT
            strength = 0.0

        return Signal(
            ticker=ticker.upper(),
            direction=direction,
            strength=strength,
            price=stats["current_price"],
            indicator_values={
                "z_score": round(stats["z_score"], 4),
                "rolling_mean": round(stats["mean"], 4),
                "rolling_std": round(stats["std"], 4),
                "upper_band": round(stats["upper_band"], 4),
                "lower_band": round(stats["lower_band"], 4),
            },
            metadata={"window": self.window, "z_threshold": self.z_threshold},
        )
