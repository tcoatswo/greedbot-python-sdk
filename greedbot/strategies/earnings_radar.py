"""
GreedBot Earnings Radar & Volatility Harvesting Strategies
----------------------------------------------------------
Event-driven options and equities strategies driven by the 90-day Earnings Radar
(/hub/earnings/latest) and event-dated options expected move (/hub/earnings/expected-move).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from ..client import GreedBotClient
from ..models import BotRunResult, OrderIntent, Side
from .base import Strategy


class EarningsRadarStrategy(Strategy):
    """
    90-day Earnings Radar strategy that filters reports by business-day windows
    ('today', 'next-bd', 'next-7-bd', 'next-30-bd', 'next-90-days') and prices
    event-dated options expected moves.
    """

    def __init__(self, target_window: str = "next-7-bd", max_candidates: int = 5):
        self.target_window = target_window
        self.max_candidates = int(max_candidates)

    @property
    def name(self) -> str:
        return f"earnings_radar_{self.target_window}"

    def scan_radar(self, client: GreedBotClient) -> List[Dict[str, Any]]:
        """
        Scan qualifying reports within the target horizon and price their expected moves.
        """
        radar_resp = client.get_hub_earnings()
        reports = radar_resp.get("reports", []) if isinstance(radar_resp, dict) else []

        candidates: List[Dict[str, Any]] = []
        for r in reports:
            if not isinstance(r, dict):
                continue
            window = r.get("window", "")
            ticker = r.get("ticker", "")
            if not ticker:
                continue

            # Check if report falls within the target horizon
            if self.target_window == "all" or window == self.target_window:
                # Price expected move
                try:
                    exp = client.get_hub_earnings_expected_move(ticker=ticker)
                    exp_pct = float(exp.get("expected_move_pct", 5.0) or 5.0)
                    status = exp.get("status", "priced")
                except Exception:
                    exp_pct = 5.0
                    status = "estimated"

                candidates.append({
                    "ticker": ticker.upper(),
                    "report_date": r.get("report_date", ""),
                    "window": window,
                    "model_rank": r.get("rank", 999),
                    "expected_move_pct": exp_pct,
                    "status": status,
                    "strategy": "PRE_EARNINGS_CONVEXITY",
                })

            if len(candidates) >= self.max_candidates:
                break

        return candidates

    def run(self, client: GreedBotClient, capital_usd: float = 10000.0) -> BotRunResult:
        candidates = self.scan_radar(client)
        if not candidates:
            return BotRunResult(trades=[], summary={"status": "No upcoming earnings candidates found"}, target_dollars={}, intents=[])

        per_candidate_capital = round(capital_usd / len(candidates), 2)
        intents: List[OrderIntent] = []
        target_dollars: Dict[str, float] = {}

        for c in candidates:
            sym = c["ticker"].lower()
            intents.append(OrderIntent(ticker=sym, side=Side.BUY, dollars=per_candidate_capital))
            target_dollars[sym] = per_candidate_capital

        return BotRunResult(
            trades=candidates,
            summary={"candidates_count": len(candidates), "target_window": self.target_window},
            target_dollars=target_dollars,
            intents=intents,
        )


class VolatilityHarvestEngine:
    """
    Scans for high-implied-volatility earnings setups for delta-neutral Iron Condors.
    """

    def __init__(self, client: Optional[GreedBotClient] = None):
        self.client = client or GreedBotClient()

    def scan_harvest(self) -> List[Dict[str, Any]]:
        radar = self.client.get_hub_earnings()
        reports = radar.get("reports", []) if isinstance(radar, dict) else []

        candidates: List[Dict[str, Any]] = []
        for item in reports:
            if not isinstance(item, dict):
                continue
            sym = item.get("ticker", "")
            iv = float(item.get("implied_volatility", 0.0) or 0.0)
            if iv > 50.0 or item.get("window") in ("today", "next-bd"):
                candidates.append({
                    "ticker": sym.upper(),
                    "report_date": item.get("report_date", ""),
                    "window": item.get("window", ""),
                    "strategy": "IRON_CONDOR_VOLATILITY_HARVEST",
                    "implied_volatility": iv,
                    "action": "Sell Iron Condor outside 1-Sigma Expected Move Boundary",
                })
        return candidates


class SectorSpilloverArb:
    """
    Identifies sympathy volatility spillover opportunities during earnings cycles.
    """

    def __init__(self, client: Optional[GreedBotClient] = None):
        self.client = client or GreedBotClient()

    def scan_spillovers(self) -> List[Dict[str, Any]]:
        radar = self.client.get_hub_earnings()
        reports = radar.get("reports", []) if isinstance(radar, dict) else []

        opportunities: List[Dict[str, Any]] = []
        for e in reports:
            if not isinstance(e, dict):
                continue
            sym = e.get("ticker", "")
            iv = float(e.get("implied_volatility", 0.0) or 0.0)
            if iv > 60.0 or e.get("window") in ("today", "next-bd"):
                opportunities.append({
                    "primary_ticker": sym.upper(),
                    "sector": e.get("sector", "Tech"),
                    "implied_volatility": iv,
                    "spillover_targets": e.get("sympathy_tickers", []),
                    "strategy": "SECTOR_VOL_CONTAGION_ARB",
                })
        return opportunities
