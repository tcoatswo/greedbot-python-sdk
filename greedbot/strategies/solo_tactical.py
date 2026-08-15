"""
GreedBot Solo Tactical Strategy (Single-Ticker IN/FLAT)
-------------------------------------------------------
Disciplined single-asset tactical bot. Driven by /targets aggregated algorithmic signal.
Maps signals above `MIN_SIGNAL` threshold into 100% allocation (IN), and weak/negative
signals into 100% Cash (FLAT), preventing churn on noisy signals.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence
from ..client import GreedBotClient
from ..dataframe import extract_signal
from ..models import BotRunResult, OrderIntent, Side
from .base import Strategy

DEFAULT_SOLO_TICKER: str = "nvda"
DEFAULT_INTERVALS: List[str] = ["1w", "1d"]
MIN_SIGNAL: float = 0.05


class SoloTacticalStrategy(Strategy):
    """
    Single-asset tactical strategy.
    Evaluates /targets directional algo score with noise filtering to toggle between IN and FLAT.
    """

    def __init__(
        self,
        ticker: str = DEFAULT_SOLO_TICKER,
        intervals: Optional[Sequence[str]] = None,
        min_signal: float = MIN_SIGNAL,
    ):
        self.ticker = ticker.strip().lower()
        self.intervals = list(intervals or DEFAULT_INTERVALS)
        self.min_signal = float(min_signal)

    @property
    def name(self) -> str:
        return f"solo_tactical_{self.ticker}"

    def run(self, client: GreedBotClient, capital_usd: float = 10000.0) -> BotRunResult:
        if not math.isfinite(capital_usd) or capital_usd <= 0.0:
            raise ValueError(f"capital_usd must be finite and > 0, got {capital_usd}")

        # 1. Fetch directional algo signal from /targets
        targets_resp = client.get_targets(
            tickers=[self.ticker],
            intervals=self.intervals,
        )
        signal = extract_signal(targets_resp, self.ticker)

        # 2. Two-state decision rule: signal > min_signal -> IN, else FLAT
        desired_dollars = capital_usd if signal > self.min_signal else 0.0
        target_cash = capital_usd - desired_dollars
        target_dollars = {self.ticker: desired_dollars}

        # 3. Compute rebalance trades from all-cash -> target
        target_tickers = [self.ticker]
        target_targets = [desired_dollars]
        rebalance = client.get_rebalance(
            current={"ticker": [], "target": [], "cash": capital_usd},
            target={"ticker": target_tickers, "target": target_targets, "cash": target_cash},
            current_input_type="dollars",
            target_input_type="dollars",
            output_type="shares",
        )

        # 4. Generate order intents (IN = Buy, FLAT = empty)
        intents: List[OrderIntent] = []
        if desired_dollars > 0.0:
            intents.append(
                OrderIntent(
                    ticker=self.ticker,
                    side=Side.BUY,
                    dollars=desired_dollars,
                )
            )

        return BotRunResult(
            trades=rebalance.get("trades", []),
            summary=rebalance.get("summary", {}),
            target_dollars=target_dollars,
            intents=intents,
        )
