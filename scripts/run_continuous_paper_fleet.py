#!/usr/bin/env python3
"""
GreedBot Continuous Paper Trading & Fly Trader Simulation Daemon
----------------------------------------------------------------
Runs continuous 24/7 background simulations for both:
1. Drosophila Connectome Bio-Trader (Neural ODE + Merton Jump Kelly + Dopamine Plasticity)
2. Institutional Quant Paper Portfolio (GEX + Iron Condor Theta Harvesting + Chandelier Exits)

Architecture:
- 100% Local Compute (Zero LLM tokens, Zero paid API calls)
- Live/Simulated multi-asset ticks (BTC, ETH, SPY, QQQ, NVDA)
- Persists all executions, positions, and equity curves to ~/clawd/data/paper_trading.db
"""

import logging
import math
import os
import random
import signal
import sys
import time
from datetime import datetime

import numpy as np

# Ensure greedbot is imported
import greedbot
from greedbot.paper_engine import InstitutionalPaperBroker
from greedbot.fly_trader import DrosophilaConnectomeTrader, ConnectomeSensoryInput
from greedbot.quant.gex import GEXEngine, OptionContractData
from greedbot.quant.spreads import IronCondor
from greedbot.models import Side

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("paper_fleet")

DB_PATH = os.path.expanduser("~/clawd/data/paper_trading.db")

RUNNING = True

def handle_sigterm(signum, frame):
    global RUNNING
    logger.info("Termination signal received. Shutting down cleanly...")
    RUNNING = False

signal.signal(signal.SIGINT, handle_sigterm)
signal.signal(signal.SIGTERM, handle_sigterm)


class MultiAssetSimulatedMarket:
    """
    Simulates realistic price walks with stochastic volatility and jump diffusion
    for continuous offline/local paper trading.
    """

    def __init__(self):
        self.prices = {
            "SPY": 580.0,
            "QQQ": 490.0,
            "NVDA": 118.0,
            "BTC": 78000.0,
            "ETH": 3100.0,
        }
        self.vols = {
            "SPY": 0.16,
            "QQQ": 0.22,
            "NVDA": 0.45,
            "BTC": 0.55,
            "ETH": 0.60,
        }
        self.tick_history = {k: [] for k in self.prices}

    def generate_tick(self, ticker: str) -> float:
        p = self.prices[ticker]
        vol = self.vols[ticker]
        dt = 1.0 / (252.0 * 390.0 * 60.0)  # 1-second step

        # Geometric Brownian Motion step
        drift = 0.08 * dt
        shock = vol * math.sqrt(dt) * np.random.normal(0, 1)
        
        # Occasional jump shock (0.1% chance)
        if random.random() < 0.001:
            jump = np.random.normal(-0.015, 0.02)
        else:
            jump = 0.0

        new_p = max(0.01, p * math.exp(drift + shock + jump))
        self.prices[ticker] = new_p
        
        self.tick_history[ticker].append(new_p)
        if len(self.tick_history[ticker]) > 300:
            self.tick_history[ticker].pop(0)

        return new_p

    def get_velocity(self, ticker: str) -> float:
        hist = self.tick_history[ticker]
        if len(hist) < 2:
            return 0.0
        return ((hist[-1] - hist[0]) / hist[0]) * 100.0


def main_loop(iterations: int = 100, tick_interval_sec: float = 0.1, standalone: bool = False):
    logger.info("Initializing Institutional Paper Broker ($100k starting capital)...")
    broker = InstitutionalPaperBroker(starting_cash=100000.0, db_path=DB_PATH)

    logger.info("Initializing Drosophila Connectome Fly Trader (2000 Kenyon Cells, MBONs)...")
    fly = DrosophilaConnectomeTrader(broker=broker)

    market = MultiAssetSimulatedMarket()
    tickers = ["SPY", "QQQ", "NVDA", "BTC", "ETH"]

    logger.info("Starting Paper Fleet Simulation Loop...")
    step = 0

    while RUNNING and (standalone or step < iterations):
        step += 1
        ticker = random.choice(tickers)
        current_price = market.generate_tick(ticker)
        broker.update_market_price(ticker, current_price)

        velocity = market.get_velocity(ticker)
        bid_ask_delta = np.clip(np.random.normal(0.05 if velocity > 0 else -0.05, 0.3), -1.0, 1.0)
        net_gex_regime = 1.0 if abs(velocity) < 0.2 else -1.0
        iv_skew = 0.20 + abs(velocity) * 0.05

        sensor = ConnectomeSensoryInput(
            ticker=ticker,
            price=current_price,
            price_velocity_5m=velocity,
            bid_ask_delta=float(bid_ask_delta),
            net_gex_regime=net_gex_regime,
            iv_skew=iv_skew,
        )

        decision = fly.process_tick(sensor)

        # Execute decision in paper broker
        if decision.action == "BUY" and broker.cash > decision.target_dollars:
            qty = max(1.0, round(decision.target_dollars / current_price, 4))
            try:
                fill = broker.execute_order(ticker=ticker, side=Side.BUY, quantity=qty, mid_price=current_price)
                logger.info(f"[FLY-BUY] {qty} {ticker} @ ${fill.price:,.2f} | Cash: ${broker.cash:,.2f}")
            except Exception as e:
                logger.debug(f"Buy rejected: {e}")

        elif decision.action == "SELL" and ticker.lower() in broker.positions:
            curr_pos = broker.positions[ticker.lower()]
            if curr_pos > 0:
                sell_qty = min(curr_pos, max(1.0, round(curr_pos * 0.5, 4)))
                try:
                    fill = broker.execute_order(ticker=ticker, side=Side.SELL, quantity=sell_qty, mid_price=current_price)
                    logger.info(f"[FLY-SELL] {sell_qty} {ticker} @ ${fill.price:,.2f} | Realized PnL: ${broker.realized_pnl:,.2f}")
                    # Synaptic dopamine feedback
                    fly.learn_from_pnl(broker.realized_pnl)
                except Exception as e:
                    logger.debug(f"Sell rejected: {e}")

        # Periodic Snapshot (every 20 steps)
        if step % 20 == 0:
            snapshot = broker.record_snapshot()
            logger.info(
                f"📊 [SNAPSHOT #{step}] Portfolio: ${snapshot['portfolio_value']:,.2f} | "
                f"Cash: ${snapshot['cash']:,.2f} | Realized: ${snapshot['realized_pnl']:+,.2f} | "
                f"Open Positions: {snapshot['positions_count']}"
            )

        time.sleep(tick_interval_sec)

    logger.info("Simulation completed or stopped.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="GreedBot Continuous Paper Trading & Fly Trader Runner")
    parser.add_argument("--steps", type=int, default=100, help="Number of simulation steps")
    parser.add_argument("--interval", type=float, default=0.05, help="Seconds per tick")
    parser.add_argument("--continuous", action="store_true", help="Run indefinitely in background")
    args = parser.parse_args()

    main_loop(iterations=args.steps, tick_interval_sec=args.interval, standalone=args.continuous)
