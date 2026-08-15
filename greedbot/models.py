"""
GreedBot Data Models & Primitives
---------------------------------
Typed dataclasses, enums, and data models representing GreedBot API payloads,
order intents, slot currency, risk parameters, and execution fills.
"""

from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union


class Side(str, Enum):
    """
    Direction of an order intent.

    ShortSell and BuyToCover are distinct from Sell and Buy because the
    /rebalance endpoint emits positive-notional trades; a short leg is
    a routing directive the executing side must honor, not a sign bit.
    """
    BUY = "Buy"
    SELL = "Sell"
    SHORT_SELL = "ShortSell"
    BUY_TO_COVER = "BuyToCover"

    @classmethod
    def from_str(cls, value: str) -> Side:
        val = value.strip().lower()
        if val in ("buy", "long", "b"):
            return cls.BUY
        elif val in ("sell", "s"):
            return cls.SELL
        elif val in ("shortsell", "short_sell", "short", "ss"):
            return cls.SHORT_SELL
        elif val in ("buytocover", "buy_to_cover", "cover", "btc"):
            return cls.BUY_TO_COVER
        raise ValueError(f"Unknown side string: {value}")


@dataclass
class SlotInfo:
    """
    The `slot` block every hub response carries: which snapshot this is, and when it is effective.

    WHY A BOT SHOULD CHECK THIS:
    Hub endpoints are cached per slot, and while a bake is running (around 00:00 UTC)
    they deliberately serve the PREVIOUS slot rather than a half-written new one.
    Checking the effective window turns that silent staleness into a proactive decision.
    """
    year: int
    refresh_n: int
    interval: str
    quote_type: str
    effective_at: str  # RFC3339 UTC string
    effective_until: str  # RFC3339 UTC string

    @classmethod
    def from_payload(cls, payload: Dict[str, Any]) -> Optional[SlotInfo]:
        """Parse slot info from an API response body containing a 'slot' key."""
        if not isinstance(payload, dict):
            return None
        slot = payload.get("slot")
        if not isinstance(slot, dict):
            return None

        try:
            year = int(slot["year"])
            refresh_n = int(slot["refresh_n"])
            interval = str(slot["interval"])
            quote_type = str(slot["quote_type"])
            effective_at = str(slot["effective_at"])
            effective_until = str(slot["effective_until"])
            return cls(
                year=year,
                refresh_n=refresh_n,
                interval=interval,
                quote_type=quote_type,
                effective_at=effective_at,
                effective_until=effective_until,
            )
        except (KeyError, ValueError, TypeError):
            return None

    def _parse_ts(self, ts_str: str) -> Optional[datetime.datetime]:
        """Parse ISO8601 / RFC3339 timestamp with UTC timezone."""
        try:
            cleaned = ts_str.strip()
            if cleaned.endswith("Z"):
                cleaned = cleaned[:-1] + "+00:00"
            return datetime.datetime.fromisoformat(cleaned)
        except Exception:
            return None

    def is_effective_at(self, dt: datetime.datetime) -> bool:
        """
        Whether this snapshot is still effective at the given datetime `dt`.

        Returns False if the window has closed (the slot is superseded) or timestamps
        cannot be parsed.
        """
        start = self._parse_ts(self.effective_at)
        end = self._parse_ts(self.effective_until)
        if start is None or end is None:
            return False

        # Ensure dt has timezone info
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=datetime.timezone.utc)
        if end.tzinfo is None:
            end = end.replace(tzinfo=datetime.timezone.utc)

        return start <= dt < end

    def is_effective_now(self) -> bool:
        """Whether this snapshot is still effective against current UTC time."""
        now = datetime.datetime.now(datetime.timezone.utc)
        return self.is_effective_at(now)


@dataclass
class OrderIntent:
    """
    One planned order: what a Strategy asks a Broker to execute.

    Dollar-denominated (quantity is derived at fill time from fill price).
    `limit`: strict limit price; None = marketable at supplied fill price.
    `stop`: planned stop-loss price for the resulting position.
    """
    ticker: str
    side: Side
    dollars: float
    limit: Optional[float] = None
    stop: Optional[float] = None

    def __post_init__(self):
        self.ticker = self.ticker.strip().lower()
        if isinstance(self.side, str) and not isinstance(self.side, Side):
            self.side = Side.from_str(self.side)
        if not math.isfinite(self.dollars) or self.dollars <= 0:
            raise ValueError(f"OrderIntent dollars must be finite and > 0, got {self.dollars}")
        if self.limit is not None and (not math.isfinite(self.limit) or self.limit <= 0):
            raise ValueError(f"OrderIntent limit must be finite and > 0, got {self.limit}")
        if self.stop is not None and (not math.isfinite(self.stop) or self.stop <= 0):
            raise ValueError(f"OrderIntent stop must be finite and > 0, got {self.stop}")


@dataclass
class Fill:
    """One executed order fill returned by a Broker."""
    ticker: str
    side: Side
    quantity: float
    price: float
    fees: float = 0.0

    def __post_init__(self):
        self.ticker = self.ticker.strip().lower()
        if isinstance(self.side, str) and not isinstance(self.side, Side):
            self.side = Side.from_str(self.side)


@dataclass
class BotRunResult:
    """
    Result of a bot strategy execution.

    `trades`: raw output from /rebalance/baked.
    `summary`: summary object from /rebalance/baked.
    `target_dollars`: per-ticker target dollar holdings used in rebalancing.
    `intents`: list of executable typed OrderIntent objects.
    """
    trades: Any
    summary: Any
    target_dollars: Dict[str, float]
    intents: List[OrderIntent] = field(default_factory=list)


@dataclass
class TradePlan:
    """
    A trade journal plan corresponding to GreedBot's unmetered /api/v1/log endpoint.
    """
    ticker: str
    direction: str  # "long" or "short"
    entry: str
    stop: str
    target: Optional[str] = None
    risk_amount: str = "500"
    account_equity: Optional[str] = None
    quote_type: str = "equity"
    exit_plan_type: str = "fixed_target"  # "fixed_target" | "trailing" | "time" | "discretionary"
    tags: List[str] = field(default_factory=list)
    thesis: str = "Quantitative model signal"
    logged_after_entry: bool = False
    id: Optional[str] = None
    status: Optional[str] = None  # "planned" | "open" | "closed" | "canceled"
    created_at: Optional[str] = None
    opened_at: Optional[str] = None
    closed_at: Optional[str] = None
    canceled_at: Optional[str] = None
    net_pnl: Optional[str] = None
    realized_r: Optional[str] = None
    exit_reason: Optional[str] = None
    exit_notes: Optional[str] = None
    cancel_reason: Optional[str] = None
    followed_plan: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "ticker": self.ticker.upper(),
            "direction": self.direction.lower(),
            "entry": str(self.entry),
            "stop": str(self.stop),
            "risk_amount": str(self.risk_amount),
            "thesis": str(self.thesis),
            "quote_type": self.quote_type,
            "exit_plan_type": self.exit_plan_type,
            "logged_after_entry": self.logged_after_entry,
        }
        if self.target:
            d["target"] = str(self.target)
        if self.account_equity:
            d["account_equity"] = str(self.account_equity)
        if self.tags:
            d["tags"] = self.tags
        return d
