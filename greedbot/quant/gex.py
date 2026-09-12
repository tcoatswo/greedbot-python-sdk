"""
GreedBot Market-Maker Gamma Exposure (GEX) & Max Pain Engine
-----------------------------------------------------------
Analyzes option chain open interest to determine aggregate dealer gamma exposure,
volatility flip points (Zero Gamma), Call/Put walls, and expiration Max Pain.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math

from .rust_engine import calculate_greeks

@dataclass
class OptionContractData:
    strike: float
    is_call: bool
    open_interest: int
    dte: float
    iv: Optional[float] = None
    gamma: Optional[float] = None

@dataclass
class GEXResult:
    spot: float
    net_gex_dollars: float
    call_gex_dollars: float
    put_gex_dollars: float
    zero_gamma_flip: Optional[float]
    call_wall: float
    put_wall: float
    max_pain: float
    strike_breakdown: List[Dict[str, float]]

    def summary(self) -> str:
        regime = "LONG GAMMA (Mean-Reverting / Volatility Dampening)" if self.net_gex_dollars >= 0 else "SHORT GAMMA (Trend-Accelerating / High Volatility)"
        flip_str = f"${self.zero_gamma_flip:.2f}" if self.zero_gamma_flip is not None else "N/A"
        return (
            f"--- Market Maker Gamma Exposure (GEX) Summary ---\n"
            f"Spot Price       : ${self.spot:.2f}\n"
            f"Regime           : {regime}\n"
            f"Net GEX ($/1%)   : ${self.net_gex_dollars:,.2f}\n"
            f"Zero-Gamma Flip  : {flip_str}\n"
            f"Call Wall (Res)  : ${self.call_wall:.2f}\n"
            f"Put Wall (Supp)  : ${self.put_wall:.2f}\n"
            f"Max Pain Strike  : ${self.max_pain:.2f}\n"
        )


class GEXEngine:
    """
    Computes dealer positioning, net gamma exposure, and expiration max pain.
    """

    def __init__(self, spot: float, risk_free_rate: float = 0.045):
        self.spot = float(spot)
        self.risk_free_rate = risk_free_rate

    def calculate_gex(
        self,
        contracts: List[OptionContractData],
        default_iv: float = 0.20,
    ) -> GEXResult:
        """
        Calculate aggregate GEX from a list of option contracts.
        Dealer Assumption: Market makers are long calls and short puts (standard industry convention).
        Call GEX ($/1%) = OI * Gamma * Spot * Spot * 100 * 0.01
        Put GEX ($/1%) = - (OI * Gamma * Spot * Spot * 100 * 0.01)
        """
        strikes = sorted(list(set(c.strike for c in contracts)))
        strike_map: Dict[float, Dict[str, float]] = {
            k: {"call_oi": 0.0, "put_oi": 0.0, "call_gex": 0.0, "put_gex": 0.0, "net_gex": 0.0}
            for k in strikes
        }

        total_call_gex = 0.0
        total_put_gex = 0.0

        for c in contracts:
            gamma = c.gamma
            if gamma is None:
                iv = c.iv if (c.iv is not None and c.iv > 0) else default_iv
                greeks = calculate_greeks(
                    spot=self.spot,
                    strike=c.strike,
                    dte=max(c.dte, 1.0),
                    iv=iv,
                    is_call=c.is_call,
                    rate=self.risk_free_rate,
                )
                gamma = greeks.gamma

            # Dollar gamma per 1% underlying move
            dollar_gamma_1pct = (c.open_interest * 100.0) * gamma * (self.spot ** 2) * 0.01

            if c.is_call:
                total_call_gex += dollar_gamma_1pct
                strike_map[c.strike]["call_oi"] += c.open_interest
                strike_map[c.strike]["call_gex"] += dollar_gamma_1pct
            else:
                total_put_gex += dollar_gamma_1pct
                strike_map[c.strike]["put_oi"] += c.open_interest
                strike_map[c.strike]["put_gex"] += dollar_gamma_1pct

        # Calculate Net GEX per strike
        for k in strikes:
            strike_map[k]["net_gex"] = strike_map[k]["call_gex"] - strike_map[k]["put_gex"]

        net_gex_dollars = total_call_gex - total_put_gex

        # Find Call Wall (strike with highest Call OI or Call GEX)
        call_wall = max(strikes, key=lambda k: strike_map[k]["call_gex"]) if strikes else self.spot
        # Find Put Wall (strike with highest Put OI or Put GEX)
        put_wall = max(strikes, key=lambda k: strike_map[k]["put_gex"]) if strikes else self.spot

        # Zero Gamma Flip Level (interpolated where net GEX crosses 0)
        zero_gamma_flip = self._find_zero_gamma_flip(strikes, strike_map)

        # Max Pain Calculation
        max_pain = self.calculate_max_pain(contracts)

        breakdown = [
            {"strike": k, **strike_map[k]}
            for k in strikes
        ]

        return GEXResult(
            spot=self.spot,
            net_gex_dollars=net_gex_dollars,
            call_gex_dollars=total_call_gex,
            put_gex_dollars=total_put_gex,
            zero_gamma_flip=zero_gamma_flip,
            call_wall=call_wall,
            put_wall=put_wall,
            max_pain=max_pain,
            strike_breakdown=breakdown,
        )

    def calculate_max_pain(self, contracts: List[OptionContractData]) -> float:
        """
        Calculates the strike price where option buyers lose the most money at expiration
        (i.e., minimum total payout by option writers/market makers).
        """
        strikes = sorted(list(set(c.strike for c in contracts)))
        if not strikes:
            return self.spot

        min_loss = float("inf")
        max_pain_strike = self.spot

        for test_strike in strikes:
            total_loss = 0.0
            for c in contracts:
                if c.is_call:
                    payout = max(0.0, test_strike - c.strike) * c.open_interest * 100.0
                else:
                    payout = max(0.0, c.strike - test_strike) * c.open_interest * 100.0
                total_loss += payout

            if total_loss < min_loss:
                min_loss = total_loss
                max_pain_strike = test_strike

        return max_pain_strike

    def _find_zero_gamma_flip(
        self,
        strikes: List[float],
        strike_map: Dict[float, Dict[str, float]],
    ) -> Optional[float]:
        """
        Finds the exact price where cumulative Net GEX switches signs.
        """
        if len(strikes) < 2:
            return None

        cum_gex = []
        running = 0.0
        for k in strikes:
            running += strike_map[k]["net_gex"]
            cum_gex.append((k, running))

        for i in range(len(cum_gex) - 1):
            k1, g1 = cum_gex[i]
            k2, g2 = cum_gex[i + 1]
            if (g1 <= 0 and g2 > 0) or (g1 >= 0 and g2 < 0):
                if abs(g2 - g1) > 1e-6:
                    zero_cross = k1 + (0 - g1) * (k2 - k1) / (g2 - g1)
                    return round(zero_cross, 2)
                return k1

        return None
