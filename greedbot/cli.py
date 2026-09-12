"""
GreedBot CLI Entrypoint
-----------------------
High-speed terminal CLI for GreedBot API, quantitative strategies,
GEX analytics, multi-leg spreads, Monte Carlo stress-testing, and visual dashboards.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

from tabulate import tabulate

from .client import GreedBotClient
from .journal import TradeJournal
from .models import BotRunResult, OrderIntent, Side, TradePlan
from .quant.kelly import KellyPositionSizer
from .quant.markowitz import MeanVarianceOptimizer
from .quant.rust_engine import calculate_greeks, solve_iv, generate_volatility_surface, is_rust_accelerated
from .quant.gex import GEXEngine, OptionContractData
from .quant.spreads import IronCondor, VerticalSpread, Straddle, Strangle
from .quant.monte_carlo import MonteCarloEngine
from .dashboard import print_terminal_dashboard


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="greedbot",
        description="GreedBot Unofficial Python SDK & High-Throughput Quant CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # ping
    subparsers.add_parser("ping", help="Ping the GreedBot API server")

    # targets
    targets_p = subparsers.add_parser("targets", help="Get GreedBot targets for a ticker")
    targets_p.add_argument("ticker", type=str, help="Ticker symbol")

    # greeks
    greeks_p = subparsers.add_parser("greeks", help="Compute analytical Black-Scholes Greeks")
    greeks_p.add_argument("--spot", type=float, required=True, help="Underlying spot price")
    greeks_p.add_argument("--strike", type=float, required=True, help="Strike price")
    greeks_p.add_argument("--dte", type=float, default=30.0, help="Days to expiration")
    greeks_p.add_argument("--iv", type=float, default=0.20, help="Implied Volatility (e.g. 0.20 for 20 pct)")
    greeks_p.add_argument("--put", action="store_true", help="Calculate Put Greeks instead of Call")

    # solve-iv
    iv_p = subparsers.add_parser("solve-iv", help="Solve Implied Volatility from market option price")
    iv_p.add_argument("--spot", type=float, required=True)
    iv_p.add_argument("--strike", type=float, required=True)
    iv_p.add_argument("--dte", type=float, default=30.0)
    iv_p.add_argument("--price", type=float, required=True, help="Market option price")
    iv_p.add_argument("--put", action="store_true")

    # gex
    gex_p = subparsers.add_parser("gex", help="Compute dealer Gamma Exposure (GEX) and Max Pain")
    gex_p.add_argument("--spot", type=float, default=580.0, help="Underlying spot price")

    # spread
    spread_p = subparsers.add_parser("spread", help="Profile a multi-leg option strategy")
    spread_p.add_argument("--type", choices=["iron-condor", "straddle", "strangle", "vertical"], default="iron-condor")
    spread_p.add_argument("--spot", type=float, default=580.0)

    # mc (monte carlo)
    mc_p = subparsers.add_parser("mc", help="Run Monte Carlo portfolio jump-diffusion stress test")
    mc_p.add_argument("--capital", type=float, default=100000.0)
    mc_p.add_argument("--days", type=int, default=30)
    mc_p.add_argument("--sims", type=int, default=5000)

    # dashboard
    dash_p = subparsers.add_parser("dashboard", help="Launch interactive quant & volatility dashboard")
    dash_p.add_argument("--spot", type=float, default=580.0)

    args = parser.parse_args()

    if args.command == "ping":
        client = GreedBotClient()
        pong = client.ping()
        print(f"Ping response: {pong}")
    elif args.command == "targets":
        client = GreedBotClient()
        res = client.get_targets(args.ticker)
        print(json.dumps(res, indent=2))
    elif args.command == "greeks":
        g = calculate_greeks(
            spot=args.spot,
            strike=args.strike,
            dte=args.dte,
            iv=args.iv,
            is_call=not args.put,
        )
        print(f"Rust Acceleration : {is_rust_accelerated()}")
        print(f"Option Type       : {'Put' if args.put else 'Call'}")
        print(f"Theoretical Price : ${g.price:.2f}")
        print(f"Delta             : {g.delta:+.4f}")
        print(f"Gamma             : {g.gamma:.6f}")
        print(f"Vega              : {g.vega:.4f}")
        print(f"Theta             : {g.theta:+.4f}/day")
        print(f"Rho               : {g.rho:+.4f}")
        print(f"Vanna             : {g.vanna:+.6f}")
        print(f"Volga             : {g.volga:+.6f}")
    elif args.command == "solve-iv":
        iv = solve_iv(
            spot=args.spot,
            strike=args.strike,
            dte=args.dte,
            market_price=args.price,
            is_call=not args.put,
        )
        print(f"Calculated Implied Volatility: {iv * 100:.2f}%")
    elif args.command == "gex":
        engine = GEXEngine(spot=args.spot)
        contracts = [
            OptionContractData(strike=args.spot * 0.95, is_call=False, open_interest=12000, dte=30, iv=0.24),
            OptionContractData(strike=args.spot * 0.98, is_call=False, open_interest=8500, dte=30, iv=0.22),
            OptionContractData(strike=args.spot * 1.00, is_call=True, open_interest=15000, dte=30, iv=0.20),
            OptionContractData(strike=args.spot * 1.02, is_call=True, open_interest=9500, dte=30, iv=0.19),
            OptionContractData(strike=args.spot * 1.05, is_call=True, open_interest=22000, dte=30, iv=0.18),
        ]
        res = engine.calculate_gex(contracts)
        print(res.summary())
    elif args.command == "spread":
        if args.type == "iron-condor":
            spread = IronCondor(
                spot=args.spot,
                put_wing=args.spot * 0.90,
                put_short=args.spot * 0.95,
                call_short=args.spot * 1.05,
                call_wing=args.spot * 1.10,
                dte=30,
            )
        elif args.type == "straddle":
            spread = Straddle(spot=args.spot, strike=args.spot, dte=30)
        elif args.type == "strangle":
            spread = Strangle(spot=args.spot, put_strike=args.spot * 0.95, call_strike=args.spot * 1.05, dte=30)
        else:
            spread = VerticalSpread(spot=args.spot, long_strike=args.spot * 0.95, short_strike=args.spot * 1.05, dte=30)
        
        greeks = spread.get_net_greeks(args.spot)
        print(f"Strategy: {spread.name}")
        print(f"Net Delta : {greeks.net_delta:+.4f}")
        print(f"Net Gamma : {greeks.net_gamma:+.6f}")
        print(f"Net Vega  : {greeks.net_vega:+.4f}")
        print(f"Net Theta : {greeks.net_theta:+.2f}/day")
        print(f"Max Profit: ${greeks.max_profit:,.2f}")
        print(f"Max Loss  : -${abs(greeks.max_loss or 0):,.2f}")
        print(f"Break-Evens: {greeks.break_even_points}")
    elif args.command == "mc":
        engine = MonteCarloEngine(portfolio_value=args.capital, annual_volatility=0.22, jump_intensity=0.5, jump_mean=-0.08, jump_vol=0.10)
        res = engine.run_simulation(days=args.days, num_simulations=args.sims)
        print(res.summary())
    elif args.command == "dashboard":
        print_terminal_dashboard(spot=args.spot)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
