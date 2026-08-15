"""
GreedBot Data Sources Base Interface
------------------------------------
Defines base interfaces for external data adapters (market data, filings, news).
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List, Optional


class DataSource(abc.ABC):
    """Abstract base class for all external data sources."""

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Name of the data source."""
        pass
