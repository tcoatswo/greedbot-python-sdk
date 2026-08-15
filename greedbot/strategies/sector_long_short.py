"""
GreedBot Sector Dollar-Neutral Long/Short Strategy
--------------------------------------------------
Constructs dollar-neutral long/short portfolios across 11 US Sector SPDR ETFs:
Ranks sectors using /pizza multi-factor model, goes Long the top N sectors and
Short the bottom N sectors with equal dollar exposure and strict risk limits.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence
from ..client import GreedBotClient
from ..dataframe import ranking_from_pizza
from ..models import BotRunResult, OrderIntent, Side
from ..risk import RiskLimits
from .base import Strategy

SECTOR_ETFS: List[str] = [
    "xle", "xlf", "xlk", "xli", "xlv", "xly", "xlp", "xlu", "xlb", "xlre", "xlc"
]


class SectorLongShortStrategy(Strategy):
    """
    Dollar-neutral sector pair trading strategy.
    Long top-N sectors, Short bottom-N sectors.
    """

    def __init__(
        self,
        sector_universe: Optional[Sequence[str]] = None,
        gross_fraction: float = 0.20,
        per_name_cap: float = 0.05,
        n_long: int = 2,
        n_short: int = 2,
    ):
        self.sector_universe = [s.lower().strip() for s in (sector_universe or SECTOR_ETFS)]
        self.gross_fraction = float(gross_fraction)
        self.per_name_cap = float(per_name_cap)
        self.n_long = int(n_long)
        self.n_short = int(n_short)

    @property
    def name(self) -> str:
        return "sector_dollar_neutral_ls"

    def run(self, client: GreedBotClient, capital_usd: float = 10000.0) -> BotRunResult:
        if not math.isfinite(capital_usd) or capital_usd <= 0.0:
            raise ValueError(f"capital_usd must be finite and > 0, got {capital_usd}")

        # Sizing math checks
        per_leg_dollars = capital_usd * self.gross_fraction / 2.0
        per_long = per_leg_dollars / float(self.n_long)
        per_short = per_leg_dollars / float(self.n_short)
        cap_dollars = capital_usd * self.per_name_cap

        if per_long > cap_dollars + 1e-6 or per_short > cap_dollars + 1e-6:
            raise ValueError(
                f"Constructed per-name size ({per_long:.2f} long / {per_short:.2f} short) "
                f"exceeds PER_NAME_CAP ({cap_dollars:.2f}). Tighten gross_fraction or raise per_name_cap."
            )

        # 1. Fetch /pizza ranking over the sector universe
        pizza_resp = client.get_pizza(
            tickers=self.sector_universe,
            fundamentals_mode="off",
        )
        ranking = ranking_from_pizza(pizza_resp)
        if len(ranking) < (self.n_long + self.n_short):
            raise ValueError(
                f"Insufficient ranked sectors ({len(ranking)}) for N_LONG ({self.n_long}) + N_SHORT ({self.n_short})"
            )

        # 2. Pick top-N long (highest slice at end of ranking) and bottom-N short (lowest slice at beginning)
        shorts = [ticker for ticker, _ in ranking[:self.n_short]]
        longs = [ticker for ticker, _ in ranking[-self.n_long:]]

        # 3. Target dollar allocations (positive notionals for rebalance calculation)
        target_dollars: Dict[str, float] = {}
        for t in longs:
            target_dollars[t] = round(per_long, 2)
        for t in shorts:
            target_dollars[t] = round(per_short, 2)

        # 4. Rebalance long basket & short basket
        long_rebalance = client.get_rebalance(
            current={"ticker": [], "target": [], "cash": capital_usd},
            target={
                "ticker": longs,
                "target": [per_long] * len(longs),
                "cash": max(0.0, capital_usd - (per_long * len(longs))),
            },
            current_input_type="dollars",
            target_input_type="dollars",
            output_type="shares",
        )

        short_rebalance = client.get_rebalance(
            current={"ticker": [], "target": [], "cash": capital_usd},
            target={
                "ticker": shorts,
                "target": [per_short] * len(shorts),
                "cash": max(0.0, capital_usd - (per_short * len(shorts))),
            },
            current_input_type="dollars",
            target_input_type="dollars",
            output_type="shares",
        )

        # 5. Tag output trades with leg information
        combined_trades: List[Dict[str, Any]] = []
        for t in long_rebalance.get("trades", []):
            if isinstance(t, dict):
                t_copy = dict(t)
                t_copy["leg"] = "long"
                combined_trades.append(t_copy)

        for t in short_rebalance.get("trades", []):
            if isinstance(t, dict):
                t_copy = dict(t)
                t_copy["leg"] = "short"
                combined_trades.append(t_copy)

        # 6. Validate risk invariants
        risk_limits = RiskLimits(
            max_gross_fraction=self.gross_fraction,
            per_name_cap_fraction=self.per_name_cap,
        )
        risk_limits.validate_targets(capital_usd, target_dollars)

        # 7. Generate typed OrderIntents: Long -> Side.BUY, Short -> Side.SHORT_SELL
        intents: List[OrderIntent] = []
        for t in longs:
            intents.append(OrderIntent(ticker=t, side=Side.BUY, dollars=per_long))
        for t in shorts:
            intents.append(OrderIntent(ticker=t, side=Side.SHORT_SELL, dollars=per_short))

        gross_actual = (per_long * len(longs)) + (per_short * len(shorts))
        signed_actual = (per_long * len(longs)) - (per_short * len(shorts))

        summary = {
            "long_summary": long_rebalance.get("summary", {}),
            "short_summary": short_rebalance.get("summary", {}),
            "gross_dollars": round(gross_actual, 2),
            "signed_dollars": round(signed_actual, 2),
            "execution_note": (
                "Execute from BotRunResult.intents, which already encodes routing "
                "(Buy for long leg, ShortSell for short leg)."
            ),
        }

        return BotRunResult(
            trades=combined_trades,
            summary=summary,
            target_dollars=target_dollars,
            intents=intents,
        )
