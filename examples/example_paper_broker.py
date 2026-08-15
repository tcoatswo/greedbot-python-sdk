"""
Example Paper Broker Simulation with Yahoo Finance
--------------------------------------------------
Demonstrates simulated trade execution with PaperBroker using live/historical
market prices from Yahoo Finance without lookahead bias.
"""

from greedbot import OrderIntent, PaperBroker, Side, YahooFinanceSource

def main():
    print("⚡ Running PaperBroker Simulation with Live Market Data...")

    # 1. Initialize Paper Broker with $50,000 cash and $1 flat fee per fill
    broker = PaperBroker(cash_usd=50000.0, fee_per_fill=1.0)
    print(f"Starting Cash: ${broker.cash:,.2f}")

    # 2. Define planned order intents
    intents = [
        OrderIntent(ticker="aapl", side=Side.BUY, dollars=10000.0),
        OrderIntent(ticker="msft", side=Side.BUY, dollars=10000.0, limit=600.0),
        OrderIntent(ticker="nvda", side=Side.BUY, dollars=10000.0),
    ]

    # 3. Fetch current bar prices from Yahoo Finance
    market_source = YahooFinanceSource()
    tickers = [i.ticker for i in intents]
    prices = market_source.get_latest_prices(tickers)
    print(f"\nFetched Market Prices: {prices}")

    # 4. Execute batch through PaperBroker
    fills = broker.execute(intents, prices=prices)
    print(f"\nExecuted Fills ({len(fills)}):")
    for f in fills:
        print(f"  • {f.side.value} {f.quantity:.2f} shs of {f.ticker.upper()} @ ${f.price:.2f} (Fee: ${f.fees:.2f})")

    print(f"\nUpdated Paper Positions: {broker.positions}")
    print(f"Remaining Cash: ${broker.cash:,.2f}")

    # 5. Execute a partial reduce/sell
    sell_intents = [
        OrderIntent(ticker="aapl", side=Side.SELL, dollars=5000.0),
    ]
    sell_fills = broker.execute(sell_intents, prices=prices)
    print(f"\nExecuted Partial Sell of AAPL:")
    for f in sell_fills:
        print(f"  • {f.side.value} {f.quantity:.2f} shs of {f.ticker.upper()} @ ${f.price:.2f}")

    print(f"Final Paper Positions: {broker.positions}")
    print(f"Final Cash: ${broker.cash:,.2f}")

if __name__ == "__main__":
    main()
