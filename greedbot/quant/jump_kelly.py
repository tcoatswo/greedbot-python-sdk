"""
Merton Jump-Diffusion Non-Linear Kelly Sizing Engine
---------------------------------------------------
Calculates optimal continuous-time fractional Kelly sizing (f*) for
asymmetric derivatives and OTM options under jump-diffusion dynamics
with continuous running-maximum drawdown penalties.
"""

from __future__ import annotations

import numpy as np
from typing import Any, Dict, Optional, Tuple, Union


def bisection_solve(f_func, a: float = 0.0, b: float = 1.0, tol: float = 1e-5, max_iter: int = 50) -> float:
    """Robust zero-finding on bounded interval [a, b]."""
    fa = f_func(a)
    fb = f_func(b)
    if fa * fb > 0:
        return 0.0  # No root or strictly negative expected utility

    for _ in range(max_iter):
        mid = (a + b) / 2.0
        fmid = f_func(mid)
        if abs(fmid) < tol or (b - a) / 2.0 < tol:
            return mid
        if fa * fmid < 0:
            b = mid
            fb = fmid
        else:
            a = mid
            fa = fmid
    return (a + b) / 2.0


def compute_jump_kelly(
    S: np.ndarray,
    O: np.ndarray,
    delta: np.ndarray,
    gamma: np.ndarray,
    theta: np.ndarray,
    sigma: np.ndarray,
    mu: float = 0.05,
    lambda_jump: float = 1.5,
    mu_J: float = 0.10,
    sigma_J: float = 0.20,
    gamma_penalty: float = 1.5,
    num_integration_nodes: int = 21,
) -> np.ndarray:
    """
    Vectorized computation of the Non-Linear Kelly fraction f* for OTM options
    under a Jump-Diffusion process with continuous drawdown penalty.
    """
    S = np.asarray(S, dtype=float)
    O = np.asarray(O, dtype=float)
    delta = np.asarray(delta, dtype=float)
    gamma = np.asarray(gamma, dtype=float)
    theta = np.asarray(theta, dtype=float)
    sigma = np.asarray(sigma, dtype=float)

    # 1. Option Continuous Drift & Variance from Greeks
    mu_O = (theta + mu * S * delta + 0.5 * (sigma**2) * (S**2) * gamma) / O
    sigma_O = (S / O) * delta * sigma

    # 2. Gauss-Hermite Quadrature for Expected Jump Integral
    z_nodes, w_nodes = np.polynomial.hermite.hermgauss(num_integration_nodes)
    z_nodes = z_nodes * np.sqrt(2.0)
    w_nodes = w_nodes / np.sqrt(np.pi)

    # Convert nodes to Log-Normal Jump severities
    J_nodes = np.exp(mu_J + sigma_J * z_nodes)

    optimal_f = np.zeros_like(S, dtype=float)

    for i in range(len(S)):
        _mu_O = mu_O[i]
        _sigma_O = sigma_O[i]

        # Second-order Greek approximation of jump impact
        J_impact = (
            S[i] * delta[i] * (J_nodes - 1.0)
            + 0.5 * (S[i] ** 2) * gamma[i] * ((J_nodes - 1.0) ** 2)
        ) / O[i]

        def marginal_growth(f: float) -> float:
            denom = 1.0 + f * J_impact
            denom = np.where(denom <= 1e-4, 1e-4, denom)
            jump_marginal = np.sum(w_nodes * (J_impact / denom))
            foc = _mu_O - (1.0 + 2.0 * gamma_penalty) * f * (_sigma_O**2) + lambda_jump * jump_marginal
            return float(foc)

        optimal_f[i] = bisection_solve(marginal_growth, a=0.0, b=1.0)

    return optimal_f


class MertonJumpKellySizer:
    """
    High-level sizer for Merton Jump-Diffusion Kelly options positioning.
    """

    def __init__(
        self,
        mu: float = 0.05,
        lambda_jump: float = 1.5,
        mu_J: float = 0.10,
        sigma_J: float = 0.20,
        gamma_penalty: float = 1.5,
    ):
        self.mu = mu
        self.lambda_jump = lambda_jump
        self.mu_J = mu_J
        self.sigma_J = sigma_J
        self.gamma_penalty = gamma_penalty

    def size_contract(
        self,
        stock_price: float,
        option_price: float,
        delta: float,
        gamma: float,
        theta: float,
        iv: float,
        capital_usd: float = 10000.0,
        max_risk_cap_pct: float = 0.25,
    ) -> Dict[str, Any]:
        """Calculates optimal fractional and dollar risk allocation for a single option contract."""
        f_arr = compute_jump_kelly(
            S=np.array([stock_price]),
            O=np.array([option_price]),
            delta=np.array([delta]),
            gamma=np.array([gamma]),
            theta=np.array([theta]),
            sigma=np.array([iv]),
            mu=self.mu,
            lambda_jump=self.lambda_jump,
            mu_J=self.mu_J,
            sigma_J=self.sigma_J,
            gamma_penalty=self.gamma_penalty,
        )
        f_star = float(f_arr[0])
        applied_fraction = min(f_star, max_risk_cap_pct)
        risk_dollars = round(capital_usd * applied_fraction, 2)

        return {
            "f_star": round(f_star, 4),
            "applied_fraction": round(applied_fraction, 4),
            "target_risk_dollars": risk_dollars,
            "capital_usd": capital_usd,
            "stock_price": stock_price,
            "option_price": option_price,
            "delta": delta,
            "gamma": gamma,
            "iv": iv,
        }
