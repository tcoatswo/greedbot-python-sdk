"""
Example Statistical Arbitrage Pairs Trading (Cointegration & OLS Spread)
------------------------------------------------------------------------
Calculates dynamic OLS hedge ratio beta, spread series, and spread Z-score
between cointegrated assets (SPY vs QQQ) to trade market-neutral spread convergence.
"""

from greedbot import StatArbPairsStrategy

def main():
    ticker_a = "SPY"
    ticker_b = "QQQ"
    capital_usd = 50000.0

    print(f"⚡ Running Statistical Arbitrage Pairs Trading ({ticker_a} vs {ticker_b})...")

    strategy = StatArbPairsStrategy(
        ticker_a=ticker_a,
        ticker_b=ticker_b,
        lookback_window=60,
        z_threshold=2.0,
        gross_fraction=0.20,
    )

    # Simulated cointegrated series with a transient divergence
    prices_b = [400.0 + i * 0.5 + (i % 4) * 0.8 for i in range(70)]
    prices_a = [p * 1.3 + (8.0 if i >= 65 else 0.0) for i, p in enumerate(prices_b)]

    result = strategy.run(capital_usd=capital_usd, prices_a=prices_a, prices_b=prices_b)
    summary = result.summary

    print("\nCointegration & Spread Statistics:")
    print(f"  • Pair: {summary['pair']}")
    print(f"  • Dynamic OLS Hedge Ratio (β): {summary['beta']:.4f}")
    print(f"  • Spread Z-Score: {summary['spread_z']:+.2f}")

    print(f"\nOrder Intents ({len(result.intents)}):")
    for intent in result.intents:
        print(f"  • {intent.side.value} {intent.ticker.upper()} ${intent.dollars:,.2f}")

if __name__ == "__main__":
    main()
