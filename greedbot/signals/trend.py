"""
Trend Following and Momentum Signal Generators
----------------------------------------------
Implements Moving Average Crossover and Time-Series Momentum (Rate of Change & Acceleration).
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Sequence
import numpy as np

from .base import Signal, SignalDirection, SignalGenerator


class MovingAverageCrossover(SignalGenerator):
    """
    Moving Average Crossover Signal Generator.
    
    Formula:
        SMA_n = (1/n) * sum(P_{t-i})
    
    Logic:
        LONG  when SMA_short > SMA_long + threshold
        SHORT when SMA_short < SMA_long - threshold
        FLAT  when within threshold deadband
    """

    def __init__(self, short_window: int = 10, long_window: int = 50, deadband_pct: float = 0.0):
        if short_window <= 0 or long_window <= 0 or short_window >= long_window:
            raise ValueError(f"Requires 0 < short_window < long_window, got {short_window} and {long_window}")
        self.short_window = short_window
        self.long_window = long_window
        self.deadband_pct = deadband_pct

    @property
    def name(self) -> str:
        return f"sma_crossover_{self.short_window}_{self.long_window}"

    def calculate_sma(self, prices: Sequence[float], window: int) -> float:
        if len(prices) < window:
            raise ValueError(f"Need at least {window} prices, got {len(prices)}")
        return float(np.mean(prices[-window:]))

    def generate(self, ticker: str, prices: Sequence[float]) -> Signal:
        if len(prices) < self.long_window:
            raise ValueError(f"Insufficient history ({len(prices)} bars < long window {self.long_window})")

        sma_short = self.calculate_sma(prices, self.short_window)
        sma_long = self.calculate_sma(prices, self.long_window)
        diff_pct = (sma_short - sma_long) / sma_long

        if diff_pct > self.deadband_pct:
            direction = SignalDirection.LONG
            strength = min(1.0, diff_pct * 10.0)
        elif diff_pct < -self.deadband_pct:
            direction = SignalDirection.SHORT
            strength = min(1.0, abs(diff_pct) * 10.0)
        else:
            direction = SignalDirection.FLAT
            strength = 0.0

        current_price = float(prices[-1])
        return Signal(
            ticker=ticker.upper(),
            direction=direction,
            strength=strength,
            price=current_price,
            indicator_values={
                f"sma_{self.short_window}": round(sma_short, 4),
                f"sma_{self.long_window}": round(sma_long, 4),
                "diff_pct": round(diff_pct * 100, 2),
            },
            metadata={"short_window": self.short_window, "long_window": self.long_window},
        )


class TimeSeriesMomentum(SignalGenerator):
    """
    Time-Series Momentum & Rate of Change (ROC) Generator.
    
    Formula:
        M_t = ((P_t - P_{t-k}) / P_{t-k}) * 100
        Delta M_t = M_t - M_{t-1} (Acceleration)
        
    Logic:
        LONG  when M_t > 0 and accelerating (or above acceleration threshold)
        SHORT when M_t < 0 and decelerating
    """

    def __init__(self, lookback_k: int = 14, require_acceleration: bool = True):
        if lookback_k <= 0:
            raise ValueError(f"lookback_k must be > 0, got {lookback_k}")
        self.lookback_k = lookback_k
        self.require_acceleration = require_acceleration

    @property
    def name(self) -> str:
        return f"ts_momentum_k{self.lookback_k}"

    def generate(self, ticker: str, prices: Sequence[float]) -> Signal:
        min_required = self.lookback_k + 2
        if len(prices) < min_required:
            raise ValueError(f"Insufficient history ({len(prices)} bars < required {min_required})")

        p_t = float(prices[-1])
        p_prev = float(prices[-2])
        p_k = float(prices[-1 - self.lookback_k])
        p_k_prev = float(prices[-2 - self.lookback_k])

        roc_curr = ((p_t - p_k) / p_k) * 100.0
        roc_prev = ((p_prev - p_k_prev) / p_k_prev) * 100.0
        acceleration = roc_curr - roc_prev

        if roc_curr > 0:
            if not self.require_acceleration or acceleration > 0:
                direction = SignalDirection.LONG
                strength = min(1.0, roc_curr / 10.0)
            else:
                direction = SignalDirection.FLAT
                strength = 0.0
        elif roc_curr < 0:
            if not self.require_acceleration or acceleration < 0:
                direction = SignalDirection.SHORT
                strength = min(1.0, abs(roc_curr) / 10.0)
            else:
                direction = SignalDirection.FLAT
                strength = 0.0
        else:
            direction = SignalDirection.FLAT
            strength = 0.0

        return Signal(
            ticker=ticker.upper(),
            direction=direction,
            strength=strength,
            price=p_t,
            indicator_values={
                "momentum_pct": round(roc_curr, 4),
                "acceleration": round(acceleration, 4),
            },
            metadata={"lookback_k": self.lookback_k, "require_acceleration": self.require_acceleration},
        )
