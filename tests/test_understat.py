import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# Add src to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from fetch.understat_common import get_current_season, get_team_matches, get_upcoming_fixtures

class TestUnderstatCommon(unittest.TestCase):

    @patch('fetch.understat_common.UnderstatClient')
    def test_get_team_matches(self, mock_client_class):
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock team data mapping team ID to title
        mock_team_data = {
            "101": {"title": "Team A"},
            "102": {"title": "Team B"},
            "103": {"title": "Team C"},
        }
        mock_client.league.return_value.get_team_data.return_value = mock_team_data

        # Mock match data
        # Let's provide 3 home matches and 3 away matches for Team A
        # Team A is id "101"
        mock_match_data = [
            # Played Home
            {
                "isResult": True,
                "datetime": "2025-09-01 15:00:00",
                "h": {"id": "101", "title": "Team A"},
                "a": {"id": "102", "title": "Team B"},
                "xG": {"h": "1.50", "a": "0.80"}
            },
            {
                "isResult": True,
                "datetime": "2025-08-15 15:00:00",
                "h": {"id": "101", "title": "Team A"},
                "a": {"id": "103", "title": "Team C"},
                "xG": {"h": "2.10", "a": "1.10"}
            },
            # Played Away
            {
                "isResult": True,
                "datetime": "2025-09-10 15:00:00",
                "h": {"id": "102", "title": "Team B"},
                "a": {"id": "101", "title": "Team A"},
                "xG": {"h": "0.50", "a": "2.50"}
            },
            {
                "isResult": True,
                "datetime": "2025-08-20 15:00:00",
                "h": {"id": "103", "title": "Team C"},
                "a": {"id": "101", "title": "Team A"},
                "xG": {"h": "1.20", "a": "1.80"}
            },
            # Extra matches that shouldn't be selected once limit (2 home + 2 away) is met
            {
                "isResult": True,
                "datetime": "2025-08-01 15:00:00",
                "h": {"id": "101", "title": "Team A"},
                "a": {"id": "102", "title": "Team B"},
                "xG": {"h": "3.00", "a": "0.50"}
            },
            {
                "isResult": True,
                "datetime": "2025-08-02 15:00:00",
                "h": {"id": "102", "title": "Team B"},
                "a": {"id": "101", "title": "Team A"},
                "xG": {"h": "0.40", "a": "0.90"}
            },
        ]
        mock_client.league.return_value.get_match_data.return_value = mock_match_data

        # Act
        matches = get_team_matches(league_code="La_Liga", team_name="Team A", total_matches=4, season="2025")

        # Assert
        # Should have exactly 4 matches (2 home, 2 away)
        self.assertEqual(len(matches), 4)
        home_matches = [m for m in matches if m['venue'] == 'home']
        away_matches = [m for m in matches if m['venue'] == 'away']
        self.assertEqual(len(home_matches), 2)
        self.assertEqual(len(away_matches), 2)

        # Confirm we got the most recent ones (by datetime)
        # Home matches: 2025-09-01 (xg_for=1.5) and 2025-08-15 (xg_for=2.1)
        # Not the 2025-08-01 (xg_for=3.0) match
        self.assertEqual(home_matches[0]['date'], "2025-09-01 15:00:00")
        self.assertEqual(home_matches[0]['xg_for'], 1.5)
        self.assertEqual(home_matches[0]['xg_against'], 0.8)

        self.assertEqual(home_matches[1]['date'], "2025-08-15 15:00:00")
        self.assertEqual(home_matches[1]['xg_for'], 2.1)

        # Away matches: 2025-09-10 (xg_for=2.5) and 2025-08-20 (xg_for=1.8)
        self.assertEqual(away_matches[0]['date'], "2025-09-10 15:00:00")
        self.assertEqual(away_matches[0]['xg_for'], 2.5)

    @patch('fetch.understat_common.UnderstatClient')
    def test_get_upcoming_fixtures(self, mock_client_class):
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock match data with upcoming games
        mock_match_data = [
            # Played
            {
                "isResult": True,
                "datetime": "2025-08-15 15:00:00",
                "h": {"id": "1", "title": "Team A"},
                "a": {"id": "2", "title": "Team B"},
            },
            # Upcoming within 7 days of first upcoming (First is 2025-08-22)
            {
                "isResult": False,
                "datetime": "2025-08-22 19:45:00",
                "h": {"id": "1", "title": "Team A"},
                "a": {"id": "3", "title": "Team C"},
            },
            {
                "isResult": False,
                "datetime": "2025-08-24 15:00:00",
                "h": {"id": "2", "title": "Team B"},
                "a": {"id": "4", "title": "Team D"},
            },
            # Upcoming past 7 days of first upcoming (2025-08-30 is 8 days later)
            {
                "isResult": False,
                "datetime": "2025-08-30 15:00:00",
                "h": {"id": "3", "title": "Team C"},
                "a": {"id": "4", "title": "Team D"},
            }
        ]
        mock_client.league.return_value.get_match_data.return_value = mock_match_data

        # Act
        fixtures = get_upcoming_fixtures(league_code="Serie_A", season="2025")

        # Assert
        # Should filter only the upcoming ones within 7 days of the first upcoming match
        self.assertEqual(len(fixtures), 2)
        self.assertEqual(fixtures[0]['home_team'], "Team A")
        self.assertEqual(fixtures[0]['away_team'], "Team C")
        self.assertEqual(fixtures[1]['home_team'], "Team B")
        self.assertEqual(fixtures[1]['away_team'], "Team D")

    @patch.dict(os.environ, {"MOCK_UPCOMING": "1"})
    @patch('fetch.understat_common.UnderstatClient')
    def test_mock_upcoming_fixtures(self, mock_client_class):
        # Arrange
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # No upcoming fixtures in the data
        mock_match_data = [
            {
                "isResult": True,
                "datetime": "2025-05-18 15:00:00",
                "h": {"id": "1", "title": "Team A"},
                "a": {"id": "2", "title": "Team B"},
            },
            {
                "isResult": True,
                "datetime": "2025-05-11 15:00:00",
                "h": {"id": "3", "title": "Team C"},
                "a": {"id": "4", "title": "Team D"},
            }
        ]
        mock_client.league.return_value.get_match_data.return_value = mock_match_data

        # Act
        fixtures = get_upcoming_fixtures(league_code="Bundesliga", season="2025")

        # Assert
        # Since MOCK_UPCOMING=1, it should fall back to mock fixtures using recent played matches
        self.assertEqual(len(fixtures), 2)
        self.assertEqual(fixtures[0]['home_team'], "Team A")
        self.assertEqual(fixtures[0]['away_team'], "Team B")
        self.assertEqual(fixtures[1]['home_team'], "Team C")
        self.assertEqual(fixtures[1]['away_team'], "Team D")

if __name__ == "__main__":
    unittest.main()
