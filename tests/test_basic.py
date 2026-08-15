"""Basic smoke tests for GreedBot SDK."""
import unittest
from greedbot import GreedBotClient
from greedbot.strategies import (
    OptionKellyEngine,
    SectorSpilloverArb,
    QualitativeOverlayEngine,
    MacroRegimeMatrix,
    VolatilityHarvestEngine,
    ETFBarbellStrategy,
    SoloTacticalStrategy,
    SectorLongShortStrategy,
    BotFleetFollower,
)

class TestGreedBotSDK(unittest.TestCase):
    def test_client_init(self):
        client = GreedBotClient(api_key="test_key")
        self.assertEqual(client.api_key, "test_key")
        self.assertEqual(client.base_url, "https://greedbot.com")

    def test_strategy_engines_init(self):
        client = GreedBotClient(api_key="test_key")
        kelly = OptionKellyEngine(client)
        spill = SectorSpilloverArb(client)
        qual = QualitativeOverlayEngine(client)
        macro = MacroRegimeMatrix(client)
        vol = VolatilityHarvestEngine(client)
        etf = ETFBarbellStrategy()
        solo = SoloTacticalStrategy()
        sector_ls = SectorLongShortStrategy()
        follower = BotFleetFollower()
        
        self.assertIsNotNone(kelly)
        self.assertIsNotNone(spill)
        self.assertIsNotNone(qual)
        self.assertIsNotNone(macro)
        self.assertIsNotNone(vol)
        self.assertIsNotNone(etf)
        self.assertIsNotNone(solo)
        self.assertIsNotNone(sector_ls)
        self.assertIsNotNone(follower)

if __name__ == "__main__":
    unittest.main()
