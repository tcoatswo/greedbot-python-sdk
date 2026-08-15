"""
GreedBot Macro Dynamic Regime-Switching Matrix
----------------------------------------------
Dynamically rebalances multi-asset portfolios across Equities, Commodities,
Bonds, and Defensive Cash based on macroeconomic cycle indicators from /hub/macro/latest.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence, Union
from ..client import GreedBotClient
from ..models import BotRunResult, OrderIntent, Side
from .base import Strategy

DEFAULT_MACRO_BASKET: Dict[str, str] = {
    "spy": "US Equities",
    "qqq": "Tech Growth",
    "gld": "Gold / Inflation Hedge",
    "tlt": "Long-Term Treasuries",
    "pdbc": "Commodities",
}


class MacroRegimeMatrix(Strategy):
    """
    Dynamic Macro Regime-Switching Strategy.
    Adjusts asset weights according to prevailing macroeconomic regimes
    (Bull Momentum, Goldilocks, Stagflation, Contraction, Crisis).
    """

    def __init__(
        self,
        client_or_basket: Optional[Union[GreedBotClient, Dict[str, str]]] = None,
        asset_basket: Optional[Dict[str, str]] = None,
    ):
        if isinstance(client_or_basket, GreedBotClient):
            self.client = client_or_basket
            self.asset_basket = asset_basket or DEFAULT_MACRO_BASKET
        elif isinstance(client_or_basket, dict):
            self.client = None
            self.asset_basket = client_or_basket
        else:
            self.client = None
            self.asset_basket = asset_basket or DEFAULT_MACRO_BASKET

    @property
    def name(self) -> str:
        return "macro_dynamic_regime_matrix"

    def get_regime_allocations(
        self,
        client: Optional[GreedBotClient] = None,
        capital_usd: float = 100000.0
    ) -> Dict[str, Any]:
        cli = client or self.client or GreedBotClient()
        macro = cli.get_hub_macro()
        regime = macro.get("regime", "BULL_MOMENTUM") if isinstance(macro, dict) else "BULL_MOMENTUM"

        # Regime-specific target weights
        regime_weights: Dict[str, Dict[str, float]] = {
            "BULL_MOMENTUM": {"qqq": 0.40, "spy": 0.35, "gld": 0.10, "pdbc": 0.10, "tlt": 0.05},
            "GOLDILOCKS": {"spy": 0.45, "qqq": 0.35, "tlt": 0.10, "gld": 0.05, "pdbc": 0.05},
            "STAGFLATION": {"gld": 0.35, "pdbc": 0.35, "spy": 0.15, "tlt": 0.05, "qqq": 0.10},
            "CONTRACTION": {"tlt": 0.40, "gld": 0.30, "spy": 0.15, "qqq": 0.10, "pdbc": 0.05},
            "CRISIS": {"tlt": 0.50, "gld": 0.30, "spy": 0.10, "qqq": 0.05, "pdbc": 0.05},
        }

        weights = regime_weights.get(regime.upper(), regime_weights["BULL_MOMENTUM"])
        allocations: Dict[str, Dict[str, float]] = {}

        for ticker, weight in weights.items():
            allocations[ticker.upper()] = {
                "asset_class": self.asset_basket.get(ticker, "Asset"),
                "target_weight_pct": round(weight * 100, 2),
                "target_dollars": round(capital_usd * weight, 2),
            }

        return {
            "active_regime": regime,
            "macro_opinion": macro.get("opinion", "Expansionary") if isinstance(macro, dict) else "Expansionary",
            "portfolio_capital": capital_usd,
            "allocations": allocations,
        }

    def run(self, client: Optional[GreedBotClient] = None, capital_usd: float = 100000.0) -> BotRunResult:
        cli = client or self.client or GreedBotClient()
        res = self.get_regime_allocations(cli, capital_usd)
        target_dollars: Dict[str, float] = {
            t.lower(): details["target_dollars"] for t, details in res["allocations"].items()
        }

        intents: List[OrderIntent] = [
            OrderIntent(ticker=t, side=Side.BUY, dollars=dollars)
            for t, dollars in target_dollars.items()
            if dollars > 0
        ]

        return BotRunResult(
            trades=list(res["allocations"].values()),
            summary=res,
            target_dollars=target_dollars,
            intents=intents,
        )
