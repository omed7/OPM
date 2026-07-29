import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import datetime

# Add src to python path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from fetch.thesportsdb_common import (
    fetch_league_id,
    check_plausibility,
    fetch_thesportsdb_league,
    ACTIVE_TEAMS
)

class TestTheSportsDB(unittest.TestCase):

    @patch('requests.get')
    def test_fetch_league_id_success(self, mock_get):
        # Mock league search response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "countries": [
                {"strLeague": "American Major League Soccer", "idLeague": "4346"},
                {"strLeague": "American NASL", "idLeague": "4435"}
            ]
        }
        mock_get.return_value = mock_response

        # Act
        league_id = fetch_league_id("MLS")

        # Assert
        self.assertEqual(league_id, "4346")
        mock_get.assert_called_with("https://www.thesportsdb.com/api/v1/json/123/search_all_leagues.php?c=United States&s=Soccer")

    @patch('requests.get')
    def test_fetch_league_id_not_found_raises_exception(self, mock_get):
        # Mock empty response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"countries": []}
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            fetch_league_id("MLS")

    def test_plausibility_check_success(self):
        # Prepare valid inputs
        today_plus_1 = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()

        upcoming_events = [
            {
                "strHomeTeam": "New York City FC",
                "strAwayTeam": "Toronto FC",
                "dateEvent": today_plus_1
            }
        ]

        # We need 2 home and 2 away played matches for both teams (total matches = 4)
        played_events = [
            # New York City FC: 2 home, 2 away
            {"strHomeTeam": "New York City FC", "strAwayTeam": "Inter Miami", "intHomeScore": 2, "intAwayScore": 1, "dateEvent": "2024-02-25"},
            {"strHomeTeam": "New York City FC", "strAwayTeam": "LA Galaxy", "intHomeScore": 1, "intAwayScore": 0, "dateEvent": "2024-02-24"},
            {"strHomeTeam": "Columbus Crew", "strAwayTeam": "New York City FC", "intHomeScore": 0, "intAwayScore": 2, "dateEvent": "2024-02-23"},
            {"strHomeTeam": "Atlanta United", "strAwayTeam": "New York City FC", "intHomeScore": 1, "intAwayScore": 1, "dateEvent": "2024-02-22"},

            # Toronto FC: 2 home, 2 away
            {"strHomeTeam": "Toronto FC", "strAwayTeam": "CF Montréal", "intHomeScore": 3, "intAwayScore": 2, "dateEvent": "2024-02-25"},
            {"strHomeTeam": "Toronto FC", "strAwayTeam": "Austin FC", "intHomeScore": 0, "intAwayScore": 0, "dateEvent": "2024-02-24"},
            {"strHomeTeam": "FC Cincinnati", "strAwayTeam": "Toronto FC", "intHomeScore": 2, "intAwayScore": 2, "dateEvent": "2024-02-23"},
            {"strHomeTeam": "Charlotte FC", "strAwayTeam": "Toronto FC", "intHomeScore": 1, "intAwayScore": 2, "dateEvent": "2024-02-22"},
        ]

        # Act
        is_plausible, reason = check_plausibility("MLS", upcoming_events, played_events, total_matches=4)

        # Assert
        self.assertTrue(is_plausible)
        self.assertEqual(reason, "Passed")

    def test_plausibility_check_stale_date(self):
        # Prepare inputs with past date
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        upcoming_events = [
            {
                "strHomeTeam": "New York City FC",
                "strAwayTeam": "Toronto FC",
                "dateEvent": yesterday
            }
        ]
        played_events = []

        is_plausible, reason = check_plausibility("MLS", upcoming_events, played_events, total_matches=4)
        self.assertFalse(is_plausible)
        self.assertIn("Stale event date", reason)

    def test_plausibility_check_unrecognized_team(self):
        # Prepare inputs with fake team
        today_plus_1 = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        upcoming_events = [
            {
                "strHomeTeam": "Fake Team FC",
                "strAwayTeam": "Toronto FC",
                "dateEvent": today_plus_1
            }
        ]
        played_events = []

        is_plausible, reason = check_plausibility("MLS", upcoming_events, played_events, total_matches=4)
        self.assertFalse(is_plausible)
        self.assertIn("Unrecognized team: Fake Team FC", reason)

    def test_plausibility_check_insufficient_history(self):
        # Prepare inputs where Toronto FC does not have enough home matches
        today_plus_1 = (datetime.date.today() + datetime.timedelta(days=1)).isoformat()
        upcoming_events = [
            {
                "strHomeTeam": "New York City FC",
                "strAwayTeam": "Toronto FC",
                "dateEvent": today_plus_1
            }
        ]

        played_events = [
            # New York City FC has 2 home, 2 away
            {"strHomeTeam": "New York City FC", "strAwayTeam": "Inter Miami", "intHomeScore": 2, "intAwayScore": 1, "dateEvent": "2024-02-25"},
            {"strHomeTeam": "New York City FC", "strAwayTeam": "LA Galaxy", "intHomeScore": 1, "intAwayScore": 0, "dateEvent": "2024-02-24"},
            {"strHomeTeam": "Columbus Crew", "strAwayTeam": "New York City FC", "intHomeScore": 0, "intAwayScore": 2, "dateEvent": "2024-02-23"},
            {"strHomeTeam": "Atlanta United", "strAwayTeam": "New York City FC", "intHomeScore": 1, "intAwayScore": 1, "dateEvent": "2024-02-22"},

            # Toronto FC has only 1 home match
            {"strHomeTeam": "Toronto FC", "strAwayTeam": "CF Montréal", "intHomeScore": 3, "intAwayScore": 2, "dateEvent": "2024-02-25"},
            {"strHomeTeam": "FC Cincinnati", "strAwayTeam": "Toronto FC", "intHomeScore": 2, "intAwayScore": 2, "dateEvent": "2024-02-23"},
            {"strHomeTeam": "Charlotte FC", "strAwayTeam": "Toronto FC", "intHomeScore": 1, "intAwayScore": 2, "dateEvent": "2024-02-22"},
        ]

        is_plausible, reason = check_plausibility("MLS", upcoming_events, played_events, total_matches=4)
        self.assertFalse(is_plausible)
        self.assertIn("Insufficient match history for Toronto FC", reason)

if __name__ == "__main__":
    unittest.main()
