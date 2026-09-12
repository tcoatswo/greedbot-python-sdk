"""
GreedBot Monte Carlo Portfolio Stress-Testing & CVaR Engine
----------------------------------------------------------
Simulates stochastic multi-asset price paths using Geometric Brownian Motion (GBM)
and Merton Jump Diffusion to compute Portfolio Value at Risk (VaR) and Conditional VaR (Expected Shortfall).
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import math
import numpy as np

@dataclass
class MonteCarloResult:
    initial_portfolio_value: float
    time_horizon_days: int
    num_simulations: int
    var_95_pct: float
    var_99_pct: float
    cvar_95_pct: float  # Expected Shortfall
    cvar_99_pct: float
    median_ending_value: float
    mean_ending_value: float
    simulated_paths: np.ndarray  # Shape: (num_simulations, time_horizon_days + 1)

    def summary(self) -> str:
        return (
            f"--- Monte Carlo Risk & Stress-Test Summary ---\n"
            f"Initial Portfolio   : ${self.initial_portfolio_value:,.2f}\n"
            f"Time Horizon        : {self.time_horizon_days} days ({self.num_simulations:,} paths)\n"
            f"Expected Ending Val : ${self.mean_ending_value:,.2f} (Median: ${self.median_ending_value:,.2f})\n"
            f"95% Value at Risk   : -${self.var_95_pct:,.2f} (Loss at 95th percentile)\n"
            f"99% Value at Risk   : -${self.var_99_pct:,.2f} (Loss at 99th percentile)\n"
            f"95% Expected Shortfall (CVaR): -${self.cvar_95_pct:,.2f} (Avg loss in worst 5% tails)\n"
            f"99% Expected Shortfall (CVaR): -${self.cvar_99_pct:,.2f} (Avg loss in worst 1% tails)\n"
        )


class MonteCarloEngine:
    """
    Monte Carlo stress-testing engine with jump diffusion support.
    """

    def __init__(
        self,
        portfolio_value: float,
        expected_annual_return: float = 0.10,
        annual_volatility: float = 0.20,
        jump_intensity: float = 0.0,
        jump_mean: float = 0.0,
        jump_vol: float = 0.0,
        seed: Optional[int] = 42,
    ):
        self.portfolio_value = float(portfolio_value)
        self.mu = expected_annual_return
        self.sigma = annual_volatility
        self.jump_intensity = jump_intensity  # Expected jumps per year
        self.jump_mean = jump_mean
        self.jump_vol = jump_vol
        if seed is not None:
            np.random.seed(seed)

    def run_simulation(
        self,
        days: int = 30,
        num_simulations: int = 10000,
    ) -> MonteCarloResult:
        dt = 1.0 / 252.0
        steps = days

        # Standard GBM shock
        drift = (self.mu - 0.5 * self.sigma ** 2) * dt
        vol = self.sigma * np.sqrt(dt)

        # Standard normal random variates
        z = np.random.normal(0.0, 1.0, size=(num_simulations, steps))
        returns = drift + vol * z

        # Add Merton Jump-Diffusion component if specified
        if self.jump_intensity > 0.0:
            # Poisson arrival for jumps
            jump_prob = self.jump_intensity * dt
            n_jumps = np.random.poisson(jump_prob, size=(num_simulations, steps))
            jump_sizes = np.random.normal(self.jump_mean, self.jump_vol, size=(num_simulations, steps))
            returns += n_jumps * jump_sizes

        # Compute price trajectories
        cum_returns = np.cumsum(returns, axis=1)
        paths = np.zeros((num_simulations, steps + 1))
        paths[:, 0] = self.portfolio_value
        paths[:, 1:] = self.portfolio_value * np.exp(cum_returns)

        ending_values = paths[:, -1]
        pnl = ending_values - self.portfolio_value  # Negative = Loss

        # Value at Risk (Loss amounts)
        var_95 = float(-np.percentile(pnl, 5))
        var_99 = float(-np.percentile(pnl, 1))

        # Conditional VaR (Expected Shortfall)
        tail_95 = pnl[pnl <= -var_95]
        cvar_95 = float(-np.mean(tail_95)) if len(tail_95) > 0 else var_95

        tail_99 = pnl[pnl <= -var_99]
        cvar_99 = float(-np.mean(tail_99)) if len(tail_99) > 0 else var_99

        return MonteCarloResult(
            initial_portfolio_value=self.portfolio_value,
            time_horizon_days=days,
            num_simulations=num_simulations,
            var_95_pct=max(0.0, var_95),
            var_99_pct=max(0.0, var_99),
            cvar_95_pct=max(0.0, cvar_95),
            cvar_99_pct=max(0.0, cvar_99),
            median_ending_value=float(np.median(ending_values)),
            mean_ending_value=float(np.mean(ending_values)),
            simulated_paths=paths,
        )
