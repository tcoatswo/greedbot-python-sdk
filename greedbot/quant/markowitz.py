"""
Markowitz Modern Portfolio Theory & Mean-Variance Optimization
--------------------------------------------------------------
Calculates the efficient frontier, global minimum variance (GMV) portfolio,
and maximum Sharpe ratio (tangency) asset weights using return covariance matrices.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Sequence
import numpy as np


class MeanVarianceOptimizer:
    """
    Markowitz Mean-Variance Portfolio Optimizer.
    
    Formulas:
        Portfolio Expected Return:   mu_p = w^T * mu
        Portfolio Variance:          sigma_p^2 = w^T * Sigma * w
        
        Global Minimum Variance (GMV):
            w_GMV = (Sigma^-1 * 1) / (1^T * Sigma^-1 * 1)
            
        Maximum Sharpe Ratio (Tangency):
            w_tan = (Sigma^-1 * (mu - r_f * 1)) / (1^T * Sigma^-1 * (mu - r_f * 1))
    """

    def __init__(self, risk_free_rate: float = 0.04):
        self.risk_free_rate = risk_free_rate

    @staticmethod
    def calculate_returns(price_matrix: Sequence[Sequence[float]]) -> np.ndarray:
        """Convert price series per asset to periodic percentage returns."""
        prices = np.array(price_matrix, dtype=float)
        # prices shape: (T, N) where T = periods, N = assets
        returns = np.diff(prices, axis=0) / prices[:-1]
        return returns

    def optimize_gmv(
        self,
        returns: np.ndarray,
        tickers: Sequence[str],
        long_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Calculates Global Minimum Variance (GMV) portfolio weights.
        """
        n_assets = returns.shape[1]
        cov_matrix = np.cov(returns, rowvar=False)

        # Add tiny regularization to diagonal for numerical inversion stability
        reg_cov = cov_matrix + (np.eye(n_assets) * 1e-6)
        inv_cov = np.linalg.pinv(reg_cov)
        ones = np.ones(n_assets)

        raw_weights = inv_cov.dot(ones) / (ones.T.dot(inv_cov).dot(ones))

        if long_only:
            # Project to simplex (non-negative weights summing to 1.0)
            raw_weights = np.maximum(0.0, raw_weights)
            total = np.sum(raw_weights)
            if total > 0:
                raw_weights = raw_weights / total
            else:
                raw_weights = np.ones(n_assets) / n_assets

        mean_returns = np.mean(returns, axis=0)
        port_return = float(np.dot(raw_weights, mean_returns))
        port_var = float(raw_weights.T.dot(cov_matrix).dot(raw_weights))
        port_vol = math.sqrt(max(0.0, port_var))

        allocations = {
            t.upper(): round(float(w), 4) for t, w in zip(tickers, raw_weights)
        }

        return {
            "strategy": "GLOBAL_MINIMUM_VARIANCE",
            "weights": allocations,
            "expected_return": round(port_return, 6),
            "volatility": round(port_vol, 6),
            "annualized_volatility": round(port_vol * math.sqrt(252), 4),
            "long_only": long_only,
        }

    def optimize_tangency(
        self,
        returns: np.ndarray,
        tickers: Sequence[str],
        long_only: bool = True,
    ) -> Dict[str, Any]:
        """
        Calculates Maximum Sharpe Ratio (Tangency) portfolio weights.
        """
        n_assets = returns.shape[1]
        cov_matrix = np.cov(returns, rowvar=False)
        mean_returns = np.mean(returns, axis=0)

        daily_rf = self.risk_free_rate / 252.0
        excess_returns = mean_returns - daily_rf

        reg_cov = cov_matrix + (np.eye(n_assets) * 1e-6)
        inv_cov = np.linalg.pinv(reg_cov)

        raw_weights = inv_cov.dot(excess_returns)
        sum_weights = np.sum(raw_weights)

        if abs(sum_weights) > 1e-9:
            raw_weights = raw_weights / sum_weights
        else:
            raw_weights = np.ones(n_assets) / n_assets

        if long_only:
            raw_weights = np.maximum(0.0, raw_weights)
            total = np.sum(raw_weights)
            if total > 0:
                raw_weights = raw_weights / total
            else:
                raw_weights = np.ones(n_assets) / n_assets

        port_return = float(np.dot(raw_weights, mean_returns))
        port_var = float(raw_weights.T.dot(cov_matrix).dot(raw_weights))
        port_vol = math.sqrt(max(0.0, port_var))
        sharpe = (port_return - daily_rf) / port_vol if port_vol > 1e-9 else 0.0

        allocations = {
            t.upper(): round(float(w), 4) for t, w in zip(tickers, raw_weights)
        }

        return {
            "strategy": "MAXIMUM_SHARPE_TANGENCY",
            "weights": allocations,
            "expected_return": round(port_return, 6),
            "volatility": round(port_vol, 6),
            "annualized_sharpe_ratio": round(sharpe * math.sqrt(252), 4),
            "long_only": long_only,
        }
