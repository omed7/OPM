import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO

# Add src to python path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from fetch.besta_deild import get_besta_deild_data
from output_writer import process_besta_deild

class TestBestaDeild(unittest.TestCase):

    @patch.dict(os.environ, {"API_FOOTBALL_KEY": "test_key"})
    @patch('requests.get')
    def test_diagnostic_logging(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "response": [
                {
                    "fixture": {
                        "id": 1,
                        "date": "2026-04-10T19:00:00Z",
                        "timestamp": 1775847600,
                        "status": {"short": "FT"}
                    },
                    "teams": {
                        "home": {"id": 10, "name": "Team A"},
                        "away": {"id": 20, "name": "Team B"}
                    },
                    "goals": {"home": 2, "away": 1}
                },
                {
                    "fixture": {
                        "id": 2,
                        "date": "2026-04-11T19:00:00Z",
                        "timestamp": 1775934000,
                        "status": {"short": "FT"}
                    },
                    "teams": {
                        "home": {"id": 10, "name": "Team A"},
                        "away": {"id": 30, "name": "Team C"}
                    },
                    "goals": {"home": 0, "away": 3}
                },
                {
                    "fixture": {
                        "id": 3,
                        "date": "2026-04-12T19:00:00Z",
                        "timestamp": 1776020400,
                        "status": {"short": "NS"}
                    },
                    "teams": {
                        "home": {"id": 20, "name": "Team B"},
                        "away": {"id": 30, "name": "Team C"}
                    },
                    "goals": {"home": None, "away": None}
                },
                {
                    "fixture": {
                        "id": 4,
                        "date": "2026-04-13T19:00:00Z",
                        "timestamp": 1776106800,
                        "status": {"short": "PST"}
                    },
                    "teams": {
                        "home": {"id": 30, "name": "Team C"},
                        "away": {"id": 10, "name": "Team A"}
                    },
                    "goals": {"home": None, "away": None}
                }
            ]
        }
        mock_get.return_value = mock_response

        # Act
        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            get_besta_deild_data(season="2026", total_matches=2)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()

        # Assert
        self.assertIn("Total fixtures returned: 4", output)
        self.assertIn("Fixture status breakdown:", output)
        self.assertIn("'FT': 2", output)
        self.assertIn("'NS': 1", output)
        self.assertIn("'PST': 1", output)

    @patch.dict(os.environ, {"API_FOOTBALL_KEY": "test_key", "SEASON": "2025"})
    @patch('output_writer.get_besta_deild_data')
    def test_season_configurability(self, mock_get_data):
        # Arrange
        mock_get_data.return_value = []

        # Act
        process_besta_deild()

        # Assert
        mock_get_data.assert_called_with(season="2025", total_matches=4)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key_raises_value_error(self):
        # Act & Assert
        with self.assertRaises(ValueError):
            get_besta_deild_data()

if __name__ == "__main__":
    unittest.main()
