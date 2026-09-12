"""
GreedBot Multi-Leg Options Spread Engine & Payoff Profiler
---------------------------------------------------------
Constructs multi-leg option strategies (Iron Condor, Verticals, Straddles, Strangles,
Butterflies, Calendars) with composite Greeks, expiration P&L, break-evens, and margin requirements.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math

from .rust_engine import calculate_greeks, OptionGreeks

@dataclass
class OptionLeg:
    strike: float
    dte: float
    is_call: bool
    is_long: bool
    quantity: int = 1
    premium: Optional[float] = None
    iv: float = 0.20

    def get_greeks(self, spot: float, rate: float = 0.045) -> OptionGreeks:
        g = calculate_greeks(
            spot=spot,
            strike=self.strike,
            dte=max(self.dte, 1.0),
            iv=self.iv,
            is_call=self.is_call,
            rate=rate
        )
        multiplier = self.quantity if self.is_long else -self.quantity
        return OptionGreeks(
            price=g.price * multiplier,
            delta=g.delta * multiplier,
            gamma=g.gamma * multiplier,
            vega=g.vega * multiplier,
            theta=g.theta * multiplier,
            rho=g.rho * multiplier,
            vanna=g.vanna * multiplier,
            volga=g.volga * multiplier,
            iv=self.iv,
        )

    def payoff_at_expiration(self, spot_at_expiry: float) -> float:
        if self.is_call:
            intrinsic = max(0.0, spot_at_expiry - self.strike)
        else:
            intrinsic = max(0.0, self.strike - spot_at_expiry)
        
        prem = self.premium if self.premium is not None else 0.0
        if self.is_long:
            return (intrinsic - prem) * self.quantity * 100.0
        else:
            return (prem - intrinsic) * self.quantity * 100.0


@dataclass
class CompositeSpreadGreeks:
    net_delta: float
    net_gamma: float
    net_vega: float
    net_theta: float
    net_cost: float
    max_profit: Optional[float]
    max_loss: Optional[float]
    break_even_points: List[float]


class OptionSpread:
    """Base class for multi-leg option strategies."""
    
    def __init__(self, name: str, legs: List[OptionLeg]):
        self.name = name
        self.legs = legs

    def get_net_greeks(self, spot: float, rate: float = 0.045) -> CompositeSpreadGreeks:
        net_delta = 0.0
        net_gamma = 0.0
        net_vega = 0.0
        net_theta = 0.0
        net_cost = 0.0

        for leg in self.legs:
            g = leg.get_greeks(spot, rate)
            net_delta += g.delta
            net_gamma += g.gamma
            net_vega += g.vega
            net_theta += g.theta
            cost_per_share = (leg.premium if leg.premium is not None else abs(g.price))
            net_cost += cost_per_share * (100.0 * leg.quantity if leg.is_long else -100.0 * leg.quantity)

        # Calculate P&L profile across a price sweep
        min_strike = min(leg.strike for leg in self.legs)
        max_strike = max(leg.strike for leg in self.legs)
        sweep_low = min(spot * 0.70, min_strike * 0.85)
        sweep_high = max(spot * 1.30, max_strike * 1.15)
        steps = 200
        step_size = (sweep_high - sweep_low) / steps

        payouts = []
        break_evens = []
        prev_payout = None
        prev_s = None

        for i in range(steps + 1):
            s = sweep_low + i * step_size
            payout = sum(leg.payoff_at_expiration(s) for leg in self.legs)
            payouts.append(payout)
            if prev_payout is not None:
                if (prev_payout <= 0 and payout > 0) or (prev_payout >= 0 and payout < 0):
                    be = prev_s + (0 - prev_payout) * (s - prev_s) / (payout - prev_payout)
                    break_evens.append(round(be, 2))
            prev_payout = payout
            prev_s = s

        max_profit = max(payouts) if payouts else None
        max_loss = min(payouts) if payouts else None

        return CompositeSpreadGreeks(
            net_delta=net_delta,
            net_gamma=net_gamma,
            net_vega=net_vega,
            net_theta=net_theta,
            net_cost=net_cost,
            max_profit=max_profit,
            max_loss=max_loss,
            break_even_points=break_evens,
        )

    def generate_payoff_curve(self, spot: float, price_range_pct: float = 0.20, points: int = 50) -> List[Dict[str, float]]:
        low = spot * (1.0 - price_range_pct)
        high = spot * (1.0 + price_range_pct)
        step = (high - low) / (points - 1)
        curve = []
        for i in range(points):
            s = low + i * step
            pnl = sum(leg.payoff_at_expiration(s) for leg in self.legs)
            curve.append({"spot": round(s, 2), "pnl": round(pnl, 2)})
        return curve


class IronCondor(OptionSpread):
    """
    Constructs a 4-leg Iron Condor:
    - Long Put (wing)
    - Short Put (body)
    - Short Call (body)
    - Long Call (wing)
    """
    def __init__(
        self,
        spot: float,
        put_wing: float,
        put_short: float,
        call_short: float,
        call_wing: float,
        dte: float,
        iv: float = 0.20,
        quantity: int = 1,
    ):
        legs = [
            OptionLeg(strike=put_wing, dte=dte, is_call=False, is_long=True, quantity=quantity, iv=iv),
            OptionLeg(strike=put_short, dte=dte, is_call=False, is_long=False, quantity=quantity, iv=iv),
            OptionLeg(strike=call_short, dte=dte, is_call=True, is_long=False, quantity=quantity, iv=iv),
            OptionLeg(strike=call_wing, dte=dte, is_call=True, is_long=True, quantity=quantity, iv=iv),
        ]
        # Auto-compute standard theoretical premiums if none specified
        for leg in legs:
            g = calculate_greeks(spot, leg.strike, dte, iv, leg.is_call)
            leg.premium = g.price

        super().__init__(name=f"Iron Condor {put_wing}/{put_short}/{call_short}/{call_wing}", legs=legs)


class VerticalSpread(OptionSpread):
    """
    Constructs a 2-leg Vertical Spread (Bull Call, Bear Put, Bull Put, Bear Call).
    """
    def __init__(
        self,
        spot: float,
        long_strike: float,
        short_strike: float,
        dte: float,
        is_call: bool = True,
        iv: float = 0.20,
        quantity: int = 1,
    ):
        long_leg = OptionLeg(strike=long_strike, dte=dte, is_call=is_call, is_long=True, quantity=quantity, iv=iv)
        short_leg = OptionLeg(strike=short_strike, dte=dte, is_call=is_call, is_long=False, quantity=quantity, iv=iv)
        long_leg.premium = calculate_greeks(spot, long_strike, dte, iv, is_call).price
        short_leg.premium = calculate_greeks(spot, short_strike, dte, iv, is_call).price
        
        spread_type = "Debit" if long_leg.premium > short_leg.premium else "Credit"
        super().__init__(name=f"Vertical {spread_type} {'Call' if is_call else 'Put'} {long_strike}/{short_strike}", legs=[long_leg, short_leg])


class Straddle(OptionSpread):
    """Constructs a Long or Short Straddle at the same strike."""
    def __init__(self, spot: float, strike: float, dte: float, is_long: bool = True, iv: float = 0.20, quantity: int = 1):
        call_leg = OptionLeg(strike=strike, dte=dte, is_call=True, is_long=is_long, quantity=quantity, iv=iv)
        put_leg = OptionLeg(strike=strike, dte=dte, is_call=False, is_long=is_long, quantity=quantity, iv=iv)
        call_leg.premium = calculate_greeks(spot, strike, dte, iv, True).price
        put_leg.premium = calculate_greeks(spot, strike, dte, iv, False).price
        super().__init__(name=f"{'Long' if is_long else 'Short'} Straddle @ ${strike}", legs=[call_leg, put_leg])


class Strangle(OptionSpread):
    """Constructs an OTM Long or Short Strangle."""
    def __init__(self, spot: float, put_strike: float, call_strike: float, dte: float, is_long: bool = True, iv: float = 0.20, quantity: int = 1):
        put_leg = OptionLeg(strike=put_strike, dte=dte, is_call=False, is_long=is_long, quantity=quantity, iv=iv)
        call_leg = OptionLeg(strike=call_strike, dte=dte, is_call=True, is_long=is_long, quantity=quantity, iv=iv)
        put_leg.premium = calculate_greeks(spot, put_strike, dte, iv, False).price
        call_leg.premium = calculate_greeks(spot, call_strike, dte, iv, True).price
        super().__init__(name=f"{'Long' if is_long else 'Short'} Strangle {put_strike}P/{call_strike}C", legs=[put_leg, call_leg])
