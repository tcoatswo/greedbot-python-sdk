"""
GreedBot CLI Entrypoint
-----------------------
High-speed terminal CLI for GreedBot API, quantitative strategies,
GEX analytics, multi-leg spreads, Monte Carlo stress-testing, backtesting,
and interactive visual dashboards.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from tabulate import tabulate

from .backtest import BacktestEngine
from .client import GreedBotClient
from .dashboard import print_terminal_dashboard
from .datasources.market import YahooFinanceSource
from .journal import TradeJournal
from .quant.gex import GEXEngine, OptionContractData
from .quant.kelly import KellyPositionSizer
from .quant.markowitz import MeanVarianceOptimizer
from .quant.monte_carlo import MonteCarloEngine
from .quant.risk_parity import RiskParityOptimizer
from .quant.rust_engine import (
    calculate_greeks,
    is_rust_accelerated,
    solve_iv,
)
from .quant.spreads import (
    IronCondor,
    Straddle,
    Strangle,
    VerticalSpread,
)
from .signals import (
    BollingerMeanReversion,
    MACDCrossover,
    MovingAverageCrossover,
    RSIMeanReversion,
)
from .strategies import (
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
        description="GreedBot Unofficial Python SDK & High-Throughput Quant CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

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
    p_quant.add_argument("calc", choices=["kelly", "markowitz", "risk-parity"], help="Calculation type")
    p_quant.add_argument("--win-rate", type=float, default=0.55, help="Win rate p (0.0 - 1.0)")
    p_quant.add_argument("--win-loss-ratio", type=float, default=1.8, help="Win/loss payoff ratio b")
    p_quant.add_argument("--capital", type=float, default=10000.0, help="Capital in USD")

    # backtest
    p_bt = subparsers.add_parser("backtest", help="Run event-driven backtest simulation for quantitative signals")
    p_bt.add_argument("signal", choices=["trend", "mean_revert", "rsi", "macd"], help="Signal generator type")
    p_bt.add_argument("--ticker", default="NVDA", help="Asset ticker symbol (default: NVDA)")
    p_bt.add_argument("--capital", type=float, default=10000.0, help="Initial capital in USD")
    p_bt.add_argument("--slippage-bps", type=float, default=5.0, help="Slippage in basis points")
    p_bt.add_argument("--fee", type=float, default=1.0, help="Commission fee per trade")
    p_bt.add_argument("--json", action="store_true", help="Output raw JSON metrics")

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
    if not args.command:
        parser.print_help()
        sys.exit(0)

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
        elif args.calc == "markowitz":
            opt = MeanVarianceOptimizer()
            tickers = ["NVDA", "AAPL", "MSFT", "GOOGL"]
            import numpy as np
            np.random.seed(42)
            returns = np.random.normal(0.0008, 0.015, (252, len(tickers)))
            gmv = opt.optimize_gmv(returns, tickers)
            tan = opt.optimize_tangency(returns, tickers)
            print_json({"gmv_portfolio": gmv, "tangency_portfolio": tan})
        elif args.calc == "risk-parity":
            rp = RiskParityOptimizer()
            tickers = ["SPY", "TLT", "GLD", "DBC"]
            import numpy as np
            np.random.seed(42)
            returns = np.random.normal(0.0005, 0.012, (252, len(tickers)))
            inv_vol = rp.optimize_inverse_volatility(returns, tickers)
            erc = rp.optimize_equal_risk_contribution(returns, tickers)
            print_json({"inverse_volatility": inv_vol, "equal_risk_contribution": erc})

    elif args.command == "backtest":
        ds = YahooFinanceSource()
        prices = ds.get_historical_prices(args.ticker, period="1y")
        engine = BacktestEngine(
            initial_capital=args.capital,
            slippage_bps=args.slippage_bps,
            fee_per_trade=args.fee,
        )
        if args.signal == "trend":
            gen = MovingAverageCrossover(short_window=10, long_window=30)
        elif args.signal == "mean_revert":
            gen = BollingerMeanReversion(window=20, z_threshold=2.0)
        elif args.signal == "rsi":
            gen = RSIMeanReversion(period=14, oversold_threshold=30.0, overbought_threshold=70.0)
        elif args.signal == "macd":
            gen = MACDCrossover(fast_period=12, slow_period=26, signal_period=9)

        warmup = 36
        res = engine.run_signal_series(
            ticker=args.ticker,
            prices=prices,
            signal_generator=gen,
            min_warmup_bars=warmup,
        )
        if args.json:
            print_json({
                "ticker": args.ticker.upper(),
                "signal": args.signal,
                "initial_capital": res.metrics.initial_capital,
                "final_equity": res.metrics.final_equity,
                "net_profit": res.metrics.net_profit,
                "total_return_pct": res.metrics.total_return_pct,
                "cagr_pct": res.metrics.cagr_pct,
                "sharpe": res.metrics.annualized_sharpe,
                "sortino": res.metrics.annualized_sortino,
                "max_drawdown_pct": res.metrics.max_drawdown_pct,
                "var_95_pct": res.metrics.var_95_pct,
                "cvar_95_pct": res.metrics.cvar_95_pct,
                "win_rate_pct": res.metrics.win_rate_pct,
                "profit_factor": res.metrics.profit_factor,
            })
        else:
            print(f"\n⚡ Backtest Simulation Tear Sheet: {args.ticker.upper()} ({gen.name})")
            print(res.summary())

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
            print(f"\n⚡ Strategy Execution: {strat.name}")
            print(f"Capital: ${capital:,.2f}")
            table_rows = []
            for ticker, amt in res.target_dollars.items():
                table_rows.append([ticker.upper(), f"${amt:,.2f}"])
            if table_rows:
                print("\nTarget Dollar Allocations:")
                print(tabulate(table_rows, headers=["Ticker", "Allocation ($)"], tablefmt="simple"))
            print("\nOrder Intents:")
            intent_rows = []
            for intent in res.intents:
                intent_rows.append([
                    intent.ticker.upper(),
                    intent.side.value.upper(),
                    f"${intent.dollars:,.2f}" if intent.dollars else f"{intent.shares} shs",
                    intent.order_type.value.upper(),
                ])
            print(tabulate(intent_rows, headers=["Ticker", "Side", "Size", "Type"], tablefmt="simple"))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
