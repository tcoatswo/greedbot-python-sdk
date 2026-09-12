"""
GreedBot High-Throughput Native Rust Quant Engine
-------------------------------------------------
Sub-microsecond Black-Scholes Greeks, Newton-Raphson IV solver, and
parallel 3D Volatility Surface generator powered by the Rust backend.
"""

import ctypes
import os
import sys
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

class OptionGreeksStruct(ctypes.Structure):
    _fields_ = [
        ("price", ctypes.c_double),
        ("delta", ctypes.c_double),
        ("gamma", ctypes.c_double),
        ("vega", ctypes.c_double),
        ("theta", ctypes.c_double),
        ("rho", ctypes.c_double),
        ("vanna", ctypes.c_double),
        ("volga", ctypes.c_double),
        ("iv", ctypes.c_double),
    ]

@dataclass
class OptionGreeks:
    price: float
    delta: float
    gamma: float
    vega: float
    theta: float
    rho: float
    vanna: float
    volga: float
    iv: float

    def to_dict(self):
        return {
            "price": self.price,
            "delta": self.delta,
            "gamma": self.gamma,
            "vega": self.vega,
            "theta": self.theta,
            "rho": self.rho,
            "vanna": self.vanna,
            "volga": self.volga,
            "iv": self.iv,
        }

def _find_rust_lib() -> Optional[ctypes.CDLL]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    search_paths = [
        os.path.join(base_dir, "crates", "greedbot_quant", "target", "release", "libgreedbot_quant.so"),
        os.path.join(base_dir, "crates", "greedbot_quant", "target", "release", "libgreedbot_quant.dylib"),
        os.path.join(base_dir, "crates", "greedbot_quant", "target", "release", "greedbot_quant.dll"),
        os.path.join(os.path.dirname(__file__), "libgreedbot_quant.so"),
    ]
    for p in search_paths:
        if os.path.exists(p):
            try:
                lib = ctypes.CDLL(p)
                lib.greedbot_c_greeks.argtypes = [
                    ctypes.c_double, ctypes.c_double, ctypes.c_double,
                    ctypes.c_double, ctypes.c_double, ctypes.c_double,
                    ctypes.c_bool, ctypes.POINTER(OptionGreeksStruct)
                ]
                lib.greedbot_c_greeks.restype = ctypes.c_int

                lib.greedbot_c_solve_iv.argtypes = [
                    ctypes.c_double, ctypes.c_double, ctypes.c_double,
                    ctypes.c_double, ctypes.c_double, ctypes.c_double,
                    ctypes.c_bool
                ]
                lib.greedbot_c_solve_iv.restype = ctypes.c_double

                lib.greedbot_c_batch_greeks.argtypes = [
                    ctypes.POINTER(ctypes.c_double),
                    ctypes.POINTER(ctypes.c_double),
                    ctypes.POINTER(ctypes.c_double),
                    ctypes.POINTER(ctypes.c_double),
                    ctypes.POINTER(ctypes.c_double),
                    ctypes.POINTER(ctypes.c_double),
                    ctypes.POINTER(ctypes.c_uint8),
                    ctypes.c_size_t,
                    ctypes.POINTER(OptionGreeksStruct)
                ]
                lib.greedbot_c_batch_greeks.restype = ctypes.c_int
                return lib
            except Exception:
                continue
    return None

_RUST_LIB = _find_rust_lib()

def is_rust_accelerated() -> bool:
    """Returns True if the high-performance native Rust engine is loaded."""
    return _RUST_LIB is not None

