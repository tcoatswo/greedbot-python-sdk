"""
GreedBot Option Kelly Convexity Sizing Engine
---------------------------------------------
Non-linear Kelly capital allocation for derivative options trading.
Combines directional Kelly score from /kelly with options market expected move
from /hub/earnings/expected-move to size convex asymmetric risk budgets.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Union
import numpy as np
from ..client import GreedBotClient
from ..models import BotRunResult, OrderIntent, Side
from ..quant.jump_kelly import compute_jump_kelly
from .base import Strategy


class OptionKellyEngine(Strategy):
    """
    Non-linear Kelly Options Convexity Sizing Engine.
    """

    def __init__(
        self,
        client_or_ticker: Optional[Union[GreedBotClient, str]] = None,
        default_ticker: str = "nvda",
        max_risk_budget_pct: float = 0.20,
        client: Optional[GreedBotClient] = None,
    ):
        if isinstance(client_or_ticker, GreedBotClient):
            self.client = client_or_ticker
            self.default_ticker = default_ticker.strip().lower()
        elif isinstance(client_or_ticker, str):
            self.client = client
            self.default_ticker = client_or_ticker.strip().lower()
        else:
            self.client = client
            self.default_ticker = default_ticker.strip().lower()

        self.max_risk_budget_pct = float(max_risk_budget_pct)

    @property
    def name(self) -> str:
        return "option_kelly_convexity"

    def calculate_sizing(
        self,
        client_or_ticker: Optional[Union[GreedBotClient, str]] = None,
        ticker: Optional[str] = None,
        portfolio_size: float = 10000.0,
        client: Optional[GreedBotClient] = None,
    ) -> Dict[str, Any]:
        """
        Calculate option position sizing and risk budget based on Kelly fraction and expected move.
        """
        cli = client
        sym = ticker

        if isinstance(client_or_ticker, GreedBotClient):
            cli = cli or client_or_ticker
        elif isinstance(client_or_ticker, str):
            sym = sym or client_or_ticker

        cli = cli or self.client or GreedBotClient()
        sym = (sym or self.default_ticker).strip().lower()

        # 1. Fetch Kelly fraction
        kelly_val = 0.5
        try:
            kelly_resp = cli.get_kelly(tickers=[sym])
            if isinstance(kelly_resp, dict):
                df = kelly_resp.get("df", {})
                if "kelly" in df and df["kelly"]:
                    kelly_val = float(df["kelly"][0] or 0.5)
        except Exception:
            kelly_val = 0.5

        # 2. Fetch expected move
        expected_move_pct = 5.0
        try:
            exp_resp = cli.get_hub_earnings_expected_move(ticker=sym)
            if isinstance(exp_resp, dict):
                expected_move_pct = float(exp_resp.get("expected_move_pct", 5.0) or 5.0)
        except Exception:
            expected_move_pct = 5.0

        # 3. Calculate convex option risk budget via Merton Jump-Diffusion Kelly Engine
        try:
            f_star_arr = compute_jump_kelly(
                S=np.array([100.0]),
                O=np.array([max(0.10, 100.0 * (expected_move_pct / 100.0))]),
                delta=np.array([0.30 if kelly_val >= 0 else -0.30]),
                gamma=np.array([0.04]),
                theta=np.array([-0.05]),
                sigma=np.array([0.30]),
                mu=0.05,
                lambda_jump=1.5,
                mu_J=0.10,
                sigma_J=0.20,
                gamma_penalty=1.5,
            )
            jump_f = float(f_star_arr[0])
        except Exception:
            jump_f = 0.15 * max(0.05, min(abs(float(kelly_val)), 1.0))

        effective_fraction = jump_f if jump_f > 0 else (0.10 * max(0.05, min(abs(float(kelly_val)), 1.0)))
        risk_budget = round(portfolio_size * min(effective_fraction, self.max_risk_budget_pct), 2)
        direction = "CALL" if kelly_val >= 0 else "PUT"

        return {
            "ticker": sym.upper(),
            "kelly_conviction": round(effective_fraction, 4),
            "portfolio_size": portfolio_size,
            "max_risk_budget": risk_budget,
            "expected_move_pct": round(expected_move_pct, 2),
            "structure": "OUT_OF_THE_MONEY_SINGLE",
            "direction": direction,
            "engine": "Merton Jump-Diffusion Gauss-Hermite",
            "recommended_action": f"Buy OTM {direction} with max premium risk capped at ${risk_budget:.2f}",
        }

    def run(self, client: Optional[GreedBotClient] = None, capital_usd: float = 10000.0) -> BotRunResult:
        cli = client or self.client or GreedBotClient()
        sizing = self.calculate_sizing(client=cli, ticker=self.default_ticker, portfolio_size=capital_usd)
        side = Side.BUY if sizing["direction"] == "CALL" else Side.SHORT_SELL
        dollars = sizing["max_risk_budget"]

        intents = [
            OrderIntent(
                ticker=self.default_ticker,
                side=side,
                dollars=dollars,
            )
        ]

        return BotRunResult(
            trades=[sizing],
            summary={"sizing_details": sizing},
            target_dollars={self.default_ticker: dollars},
            intents=intents,
        )
