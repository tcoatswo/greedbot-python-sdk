"""Basic smoke test for GreedBot SDK using standard unittest."""
import unittest
from greedbot import GreedBotClient
from greedbot.strategies import (
    OptionKellyEngine,
    SectorSpilloverArb,
    QualitativeOverlayEngine,
    MacroRegimeMatrix,
    VolatilityHarvestEngine,
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
        
        self.assertIsNotNone(kelly)
        self.assertIsNotNone(spill)
        self.assertIsNotNone(qual)
        self.assertIsNotNone(macro)
        self.assertIsNotNone(vol)

if __name__ == "__main__":
    unittest.main()
