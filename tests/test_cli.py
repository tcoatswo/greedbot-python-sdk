"""
Unit tests for CLI commands and argument parser.
"""

import unittest
from unittest.mock import MagicMock, patch
from greedbot.cli import main


class TestCLI(unittest.TestCase):

    @patch("greedbot.cli.GreedBotClient")
    def test_cli_ping(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.ping.return_value = "PONG"
        mock_client_cls.return_value = mock_client

        with patch("sys.argv", ["greedbot", "ping"]):
            main()
        mock_client.ping.assert_called_once()

    @patch("greedbot.cli.GreedBotClient")
    def test_cli_targets(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.get_targets.return_value = {"df": {"ticker": ["nvda"]}}
        mock_client_cls.return_value = mock_client

        with patch("sys.argv", ["greedbot", "targets", "NVDA"]):
            main()
        mock_client.get_targets.assert_called_once()


if __name__ == "__main__":
    unittest.main()
