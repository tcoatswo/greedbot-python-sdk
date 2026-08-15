"""
GreedBot Qualitative LLM Overlay Engine
---------------------------------------
Pipes structured LLM qualitative catalyst sentiment & conviction against
options market-implied expected moves (/hub/earnings/expected-move) to identify
asymmetric volatility mispricings.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Union
from ..client import GreedBotClient
from ..models import BotRunResult, OrderIntent, Side
from .base import Strategy


class QualitativeOverlayEngine(Strategy):
    """
    Qualitative LLM Overlay vs Implied Move Engine.
    """

    def __init__(
        self,
        client_or_ticker: Optional[Union[GreedBotClient, str]] = None,
        default_ticker: str = "nvda",
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

    @property
    def name(self) -> str:
        return "qualitative_llm_overlay"

    def evaluate_divergence(
        self,
        client_or_ticker: Optional[Union[GreedBotClient, str]] = None,
        ticker: Optional[str] = None,
        qualitative_sentiment: float = 0.85,
        conviction: float = 0.85,
        client: Optional[GreedBotClient] = None,
    ) -> Dict[str, Any]:
        """
        Compare market-implied expected move with LLM qualitative expected move.
        """
        cli = client
        sym = ticker

        if isinstance(client_or_ticker, GreedBotClient):
            cli = cli or client_or_ticker
        elif isinstance(client_or_ticker, str):
            sym = sym or client_or_ticker

        cli = cli or self.client or GreedBotClient()
        sym = (sym or self.default_ticker).strip().lower()

        try:
            exp = cli.get_hub_earnings_expected_move(ticker=sym)
            mkt_move = float(exp.get("expected_move_pct", 5.0) or 5.0) if isinstance(exp, dict) else 5.0
        except Exception:
            mkt_move = 5.0

        # Compute qualitative expected move
        qual_move = round(mkt_move * (1.0 + (qualitative_sentiment * conviction * 0.9)), 2)
        delta = round(qual_move - mkt_move, 2)

        if delta > 2.0:
            assessment = "ASYMMETRIC_UNDERPRICED_VOLATILITY"
            recommendation = f"Buy Out-of-the-Money Call Spread (Targeting +{qual_move}% move)"
        elif delta < -2.0:
            assessment = "OVERPRICED_IMPLIED_MOVE"
            recommendation = "Sell Option Premium / Credit Spread"
        else:
            assessment = "FAIRLY_PRICED"
            recommendation = "Neutral / Pass"

        return {
            "ticker": sym.upper(),
            "market_expected_move_pct": mkt_move,
            "qualitative_expected_move_pct": qual_move,
            "asymmetry_delta_pct": delta,
            "qualitative_sentiment": qualitative_sentiment,
            "catalyst_conviction": conviction,
            "assessment": assessment,
            "recommended_trade": recommendation,
        }

    def run(self, client: Optional[GreedBotClient] = None, capital_usd: float = 10000.0) -> BotRunResult:
        cli = client or self.client or GreedBotClient()
        div = self.evaluate_divergence(client=cli, ticker=self.default_ticker)
        intents = [
            OrderIntent(
                ticker=self.default_ticker,
                side=Side.BUY,
                dollars=capital_usd * 0.10,
            )
        ]
        return BotRunResult(
            trades=[div],
            summary=div,
            target_dollars={self.default_ticker: capital_usd * 0.10},
            intents=intents,
        )
