"""
Dynamic Position Protection, Chandelier Exits & Trailing Stops
--------------------------------------------------------------
Implements volatility-adjusted ATR Chandelier stops, R-multiple profit ratchets,
and time-based exit managers for live and paper trading bots.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence
import numpy as np


@dataclass
class PositionExitStatus:
    """Status evaluation of an active position's stops."""
    ticker: str
    is_triggered: bool
    trigger_reason: Optional[str]
    current_price: float
    stop_price: float
    unrealized_pnl: float
    r_multiple: float


class ChandelierExit:
    """
    ATR-based Chandelier Exit.
    
    Formulas:
        Long Position:  Stop = Highest_High(n) - (k * ATR_n)
        Short Position: Stop = Lowest_Low(n) + (k * ATR_n)
        
    Invariant:
        For long positions, the stop price ONLY ratchets UPWARD and never loosens downward.
        For short positions, the stop price ONLY ratchets DOWNWARD.
    """

    def __init__(self, atr_period: int = 14, multiplier_k: float = 3.0):
        if atr_period <= 0:
            raise ValueError("atr_period must be > 0")
        if multiplier_k <= 0:
            raise ValueError("multiplier_k must be > 0")
        self.atr_period = atr_period
        self.multiplier_k = multiplier_k

    @staticmethod
    def calculate_atr(
        highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], period: int = 14
    ) -> float:
        n = min(len(highs), len(lows), len(closes))
        if n < 2:
            return float(highs[-1] - lows[-1]) if n > 0 else 1.0

        p = min(period, n - 1)
        h = np.array(highs[-p:], dtype=float)
        l = np.array(lows[-p:], dtype=float)
        prev_c = np.array(closes[-p - 1 : -1], dtype=float)

        tr1 = h - l
        tr2 = np.abs(h - prev_c)
        tr3 = np.abs(l - prev_c)

        tr = np.maximum(tr1, np.maximum(tr2, tr3))
        return float(np.mean(tr))

    def update_long_stop(
        self,
        current_stop: float,
        highs: Sequence[float],
        lows: Sequence[float],
        closes: Sequence[float],
    ) -> float:
        atr = self.calculate_atr(highs, lows, closes, self.atr_period)
        highest_high = float(np.max(highs[-self.atr_period:]))
        computed_stop = highest_high - (self.multiplier_k * atr)
        # Only ratchet upward
        return max(current_stop, computed_stop)

    def update_short_stop(
        self,
        current_stop: float,
        highs: Sequence[float],
        lows: Sequence[float],
        closes: Sequence[float],
    ) -> float:
        atr = self.calculate_atr(highs, lows, closes, self.atr_period)
        lowest_low = float(np.min(lows[-self.atr_period:]))
        computed_stop = lowest_low + (self.multiplier_k * atr)
        # Only ratchet downward
        return min(current_stop, computed_stop) if current_stop > 0 else computed_stop


class TrailingStopManager:
    """
    R-Multiple and High-Watermark Trailing Stop Manager.
    
    Ratcheting Rules:
        - Gain reaches +1.0R -> Move Stop to Breakeven (Entry)
        - Gain reaches +2.0R -> Lock in +1.0R
        - Gain reaches +3.0R -> Lock in +2.0R
    """

    def __init__(self, ticker: str, entry_price: float, initial_stop: float, direction: str = "long"):
        if entry_price <= 0:
            raise ValueError("entry_price must be > 0")
        self.ticker = ticker.upper()
        self.entry_price = float(entry_price)
        self.current_stop = float(initial_stop)
        self.direction = direction.lower()
        self.risk_1r = abs(self.entry_price - self.current_stop)
        self.highest_price = self.entry_price
        self.lowest_price = self.entry_price

    def update(self, current_price: float) -> PositionExitStatus:
        p = float(current_price)

        if self.direction == "long":
            self.highest_price = max(self.highest_price, p)
            unrealized_pnl = p - self.entry_price
            r_mult = unrealized_pnl / self.risk_1r if self.risk_1r > 1e-9 else 0.0

            # Profit ratcheting
            if r_mult >= 3.0:
                self.current_stop = max(self.current_stop, self.entry_price + (2.0 * self.risk_1r))
            elif r_mult >= 2.0:
                self.current_stop = max(self.current_stop, self.entry_price + (1.0 * self.risk_1r))
            elif r_mult >= 1.0:
                self.current_stop = max(self.current_stop, self.entry_price)  # Breakeven

            triggered = p <= self.current_stop
            reason = "TRAILING_STOP_TRIGGERED" if triggered else None

        else:  # Short
            self.lowest_price = min(self.lowest_price, p)
            unrealized_pnl = self.entry_price - p
            r_mult = unrealized_pnl / self.risk_1r if self.risk_1r > 1e-9 else 0.0

            if r_mult >= 3.0:
                self.current_stop = min(self.current_stop, self.entry_price - (2.0 * self.risk_1r))
            elif r_mult >= 2.0:
                self.current_stop = min(self.current_stop, self.entry_price - (1.0 * self.risk_1r))
            elif r_mult >= 1.0:
                self.current_stop = min(self.current_stop, self.entry_price)

            triggered = p >= self.current_stop
            reason = "TRAILING_STOP_TRIGGERED" if triggered else None

        return PositionExitStatus(
            ticker=self.ticker,
            is_triggered=triggered,
            trigger_reason=reason,
            current_price=p,
            stop_price=self.current_stop,
            unrealized_pnl=round(unrealized_pnl, 2),
            r_multiple=round(r_mult, 2),
        )
