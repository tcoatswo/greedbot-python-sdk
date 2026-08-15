"""
GreedBot Broker & Paper Execution Backend
-----------------------------------------
Defines the `Broker` abstract base class and `PaperBroker` reference simulated
execution backend with strict limit enforcement, reduce/close-only validation,
caller-supplied price fills (no lookahead), and batch-atomic rollback.
"""

from __future__ import annotations

import abc
import copy
import math
from typing import Dict, List, Optional, Sequence
from .models import Fill, OrderIntent, Side

# Float-dust tolerances
CASH_EPSILON: float = 1e-9
QUANTITY_EPSILON: float = 1e-9


class Broker(abc.ABC):
    """
    Execution backend interface: order intents in, fills out.
    """

    @abc.abstractmethod
    def execute(
        self,
        intents: Sequence[OrderIntent],
        prices: Dict[str, float]
    ) -> List[Fill]:
        """
        Execute order intents against the supplied per-ticker prices.
        Returns the fills that actually occurred.
        """
        pass

    @property
    @abc.abstractmethod
    def cash(self) -> float:
        """Current cash balance in USD."""
        pass

    @property
    @abc.abstractmethod
    def positions(self) -> Dict[str, float]:
        """Current signed share positions (positive = long, negative = short)."""
        pass


class PaperBroker(Broker):
    """
    Simulated broker for paper trading.

    Fill Model & Invariants:
    1. Caller-supplied prices only: Fills happen ONLY at prices passed by the caller
       (e.g., next bar's open after the signal bake). There is no hidden price feed.
    2. Limit order logic:
       - Buy / BuyToCover: fills only if price <= limit.
       - Sell / ShortSell: fills only if price >= limit.
       - Malformed limit (NaN, <= 0, inf) rejects the entire batch.
    3. Reduce/close-only validation:
       - `Sell` is reduce/close-only for long positions; selling more than held or while flat
         is rejected to prevent unintended short opening.
       - `BuyToCover` is reduce/close-only for short positions; covering more than held or while flat
         is rejected to prevent unintended long opening.
       - Opening sides are explicitly `Buy` and `ShortSell`.
    4. Overdraft protection:
       - Insufficient cash (including fee_per_fill) rejects the entire batch.
    5. Batch-atomic rollback:
       - Staged mutations only commit if every intent in the batch executes without error.
    """

    def __init__(self, cash_usd: float, fee_per_fill: float = 0.0):
        if not math.isfinite(cash_usd) or cash_usd <= 0.0:
            raise ValueError(f"cash_usd must be finite and > 0, got {cash_usd}")
        if not math.isfinite(fee_per_fill) or fee_per_fill < 0.0:
            raise ValueError(f"fee_per_fill must be finite and >= 0, got {fee_per_fill}")

        self._cash: float = float(cash_usd)
        self._positions: Dict[str, float] = {}
        self.fee_per_fill: float = float(fee_per_fill)

    @property
    def cash(self) -> float:
        return self._cash

    @property
    def positions(self) -> Dict[str, float]:
        return dict(self._positions)

    @staticmethod
    def _limit_allows(side: Side, limit: float, price: float) -> bool:
        if side in (Side.BUY, Side.BUY_TO_COVER):
            return price <= limit
        else:  # SELL, SHORT_SELL
            return price >= limit

    def execute(
        self,
        intents: Sequence[OrderIntent],
        prices: Dict[str, float]
    ) -> List[Fill]:
        # Normalize prices dictionary keys
        norm_prices = {k.strip().lower(): float(v) for k, v in prices.items()}

        # Staged state for batch atomicity
        staged_cash = self._cash
        staged_positions = copy.deepcopy(self._positions)
        fills: List[Fill] = []

        for intent in intents:
            ticker = intent.ticker.strip().lower()

            if not math.isfinite(intent.dollars) or intent.dollars <= 0.0:
                raise ValueError(
                    f"intent for {ticker} has non-positive dollars {intent.dollars}"
                )

            if intent.limit is not None:
                if not math.isfinite(intent.limit) or intent.limit <= 0.0:
                    raise ValueError(
                        f"intent for {ticker} has invalid limit {intent.limit}: must be finite and > 0"
                    )

            if ticker not in norm_prices:
                # No price for this bar: the order rests, nothing fills
                continue

            price = norm_prices[ticker]
            if not math.isfinite(price) or price <= 0.0:
                raise ValueError(f"non-positive price for {ticker}: {price}")

            if intent.limit is not None and not self._limit_allows(intent.side, intent.limit, price):
                continue

            quantity = intent.dollars / price
            held = staged_positions.get(ticker, 0.0)

            # Reduce/close-only sides validate against staged position
            if intent.side == Side.SELL:
                if quantity > held + QUANTITY_EPSILON:
                    raise ValueError(
                        f"sell of {quantity:.4f} shares of {ticker} exceeds current long position "
                        f"({held:.4f}): Sell is reduce/close-only; use ShortSell to open a short"
                    )
            elif intent.side == Side.BUY_TO_COVER:
                if quantity > -held + QUANTITY_EPSILON:
                    raise ValueError(
                        f"buy-to-cover of {quantity:.4f} shares of {ticker} exceeds current short "
                        f"position ({held:.4f}): BuyToCover is reduce/close-only; use Buy to open a long"
                    )

            # Calculate cash and position deltas
            if intent.side in (Side.BUY, Side.BUY_TO_COVER):
                cash_delta = -intent.dollars
                pos_delta = quantity
            else:  # SELL, SHORT_SELL
                cash_delta = intent.dollars
                pos_delta = -quantity

            new_cash = staged_cash + cash_delta - self.fee_per_fill
            if new_cash < -CASH_EPSILON:
                side_name = intent.side.value.lower()
                raise ValueError(
                    f"insufficient cash for {side_name} intent on {ticker}: "
                    f"cash {staged_cash:.2f}, needed {intent.dollars + self.fee_per_fill:.2f}"
                )

            # Clamp float dust so exactly-funded batches land on 0.00
            staged_cash = max(0.0, new_cash)
            new_pos = held + pos_delta

            # If position is approximately zero, remove or set to 0.0
            if abs(new_pos) < QUANTITY_EPSILON:
                staged_positions.pop(ticker, None)
            else:
                staged_positions[ticker] = new_pos

            fills.append(
                Fill(
                    ticker=ticker,
                    side=intent.side,
                    quantity=quantity,
                    price=price,
                    fees=self.fee_per_fill,
                )
            )

        # Commit staged state on successful batch completion
        self._cash = staged_cash
        self._positions = staged_positions
        return fills
