"""
Avellaneda-Stoikov High-Frequency Market Making Strategy
--------------------------------------------------------
Places two-sided limit orders (Bid / Ask) around an inventory-adjusted reservation price
to earn the bid-ask spread while dynamically managing inventory risk.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from ..client import GreedBotClient
from ..models import BotRunResult, OrderIntent, Side
from ..signals.market_maker import AvellanedaStoikovMarketMaker
from .base import Strategy


class MarketMakerStrategy(Strategy):
    """
    Avellaneda-Stoikov Market Making Strategy.
    """

    def __init__(
        self,
        ticker: str = "NVDA",
        gamma: float = 0.1,
        k: float = 1.5,
        quote_size_usd: float = 1000.0,
        client: Optional[GreedBotClient] = None,
    ):
        self.ticker = ticker.upper().strip()
        self.mm_model = AvellanedaStoikovMarketMaker(gamma=gamma, k=k)
        self.quote_size_usd = quote_size_usd
        self.client = client

    @property
    def name(self) -> str:
        return f"market_maker_{self.ticker.lower()}"

    def compute_quotes(
        self,
        mid_price: float,
        inventory_q: float = 0.0,
        volatility_sigma: float = 0.02,
        time_remaining: float = 1.0,
    ) -> Dict[str, Any]:
        return self.mm_model.calculate_quotes(
            mid_price=mid_price,
            inventory_q=inventory_q,
            volatility_sigma=volatility_sigma,
            time_remaining=time_remaining,
        )

    def run(
        self,
        client: Optional[GreedBotClient] = None,
        capital_usd: float = 10000.0,
        mid_price: float = 100.0,
        inventory_q: float = 0.0,
        volatility_sigma: float = 0.02,
    ) -> BotRunResult:
        quotes = self.compute_quotes(
            mid_price=mid_price,
            inventory_q=inventory_q,
            volatility_sigma=volatility_sigma,
        )

        intents: List[OrderIntent] = [
            # Limit Buy at Bid
            OrderIntent(
                ticker=self.ticker.lower(),
                side=Side.BUY,
                dollars=self.quote_size_usd,
                limit=quotes["bid_price"],
            ),
            # Limit Sell/Short at Ask
            OrderIntent(
                ticker=self.ticker.lower(),
                side=Side.SELL if inventory_q > 0 else Side.SHORT_SELL,
                dollars=self.quote_size_usd,
                limit=quotes["ask_price"],
            ),
        ]

        target_dollars = {self.ticker.lower(): self.quote_size_usd * 2.0}

        return BotRunResult(
            trades=[quotes],
            summary={"quotes": quotes, "inventory_q": inventory_q},
            target_dollars=target_dollars,
            intents=intents,
        )
