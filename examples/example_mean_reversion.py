"""
Example Mean Reversion Strategy (Bollinger Bands & Z-Score)
-----------------------------------------------------------
Identifies statistically extreme price deviations (Z-score > 2 or < -2)
and trades for a return to the rolling mean.
"""

from greedbot import MeanReversionStrategy, BollingerMeanReversion

def main():
    ticker = "SPY"
    capital_usd = 25000.0

    print(f"⚡ Running Bollinger Bands & Z-Score Mean Reversion for {ticker}...")

    strategy = MeanReversionStrategy(
        ticker=ticker,
        window=20,
        z_threshold=2.0,
        kelly_fraction=0.50,
    )

    # Simulated price series with oversold dip at end
    prices = [500.0 + (i % 5) * 1.2 for i in range(25)]
    prices[-1] = 485.0  # Sharp temporary drop causing Z < -2

    result = strategy.run(capital_usd=capital_usd, prices=prices)
    eval_data = result.summary["evaluation"]

    print("\nMean Reversion Indicator Evaluation:")
    print(f"  • Current Price: ${eval_data['current_price']:.2f}")
    print(f"  • Rolling Mean (20): ${eval_data['rolling_mean']:.2f}")
    print(f"  • Bollinger Upper (+2σ): ${eval_data['upper_band']:.2f}")
    print(f"  • Bollinger Lower (-2σ): ${eval_data['lower_band']:.2f}")
    print(f"  • Statistical Z-Score: {eval_data['z_score']:+.2f}")
    print(f"  • Action: {eval_data['action']}")

    print(f"\nOrder Intents ({len(result.intents)}):")
    for intent in result.intents:
        print(f"  • {intent.side.value} {intent.ticker.upper()} ${intent.dollars:,.2f}")

if __name__ == "__main__":
    main()
