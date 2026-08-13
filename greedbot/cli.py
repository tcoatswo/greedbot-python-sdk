"""
GreedBot CLI Entrypoint
-----------------------
Provides high-speed terminal interaction with GreedBot API & Strategies.
"""

import sys
import os
import argparse
import json
from tabulate import tabulate
from .client import GreedBotClient
from .strategies import (
    OptionKellyEngine,
    SectorSpilloverArb,
    QualitativeOverlayEngine,
    MacroRegimeMatrix,
    VolatilityHarvestEngine,
)

def main():
    parser = argparse.ArgumentParser(description="GreedBot Quantitative Trading SDK & CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # targets
    p_targets = subparsers.add_parser("targets", help="Fetch quantitative price targets")
    p_targets.add_argument("tickers", nargs="+", help="Stock ticker symbols")

    # kelly
    p_kelly = subparsers.add_parser("kelly", help="Fetch Kelly sizing fraction")
    p_kelly.add_argument("tickers", nargs="+", help="Stock ticker symbols")

    # pizza
    p_pizza = subparsers.add_parser("pizza", help="Fetch GreedBot Pizza Momentum Leaderboard")
    p_pizza.add_argument("tickers", nargs="*", help="Optional filter tickers")

    # scan
    p_scan = subparsers.add_parser("scan", help="Run full quantitative AI strategy scan across all 5 models")
    p_scan.add_argument("--json", action="store_true", help="Output raw JSON instead of text")

    args = parser.parse_args()
    client = GreedBotClient()

    if args.command == "targets":
        res = client.get_targets(args.tickers)
        print(json.dumps(res, indent=2))
    elif args.command == "kelly":
        res = client.get_kelly(args.tickers)
        print(json.dumps(res, indent=2))
    elif args.command == "pizza":
        res = client.get_pizza(args.tickers)
        print(json.dumps(res, indent=2))
    elif args.command == "scan":
        qual = QualitativeOverlayEngine(client)
        kelly = OptionKellyEngine(client)
        macro = MacroRegimeMatrix(client)

        print("\n⚡ [GreedBot AI Quantitative Strategy Scan]")
        print("---------------------------------------------")
        for sym in ["NVDA", "TSLA", "MSFT"]:
            q_res = qual.evaluate_divergence(sym)
            k_res = kelly.calculate_sizing(sym)
            print(f"\n🔹 {sym}: {q_res['assessment']}")
            print(f"  • Mkt Implied: {q_res['market_expected_move_pct']}% | Forecast: {q_res['qualitative_expected_move_pct']}%")
            print(f"  • Trade: {q_res['recommended_trade']}")
            print(f"  • Kelly Risk Cap: ${k_res['max_risk_budget']} ({k_res['recommended_action']})")

if __name__ == "__main__":
    main()
