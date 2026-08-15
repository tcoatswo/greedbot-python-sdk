"""
Trend Following & Momentum Quantitative Trading Strategy
--------------------------------------------------------
Combines Moving Average Crossover (Fast vs Slow SMA) and Time-Series Momentum
to capture sustained directional trends with fractional Kelly risk sizing.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence
from ..client import GreedBotClient
from ..models import BotRunResult, OrderIntent, Side
from ..quant.kelly import KellyPositionSizer
from ..signals.trend import MovingAverageCrossover, TimeSeriesMomentum
from .base import Strategy


class TrendFollowingStrategy(Strategy):
    """
    Dual-Factor Trend Following Strategy.
    """

    def __init__(
        self,
        ticker: str = "NVDA",
        short_window: int = 10,
        long_window: int = 50,
        momentum_lookback: int = 14,
        kelly_fraction: float = 0.50,
        client: Optional[GreedBotClient] = None,
    ):
        self.ticker = ticker.upper().strip()
        self.sma_gen = MovingAverageCrossover(short_window=short_window, long_window=long_window)
        self.mom_gen = TimeSeriesMomentum(lookback_k=momentum_lookback)
        self.kelly_sizer = KellyPositionSizer(default_fraction=kelly_fraction)
        self.client = client

    @property
    def name(self) -> str:
        return f"trend_following_{self.ticker.lower()}"

    def evaluate_signal(self, prices: Sequence[float]) -> Dict[str, Any]:
        """Evaluate SMA and Momentum signals from historical price series."""
        sma_sig = self.sma_gen.generate(self.ticker, prices)
        mom_sig = self.mom_gen.generate(self.ticker, prices)

        # Composite score
        is_bullish = sma_sig.is_bullish and (mom_sig.is_bullish or mom_sig.is_flat)
        is_bearish = sma_sig.is_bearish and (mom_sig.is_bearish or mom_sig.is_flat)

        if is_bullish:
            action = "BUY"
            direction = Side.BUY
            confidence = (sma_sig.strength + mom_sig.strength) / 2.0
        elif is_bearish:
            action = "SHORT_SELL"
            direction = Side.SHORT_SELL
            confidence = (sma_sig.strength + mom_sig.strength) / 2.0
        else:
            action = "FLAT"
            direction = None
            confidence = 0.0

        return {
            "ticker": self.ticker,
            "action": action,
            "direction": direction,
            "confidence": round(confidence, 4),
            "sma_short": sma_sig.indicator_values.get(f"sma_{self.sma_gen.short_window}"),
            "sma_long": sma_sig.indicator_values.get(f"sma_{self.sma_gen.long_window}"),
            "momentum_pct": mom_sig.indicator_values.get("momentum_pct"),
            "acceleration": mom_sig.indicator_values.get("acceleration"),
            "current_price": float(prices[-1]),
        }

    def run(
        self,
        client: Optional[GreedBotClient] = None,
        capital_usd: float = 10000.0,
        prices: Optional[Sequence[float]] = None,
    ) -> BotRunResult:
        cli = client or self.client or GreedBotClient()

        if prices is None:
            # Fetch synthetic / sample trend prices if not provided
            prices = [100.0 + i * 0.5 + math.sin(i / 5.0) * 2.0 for i in range(80)]

        eval_res = self.evaluate_signal(prices)
        target_dollars: Dict[str, float] = {}
        intents: List[OrderIntent] = []

        if eval_res["direction"] is not None:
            # Size position using Kelly sizing
            sizing = self.kelly_sizer.size_position(
                capital_usd=capital_usd,
                win_rate=0.55,
                win_loss_ratio=1.8,
            )
            alloc_dollars = sizing["target_dollars"]
            target_dollars[self.ticker.lower()] = alloc_dollars
            intents.append(
                OrderIntent(
                    ticker=self.ticker.lower(),
                    side=eval_res["direction"],
                    dollars=alloc_dollars,
                )
            )
        else:
            target_dollars[self.ticker.lower()] = 0.0

        return BotRunResult(
            trades=[eval_res],
            summary={"evaluation": eval_res, "capital": capital_usd},
            target_dollars=target_dollars,
            intents=intents,
        )
