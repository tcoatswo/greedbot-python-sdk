"""
GreedBot Qualitative LLM Overlay Engine
---------------------------------------
Pipes structured LLM qualitative catalyst sentiment & conviction against
options market-implied expected moves (/hub/earnings/expected-move) to identify
asymmetric volatility mispricings.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional, Union
from ..client import GreedBotClient
from ..models import BotRunResult
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
        qualitative_sentiment: Optional[float] = None,
        conviction: Optional[float] = None,
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
        if (qualitative_sentiment is None or conviction is None
                or not math.isfinite(qualitative_sentiment)
                or not math.isfinite(conviction)
                or not -1.0 <= qualitative_sentiment <= 1.0
                or not 0.0 <= conviction <= 1.0):
            raise ValueError("Provide validated sentiment [-1, 1] and conviction [0, 1]")

        exp = cli.get_hub_earnings_expected_move(ticker=sym)
        if not isinstance(exp, dict) or "expected_move_pct" not in exp:
            raise ValueError("Expected move data is unavailable")
        mkt_move = float(exp["expected_move_pct"])
        if not math.isfinite(mkt_move) or mkt_move <= 0:
            raise ValueError("Expected move must be finite and positive")

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

    def run(self, client: Optional[GreedBotClient] = None, capital_usd: float = 10000.0,
            qualitative_sentiment: Optional[float] = None,
            conviction: Optional[float] = None) -> BotRunResult:
        cli = client or self.client or GreedBotClient()
        div = self.evaluate_divergence(client=cli, ticker=self.default_ticker,
                                       qualitative_sentiment=qualitative_sentiment,
                                       conviction=conviction)
        # The assessment concerns option spreads. An equity OrderIntent cannot
        # express those legs, so do not manufacture an underlying-stock order.
        return BotRunResult(
            trades=[div],
            summary=div,
            target_dollars={},
            intents=[],
        )
