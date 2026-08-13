"""Basic smoke test for GreedBot SDK."""
import pytest
from greedbot import GreedBotClient
from greedbot.strategies import (
    OptionKellyEngine,
    SectorSpilloverArb,
    QualitativeOverlayEngine,
    MacroRegimeMatrix,
    VolatilityHarvestEngine,
)

def test_client_init():
    client = GreedBotClient(api_key="test_key")
    assert client.api_key == "test_key"
    assert client.base_url == "https://greedbot.com"

def test_strategy_engines_init():
    client = GreedBotClient(api_key="test_key")
    kelly = OptionKellyEngine(client)
    spill = SectorSpilloverArb(client)
    qual = QualitativeOverlayEngine(client)
    macro = MacroRegimeMatrix(client)
    vol = VolatilityHarvestEngine(client)
    assert kelly is not None
    assert spill is not None
    assert qual is not None
    assert macro is not None
    assert vol is not None
