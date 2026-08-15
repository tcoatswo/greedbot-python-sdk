"""
Example Avellaneda-Stoikov Market Making Strategy
-------------------------------------------------
Calculates inventory-risk-adjusted reservation price and optimal spread
to place two-sided limit orders and capture bid-ask spreads.
"""

from greedbot import AvellanedaStoikovMarketMaker, MarketMakerStrategy

def main():
    ticker = "NVDA"
    mid_price = 125.00
    volatility = 0.03  # 3% daily volatility

    print(f"⚡ Running Avellaneda-Stoikov Market Maker for {ticker} @ Mid: ${mid_price:.2f}...")

    mm_model = AvellanedaStoikovMarketMaker(gamma=0.1, k=1.5)

    # 1. Neutral inventory (q = 0)
    quotes_neutral = mm_model.calculate_quotes(
        mid_price=mid_price,
        inventory_q=0.0,
        volatility_sigma=volatility,
    )
    print("\n1. Neutral Inventory Quotes (q = 0):")
    print(f"  • Reservation Price: ${quotes_neutral['reservation_price']:.2f} (Mid: ${mid_price:.2f})")
    print(f"  • Bid Quote: ${quotes_neutral['bid_price']:.2f}")
    print(f"  • Ask Quote: ${quotes_neutral['ask_price']:.2f}")
    print(f"  • Spread: ${quotes_neutral['spread']:.2f}")

    # 2. Long inventory skew (q = +500 shares)
    # Reservation price automatically drops, lowering both bid and ask to encourage sells
    quotes_long = mm_model.calculate_quotes(
        mid_price=mid_price,
        inventory_q=500.0,
        volatility_sigma=volatility,
    )
    print("\n2. Long Inventory Skewed Quotes (q = +500 shares):")
    print(f"  • Reservation Price: ${quotes_long['reservation_price']:.2f} (Dropped below mid to shed inventory)")
    print(f"  • Lowered Bid: ${quotes_long['bid_price']:.2f}")
    print(f"  • Lowered Ask: ${quotes_long['ask_price']:.2f}")

    # 3. Strategy Order Intent Generation
    strategy = MarketMakerStrategy(ticker=ticker, quote_size_usd=2500.0)
    result = strategy.run(mid_price=mid_price, inventory_q=0.0, volatility_sigma=volatility)

    print("\nGenerated Dual Limit Order Intents:")
    for intent in result.intents:
        print(f"  • Limit {intent.side.value} {intent.ticker.upper()} ${intent.dollars:,.2f} @ Limit Price ${intent.limit:.2f}")

if __name__ == "__main__":
    main()
