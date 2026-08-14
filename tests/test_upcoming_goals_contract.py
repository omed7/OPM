import unittest
from unittest.mock import patch

from src import output_writer


class TestUpcomingGoalsContract(unittest.TestCase):
    def setUp(self):
        self.original_predictions = output_writer.global_db_predictions
        output_writer.global_db_predictions = []

    def tearDown(self):
        output_writer.global_db_predictions = self.original_predictions

    @patch("src.output_writer.parse_upcoming_fixtures")
    @patch("src.output_writer.urllib.request.urlopen")
    def test_oddalerts_public_fixture_contains_calculated_goal_fields(
        self, mock_urlopen, mock_parser
    ):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"<html>fixtures</html>"
        mock_parser.return_value = [
            {"home_team": "Home FC", "away_team": "Away FC", "date": "2026-08-16"}
        ]
        records = [
            {"team": "Home FC", "opponent": "H1", "date": "2026-08-10", "venue": "home", "xg_for": 2.0, "xg_against": 1.0, "goals_for": 2, "goals_against": 1, "league": "mls"},
            {"team": "Home FC", "opponent": "H2", "date": "2026-08-09", "venue": "away", "xg_for": 1.0, "xg_against": 2.0, "goals_for": 1, "goals_against": 2, "league": "mls"},
            {"team": "Home FC", "opponent": "H3", "date": "2026-08-08", "venue": "home", "xg_for": 4.0, "xg_against": 3.0, "goals_for": 4, "goals_against": 3, "league": "mls"},
            {"team": "Home FC", "opponent": "H4", "date": "2026-08-07", "venue": "away", "xg_for": 3.0, "xg_against": 4.0, "goals_for": 3, "goals_against": 4, "league": "mls"},
            {"team": "Away FC", "opponent": "A1", "date": "2026-08-11", "venue": "home", "xg_for": 1.0, "xg_against": 1.5, "goals_for": 1, "goals_against": 2, "league": "mls"},
            {"team": "Away FC", "opponent": "A2", "date": "2026-08-10", "venue": "away", "xg_for": 3.0, "xg_against": 1.0, "goals_for": 3, "goals_against": 1, "league": "mls"},
            {"team": "Away FC", "opponent": "A3", "date": "2026-08-09", "venue": "home", "xg_for": 2.0, "xg_against": 2.0, "goals_for": 2, "goals_against": 2, "league": "mls"},
            {"team": "Away FC", "opponent": "A4", "date": "2026-08-08", "venue": "away", "xg_for": 4.0, "xg_against": 3.0, "goals_for": 4, "goals_against": 3, "league": "mls"},
        ]

        league = output_writer.process_oddalerts_league(
            "mls", "Major League Soccer", "/leagues/us/mls/fixtures", records
        )

        fixture = league["fixtures"][0]
        self.assertEqual(fixture["home_expected_xg"], 2.19)
        self.assertEqual(fixture["away_expected_xg"], 2.5)
        self.assertEqual(fixture["combined_expected_xg"], 4.69)
        self.assertEqual(fixture["home_expected_goals"], 2.25)
        self.assertEqual(fixture["away_expected_goals"], 2.5)
        self.assertEqual(fixture["combined_expected_goals"], 4.75)

    @patch("src.output_writer.get_current_season", return_value="2025")
    @patch("src.output_writer.get_team_matches")
    @patch("src.output_writer.get_upcoming_fixtures")
    def test_understat_public_fixture_contains_null_goal_fields_when_unavailable(
        self, mock_upcoming, mock_team_matches, _mock_current_season
    ):
        mock_upcoming.return_value = (
            [{"home_team": "Home FC", "away_team": "Away FC", "date": "2026-08-16"}],
            "success_with_fixtures",
            None,
        )
        mock_team_matches.side_effect = [
            [
                {"opponent": "H1", "date": "2026-08-10", "venue": "home", "xg_for": 2.0, "xg_against": 1.0},
                {"opponent": "H2", "date": "2026-08-09", "venue": "away", "xg_for": 2.0, "xg_against": 1.0},
                {"opponent": "H3", "date": "2026-08-08", "venue": "home", "xg_for": 2.0, "xg_against": 1.0},
                {"opponent": "H4", "date": "2026-08-07", "venue": "away", "xg_for": 2.0, "xg_against": 1.0},
            ],
            [
                {"opponent": "A1", "date": "2026-08-10", "venue": "home", "xg_for": 1.0, "xg_against": 1.5},
                {"opponent": "A2", "date": "2026-08-09", "venue": "away", "xg_for": 1.0, "xg_against": 1.5},
                {"opponent": "A3", "date": "2026-08-08", "venue": "home", "xg_for": 1.0, "xg_against": 1.5},
                {"opponent": "A4", "date": "2026-08-07", "venue": "away", "xg_for": 1.0, "xg_against": 1.5},
            ],
        ]

        league = output_writer.process_understat_league("EPL", "Premier League", "premier_league")

        fixture = league["fixtures"][0]
        self.assertEqual(fixture["home_expected_xg"], 1.75)
        self.assertEqual(fixture["away_expected_xg"], 1.0)
        self.assertEqual(fixture["combined_expected_xg"], 2.75)
        self.assertIsNone(fixture["home_expected_goals"])
        self.assertIsNone(fixture["away_expected_goals"])
        self.assertIsNone(fixture["combined_expected_goals"])


if __name__ == "__main__":
    unittest.main()
