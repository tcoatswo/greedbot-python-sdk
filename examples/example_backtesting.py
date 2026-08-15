"""
Example Event-Driven Backtesting & Performance Analytics
--------------------------------------------------------
Simulates a multi-month bar-by-bar trading strategy on historical prices,
accounting for transaction costs and slippage, and prints a full performance tear sheet.
"""

import math
import numpy as np
from greedbot import BacktestEngine, MovingAverageCrossover, BollingerMeanReversion

def main():
    ticker = "NVDA"
    initial_capital = 50000.0

    print(f"⚡ Running Event-Driven Backtest for {ticker} (Initial Capital: ${initial_capital:,.2f})...")

    # 1. Generate realistic synthetic daily price path with trend and volatility
    np.random.seed(42)
    n_days = 252  # 1 trading year
    daily_drift = 0.0008  # +20% annual drift
    daily_vol = 0.02      # 32% annual volatility
    daily_returns = np.random.normal(daily_drift, daily_vol, n_days)
    prices = 100.0 * np.cumprod(1.0 + daily_returns)

    # 2. Initialize BacktestEngine (5 bps slippage, $1 commission per trade)
    engine = BacktestEngine(
        initial_capital=initial_capital,
        slippage_bps=5.0,
        fee_per_trade=1.00,
        risk_free_rate=0.04,
        bars_per_year=252,
    )

    # 3. Backtest Moving Average Crossover Strategy
    signal_gen = MovingAverageCrossover(short_window=10, long_window=30)
    result = engine.run_signal_series(
        ticker=ticker,
        prices=prices,
        signal_generator=signal_gen,
        min_warmup_bars=30,
        allocation_fraction=0.75,
    )

    # 4. Display Formatted Performance Tear Sheet
    print("\n" + result.summary())

    print(f"\nTotal Recorded Trades in Backtest: {len(result.trades)}")
    for t in result.trades[:5]:
        print(f"  • {t['type']}: {t['shares']:.2f} shs @ ${t['price']:.2f} (P&L: ${t.get('pnl', 0.0):+,.2f})")

if __name__ == "__main__":
    main()
