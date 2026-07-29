import os
import sys
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from fetch.sportmonks_common import fetch_sportmonks_league

class TestSportmonks(unittest.TestCase):

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_api_key_raises_value_error(self):
        with self.assertRaises(ValueError):
            fetch_sportmonks_league(271, "Denmark Superliga", "2026")

    @patch.dict(os.environ, {"SPORTMONKS_API_KEY": "test_key"})
    @patch('requests.get')
    def test_sportmonks_api_error_handling(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_get.return_value = mock_response

        with self.assertRaises(Exception) as ctx:
            fetch_sportmonks_league(271, "Denmark Superliga", "2026")

        self.assertIn("Sportmonks API request failed with status 401: Unauthorized", str(ctx.exception))

    @patch.dict(os.environ, {"SPORTMONKS_API_KEY": "test_key"})
    @patch('requests.get')
    def test_sportmonks_data_processing(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": 100,
                    "league_id": 271,
                    "starting_at": "2026-04-10 19:00:00",
                    "state": "FINISHED",
                    "participants": [
                        {"id": 1, "name": "Brondby", "meta": {"location": "home"}},
                        {"id": 2, "name": "Copenhagen", "meta": {"location": "away"}}
                    ],
                    "scores": [
                        {"participant_id": 1, "score": {"goals": 2}, "meta": {"type": "current"}},
                        {"participant_id": 2, "score": {"goals": 1}, "meta": {"type": "current"}}
                    ]
                },
                {
                    "id": 101,
                    "league_id": 271,
                    "starting_at": "2026-04-11 19:00:00",
                    "state": "FINISHED",
                    "participants": [
                        {"id": 1, "name": "Brondby", "meta": {"location": "home"}},
                        {"id": 3, "name": "Midtjylland", "meta": {"location": "away"}},
                    ],
                    "scores": [
                        {"participant_id": 1, "score": {"goals": 0}, "meta": {"type": "current"}},
                        {"participant_id": 3, "score": {"goals": 3}, "meta": {"type": "current"}}
                    ]
                },
                {
                    "id": 102,
                    "league_id": 271,
                    "starting_at": "2026-04-12 19:00:00",
                    "state": "NS",
                    "participants": [
                        {"id": 2, "name": "Copenhagen", "meta": {"location": "home"}},
                        {"id": 3, "name": "Midtjylland", "meta": {"location": "away"}}
                    ],
                    "scores": []
                }
            ]
        }
        mock_get.return_value = mock_response

        results = fetch_sportmonks_league(271, "Denmark Superliga", "2026", total_matches=2)

        self.assertEqual(len(results), 1)
        fixture = results[0]
        self.assertEqual(fixture['home_team'], "Copenhagen")
        self.assertEqual(fixture['away_team'], "Midtjylland")
        self.assertEqual(fixture['date'], "2026-04-12")

        # Verify Copenhagen history (home_history, needs 1 home, 1 away)
        # Match 100: Brondby vs Copenhagen. Copenhagen was away. goals: 2-1.
        self.assertEqual(len(fixture['home_history']), 1)
        self.assertEqual(fixture['home_history'][0]['opponent'], "Brondby")
        self.assertEqual(fixture['home_history'][0]['venue'], "away")
        self.assertEqual(fixture['home_history'][0]['goals_for'], 1)
        self.assertEqual(fixture['home_history'][0]['goals_against'], 2)

if __name__ == "__main__":
    unittest.main()
