"""
Example Markowitz Modern Portfolio Theory & Mean-Variance Optimization
----------------------------------------------------------------------
Calculates Global Minimum Variance (GMV) and Maximum Sharpe Ratio (Tangency)
portfolios across a multi-asset basket (SPY, QQQ, GLD, TLT, PDBC).
"""

import numpy as np
from greedbot import MarkowitzAllocationStrategy, MeanVarianceOptimizer

def main():
    assets = ["SPY", "QQQ", "GLD", "TLT", "PDBC"]
    capital_usd = 100000.0

    print(f"⚡ Running Markowitz Mean-Variance Portfolio Optimization on {assets}...")

    optimizer = MeanVarianceOptimizer(risk_free_rate=0.04)

    # Simulated historical returns
    np.random.seed(42)
    n_periods = 252  # 1 year daily
    daily_returns = np.random.normal(
        loc=[0.0004, 0.0005, 0.0002, 0.0001, 0.0003],
        scale=[0.010, 0.014, 0.008, 0.006, 0.012],
        size=(n_periods, len(assets)),
    )

    # 1. Global Minimum Variance (GMV) Portfolio
    gmv_res = optimizer.optimize_gmv(daily_returns, assets, long_only=True)
    print("\n1. Global Minimum Variance (GMV) Allocation:")
    for ticker, weight in gmv_res["weights"].items():
        print(f"  • {ticker}: {weight * 100:.1f}% -> ${capital_usd * weight:,.2f}")
    print(f"  Annualized Volatility: {gmv_res['annualized_volatility'] * 100:.2f}%")

    # 2. Maximum Sharpe Ratio (Tangency) Portfolio
    tan_res = optimizer.optimize_tangency(daily_returns, assets, long_only=True)
    print("\n2. Maximum Sharpe Ratio (Tangency) Allocation:")
    for ticker, weight in tan_res["weights"].items():
        print(f"  • {ticker}: {weight * 100:.1f}% -> ${capital_usd * weight:,.2f}")
    print(f"  Annualized Sharpe Ratio: {tan_res['annualized_sharpe_ratio']:.2f}")

    # 3. Strategy Execution
    strategy = MarkowitzAllocationStrategy(assets=assets, mode="tangency")
    result = strategy.run(capital_usd=capital_usd)

    print(f"\nGenerated {len(result.intents)} Rebalance Order Intents:")
    for intent in result.intents:
        print(f"  • Buy {intent.ticker.upper()}: ${intent.dollars:,.2f}")

if __name__ == "__main__":
    main()
