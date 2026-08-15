"""
Event-Driven Backtesting Engine
-------------------------------
Simulates bar-by-bar strategy execution with realistic slippage, commission fees,
and strict avoidance of lookahead bias.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence
import numpy as np

from ..models import OrderIntent, Side
from ..signals.base import Signal, SignalDirection, SignalGenerator
from ..strategies.base import Strategy
from .metrics import PerformanceMetrics


@dataclass
class BacktestResult:
    """Complete output of a strategy backtest simulation."""
    metrics: PerformanceMetrics
    trades: List[Dict[str, Any]] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    signals: List[Any] = field(default_factory=list)

    def summary(self) -> str:
        return self.metrics.generate_tear_sheet()


class BacktestEngine:
    """
    Backtesting simulation engine.
    """

    def __init__(
        self,
        initial_capital: float = 10000.0,
        slippage_bps: float = 5.0,  # 5 basis points (0.05%)
        fee_per_trade: float = 1.00,  # $1 flat ticket commission
        risk_free_rate: float = 0.04,
        bars_per_year: int = 252,
    ):
        if initial_capital <= 0:
            raise ValueError("initial_capital must be > 0")
        self.initial_capital = initial_capital
        self.slippage_bps = slippage_bps
        self.fee_per_trade = fee_per_trade
        self.risk_free_rate = risk_free_rate
        self.bars_per_year = bars_per_year

    def run_signal_series(
        self,
        ticker: str,
        prices: Sequence[float],
        signal_generator: SignalGenerator,
        min_warmup_bars: int = 20,
        allocation_fraction: float = 0.50,
    ) -> BacktestResult:
        """
        Backtest a SignalGenerator bar-by-bar on historical close prices.
        Fills occur at the NEXT bar's open price with slippage applied.
        """
        prices = [float(p) for p in prices]
        n_bars = len(prices)
        if n_bars <= min_warmup_bars + 1:
            raise ValueError(f"Need at least {min_warmup_bars + 2} bars for simulation")

        cash = self.initial_capital
        position_shares = 0.0
        avg_entry_price = 0.0
        equity_curve: List[float] = []
        trades: List[Dict[str, Any]] = []
        signals_recorded: List[Signal] = []

        slippage_mult = self.slippage_bps / 10000.0

        for i in range(min_warmup_bars, n_bars - 1):
            history_slice = prices[: i + 1]
            curr_price = prices[i]
            next_price = prices[i + 1]  # Next bar execution price

            # Mark to market current equity
            current_equity = cash + (position_shares * curr_price)
            equity_curve.append(current_equity)

            # Generate signal on available history
            sig = signal_generator.generate(ticker, history_slice)
            signals_recorded.append(sig)

            # Execute state machine at next bar price
            if sig.direction == SignalDirection.LONG and position_shares <= 0:
                # Close short if open
                if position_shares < 0:
                    fill_price = next_price * (1.0 + slippage_mult)
                    pnl = (avg_entry_price - fill_price) * abs(position_shares) - self.fee_per_trade
                    cash += (abs(position_shares) * avg_entry_price) + pnl
                    trades.append({"type": "COVER", "price": fill_price, "shares": abs(position_shares), "pnl": pnl})
                    position_shares = 0.0

                # Open long
                fill_price = next_price * (1.0 + slippage_mult)
                alloc_dollars = current_equity * allocation_fraction
                shares_to_buy = (alloc_dollars - self.fee_per_trade) / fill_price
                if shares_to_buy > 0 and cash >= (shares_to_buy * fill_price + self.fee_per_trade):
                    cash -= (shares_to_buy * fill_price + self.fee_per_trade)
                    position_shares = shares_to_buy
                    avg_entry_price = fill_price

            elif sig.direction == SignalDirection.SHORT and position_shares >= 0:
                # Close long if open
                if position_shares > 0:
                    fill_price = next_price * (1.0 - slippage_mult)
                    pnl = (fill_price - avg_entry_price) * position_shares - self.fee_per_trade
                    cash += (position_shares * fill_price) - self.fee_per_trade
                    trades.append({"type": "SELL", "price": fill_price, "shares": position_shares, "pnl": pnl})
                    position_shares = 0.0

                # Open short
                fill_price = next_price * (1.0 - slippage_mult)
                alloc_dollars = current_equity * allocation_fraction
                shares_to_short = (alloc_dollars - self.fee_per_trade) / fill_price
                if shares_to_short > 0:
                    cash += (shares_to_short * fill_price) - self.fee_per_trade
                    position_shares = -shares_to_short
                    avg_entry_price = fill_price

            elif sig.direction == SignalDirection.FLAT:
                # Flatten any open position
                if position_shares > 0:
                    fill_price = next_price * (1.0 - slippage_mult)
                    pnl = (fill_price - avg_entry_price) * position_shares - self.fee_per_trade
                    cash += (position_shares * fill_price) - self.fee_per_trade
                    trades.append({"type": "FLAT_SELL", "price": fill_price, "shares": position_shares, "pnl": pnl})
                    position_shares = 0.0
                elif position_shares < 0:
                    fill_price = next_price * (1.0 + slippage_mult)
                    pnl = (avg_entry_price - fill_price) * abs(position_shares) - self.fee_per_trade
                    cash += (abs(position_shares) * avg_entry_price) + pnl
                    trades.append({"type": "FLAT_COVER", "price": fill_price, "shares": abs(position_shares), "pnl": pnl})
                    position_shares = 0.0

        # Close position at the final bar to compute realized P&L
        final_price = prices[-1]
        if position_shares > 0:
            pnl = (final_price - avg_entry_price) * position_shares - self.fee_per_trade
            cash += (position_shares * final_price) - self.fee_per_trade
            trades.append({"type": "FINAL_CLOSE", "price": final_price, "shares": position_shares, "pnl": pnl})
        elif position_shares < 0:
            pnl = (avg_entry_price - final_price) * abs(position_shares) - self.fee_per_trade
            cash += (abs(position_shares) * avg_entry_price) + pnl
            trades.append({"type": "FINAL_CLOSE", "price": final_price, "shares": abs(position_shares), "pnl": pnl})

        equity_curve.append(cash)

        metrics = PerformanceMetrics.calculate(
            equity_curve=equity_curve,
            trades=trades,
            risk_free_rate=self.risk_free_rate,
            bars_per_year=self.bars_per_year,
        )

        return BacktestResult(
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
            signals=signals_recorded,
        )
