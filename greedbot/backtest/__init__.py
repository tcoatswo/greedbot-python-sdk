"""
GreedBot Quantitative Backtesting & Performance Analytics
---------------------------------------------------------
Contains event-driven bar-by-bar backtest simulations, transaction cost modeling,
and performance metrics analytics (CAGR, Sharpe, Sortino, Calmar, Max Drawdown).
"""

from .metrics import PerformanceMetrics
from .engine import BacktestEngine, BacktestResult

__all__ = [
    "PerformanceMetrics",
    "BacktestEngine",
    "BacktestResult",
]
