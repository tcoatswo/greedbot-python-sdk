"""
Moving Average Convergence Divergence (MACD) Signal Generator
--------------------------------------------------------------
Calculates dual-EMA trend momentum and signal line crossovers.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

from .base import Signal, SignalDirection, SignalGenerator


class MACDCrossover(SignalGenerator):
    """
    MACD (Moving Average Convergence Divergence) Trend Momentum Generator.

    Formulas:
        Fast EMA:   EMA_{fast}(P, n=12)
        Slow EMA:   EMA_{slow}(P, n=26)
        MACD Line:  MACD_t = EMA_{fast, t} - EMA_{slow, t}
        Signal Line: Signal_t = EMA(MACD, n=9)
        Histogram:  Hist_t = MACD_t - Signal_t

    Signals:
        LONG  when MACD crosses above Signal Line (Hist > 0)
        SHORT when MACD crosses below Signal Line (Hist < 0)
        FLAT  when momentum is neutral or insufficient history
    """

    def __init__(
        self,
        fast_period: int = 12,
        slow_period: int = 26,
        signal_period: int = 9,
    ):
        if fast_period >= slow_period:
            raise ValueError(f"fast_period ({fast_period}) must be strictly less than slow_period ({slow_period})")
        if signal_period < 2:
            raise ValueError(f"signal_period must be >= 2, got {signal_period}")

        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period

    @property
    def name(self) -> str:
        return f"macd_{self.fast_period}_{self.slow_period}_{self.signal_period}"

    @staticmethod
    def _compute_ema(series: Sequence[float], period: int) -> List[float]:
        """Compute exponential moving average array."""
        alpha = 2.0 / (period + 1.0)
        ema: List[float] = [float(series[0])]
        for val in series[1:]:
            ema.append(alpha * float(val) + (1.0 - alpha) * ema[-1])
        return ema

    def calculate_macd(self, prices: Sequence[float]) -> Dict[str, float]:
        """
        Calculate MACD line, Signal line, and Histogram values.
        Requires at least slow_period + signal_period bars.
        """
        p = [float(x) for x in prices]
        min_required = self.slow_period + self.signal_period
        if len(p) < min_required:
            raise ValueError(f"Need at least {min_required} price bars, got {len(p)}")

        fast_ema = self._compute_ema(p, self.fast_period)
        slow_ema = self._compute_ema(p, self.slow_period)

        macd_series = [f - s for f, s in zip(fast_ema, slow_ema)]
        signal_series = self._compute_ema(macd_series, self.signal_period)

        curr_macd = macd_series[-1]
        curr_signal = signal_series[-1]
        curr_hist = curr_macd - curr_signal

        prev_hist = macd_series[-2] - signal_series[-2] if len(macd_series) > 1 else curr_hist

        return {
            "current_price": p[-1],
            "macd": curr_macd,
            "signal_line": curr_signal,
            "histogram": curr_hist,
            "prev_histogram": prev_hist,
            "fast_ema": fast_ema[-1],
            "slow_ema": slow_ema[-1],
        }

    def generate(self, ticker: str, prices: Sequence[float]) -> Signal:
        stats = self.calculate_macd(prices)
        hist = stats["histogram"]
        prev_hist = stats["prev_histogram"]

        is_bullish_cross = hist > 0 and prev_hist <= 0
        is_bearish_cross = hist < 0 and prev_hist >= 0

        # Strength based on histogram magnitude relative to price
        price = stats["current_price"]
        pct_hist = (abs(hist) / price * 100.0) if price > 0 else 0.0

        if is_bullish_cross or (hist > 0 and hist >= prev_hist):
            direction = SignalDirection.LONG
            strength = min(1.0, 0.5 + min(0.5, pct_hist))
        elif is_bearish_cross or (hist < 0 and hist <= prev_hist):
            direction = SignalDirection.SHORT
            strength = min(1.0, 0.5 + min(0.5, pct_hist))
        elif hist > 0:
            direction = SignalDirection.LONG
            strength = 0.3
        elif hist < 0:
            direction = SignalDirection.SHORT
            strength = 0.3
        else:
            direction = SignalDirection.FLAT
            strength = 0.0

        return Signal(
            ticker=ticker.upper(),
            direction=direction,
            strength=round(strength, 4),
            price=round(price, 4),
            indicator_values={
                "macd": round(stats["macd"], 4),
                "signal_line": round(stats["signal_line"], 4),
                "histogram": round(hist, 4),
            },
            metadata={
                "fast_period": self.fast_period,
                "slow_period": self.slow_period,
                "signal_period": self.signal_period,
                "crossover": "bullish" if is_bullish_cross else ("bearish" if is_bearish_cross else "none"),
            },
        )