def calculate_greeks(
    spot: float,
    strike: float,
    dte: float,
    iv: float,
    is_call: bool = True,
    rate: float = 0.045,
    div_yield: float = 0.0,
) -> OptionGreeks:
    """
    Calculate analytical Black-Scholes Greeks (sub-microsecond execution).
    
    :param spot: Current underlying spot price
    :param strike: Option strike price
    :param dte: Days to expiration (e.g. 30.0)
    :param iv: Implied volatility as a decimal (e.g. 0.25 for 25%)
    :param is_call: True for Call, False for Put
    :param rate: Risk-free interest rate (default: 4.5%)
    :param div_yield: Dividend yield (default: 0.0%)
    """
    if _RUST_LIB is not None:
        out = OptionGreeksStruct()
        ret = _RUST_LIB.greedbot_c_greeks(
            float(spot), float(strike), float(dte),
            float(rate), float(div_yield), float(iv),
            bool(is_call), ctypes.byref(out)
        )
        if ret == 0:
            return OptionGreeks(
                price=out.price,
                delta=out.delta,
                gamma=out.gamma,
                vega=out.vega,
                theta=out.theta,
                rho=out.rho,
                vanna=out.vanna,
                volga=out.volga,
                iv=out.iv,
            )

    # Pure Python Fallback
    t = dte / 365.0
    if t <= 0.0 or iv <= 0.0:
        intrinsic = max(0.0, spot - strike) if is_call else max(0.0, strike - spot)
        return OptionGreeks(price=intrinsic, delta=1.0 if is_call and spot > strike else 0.0,
                            gamma=0.0, vega=0.0, theta=0.0, rho=0.0, vanna=0.0, volga=0.0, iv=iv)
    sqrt_t = math.sqrt(t)
    d1 = (math.log(spot / strike) + (rate - div_yield + 0.5 * iv * iv) * t) / (iv * sqrt_t)
    d2 = d1 - iv * sqrt_t
    
    def n_cdf(x):
        return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
    def n_pdf(x):
        return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

    df_q = math.exp(-div_yield * t)
    df_r = math.exp(-rate * t)
    nd1, nd2 = n_cdf(d1), n_cdf(d2)
    np_d1 = n_pdf(d1)

    if is_call:
        price = spot * df_q * nd1 - strike * df_r * nd2
        delta = df_q * nd1
        rho = strike * t * df_r * nd2 / 100.0
        theta = (-(spot * df_q * np_d1 * iv) / (2.0 * sqrt_t) - rate * strike * df_r * nd2 + div_yield * spot * df_q * nd1) / 365.0
    else:
        price = strike * df_r * n_cdf(-d2) - spot * df_q * n_cdf(-d1)
        delta = df_q * (nd1 - 1.0)
        rho = -strike * t * df_r * n_cdf(-d2) / 100.0
        theta = (-(spot * df_q * np_d1 * iv) / (2.0 * sqrt_t) + rate * strike * df_r * n_cdf(-d2) - div_yield * spot * df_q * n_cdf(-d1)) / 365.0

    gamma = (df_q * np_d1) / (spot * iv * sqrt_t)
    vega = (spot * df_q * sqrt_t * np_d1) / 100.0
    vanna = (-df_q * np_d1 * d2 / iv) / 100.0
    volga = (vega * d1 * d2 / iv) / 100.0

    return OptionGreeks(
        price=price, delta=delta, gamma=gamma, vega=vega,
        theta=theta, rho=rho, vanna=vanna, volga=volga, iv=iv
    )

def solve_iv(
    spot: float,
    strike: float,
    dte: float,
    market_price: float,
    is_call: bool = True,
    rate: float = 0.045,
    div_yield: float = 0.0,
) -> float:
    """
    Solve Implied Volatility via high-performance Newton-Raphson + Bisection solver.
    """
    if _RUST_LIB is not None:
        return _RUST_LIB.greedbot_c_solve_iv(
            float(spot), float(strike), float(dte),
            float(rate), float(div_yield), float(market_price),
            bool(is_call)
        )

    # Python Fallback
    low, high = 0.0001, 10.0
    for _ in range(40):
        mid = (low + high) * 0.5
        g = calculate_greeks(spot, strike, dte, mid, is_call, rate, div_yield)
        if abs(g.price - market_price) < 1e-4:
            return mid
        if g.price > market_price:
            high = mid
        else:
            low = mid
    return (low + high) * 0.5

def generate_volatility_surface(
    spot: float,
    base_vol: float = 0.20,
    strikes: Optional[List[float]] = None,
    dtes: Optional[List[float]] = None,
) -> List[dict]:
    """
    Generate a 3D Implied Volatility & Greeks surface grid.
    """
    if strikes is None:
        strikes = [spot * mult for mult in [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15]]
    if dtes is None:
        dtes = [7.0, 14.0, 30.0, 60.0, 90.0, 180.0]

    surface = []
    for dte in dtes:
        for strike in strikes:
            moneyness = math.log(strike / spot)
            # Volatility smile / skew adjustment
            skew = base_vol + 0.08 * (moneyness ** 2) - 0.12 * moneyness * math.sqrt(30.0 / dte)
            adj_iv = max(0.05, min(1.50, skew))
            call_greeks = calculate_greeks(spot, strike, dte, adj_iv, is_call=True)
            put_greeks = calculate_greeks(spot, strike, dte, adj_iv, is_call=False)
            surface.append({
                "strike": strike,
                "dte": dte,
                "iv": adj_iv,
                "moneyness": strike / spot,
                "call_price": call_greeks.price,
                "call_delta": call_greeks.delta,
                "put_price": put_greeks.price,
                "put_delta": put_greeks.delta,
                "gamma": call_greeks.gamma,
                "vega": call_greeks.vega,
            })
    return surface
