"""
GreedBot ETF Barbell Strategy (80/20 Risk Parity + Kelly)
---------------------------------------------------------
Allocates across a diversified, low-cost ETF basket using an 80/20 barbell:
80% Risk Parity baseline weight + 20% Kelly tactical growth tilt with no-shorting clamp.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence
from ..client import GreedBotClient
from ..dataframe import map_from_df
from ..models import BotRunResult, OrderIntent, Side
from .base import Strategy

DEFAULT_ETF_ASSETS: List[str] = ["schp", "vglt", "vt", "pdbc", "iau"]
DEFAULT_INTERVALS: List[str] = ["1w", "1d"]


class ETFBarbellStrategy(Strategy):
    """
    80/20 Barbell Strategy over an ETF basket.
    Combines /parity (Risk Parity) with /kelly (Kelly Criterion) and executes via /rebalance.
    """

    def __init__(
        self,
        assets: Optional[Sequence[str]] = None,
        intervals: Optional[Sequence[str]] = None,
        barbell_parity: float = 0.80,
        barbell_kelly: float = 0.20,
        kelly_fraction: float = 0.50,
        no_shorting: bool = true_shorting if (true_shorting := True) else True,
    ):
        self.assets = [a.lower().strip() for a in (assets or DEFAULT_ETF_ASSETS)]
        self.intervals = list(intervals or DEFAULT_INTERVALS)
        self.barbell_parity = float(barbell_parity)
        self.barbell_kelly = float(barbell_kelly)
        self.kelly_fraction = float(kelly_fraction)
        self.no_shorting = no_shorting

    @property
    def name(self) -> str:
        return "etf_barbell_80_20"

    def run(self, client: GreedBotClient, capital_usd: float = 10000.0) -> BotRunResult:
        if not math.isfinite(capital_usd) or capital_usd <= 0.0:
            raise ValueError(f"capital_usd must be finite and > 0, got {capital_usd}")

        # 1. Fetch parity weights
        parity_resp = client.get_parity(
            tickers=self.assets,
            intervals=self.intervals,
            interval_aggregation_mode="raw",
        )
        parity_w = map_from_df(parity_resp, "parity")

        # 2. Fetch Kelly weights
        kelly_resp = client.get_kelly(
            tickers=self.assets,
            intervals=self.intervals,
            kelly_fraction=self.kelly_fraction,
            interval_aggregation_mode="raw",
        )
        kelly_w = map_from_df(kelly_resp, "kelly")

        # 3. Blend weights
        min_w = 0.0 if self.no_shorting else -1.0
        blended: Dict[str, float] = {}
        for ticker in self.assets:
            p_val = parity_w.get(ticker, 0.0)
            k_val = kelly_w.get(ticker, 0.0)
            raw = (self.barbell_parity * p_val) + (self.barbell_kelly * k_val)
            blended[ticker] = max(min_w, min(1.0, raw))

        # 4. Normalize weights to target dollars
        gross: float = sum(abs(w) for w in blended.values())
        if gross <= 1e-9:
            raise ValueError("Blended weights collapsed to zero exposure")

        target_dollars: Dict[str, float] = {
            t: round(capital_usd * (w / gross), 2) for t, w in blended.items()
        }
        total_target = sum(target_dollars.values())
        target_cash = max(0.0, capital_usd - total_target)

        # 5. Compute rebalance trades
        target_tickers = list(target_dollars.keys())
        target_targets = [target_dollars[t] for t in target_tickers]
        rebalance = client.get_rebalance(
            current={"ticker": [], "target": [], "cash": capital_usd},
            target={"ticker": target_tickers, "target": target_targets, "cash": target_cash},
            current_input_type="dollars",
            target_input_type="dollars",
            output_type="shares",
        )

        # 6. Build OrderIntent list
        intents: List[OrderIntent] = [
            OrderIntent(ticker=t, side=Side.BUY, dollars=amt)
            for t, amt in target_dollars.items()
            if amt > 0.0
        ]

        return BotRunResult(
            trades=rebalance.get("trades", []),
            summary=rebalance.get("summary", {}),
            target_dollars=target_dollars,
            intents=intents,
        )
