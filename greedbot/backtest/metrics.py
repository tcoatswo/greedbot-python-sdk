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
    Includes absolute returns, risk-adjusted ratios (Sharpe, Sortino, Calmar),
    tail-risk statistics (VaR, CVaR), drawdown analytics, and optional benchmark comparisons.
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
    var_95_pct: float = 0.0
    var_99_pct: float = 0.0
    cvar_95_pct: float = 0.0
    cvar_99_pct: float = 0.0
    daily_returns: List[float] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)
    drawdown_series: List[float] = field(default_factory=list)
    # Benchmark relative analytics
    benchmark_total_return_pct: Optional[float] = None
    alpha: Optional[float] = None
    beta: Optional[float] = None
    information_ratio: Optional[float] = None
    treynor_ratio: Optional[float] = None

    @classmethod
    def calculate(
        cls,
        equity_curve: Sequence[float],
        trades: Sequence[Dict[str, Any]],
        risk_free_rate: float = 0.04,
        bars_per_year: int = 252,
        benchmark_prices: Optional[Sequence[float]] = None,
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

        # Max Drawdown & Drawdown series
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

        # Historical Value at Risk (VaR) & Conditional VaR (CVaR / Expected Shortfall)
        if len(returns) > 1:
            # Losses are negative returns; VaR represents the threshold loss percentage
            losses = -returns * 100.0
            var_95 = float(np.percentile(losses, 95))
            var_99 = float(np.percentile(losses, 99))
            cvar_95_losses = losses[losses >= var_95]
            cvar_95 = float(np.mean(cvar_95_losses)) if len(cvar_95_losses) > 0 else var_95
            cvar_99_losses = losses[losses >= var_99]
            cvar_99 = float(np.mean(cvar_99_losses)) if len(cvar_99_losses) > 0 else var_99
        else:
            var_95 = var_99 = cvar_95 = cvar_99 = 0.0

        # Benchmark relative calculations
        bench_ret_pct: Optional[float] = None
        alpha_val: Optional[float] = None
        beta_val: Optional[float] = None
        info_ratio: Optional[float] = None
        treynor_val: Optional[float] = None

        if benchmark_prices is not None and len(benchmark_prices) > 1:
            b_arr = np.array(benchmark_prices, dtype=float)
            bench_ret_pct = round(((b_arr[-1] - b_arr[0]) / b_arr[0]) * 100.0, 2)
            b_returns = np.diff(b_arr) / b_arr[:-1]

            # Match lengths
            min_len = min(len(returns), len(b_returns))
            strat_r = returns[-min_len:]
            bench_r = b_returns[-min_len:]

            var_b = float(np.var(bench_r, ddof=1)) if min_len > 1 else 0.0
            if var_b > 1e-9:
                cov_sb = float(np.cov(strat_r, bench_r)[0, 1])
                beta_calc = cov_sb / var_b
            else:
                beta_calc = 1.0

            beta_val = round(beta_calc, 2)

            # Annualized benchmark return
            bench_cagr = (((b_arr[-1] / b_arr[0]) ** (1.0 / years)) - 1.0) * 100.0 if b_arr[-1] > 0 else -100.0
            rf_pct = risk_free_rate * 100.0
            # Jensen's Alpha: CAGR - [Rf + Beta * (Bench_CAGR - Rf)]
            alpha_calc = cagr - (rf_pct + beta_calc * (bench_cagr - rf_pct))
            alpha_val = round(alpha_calc, 2)

            # Tracking error and Information Ratio
            active_ret = strat_r - bench_r
            tracking_error = float(np.std(active_ret, ddof=1)) * math.sqrt(bars_per_year) if min_len > 1 else 0.0
            if tracking_error > 1e-9:
                ir_calc = (float(np.mean(active_ret)) * bars_per_year) / tracking_error
                info_ratio = round(ir_calc, 2)

            if abs(beta_calc) > 1e-4:
                treynor_val = round((cagr - rf_pct) / beta_calc, 2)

        # Trade analytics
        n_trades = len(trades)
        wins = [t["pnl"] for t in trades if t.get("pnl", 0.0) > 0]
        losses_trade = [abs(t["pnl"]) for t in trades if t.get("pnl", 0.0) < 0]

        n_wins = len(wins)
        n_losses = len(losses_trade)
        win_rate = (n_wins / float(n_trades) * 100.0) if n_trades > 0 else 0.0

        total_gross_win = sum(wins)
        total_gross_loss = sum(losses_trade)
        if total_gross_loss > 0:
            profit_factor = total_gross_win / total_gross_loss
        else:
            profit_factor = 999.0 if total_gross_win > 0 else 0.0

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
            var_95_pct=round(var_95, 2),
            var_99_pct=round(var_99, 2),
            cvar_95_pct=round(cvar_95, 2),
            cvar_99_pct=round(cvar_99, 2),
            daily_returns=returns.tolist(),
            equity_curve=eq.tolist(),
            drawdown_series=(drawdowns * 100.0).tolist(),
            benchmark_total_return_pct=bench_ret_pct,
            alpha=alpha_val,
            beta=beta_val,
            information_ratio=info_ratio,
            treynor_ratio=treynor_val,
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
            ["Historical VaR (95% / 99%)", f"{self.var_95_pct:.2f}% / {self.var_99_pct:.2f}%"],
            ["Conditional VaR / CVaR (95% / 99%)", f"{self.cvar_95_pct:.2f}% / {self.cvar_99_pct:.2f}%"],
            ["Total Executed Trades", f"{self.total_trades}"],
            ["Win Rate", f"{self.win_rate_pct:.1f}% ({self.winning_trades}W / {self.losing_trades}L)"],
            ["Profit Factor", f"{self.profit_factor:.2f}"],
            ["Average Win / Loss", f"${self.avg_win_usd:,.2f} / ${self.avg_loss_usd:,.2f}"],
            ["Payoff Ratio (b)", f"{self.payoff_ratio:.2f}"],
        ]

        if self.benchmark_total_return_pct is not None:
            table_data.extend([
                ["Benchmark Total Return", f"{self.benchmark_total_return_pct:+.2f}%"],
                ["Beta (Market Sensitivity)", f"{self.beta:.2f}" if self.beta is not None else "N/A"],
                ["Jensen's Alpha", f"{self.alpha:+.2f}%" if self.alpha is not None else "N/A"],
                ["Information Ratio (IR)", f"{self.information_ratio:.2f}" if self.information_ratio is not None else "N/A"],
                ["Treynor Ratio", f"{self.treynor_ratio:.2f}" if self.treynor_ratio is not None else "N/A"],
            ])

        return tabulate(table_data, headers=["Performance Metric", "Value"], tablefmt="fancy_grid")
