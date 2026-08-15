"""
GreedBot Strategy Base Interface
--------------------------------
Defines the `Strategy` abstract base class for all algorithmic trading models.
"""

from __future__ import annotations

import abc
from typing import Any, Dict, List
from ..client import GreedBotClient
from ..models import BotRunResult, OrderIntent


class Strategy(abc.ABC):
    """
    A trading strategy: signals in, order intents and allocation results out.
    """

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Stable machine name for this strategy."""
        pass

    @abc.abstractmethod
    def run(self, client: GreedBotClient, capital_usd: float) -> BotRunResult:
        """Execute the strategy end-to-end and return structured results and intents."""
        pass
