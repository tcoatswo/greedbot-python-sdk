"""
GreedBot Hosted Bot Fleet Follower & Copy Trading Strategy
----------------------------------------------------------
Tracks evidence-ranked paper trading bots on the GreedBot hosted fleet (/api/v1/bots),
inspects open and planned books (/api/v1/bots/{id}/book), and replicates their allocations.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional
from ..client import GreedBotClient
from ..models import BotRunResult, OrderIntent, Side
from .base import Strategy


class BotFleetFollower(Strategy):
    """
    Follower strategy for copying allocations from top-performing GreedBot hosted bots.
    """

    def __init__(self, target_bot_id: Optional[str] = None, min_expectancy_r: float = 0.20):
        self.target_bot_id = target_bot_id
        self.min_expectancy_r = float(min_expectancy_r)

    @property
    def name(self) -> str:
        return f"bot_fleet_follower_{self.target_bot_id or 'auto'}"

    def select_best_bot(self, client: GreedBotClient) -> Optional[Dict[str, Any]]:
        """Find the highest ranked active bot by expectancy and e-value."""
        bots_data = client.get_bots()
        bots = bots_data.get("bots", []) if isinstance(bots_data, dict) else []

        active_bots = [
            b for b in bots
            if isinstance(b, dict)
            and not b.get("retired")
            and float(b.get("expectancy_r", 0.0) or 0.0) >= self.min_expectancy_r
        ]

        if not active_bots:
            return bots[0] if bots else None

        # Sort by evidence value & expectancy
        active_bots.sort(
            key=lambda b: (float(b.get("e_value", 0.0) or 0.0), float(b.get("expectancy_r", 0.0) or 0.0)),
            reverse=True,
        )
        return active_bots[0]

    def run(self, client: GreedBotClient, capital_usd: float = 10000.0) -> BotRunResult:
        if not math.isfinite(capital_usd) or capital_usd <= 0.0:
            raise ValueError(f"capital_usd must be finite and > 0, got {capital_usd}")

        bot_id = self.target_bot_id
        if not bot_id:
            best_bot = self.select_best_bot(client)
            if not best_bot:
                return BotRunResult(trades=[], summary={"status": "No active bots found"}, target_dollars={}, intents=[])
            bot_id = str(best_bot.get("id", ""))

        # Fetch the selected bot's book
        book_resp = client.get_bot_book(bot_id=bot_id)
        open_positions = book_resp.get("open_positions", []) if isinstance(book_resp, dict) else []

        if not open_positions:
            return BotRunResult(
                trades=[],
                summary={"bot_id": bot_id, "status": "Bot currently has no open positions"},
                target_dollars={},
                intents=[],
            )

        per_pos_dollars = round(capital_usd / len(open_positions), 2)
        target_dollars: Dict[str, float] = {}
        intents: List[OrderIntent] = []

        for pos in open_positions:
            sym = pos.get("ticker", "").lower().strip()
            direction = pos.get("direction", "long").lower()
            side = Side.BUY if direction == "long" else Side.SHORT_SELL

            target_dollars[sym] = per_pos_dollars
            intents.append(OrderIntent(ticker=sym, side=side, dollars=per_pos_dollars))

        return BotRunResult(
            trades=open_positions,
            summary={"followed_bot_id": bot_id, "positions_count": len(open_positions)},
            target_dollars=target_dollars,
            intents=intents,
        )
