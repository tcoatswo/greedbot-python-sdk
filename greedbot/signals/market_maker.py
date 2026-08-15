"""
Avellaneda-Stoikov High-Frequency Market Making & Liquidity Provision Model
---------------------------------------------------------------------------
Implements inventory-risk-adjusted reservation prices, optimal quote spreads,
and limit bid/ask generation.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Optional
from .base import Signal, SignalDirection, SignalGenerator


class AvellanedaStoikovMarketMaker(SignalGenerator):
    """
    Avellaneda-Stoikov Market Making Model.
    
    Formulas:
        Reservation Price:
            r(s, t) = s - q * gamma * sigma^2 * (T - t)
            
        Optimal Spread:
            delta = gamma * sigma^2 * (T - t) + (2 / gamma) * ln(1 + (gamma / k))
            
        Quotes:
            Bid = r - delta / 2
            Ask = r + delta / 2
            
    Where:
        s:      Mid-price
        q:      Current inventory (positive = long, negative = short)
        gamma:  Risk aversion parameter (> 0)
        sigma:  Asset volatility (annualized or per-period standard deviation)
        (T-t):  Fraction of trading session remaining (0.0 to 1.0)
        k:      Order book liquidity density / arrival rate parameter (> 0)
    """

    def __init__(
        self,
        gamma: float = 0.1,
        k: float = 1.5,
        default_horizon: float = 1.0,
        precision: int = 4,
    ):
        if gamma <= 0.0:
            raise ValueError(f"gamma must be > 0, got {gamma}")
        if k <= 0.0:
            raise ValueError(f"k must be > 0, got {k}")
        self.gamma = gamma
        self.k = k
        self.default_horizon = default_horizon
        self.precision = precision

    @property
    def name(self) -> str:
        return f"avellaneda_stoikov_g{self.gamma}_k{self.k}"

    def calculate_quotes(
        self,
        mid_price: float,
        inventory_q: float,
        volatility_sigma: float,
        time_remaining: Optional[float] = None,
    ) -> Dict[str, float]:
        if mid_price <= 0.0:
            raise ValueError(f"mid_price must be > 0, got {mid_price}")
        if volatility_sigma < 0.0:
            raise ValueError(f"volatility_sigma must be >= 0, got {volatility_sigma}")

        t_rem = self.default_horizon if time_remaining is None else max(1e-4, time_remaining)
        sigma2 = volatility_sigma ** 2

        # 1. Reservation Price
        reservation_price = mid_price - (inventory_q * self.gamma * sigma2 * t_rem)

        # 2. Optimal Total Spread
        # delta = gamma * sigma^2 * (T-t) + (2 / gamma) * ln(1 + gamma / k)
        spread = (self.gamma * sigma2 * t_rem) + ((2.0 / self.gamma) * math.log(1.0 + (self.gamma / self.k)))
        half_spread = spread / 2.0

        bid_price = round(reservation_price - half_spread, self.precision)
        ask_price = round(reservation_price + half_spread, self.precision)

        return {
            "mid_price": mid_price,
            "inventory_q": inventory_q,
            "reservation_price": round(reservation_price, self.precision),
            "spread": round(spread, self.precision),
            "bid_price": bid_price,
            "ask_price": ask_price,
            "bid_offset": round(mid_price - bid_price, self.precision),
            "ask_offset": round(ask_price - mid_price, self.precision),
        }

    def generate(
        self,
        ticker: str,
        mid_price: float,
        inventory_q: float = 0.0,
        volatility_sigma: float = 0.02,
        time_remaining: Optional[float] = None,
    ) -> Signal:
        quotes = self.calculate_quotes(
            mid_price=mid_price,
            inventory_q=inventory_q,
            volatility_sigma=volatility_sigma,
            time_remaining=time_remaining,
        )

        return Signal(
            ticker=ticker.upper(),
            direction=SignalDirection.PROVIDE_LIQUIDITY,
            strength=1.0,
            price=mid_price,
            indicator_values={
                "bid": quotes["bid_price"],
                "ask": quotes["ask_price"],
                "reservation_price": quotes["reservation_price"],
                "spread": quotes["spread"],
            },
            metadata={
                "inventory_q": inventory_q,
                "gamma": self.gamma,
                "k": self.k,
                "quotes": quotes,
            },
        )
