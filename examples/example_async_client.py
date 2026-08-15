"""
Example Asynchronous Client & High-Concurrency Scanner
------------------------------------------------------
Demonstrates concurrent non-blocking API calls using AsyncGreedBotClient and asyncio.
"""

import asyncio
from greedbot import AsyncGreedBotClient

async def main():
    client = AsyncGreedBotClient()
    print(f"⚡ Initialized Async Client: {client}")

    # 1. Asynchronous Health Check (Free)
    try:
        ping_res = await client.ping()
        print(f"Async Ping: {ping_res}")
    except Exception as e:
        print(f"Ping failed: {e}")

    # 2. Concurrent Multi-Ticker Expected Move Pricing
    tickers = ["NVDA", "TSLA", "AAPL", "MSFT", "AMD"]
    print(f"\n⚡ Scanning {len(tickers)} tickers concurrently with asyncio.gather()...")

    try:
        batch_moves = await client.batch_scan_expected_moves(tickers)
        for sym, data in batch_moves.items():
            if "error" in data:
                print(f"  • {sym}: Scan error - {data['error']}")
            else:
                print(f"  • {sym}: Expected Move ±{data.get('expected_move_pct')}% (Status: {data.get('status')})")
    except Exception as e:
        print(f"Batch scan failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
