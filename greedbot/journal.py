"""
GreedBot Trade Journal Helper
-----------------------------
High-level management of trading plans, lifecycle tracking, and execution logging
using GreedBot's unmetered /api/v1/log endpoints.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Union
from .client import GreedBotClient
from .models import BotRunResult, OrderIntent, Side, TradePlan

logger = logging.getLogger("greedbot.journal")


class TradeJournal:
    """
    High-level trade log manager for creating, tracking, and closing trade plans.
    All calls to /api/v1/log are completely unmetered (free with an account).
    """

    def __init__(self, client: Optional[GreedBotClient] = None):
        self.client = client or GreedBotClient()

    def record_plan(
        self,
        ticker: str,
        direction: str,
        entry: float,
        stop: float,
        target: Optional[float] = None,
        risk_amount: float = 500.0,
        thesis: str = "Quantitative model signal",
        tags: Optional[List[str]] = None,
        account_equity: Optional[float] = None,
        exit_plan_type: str = "fixed_target",
    ) -> str:
        """
        Record a new planned trade before taking entry.
        Returns the new plan ID.
        """
        plan = TradePlan(
            ticker=ticker.upper().strip(),
            direction=direction.lower().strip(),
            entry=f"{entry:.2f}",
            stop=f"{stop:.2f}",
            target=f"{target:.2f}" if target is not None else None,
            risk_amount=f"{risk_amount:.2f}",
            account_equity=f"{account_equity:.2f}" if account_equity is not None else None,
            thesis=thesis,
            tags=tags or ["algo", "greedbot"],
            exit_plan_type=exit_plan_type,
        )
        res = self.client.create_log(plan)
        plan_id = res.get("id", "")
        logger.info(f"Recorded trade plan {plan_id} for {ticker} ({direction})")
        return plan_id

    def open_trade(
        self,
        plan_id: str,
        entry_price: Optional[float] = None,
        shares: Optional[float] = None,
        opened_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark an existing planned trade as filled/opened."""
        return self.client.open_log(
            log_id=plan_id,
            entry_price=f"{entry_price:.2f}" if entry_price is not None else None,
            shares=f"{shares:.4f}" if shares is not None else None,
            opened_at=opened_at,
        )

    def close_trade(
        self,
        plan_id: str,
        exit_price: Optional[float] = None,
        net_pnl: Optional[float] = None,
        realized_r: Optional[float] = None,
        exit_reason: str = "target",
        exit_notes: str = "",
        followed_plan: str = "yes",
        closed_at: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Mark an open trade as closed with performance metrics."""
        return self.client.close_log(
            log_id=plan_id,
            exit_price=f"{exit_price:.2f}" if exit_price is not None else None,
            net_pnl=f"{net_pnl:.2f}" if net_pnl is not None else None,
            realized_r=f"{realized_r:.2f}" if realized_r is not None else None,
            exit_reason=exit_reason,
            exit_notes=exit_notes,
            followed_plan=followed_plan,
            closed_at=closed_at,
        )

    def cancel_trade(self, plan_id: str, reason: str = "Expired / Condition not met") -> Dict[str, Any]:
        """Cancel a trade plan before entry."""
        return self.client.cancel_log(log_id=plan_id, cancel_reason=reason)

    def get_active_plans(self, ticker: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all active (planned + open) trade plans."""
        res = self.client.list_logs(status="active", ticker=ticker)
        return res.get("plans", [])

    def sync_bot_result(
        self,
        result: BotRunResult,
        thesis: str = "GreedBot Strategy Execution",
        tags: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Automatically log all generated order intents from a BotRunResult into the Trade Journal.
        Returns the list of created plan IDs.
        """
        plan_ids: List[str] = []
        for intent in result.intents:
            direction = "long" if intent.side in (Side.BUY, Side.BUY_TO_COVER) else "short"
            entry = intent.limit or 100.0  # reference entry
            # Default stop at 8% risk if none specified
            stop = intent.stop or (entry * 0.92 if direction == "long" else entry * 1.08)
            target = entry * 1.15 if direction == "long" else entry * 0.85

            plan_id = self.record_plan(
                ticker=intent.ticker,
                direction=direction,
                entry=entry,
                stop=stop,
                target=target,
                risk_amount=intent.dollars * 0.08,
                thesis=thesis,
                tags=tags or ["automated", "bot_execution"],
            )
            plan_ids.append(plan_id)

        return plan_ids
