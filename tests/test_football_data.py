import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO

# Add src to python path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from fetch.football_data_common import fetch_football_data_league

class TestFootballData(unittest.TestCase):

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key_raises_value_error(self):
        # Act & Assert
        with self.assertRaises(ValueError):
            fetch_football_data_league("BSA", "Brazilian Serie A", "2026")

    @patch.dict(os.environ, {"FOOTBALL_DATA_API_KEY": "test_key"})
    @patch('requests.get')
    def test_api_error_handling(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "message": "The resource you are looking for is restricted",
            "errorCode": 403
        }
        mock_get.return_value = mock_response

        # Act & Assert
        with self.assertRaises(Exception) as ctx:
            fetch_football_data_league("BSA", "Brazilian Serie A", "2026")

        self.assertIn("API Request failed with status 403: The resource you are looking for is restricted", str(ctx.exception))

    @patch.dict(os.environ, {"FOOTBALL_DATA_API_KEY": "test_key"})
    @patch('requests.get')
    def test_diagnostic_logging_and_processing(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "matches": [
                {
                    "id": 1,
                    "utcDate": "2026-04-10T19:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"id": 10, "name": "Team A"},
                    "awayTeam": {"id": 20, "name": "Team B"},
                    "score": {"fullTime": {"home": 2, "away": 1}}
                },
                {
                    "id": 2,
                    "utcDate": "2026-04-11T19:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"id": 10, "name": "Team A"},
                    "awayTeam": {"id": 30, "name": "Team C"},
                    "score": {"fullTime": {"home": 0, "away": 3}}
                },
                {
                    "id": 3,
                    "utcDate": "2026-04-12T19:00:00Z",
                    "status": "TIMED",
                    "homeTeam": {"id": 20, "name": "Team B"},
                    "awayTeam": {"id": 30, "name": "Team C"},
                    "score": {"fullTime": {"home": None, "away": None}}
                }
            ]
        }
        mock_get.return_value = mock_response

        # Act
        captured_output = StringIO()
        sys.stdout = captured_output
        try:
            results = fetch_football_data_league("BSA", "Brazilian Serie A", "2026", total_matches=2)
        finally:
            sys.stdout = sys.__stdout__

        output = captured_output.getvalue()

        # Assert log outputs
        self.assertIn("Total fixtures returned: 3", output)
        self.assertIn("Fixture status breakdown:", output)
        self.assertIn("'FINISHED': 2", output)
        self.assertIn("'TIMED': 1", output)

        # Assert output processing
        self.assertEqual(len(results), 1)
        fixture = results[0]
        self.assertEqual(fixture['home_team'], "Team B")
        self.assertEqual(fixture['away_team'], "Team C")
        self.assertEqual(fixture['date'], "2026-04-12")

        # Verify home_history (Team B, total_matches=2, meaning 1 home and 1 away)
        # Match 1 (ID 1): Home Team A (10) vs Away Team B (20). Team B is away. goals: 2-1. So B got 1 goal_for, 2 goals_against.
        self.assertEqual(len(fixture['home_history']), 1)
        self.assertEqual(fixture['home_history'][0]['opponent'], "Team A")
        self.assertEqual(fixture['home_history'][0]['venue'], "away")
        self.assertEqual(fixture['home_history'][0]['goals_for'], 1)
        self.assertEqual(fixture['home_history'][0]['goals_against'], 2)

        # Verify away_history (Team C, total_matches=2, meaning 1 home and 1 away)
        # Match 2 (ID 2): Home Team A (10) vs Away Team C (30). Team C is away. goals: 0-3. So C got 3 goals_for, 0 goals_against.
        self.assertEqual(len(fixture['away_history']), 1)
        self.assertEqual(fixture['away_history'][0]['opponent'], "Team A")
        self.assertEqual(fixture['away_history'][0]['venue'], "away")
        self.assertEqual(fixture['away_history'][0]['goals_for'], 3)
        self.assertEqual(fixture['away_history'][0]['goals_against'], 0)

    @patch.dict(os.environ, {"FOOTBALL_DATA_API_KEY": "test_key", "MOCK_UPCOMING": "1"})
    @patch('requests.get')
    def test_mock_upcoming_behavior(self, mock_get):
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        # All matches are finished (no upcoming matches)
        mock_response.json.return_value = {
            "matches": [
                {
                    "id": 1,
                    "utcDate": "2026-04-10T19:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"id": 10, "name": "Team A"},
                    "awayTeam": {"id": 20, "name": "Team B"},
                    "score": {"fullTime": {"home": 2, "away": 1}}
                },
                {
                    "id": 2,
                    "utcDate": "2026-04-11T19:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"id": 10, "name": "Team A"},
                    "awayTeam": {"id": 30, "name": "Team C"},
                    "score": {"fullTime": {"home": 0, "away": 3}}
                },
                {
                    "id": 3,
                    "utcDate": "2026-04-12T19:00:00Z",
                    "status": "FINISHED",
                    "homeTeam": {"id": 20, "name": "Team B"},
                    "awayTeam": {"id": 30, "name": "Team C"},
                    "score": {"fullTime": {"home": 1, "away": 1}}
                }
            ]
        }
        mock_get.return_value = mock_response

        # Act
        results = fetch_football_data_league("BSA", "Brazilian Serie A", "2026", total_matches=2)

        # Assert: since MOCK_UPCOMING is 1 and upcoming_matches was empty, the last matches should be mocked as upcoming.
        # Since we added filtering to the same date as the earliest, only fixtures sharing the earliest date (2026-04-10) are kept.
        self.assertEqual(len(results), 1)
        # Chronological order of mocked upcoming matches:
        self.assertEqual(results[0]['date'], "2026-04-10")

if __name__ == "__main__":
    unittest.main()
