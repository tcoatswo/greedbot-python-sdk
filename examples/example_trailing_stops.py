"""
Example Dynamic Position Protection (Chandelier Exits & Trailing Stops)
-----------------------------------------------------------------------
Demonstrates ATR-based Chandelier stops and R-multiple profit ratchets.
"""

from greedbot import ChandelierExit, TrailingStopManager

def main():
    ticker = "NVDA"
    entry_price = 100.00
    initial_stop = 95.00  # 1R = $5.00 risk

    print(f"⚡ Testing Dynamic Trailing Stop Manager for {ticker} (Entry: ${entry_price:.2f}, Stop: ${initial_stop:.2f})...")

    # 1. R-Multiple Trailing Stop Manager
    manager = TrailingStopManager(
        ticker=ticker,
        entry_price=entry_price,
        initial_stop=initial_stop,
        direction="long",
    )

    price_progression = [100.0, 103.0, 105.5, 111.0, 116.0, 114.0, 109.0]

    print("\nPrice Action Simulation & Stop Ratchets:")
    for p in price_progression:
        status = manager.update(p)
        print(f"  • Price: ${p:6.2f} | Stop: ${status.stop_price:6.2f} | Unrealized: ${status.unrealized_pnl:+5.2f} ({status.r_multiple:+.1f}R) | Triggered: {status.is_triggered}")

    # 2. ATR Chandelier Exit
    print("\n⚡ Testing ATR Chandelier Exit:")
    chandelier = ChandelierExit(atr_period=5, multiplier_k=2.5)

    highs = [102.0, 104.0, 108.0, 112.0, 116.0]
    lows = [98.0, 101.0, 103.0, 107.0, 110.0]
    closes = [100.0, 103.0, 107.0, 111.0, 115.0]

    ratcheted_stop = chandelier.update_long_stop(
        current_stop=initial_stop,
        highs=highs,
        lows=lows,
        closes=closes,
    )
    print(f"  • Chandelier Long Stop ratcheted from ${initial_stop:.2f} to ${ratcheted_stop:.2f}")

if __name__ == "__main__":
    main()
