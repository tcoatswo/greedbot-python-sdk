"""
Quantitative Performance Metrics & Tear Sheet Generator
-------------------------------------------------------
Calculates comprehensive risk-adjusted performance statistics:
CAGR, Sharpe, Sortino, Calmar, Max Drawdown, Win Rate, Profit Factor, and Payoff Ratio.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence
import numpy as np
from tabulate import tabulate


@dataclass
class PerformanceMetrics:
    """
    Standardized quantitative trading performance metrics.
    """
    initial_capital: float
    final_equity: float
    net_profit: float
    total_return_pct: float
    cagr_pct: float
    annualized_sharpe: float
    annualized_sortino: float
    max_drawdown_pct: float
    max_drawdown_duration_bars: int
    calmar_ratio: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    avg_win_usd: float
    avg_loss_usd: float
    payoff_ratio: float
    daily_returns: List[float] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)

    @classmethod
    def calculate(
        cls,
        equity_curve: Sequence[float],
        trades: Sequence[Dict[str, Any]],
        risk_free_rate: float = 0.04,
        bars_per_year: int = 252,
    ) -> PerformanceMetrics:
        if not equity_curve:
            raise ValueError("equity_curve cannot be empty")

        eq = np.array(equity_curve, dtype=float)
        init_cap = float(eq[0])
        final_eq = float(eq[-1])
        net_profit = final_eq - init_cap
        total_ret = ((final_eq - init_cap) / init_cap) * 100.0

        n_bars = len(eq)
        years = max(1e-4, n_bars / float(bars_per_year))
        cagr = (((final_eq / init_cap) ** (1.0 / years)) - 1.0) * 100.0 if final_eq > 0 else -100.0

        # Periodic returns
        if len(eq) > 1:
            returns = np.diff(eq) / eq[:-1]
        else:
            returns = np.array([0.0])

        daily_rf = risk_free_rate / float(bars_per_year)
        excess_returns = returns - daily_rf
        mean_excess = float(np.mean(excess_returns))
        std_returns = float(np.std(returns, ddof=1)) if len(returns) > 1 else 0.0

        # Annualized Sharpe Ratio
        if std_returns > 1e-9:
            sharpe = (mean_excess / std_returns) * math.sqrt(bars_per_year)
        else:
            sharpe = 0.0

        # Annualized Sortino Ratio (Downside deviation only)
        downside_returns = returns[returns < 0]
        if len(downside_returns) > 1:
            downside_std = float(np.std(downside_returns, ddof=1))
            sortino = (mean_excess / downside_std) * math.sqrt(bars_per_year) if downside_std > 1e-9 else 0.0
        else:
            sortino = sharpe

        # Max Drawdown
        peak = np.maximum.accumulate(eq)
        drawdowns = (peak - eq) / peak
        max_dd = float(np.max(drawdowns)) * 100.0 if len(drawdowns) > 0 else 0.0

        # Max Drawdown Duration
        max_dd_bars = 0
        curr_dd_bars = 0
        for dd in drawdowns:
            if dd > 0:
                curr_dd_bars += 1
                max_dd_bars = max(max_dd_bars, curr_dd_bars)
            else:
                curr_dd_bars = 0

        # Calmar Ratio (CAGR / Max Drawdown)
        calmar = (cagr / max_dd) if max_dd > 1e-4 else (cagr if cagr > 0 else 0.0)

        # Trade analytics
        n_trades = len(trades)
        wins = [t["pnl"] for t in trades if t.get("pnl", 0.0) > 0]
        losses = [abs(t["pnl"]) for t in trades if t.get("pnl", 0.0) < 0]

        n_wins = len(wins)
        n_losses = len(losses)
        win_rate = (n_wins / float(n_trades) * 100.0) if n_trades > 0 else 0.0

        total_gross_win = sum(wins)
        total_gross_loss = sum(losses)
        profit_factor = (total_gross_win / total_gross_loss) if total_gross_loss > 0 else (999.0 if total_gross_win > 0 else 0.0)

        avg_win = (total_gross_win / n_wins) if n_wins > 0 else 0.0
        avg_loss = (total_gross_loss / n_losses) if n_losses > 0 else 0.0
        payoff = (avg_win / avg_loss) if avg_loss > 0 else 0.0

        return cls(
            initial_capital=round(init_cap, 2),
            final_equity=round(final_eq, 2),
            net_profit=round(net_profit, 2),
            total_return_pct=round(total_ret, 2),
            cagr_pct=round(cagr, 2),
            annualized_sharpe=round(sharpe, 2),
            annualized_sortino=round(sortino, 2),
            max_drawdown_pct=round(max_dd, 2),
            max_drawdown_duration_bars=max_dd_bars,
            calmar_ratio=round(calmar, 2),
            total_trades=n_trades,
            winning_trades=n_wins,
            losing_trades=n_losses,
            win_rate_pct=round(win_rate, 2),
            profit_factor=round(profit_factor, 2),
            avg_win_usd=round(avg_win, 2),
            avg_loss_usd=round(avg_loss, 2),
            payoff_ratio=round(payoff, 2),
            daily_returns=returns.tolist(),
            equity_curve=eq.tolist(),
        )

    def generate_tear_sheet(self) -> str:
        """Render a formatted ASCII table performance tear sheet."""
        table_data = [
            ["Initial Capital", f"${self.initial_capital:,.2f}"],
            ["Final Net Equity", f"${self.final_equity:,.2f}"],
            ["Total Net Profit", f"${self.net_profit:+,.2f} ({self.total_return_pct:+.2f}%)"],
            ["Compound Annual Growth (CAGR)", f"{self.cagr_pct:+.2f}%"],
            ["Annualized Sharpe Ratio", f"{self.annualized_sharpe:.2f}"],
            ["Annualized Sortino Ratio", f"{self.annualized_sortino:.2f}"],
            ["Max Drawdown (MDD)", f"{self.max_drawdown_pct:.2f}% ({self.max_drawdown_duration_bars} bars)"],
            ["Calmar Ratio", f"{self.calmar_ratio:.2f}"],
            ["Total Executed Trades", f"{self.total_trades}"],
            ["Win Rate", f"{self.win_rate_pct:.1f}% ({self.winning_trades}W / {self.losing_trades}L)"],
            ["Profit Factor", f"{self.profit_factor:.2f}"],
            ["Average Win / Loss", f"${self.avg_win_usd:,.2f} / ${self.avg_loss_usd:,.2f}"],
            ["Payoff Ratio (b)", f"{self.payoff_ratio:.2f}"],
        ]
        return tabulate(table_data, headers=["Performance Metric", "Value"], tablefmt="fancy_grid")
