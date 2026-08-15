"""
Signal Generation Base Classes and Data Structures
--------------------------------------------------
Standardized signal representation for quantitative trading engines.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional, Sequence


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"
    PROVIDE_LIQUIDITY = "PROVIDE_LIQUIDITY"


@dataclass
class Signal:
    """
    Standardized trading signal emitted by quantitative signal generators.
    """
    ticker: str
    direction: SignalDirection
    strength: float = 1.0  # -1.0 to 1.0
    price: Optional[float] = None
    indicator_values: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_bullish(self) -> bool:
        return self.direction == SignalDirection.LONG

    @property
    def is_bearish(self) -> bool:
        return self.direction == SignalDirection.SHORT

    @property
    def is_flat(self) -> bool:
        return self.direction == SignalDirection.FLAT


class SignalGenerator(ABC):
    """
    Abstract Base Class for quantitative signal generation.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the signal generator."""
        pass

    @abstractmethod
    def generate(self, *args: Any, **kwargs: Any) -> Signal:
        """Generate a trading signal from market data series."""
        pass
