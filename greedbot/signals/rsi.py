"""
Relative Strength Index (RSI) Mean Reversion Signal Generator
-------------------------------------------------------------
Implements J. Welles Wilder's smoothed Relative Strength Index (RSI) oscillator
and generates counter-trend mean reversion signals at oversold / overbought extremes.
"""

from __future__ import annotations

from typing import Dict, Sequence
import numpy as np

from .base import Signal, SignalDirection, SignalGenerator


class RSIMeanReversion(SignalGenerator):
    """
    RSI Oscillator Mean Reversion Signal Generator.

    Formulas:
        Change: Delta_t = P_t - P_{t-1}
        Gain:   U_t = max(Delta_t, 0)
        Loss:   D_t = max(-Delta_t, 0)

        Wilder's Smoothing (lookback = n):
            AvgGain_t = (AvgGain_{t-1} * (n - 1) + U_t) / n
            AvgLoss_t = (AvgLoss_{t-1} * (n - 1) + D_t) / n

        Relative Strength (RS):
            RS = AvgGain / AvgLoss (if AvgLoss > 0, else inf)

        RSI Index:
            RSI = 100 - (100 / (1 + RS))

    Signals:
        LONG  when RSI < oversold_threshold (default 30.0) -> Oversold bounce
        SHORT when RSI > overbought_threshold (default 70.0) -> Overbought pullback
        FLAT  when oversold_threshold <= RSI <= overbought_threshold
    """

    def __init__(
        self,
        period: int = 14,
        oversold_threshold: float = 30.0,
        overbought_threshold: float = 70.0,
    ):
        if period < 2:
            raise ValueError(f"period must be >= 2, got {period}")
        if not (0.0 < oversold_threshold < overbought_threshold < 100.0):
            raise ValueError(
                f"Thresholds must satisfy 0 < oversold < overbought < 100, "
                f"got oversold={oversold_threshold}, overbought={overbought_threshold}"
            )

        self.period = period
        self.oversold_threshold = float(oversold_threshold)
        self.overbought_threshold = float(overbought_threshold)

    @property
    def name(self) -> str:
        return f"rsi_p{self.period}_os{self.oversold_threshold:.0f}_ob{self.overbought_threshold:.0f}"

    def calculate_rsi(self, prices: Sequence[float]) -> Dict[str, float]:
        """
        Calculate current RSI and intermediate oscillator components.
        Requires at least period + 1 prices.
        """
        p = np.array(prices, dtype=float)
        if len(p) < self.period + 1:
            raise ValueError(f"Need at least {self.period + 1} price bars for RSI calculation, got {len(p)}")

        deltas = np.diff(p)
        gains = np.maximum(deltas, 0.0)
        losses = np.maximum(-deltas, 0.0)

        # Initial seed average
        avg_gain = float(np.mean(gains[: self.period]))
        avg_loss = float(np.mean(losses[: self.period]))

        # Wilder's exponential smoothing
        for i in range(self.period, len(deltas)):
            avg_gain = (avg_gain * (self.period - 1) + gains[i]) / float(self.period)
            avg_loss = (avg_loss * (self.period - 1) + losses[i]) / float(self.period)

        if avg_loss < 1e-12:
            rsi = 100.0 if avg_gain > 0 else 50.0
            rs = 999.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))

        return {
            "current_price": float(p[-1]),
            "rsi": float(rsi),
            "avg_gain": float(avg_gain),
            "avg_loss": float(avg_loss),
            "rs": float(rs),
        }

    def generate(self, ticker: str, prices: Sequence[float]) -> Signal:
        stats = self.calculate_rsi(prices)
        rsi = stats["rsi"]

        if rsi < self.oversold_threshold:
            # Oversold condition -> Bullish mean reversion
            direction = SignalDirection.LONG
            oversold_distance = self.oversold_threshold - rsi
            strength = min(1.0, 0.5 + (oversold_distance / 20.0))
        elif rsi > self.overbought_threshold:
            # Overbought condition -> Bearish mean reversion
            direction = SignalDirection.SHORT
            overbought_distance = rsi - self.overbought_threshold
            strength = min(1.0, 0.5 + (overbought_distance / 20.0))
        else:
            direction = SignalDirection.FLAT
            strength = 0.0

        return Signal(
            ticker=ticker.upper(),
            direction=direction,
            strength=round(strength, 4),
            price=round(stats["current_price"], 4),
            indicator_values={
                "rsi": round(rsi, 2),
                "rs": round(stats["rs"], 4),
                "oversold_threshold": self.oversold_threshold,
                "overbought_threshold": self.overbought_threshold,
            },
            metadata={
                "period": self.period,
                "strategy": "RSI_Mean_Reversion",
            },
        )
