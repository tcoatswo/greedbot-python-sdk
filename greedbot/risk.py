"""
GreedBot Risk Management & Limits
---------------------------------
Neutral risk limits and portfolio target validation primitives.
Enforces gross book exposure caps, single-name concentration caps,
and numerical sanity checks.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional, Union


@dataclass
class RiskLimits:
    """
    User-authored risk limits against which portfolio targets are validated.

    `max_gross_fraction`: Gross book cap as a fraction of equity (e.g. 0.20 = 20% gross).
                          Must be finite and in (0.0, 10.0].
    `per_name_cap_fraction`: Per-name cap as a fraction of equity (e.g. 0.05 = 5%).
                             Must be finite and in (0.0, 1.0].
    """
    max_gross_fraction: float = 0.20
    per_name_cap_fraction: float = 0.05

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

        gross = 0.0
        for ticker, dollars in target_dollars.items():
            if not math.isfinite(dollars):
                raise ValueError(f"target for {ticker} is not finite: {dollars}")

            notional = abs(dollars)
            if notional > name_cap + 1e-6:
                raise ValueError(
                    f"per-name cap violated: {ticker} {notional:.2f} > {name_cap:.2f}"
                )
            gross += notional

        if gross > gross_cap + 1e-6:
            raise ValueError(f"gross cap violated: {gross:.2f} > {gross_cap:.2f}")
