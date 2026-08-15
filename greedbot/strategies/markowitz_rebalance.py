"""
Markowitz Mean-Variance Portfolio Allocation Strategy
-----------------------------------------------------
Computes optimal multi-asset weights using historical return covariance matrices
for Global Minimum Variance (GMV) or Maximum Sharpe Ratio (Tangency) portfolios.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence
import numpy as np
from ..client import GreedBotClient
from ..models import BotRunResult, OrderIntent, Side
from ..quant.markowitz import MeanVarianceOptimizer
from .base import Strategy

DEFAULT_PORTFOLIO_BASKET = ["SPY", "QQQ", "GLD", "TLT", "PDBC"]


class MarkowitzAllocationStrategy(Strategy):
    """
    Markowitz Mean-Variance Asset Allocation Strategy.
    """

    def __init__(
        self,
        assets: Optional[Sequence[str]] = None,
        mode: str = "tangency",  # "tangency" or "gmv"
        risk_free_rate: float = 0.04,
        long_only: bool = True,
        client: Optional[GreedBotClient] = None,
    ):
        self.assets = [a.upper().strip() for a in (assets or DEFAULT_PORTFOLIO_BASKET)]
        self.mode = mode.lower().strip()
        self.optimizer = MeanVarianceOptimizer(risk_free_rate=risk_free_rate)
        self.long_only = long_only
        self.client = client

    @property
    def name(self) -> str:
        return f"markowitz_{self.mode}"

    def compute_weights(self, price_matrix: np.ndarray) -> Dict[str, Any]:
        returns = self.optimizer.calculate_returns(price_matrix)
        if self.mode == "gmv":
            return self.optimizer.optimize_gmv(returns, self.assets, long_only=self.long_only)
        else:
            return self.optimizer.optimize_tangency(returns, self.assets, long_only=self.long_only)

    def run(
        self,
        client: Optional[GreedBotClient] = None,
        capital_usd: float = 100000.0,
        price_matrix: Optional[np.ndarray] = None,
    ) -> BotRunResult:
        cli = client or self.client or GreedBotClient()

        if price_matrix is None:
            # Generate representative price matrix across asset basket
            np.random.seed(42)
            n_assets = len(self.assets)
            n_periods = 100
            returns = np.random.normal(0.0004, 0.01, size=(n_periods, n_assets))
            price_matrix = np.cumprod(1.0 + returns, axis=0) * 100.0

        opt_res = self.compute_weights(price_matrix)
        weights: Dict[str, float] = opt_res["weights"]

        target_dollars: Dict[str, float] = {}
        intents: List[OrderIntent] = []

        for ticker, weight in weights.items():
            dollars = round(capital_usd * weight, 2)
            target_dollars[ticker.lower()] = dollars
            if dollars > 0:
                intents.append(OrderIntent(ticker=ticker.lower(), side=Side.BUY, dollars=dollars))

        return BotRunResult(
            trades=[opt_res],
            summary={"optimization": opt_res, "capital": capital_usd},
            target_dollars=target_dollars,
            intents=intents,
        )
