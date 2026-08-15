"""
GreedBot CLI Entrypoint
-----------------------
High-speed terminal CLI for GreedBot API, quantitative strategies,
paper broker simulation, and unmetered trade log management.
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
from .strategies import (
    BotFleetFollower,
    EarningsRadarStrategy,
    ETFBarbellStrategy,
    MacroRegimeMatrix,
    MarketMakerStrategy,
    MarkowitzAllocationStrategy,
    MeanReversionStrategy,
    OptionKellyEngine,
    QualitativeOverlayEngine,
    SectorLongShortStrategy,
    SoloTacticalStrategy,
    StatArbPairsStrategy,
    TrendFollowingStrategy,
)


def print_json(data: Any) -> None:
    print(json.dumps(data, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="greedbot",
        description="GreedBot Quantitative Trading SDK & Volatility Intelligence CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ping
    subparsers.add_parser("ping", help="Public health check")

    # usage
    subparsers.add_parser("usage", help="View API key spend & Stripe billing meter usage")

    # targets
    p_targets = subparsers.add_parser("targets", help="Fetch quantitative price targets")
    p_targets.add_argument("tickers", nargs="+", help="Stock ticker symbols (e.g. NVDA TSLA)")
    p_targets.add_argument("--intervals", nargs="+", default=["1w", "1d"], help="Intervals (e.g. 1w 1d 1h)")
    p_targets.add_argument("--json", action="store_true", help="Output raw JSON")

    # kelly
    p_kelly = subparsers.add_parser("kelly", help="Fetch Kelly sizing fraction")
    p_kelly.add_argument("tickers", nargs="+", help="Stock ticker symbols")
    p_kelly.add_argument("--fraction", type=float, default=0.5, help="Kelly fraction (default: 0.5)")
    p_kelly.add_argument("--json", action="store_true", help="Output raw JSON")

    # parity
    p_parity = subparsers.add_parser("parity", help="Fetch Risk Parity allocation weights")
    p_parity.add_argument("tickers", nargs="+", help="Stock ticker symbols")
    p_parity.add_argument("--json", action="store_true", help="Output raw JSON")

    # pizza
    p_pizza = subparsers.add_parser("pizza", help="Fetch GreedBot Pizza Multi-Factor Leaderboard")
    p_pizza.add_argument("tickers", nargs="*", help="Optional filter tickers")
    p_pizza.add_argument("--fundamentals", choices=["off", "required", "only"], default="off", help="Fundamentals mode")
    p_pizza.add_argument("--json", action="store_true", help="Output raw JSON")

    # macro
    p_macro = subparsers.add_parser("macro", help="Fetch Macro Regime & Cycle Indicators")
    p_macro.add_argument("--json", action="store_true", help="Output raw JSON")

    # earnings
    p_earnings = subparsers.add_parser("earnings", help="Fetch 90-day Earnings Radar")
    p_earnings.add_argument("--json", action="store_true", help="Output raw JSON")

    # expected-move
    p_exp = subparsers.add_parser("expected-move", help="Price options expected move from options straddle/strangle chains")
    p_exp.add_argument("ticker", help="Ticker symbol (e.g. NVDA)")
    p_exp.add_argument("--date", help="Optional report date (YYYY-MM-DD)")
    p_exp.add_argument("--json", action="store_true", help="Output raw JSON")

    # ideas
    p_ideas = subparsers.add_parser("ideas", help="Fetch latest algorithmic trade ideas snapshot")
    p_ideas.add_argument("--json", action="store_true", help="Output raw JSON")

    # bots
    p_bots = subparsers.add_parser("bots", help="Inspect hosted bot fleet leaderboard and open books")
    p_bots.add_argument("--bot-id", help="Inspect a specific bot's book")
    p_bots.add_argument("--json", action="store_true", help="Output raw JSON")

    # plot
    p_plot = subparsers.add_parser("plot", help="Render chart image (PNG) for visual agent inspection")
    p_plot.add_argument("ticker", help="Ticker symbol")
    p_plot.add_argument("--type", choices=["chart", "algo_targets"], default="chart", help="Plot type")
    p_plot.add_argument("--interval", choices=["1d", "1w"], default="1d", help="Interval")
    p_plot.add_argument("--output", "-o", default="chart.png", help="Output PNG file path")

    # log
    p_log = subparsers.add_parser("log", help="Manage unmetered trade journal plans")
    p_log.add_argument("action", choices=["list", "create", "open", "close", "cancel"], default="list")
    p_log.add_argument("--id", help="Plan ID")
    p_log.add_argument("--ticker", help="Ticker symbol")
    p_log.add_argument("--direction", choices=["long", "short"], default="long")
    p_log.add_argument("--entry", type=float, help="Planned entry price")
    p_log.add_argument("--stop", type=float, help="Planned stop price")
    p_log.add_argument("--target", type=float, help="Planned target price")
    p_log.add_argument("--status", default="active", help="Filter status (active, planned, open, closed, all)")
    p_log.add_argument("--json", action="store_true", help="Output raw JSON")

    # run-strategy
    p_strat = subparsers.add_parser("run-strategy", help="Execute an automated quantitative strategy")
    p_strat.add_argument(
        "strategy",
        choices=[
            "etf", "solo", "sector_ls", "option_kelly", "radar", "macro",
            "trend", "mean_revert", "pairs", "mm", "markowitz", "scan"
        ],
        help="Strategy to execute",
    )
    p_strat.add_argument("--capital", type=float, default=10000.0, help="Capital in USD (default: $10,000)")
    p_strat.add_argument("--ticker", default="NVDA", help="Ticker for solo/trend/reversion strategy")
    p_strat.add_argument("--ticker2", default="QQQ", help="Second ticker for pairs trading")
    p_strat.add_argument("--json", action="store_true", help="Output raw JSON")

    # quant
    p_quant = subparsers.add_parser("quant", help="Execute standalone quantitative mathematical calculations")
    p_quant.add_argument("calc", choices=["kelly", "markowitz"], help="Calculation type")
    p_quant.add_argument("--win-rate", type=float, default=0.55, help="Win rate p (0.0 - 1.0)")
    p_quant.add_argument("--win-loss-ratio", type=float, default=1.8, help="Win/loss payoff ratio b")
    p_quant.add_argument("--capital", type=float, default=10000.0, help="Capital in USD")

    args = parser.parse_args()
    client = GreedBotClient()

    if args.command == "ping":
        res = client.ping()
        print(f"Ping response: {res}")

    elif args.command == "usage":
        res = client.get_usage()
        print_json(res)

    elif args.command == "targets":
        res = client.get_targets(args.tickers, intervals=args.intervals)
        print_json(res)

    elif args.command == "kelly":
        res = client.get_kelly(args.tickers, kelly_fraction=args.fraction)
        print_json(res)

    elif args.command == "parity":
        res = client.get_parity(args.tickers)
        print_json(res)

    elif args.command == "pizza":
        res = client.get_pizza(args.tickers if args.tickers else None, fundamentals_mode=args.fundamentals)
        print_json(res)

    elif args.command == "macro":
        res = client.get_hub_macro()
        print_json(res)

    elif args.command == "earnings":
        res = client.get_hub_earnings()
        print_json(res)

    elif args.command == "expected-move":
        res = client.get_hub_earnings_expected_move(args.ticker, date=args.date)
        print_json(res)

    elif args.command == "ideas":
        res = client.get_hub_ideas()
        print_json(res)

    elif args.command == "bots":
        if args.bot_id:
            res = client.get_bot_book(args.bot_id)
        else:
            res = client.get_bots()
        print_json(res)

    elif args.command == "plot":
        client.get_plot(args.ticker, plot_type=args.type, interval=args.interval, output_file=args.output)
        print(f"Plot saved successfully to {args.output}")

    elif args.command == "quant":
        if args.calc == "kelly":
            sizer = KellyPositionSizer(default_fraction=0.5)
            res = sizer.size_position(
                capital_usd=args.capital,
                win_rate=args.win_rate,
                win_loss_ratio=args.win_loss_ratio,
            )
            print_json(res)

    elif args.command == "log":
        journal = TradeJournal(client)
        if args.action == "list":
            res = client.list_logs(status=args.status, ticker=args.ticker)
            print_json(res)
        elif args.action == "create":
            if not (args.ticker and args.entry and args.stop):
                print("Error: --ticker, --entry, and --stop are required to create a plan.")
                sys.exit(1)
            plan_id = journal.record_plan(
                ticker=args.ticker,
                direction=args.direction,
                entry=args.entry,
                stop=args.stop,
                target=args.target,
            )
            print(f"Created trade plan ID: {plan_id}")
        elif args.action == "open":
            if not args.id:
                print("Error: --id is required to open a plan.")
                sys.exit(1)
            res = journal.open_trade(args.id)
            print_json(res)
        elif args.action == "close":
            if not args.id:
                print("Error: --id is required to close a plan.")
                sys.exit(1)
            res = journal.close_trade(args.id)
            print_json(res)
        elif args.action == "cancel":
            if not args.id:
                print("Error: --id is required to cancel a plan.")
                sys.exit(1)
            res = journal.cancel_trade(args.id)
            print_json(res)

    elif args.command == "run-strategy":
        strat_name = args.strategy
        capital = args.capital

        if strat_name == "etf":
            strat = ETFBarbellStrategy()
            res = strat.run(client, capital_usd=capital)
        elif strat_name == "solo":
            strat = SoloTacticalStrategy(ticker=args.ticker)
            res = strat.run(client, capital_usd=capital)
        elif strat_name == "sector_ls":
            strat = SectorLongShortStrategy()
            res = strat.run(client, capital_usd=capital)
        elif strat_name == "option_kelly":
            strat = OptionKellyEngine(default_ticker=args.ticker)
            res = strat.run(client, capital_usd=capital)
        elif strat_name == "radar":
            strat = EarningsRadarStrategy()
            res = strat.run(client, capital_usd=capital)
        elif strat_name == "macro":
            strat = MacroRegimeMatrix()
            res = strat.run(client, capital_usd=capital)
        elif strat_name == "trend":
            strat = TrendFollowingStrategy(ticker=args.ticker)
            res = strat.run(client, capital_usd=capital)
        elif strat_name == "mean_revert":
            strat = MeanReversionStrategy(ticker=args.ticker)
            res = strat.run(client, capital_usd=capital)
        elif strat_name == "pairs":
            strat = StatArbPairsStrategy(ticker_a=args.ticker, ticker_b=args.ticker2)
            res = strat.run(client, capital_usd=capital)
        elif strat_name == "mm":
            strat = MarketMakerStrategy(ticker=args.ticker)
            res = strat.run(client, capital_usd=capital)
        elif strat_name == "markowitz":
            strat = MarkowitzAllocationStrategy()
            res = strat.run(client, capital_usd=capital)
        elif strat_name == "scan":
            qual = QualitativeOverlayEngine()
            kelly = OptionKellyEngine()

            print("\n⚡ [GreedBot AI Quantitative Strategy Scan]")
            print("=" * 60)
            for sym in ["NVDA", "TSLA", "MSFT", "AAPL"]:
                q_res = qual.evaluate_divergence(client=client, ticker=sym)
                k_res = kelly.calculate_sizing(client=client, ticker=sym, portfolio_size=capital)
                print(f"\n🔹 {sym}: {q_res['assessment']}")
                print(f"   • Mkt Implied Move: {q_res['market_expected_move_pct']}% | Forecast: {q_res['qualitative_expected_move_pct']}%")
                print(f"   • Recommended Setup: {q_res['recommended_trade']}")
                print(f"   • Kelly Convex Budget: ${k_res['max_risk_budget']} ({k_res['recommended_action']})")
            return

        if args.json:
            print_json({
                "target_dollars": res.target_dollars,
                "intents": [vars(i) for i in res.intents],
                "summary": res.summary,
            })
        else:
            print(f"\n⚡ Strategy Execution: {strat_name.upper()}")
            print("-" * 50)
            table_data = [[t, f"${amt:,.2f}"] for t, amt in res.target_dollars.items()]
            print(tabulate(table_data, headers=["Ticker", "Target Allocation"], tablefmt="fancy_grid"))
            print(f"\nGenerated {len(res.intents)} Executable Order Intents:")
            for intent in res.intents:
                limit_info = f" (Limit: ${intent.limit:.2f})" if intent.limit else ""
                print(f"  • {intent.side.value.upper()} {intent.ticker.upper()}: ${intent.dollars:,.2f}{limit_info}")


if __name__ == "__main__":
    main()
