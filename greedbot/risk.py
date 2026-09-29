"""
GreedBot Risk Management & Limits
---------------------------------
Neutral risk limits and portfolio target validation primitives.
Enforces gross book exposure caps, single-name concentration caps,
short exposure limits, and pre-trade order firewall checks.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Sequence

from .models import OrderIntent, Side


class RiskLimitBreachError(ValueError):
    """Raised when a proposed order batch or portfolio state violates risk limits."""
    pass


@dataclass
class RiskLimits:
    """
    User-authored risk limits against which portfolio targets and orders are validated.

    `max_gross_fraction`: Gross book cap as a fraction of equity (e.g. 0.20 = 20% gross).
                          Must be finite and in (0.0, 10.0].
    `per_name_cap_fraction`: Per-name cap as a fraction of equity (e.g. 0.05 = 5%).
                             Must be finite and in (0.0, 1.0].
    `max_short_fraction`: Cap on aggregate short notional as a fraction of equity (e.g. 0.10 = 10%).
                          Must be finite and in (0.0, 10.0].
    `max_drawdown_stop_pct`: Circuit breaker drawdown threshold in percent (e.g. 15.0 = 15%).
    """
    max_gross_fraction: float = 0.20
    per_name_cap_fraction: float = 0.05
    max_short_fraction: float = 0.10
    max_drawdown_stop_pct: float = 20.0

    def validate(self) -> None:
        """
        Check that the limit fractions themselves are usable.
        Rejects non-finite, NaN, <= 0, or excessive values.
        """
        if (
            not math.isfinite(self.max_gross_fraction)
            or self.max_gross_fraction <= 0.0
            or self.max_gross_fraction > 10.0
        ):
            raise ValueError(
                f"max_gross_fraction must be finite and in (0.0, 10.0], got {self.max_gross_fraction}"
            )

        if (
            not math.isfinite(self.per_name_cap_fraction)
            or self.per_name_cap_fraction <= 0.0
            or self.per_name_cap_fraction > 1.0
        ):
            raise ValueError(
                f"per_name_cap_fraction must be finite and in (0.0, 1.0], got {self.per_name_cap_fraction}"
            )

        if (
            not math.isfinite(self.max_short_fraction)
            or self.max_short_fraction <= 0.0
            or self.max_short_fraction > 10.0
        ):
            raise ValueError(
                f"max_short_fraction must be finite and in (0.0, 10.0], got {self.max_short_fraction}"
            )

        if (
            not math.isfinite(self.max_drawdown_stop_pct)
            or self.max_drawdown_stop_pct <= 0.0
            or self.max_drawdown_stop_pct > 100.0
        ):
            raise ValueError(
                f"max_drawdown_stop_pct must be finite and in (0.0, 100.0], got {self.max_drawdown_stop_pct}"
            )

    def validate_targets(
        self,
        equity_usd: float,
        target_dollars: Dict[str, float]
    ) -> None:
        """
        Validate absolute per-ticker dollar targets against equity_usd.

        Raises ValueError if limits fail validate(), equity is non-positive or non-finite,
        any target is non-finite, gross exposure exceeds max_gross_fraction, or any single
        name exceeds per_name_cap_fraction.
        """
        self.validate()

        if not math.isfinite(equity_usd) or equity_usd <= 0.0:
            raise ValueError(f"equity_usd must be finite and > 0, got {equity_usd}")

        gross_cap = equity_usd * self.max_gross_fraction
        name_cap = equity_usd * self.per_name_cap_fraction
        short_cap = equity_usd * self.max_short_fraction

        gross = 0.0
        short_gross = 0.0
        for ticker, dollars in target_dollars.items():
            if not math.isfinite(dollars):
                raise ValueError(f"target for {ticker} is not finite: {dollars}")

            notional = abs(dollars)
            if notional > name_cap + 1e-6:
                raise ValueError(
                    f"per-name cap violated: {ticker} {notional:.2f} > {name_cap:.2f}"
                )
            gross += notional
            if dollars < 0:
                short_gross += notional

        if gross > gross_cap + 1e-6:
            raise ValueError(f"gross cap violated: {gross:.2f} > {gross_cap:.2f}")

        if short_gross > short_cap + 1e-6:
            raise ValueError(f"short cap violated: {short_gross:.2f} > {short_cap:.2f}")

    def validate_order_intents(
        self,
        equity_usd: float,
        current_positions: Dict[str, float],
        prices: Dict[str, float],
        intents: Sequence[OrderIntent],
    ) -> None:
        """
        Pre-trade risk firewall. Simulates the post-execution state of proposed OrderIntents
        and validates that the resulting portfolio complies with gross, per-name, and short limits.
        """
        self.validate()

        if not math.isfinite(equity_usd) or equity_usd <= 0.0:
            raise ValueError(f"equity_usd must be finite and > 0, got {equity_usd}")

        norm_prices = {k.strip().lower(): float(v) for k, v in prices.items()}
        simulated_positions = {k.strip().lower(): float(v) for k, v in current_positions.items()}

        for intent in intents:
            ticker = intent.ticker.strip().lower()
            if ticker not in norm_prices:
                raise ValueError(f"No price available to evaluate risk for {ticker}")

            px = norm_prices[ticker]
            if px <= 0:
                raise ValueError(f"Non-positive price for {ticker}: {px}")

            qty = intent.dollars / px
            held = simulated_positions.get(ticker, 0.0)

            if intent.side in (Side.BUY, Side.BUY_TO_COVER):
                simulated_positions[ticker] = held + qty
            else:  # SELL, SHORT_SELL
                simulated_positions[ticker] = held - qty

        # Validate simulated portfolio dollar holdings
        simulated_dollars = {
            t: shares * norm_prices[t]
            for t, shares in simulated_positions.items()
            if abs(shares) > 1e-9
        }
        self.validate_targets(equity_usd, simulated_dollars)

    def is_circuit_breaker_triggered(self, peak_equity: float, current_equity: float) -> bool:
        """
        Check if portfolio drawdown from peak exceeds the configured max_drawdown_stop_pct.
        """
        if peak_equity <= 0:
            return False
        dd_pct = ((peak_equity - current_equity) / peak_equity) * 100.0
        return dd_pct >= self.max_drawdown_stop_pct

