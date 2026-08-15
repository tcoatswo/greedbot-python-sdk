"""
Statistical Arbitrage Cointegration Pairs Trading Strategy
-----------------------------------------------------------
Executes dollar-neutral spread trades between cointegrated asset pairs
(e.g., SPY vs QQQ, XLE vs XOM, GOOG vs GOOGL).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence
from ..client import GreedBotClient
from ..models import BotRunResult, OrderIntent, Side
from ..signals.pairs import StatisticalArbitrageSpread
from .base import Strategy


class StatArbPairsStrategy(Strategy):
    """
    Statistical Arbitrage Pairs Trading Strategy.
    """

    def __init__(
        self,
        ticker_a: str = "SPY",
        ticker_b: str = "QQQ",
        lookback_window: int = 60,
        z_threshold: float = 2.0,
        gross_fraction: float = 0.20,
        client: Optional[GreedBotClient] = None,
    ):
        self.ticker_a = ticker_a.upper().strip()
        self.ticker_b = ticker_b.upper().strip()
        self.spread_gen = StatisticalArbitrageSpread(
            ticker_a=self.ticker_a,
            ticker_b=self.ticker_b,
            lookback_window=lookback_window,
            z_threshold=z_threshold,
        )
        self.gross_fraction = gross_fraction
        self.client = client

    @property
    def name(self) -> str:
        return f"stat_arb_{self.ticker_a.lower()}_{self.ticker_b.lower()}"

    def evaluate_pair(
        self, prices_a: Sequence[float], prices_b: Sequence[float]
    ) -> Dict[str, Any]:
        sig_a, sig_b = self.spread_gen.generate(prices_a, prices_b)
        return {
            "pair": f"{self.ticker_a}/{self.ticker_b}",
            "signal_a": sig_a,
            "signal_b": sig_b,
            "spread_z": sig_a.indicator_values.get("spread_z"),
            "beta": sig_a.indicator_values.get("beta"),
        }

    def run(
        self,
        client: Optional[GreedBotClient] = None,
        capital_usd: float = 10000.0,
        prices_a: Optional[Sequence[float]] = None,
        prices_b: Optional[Sequence[float]] = None,
    ) -> BotRunResult:
        cli = client or self.client or GreedBotClient()

        if prices_a is None or prices_b is None:
            # Synthetic cointegrated series with a transient divergence
            prices_b = [100.0 + i * 0.2 + math.sin(i / 4.0) * 1.5 for i in range(70)]
            # Divergence on A
            prices_a = [p * 1.5 + (3.5 if i > 60 else 0.0) for i, p in enumerate(prices_b)]

        res = self.evaluate_pair(prices_a, prices_b)
        sig_a: Any = res["signal_a"]
        sig_b: Any = res["signal_b"]

        target_dollars: Dict[str, float] = {}
        intents: List[OrderIntent] = []

        per_leg_dollars = (capital_usd * self.gross_fraction) / 2.0

        if not sig_a.is_flat and not sig_b.is_flat:
            side_a = Side.BUY if sig_a.is_bullish else Side.SHORT_SELL
            side_b = Side.BUY if sig_b.is_bullish else Side.SHORT_SELL

            target_dollars[self.ticker_a.lower()] = per_leg_dollars
            target_dollars[self.ticker_b.lower()] = per_leg_dollars

            intents.append(OrderIntent(ticker=self.ticker_a.lower(), side=side_a, dollars=per_leg_dollars))
            intents.append(OrderIntent(ticker=self.ticker_b.lower(), side=side_b, dollars=per_leg_dollars))
        else:
            target_dollars[self.ticker_a.lower()] = 0.0
            target_dollars[self.ticker_b.lower()] = 0.0

        return BotRunResult(
            trades=[{"pair": res["pair"], "spread_z": res["spread_z"], "beta": res["beta"]}],
            summary=res,
            target_dollars=target_dollars,
            intents=intents,
        )
