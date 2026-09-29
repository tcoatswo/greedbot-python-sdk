"""
Risk Parity & Equal Risk Contribution (ERC) Portfolio Optimizer
--------------------------------------------------------------
Calculates asset allocations where each asset contributes equally to total portfolio risk.
Implements inverse-volatility weighting and full Equal Risk Contribution (ERC) via
cyclical coordinate descent.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Sequence
import numpy as np


class RiskParityOptimizer:
    """
    Risk Parity & Equal Risk Contribution Portfolio Optimizer.

    Formulas:
        Portfolio Variance: sigma_p^2 = w^T * Sigma * w
        Marginal Risk Contribution: MRC_i = (Sigma * w)_i / sigma_p
        Total Risk Contribution: TRC_i = w_i * MRC_i

    Equal Risk Contribution (ERC) Condition:
        TRC_i = TRC_j = sigma_p / N  for all assets i, j
    """

    def __init__(self, max_iterations: int = 100, tolerance: float = 1e-6):
        self.max_iterations = max_iterations
        self.tolerance = tolerance

    @staticmethod
    def calculate_returns(price_matrix: Sequence[Sequence[float]]) -> np.ndarray:
        """Convert price series per asset to periodic percentage returns."""
        prices = np.array(price_matrix, dtype=float)
        returns = np.diff(prices, axis=0) / prices[:-1]
        return returns

    def optimize_inverse_volatility(
        self,
        returns: np.ndarray,
        tickers: Sequence[str],
    ) -> Dict[str, Any]:
        """
        Calculates naive inverse-volatility risk parity weights: w_i proportional to 1 / sigma_i.
        """
        n_assets = returns.shape[1]
        if n_assets != len(tickers):
            raise ValueError(f"tickers length ({len(tickers)}) must match asset columns ({n_assets})")

        stds = np.std(returns, axis=0, ddof=1)
        # Avoid zero division
        inv_vols = np.where(stds > 1e-9, 1.0 / stds, 0.0)
        total_inv_vol = np.sum(inv_vols)

        if total_inv_vol > 0:
            weights = inv_vols / total_inv_vol
        else:
            weights = np.ones(n_assets) / n_assets

        cov_matrix = np.cov(returns, rowvar=False)
        mean_returns = np.mean(returns, axis=0)
        port_return = float(np.dot(weights, mean_returns))
        port_var = float(weights.T.dot(cov_matrix).dot(weights))
        port_vol = math.sqrt(max(0.0, port_var))

        allocations = {
            t.upper(): round(float(w), 4) for t, w in zip(tickers, weights)
        }

        return {
            "strategy": "INVERSE_VOLATILITY",
            "weights": allocations,
            "expected_return": round(port_return, 6),
            "volatility": round(port_vol, 6),
            "annualized_volatility": round(port_vol * math.sqrt(252), 4),
        }

    def optimize_equal_risk_contribution(
        self,
        returns: np.ndarray,
        tickers: Sequence[str],
    ) -> Dict[str, Any]:
        """
        Calculates exact Equal Risk Contribution (ERC) portfolio weights
        using cyclical coordinate descent.
        """
        n_assets = returns.shape[1]
        if n_assets != len(tickers):
            raise ValueError(f"tickers length ({len(tickers)}) must match asset columns ({n_assets})")

        cov_matrix = np.cov(returns, rowvar=False)
        # Regularize diagonal slightly for stability
        reg_cov = cov_matrix + (np.eye(n_assets) * 1e-8)

        # Initialize with inverse volatility
        stds = np.sqrt(np.diag(reg_cov))
        inv_vols = np.where(stds > 1e-9, 1.0 / stds, 1.0)
        w = inv_vols / np.sum(inv_vols)

        target_rc = 1.0 / n_assets

        # Cyclical coordinate descent
        for _ in range(self.max_iterations):
            w_prev = w.copy()
            for i in range(n_assets):
                # Solving: a * w_i^2 + b * w_i - c = 0
                # a = sigma_ii
                # b = sum_{k != i} sigma_ik * w_k
                # c = (w^T * Sigma * w) / n_assets
                sigma_ii = reg_cov[i, i]
                cov_i = reg_cov[i, :]
                other_sum = float(np.dot(cov_i, w) - sigma_ii * w[i])
                port_var = float(w.T.dot(reg_cov).dot(w))
                c_val = target_rc * port_var

                discriminant = other_sum**2 + 4.0 * sigma_ii * c_val
                if discriminant >= 0:
                    w[i] = (-other_sum + math.sqrt(discriminant)) / (2.0 * sigma_ii)
                else:
                    w[i] = max(1e-6, w[i])

            w_sum = np.sum(w)
            if w_sum > 0:
                w = w / w_sum

            # Check convergence
            if np.max(np.abs(w - w_prev)) < self.tolerance:
                break

        # Calculate final risk contributions
        port_var = float(w.T.dot(reg_cov).dot(w))
        port_vol = math.sqrt(max(1e-12, port_var))
        mrc = reg_cov.dot(w) / port_vol
        trc = w * mrc
        trc_pct = (trc / port_vol) * 100.0 if port_vol > 0 else np.zeros(n_assets)

        mean_returns = np.mean(returns, axis=0)
        port_return = float(np.dot(w, mean_returns))

        allocations = {
            t.upper(): round(float(weight), 4) for t, weight in zip(tickers, w)
        }
        risk_contributions = {
            t.upper(): round(float(rc), 2) for t, rc in zip(tickers, trc_pct)
        }

        return {
            "strategy": "EQUAL_RISK_CONTRIBUTION",
            "weights": allocations,
            "risk_contributions_pct": risk_contributions,
            "expected_return": round(port_return, 6),
            "volatility": round(port_vol, 6),
            "annualized_volatility": round(port_vol * math.sqrt(252), 4),
        }
