"""
Example Trend Following & Momentum Strategy
-------------------------------------------
Combines Moving Average Crossover (Fast vs Slow SMA) and Time-Series Momentum
(Rate of Change & Acceleration) to trade directional breakouts with Kelly risk sizing.
"""

from greedbot import GreedBotClient, TrendFollowingStrategy, MovingAverageCrossover, TimeSeriesMomentum

def main():
    ticker = "NVDA"
    capital_usd = 25000.0

    print(f"⚡ Running Trend Following & Momentum Strategy for {ticker}...")

    strategy = TrendFollowingStrategy(
        ticker=ticker,
        short_window=10,
        long_window=50,
        momentum_lookback=14,
        kelly_fraction=0.50,
    )

    # Simulated upward trend price series
    prices = [100.0 + i * 0.8 + (i % 3) * 0.5 for i in range(70)]

    result = strategy.run(capital_usd=capital_usd, prices=prices)
    eval_data = result.summary["evaluation"]

    print("\nSignal Evaluation:")
    print(f"  • Fast SMA (10): ${eval_data['sma_short']:.2f}")
    print(f"  • Slow SMA (50): ${eval_data['sma_long']:.2f}")
    print(f"  • Momentum (ROC 14): {eval_data['momentum_pct']:+.2f}%")
    print(f"  • Acceleration: {eval_data['acceleration']:+.2f}")
    print(f"  • Action: {eval_data['action']} (Confidence: {eval_data['confidence'] * 100:.1f}%)")

    print(f"\nOrder Intents ({len(result.intents)}):")
    for intent in result.intents:
        print(f"  • {intent.side.value} {intent.ticker.upper()} ${intent.dollars:,.2f}")

if __name__ == "__main__":
    main()
