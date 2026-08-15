"""
Bollinger Bands & Z-Score Mean Reversion Strategy
-------------------------------------------------
Identifies statistically overbought and oversold price anomalies
and trades for a return toward historical rolling equilibrium.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence
from ..client import GreedBotClient
from ..models import BotRunResult, OrderIntent, Side
from ..quant.kelly import KellyPositionSizer
from ..signals.mean_reversion import BollingerMeanReversion
from .base import Strategy


class MeanReversionStrategy(Strategy):
    """
    Statistical Mean Reversion Strategy.
    """

    def __init__(
        self,
        ticker: str = "SPY",
        window: int = 20,
        z_threshold: float = 2.0,
        kelly_fraction: float = 0.50,
        client: Optional[GreedBotClient] = None,
    ):
        self.ticker = ticker.upper().strip()
        self.reversion_gen = BollingerMeanReversion(window=window, z_threshold=z_threshold)
        self.kelly_sizer = KellyPositionSizer(default_fraction=kelly_fraction)
        self.client = client

    @property
    def name(self) -> str:
        return f"mean_reversion_{self.ticker.lower()}"

    def evaluate_signal(self, prices: Sequence[float]) -> Dict[str, Any]:
        sig = self.reversion_gen.generate(self.ticker, prices)
        z = sig.indicator_values.get("z_score", 0.0)

        if sig.is_bullish:
            action = "BUY_OVERSOLD"
            direction = Side.BUY
        elif sig.is_bearish:
            action = "SHORT_OVERBOUGHT"
            direction = Side.SHORT_SELL
        else:
            action = "IN_EQUILIBRIUM_FLAT"
            direction = None

        return {
            "ticker": self.ticker,
            "action": action,
            "direction": direction,
            "z_score": z,
            "rolling_mean": sig.indicator_values.get("rolling_mean"),
            "upper_band": sig.indicator_values.get("upper_band"),
            "lower_band": sig.indicator_values.get("lower_band"),
            "current_price": sig.price,
        }

    def run(
        self,
        client: Optional[GreedBotClient] = None,
        capital_usd: float = 10000.0,
        prices: Optional[Sequence[float]] = None,
    ) -> BotRunResult:
        cli = client or self.client or GreedBotClient()

        if prices is None:
            # Sample prices exhibiting mean-reverting sinusoidal oscillation
            prices = [100.0 + math.sin(i / 3.0) * 8.0 for i in range(40)]

        eval_res = self.evaluate_signal(prices)
        target_dollars: Dict[str, float] = {}
        intents: List[OrderIntent] = []

        if eval_res["direction"] is not None:
            sizing = self.kelly_sizer.size_position(
                capital_usd=capital_usd,
                win_rate=0.60,  # High hit rate for mean reversion
                win_loss_ratio=1.2,
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
