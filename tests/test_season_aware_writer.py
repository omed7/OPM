import unittest
from unittest.mock import patch

from src import output_writer


class TestSeasonAwareOddAlertsWriter(unittest.TestCase):
    def setUp(self):
        self.original_predictions = output_writer.global_db_predictions
        output_writer.global_db_predictions = []

    def tearDown(self):
        output_writer.global_db_predictions = self.original_predictions

    @patch("src.output_writer.parse_upcoming_fixtures")
    @patch("src.output_writer.urllib.request.urlopen")
    def test_new_season_does_not_use_prior_season_oddalerts_history(
        self, mock_urlopen, mock_parser
    ):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"<html>fixtures</html>"
        mock_parser.return_value = [
            {"home_team": "Home FC", "away_team": "Away FC", "date": "2026-08-15"}
        ]
        records = []
        for team, opponent in (("Home FC", "H"), ("Away FC", "A")):
            records.extend(
                [
                    {"team": team, "opponent": f"{opponent} old home", "date": "2026-05-10", "venue": "home", "xg_for": 2.0, "xg_against": 1.0, "goals_for": 2, "goals_against": 1, "league": "eredivisie"},
                    {"team": team, "opponent": f"{opponent} old away", "date": "2026-05-03", "venue": "away", "xg_for": 1.0, "xg_against": 2.0, "goals_for": 1, "goals_against": 2, "league": "eredivisie"},
                    {"team": team, "opponent": f"{opponent} current home", "date": "2026-08-08", "venue": "home", "xg_for": 1.5, "xg_against": 1.5, "goals_for": 1, "goals_against": 1, "league": "eredivisie"},
                    {"team": team, "opponent": f"{opponent} current away", "date": "2026-08-07", "venue": "away", "xg_for": 1.5, "xg_against": 1.5, "goals_for": 1, "goals_against": 1, "league": "eredivisie"},
                ]
            )
        source_health = []

        league = output_writer.process_oddalerts_league(
            "eredivisie", "Eredivisie", "/leagues/netherlands/eredivisie/fixtures", records, source_health
        )

        self.assertEqual(league["fixtures"], [])
        self.assertIn(
            {"provider": "oddalerts_history", "league": "eredivisie", "status": "prior_season_history_filtered", "detail": "4 records"},
            source_health,
        )
        self.assertTrue(
            any(item["status"] == "current_season_history_insufficient" for item in source_health)
        )

    @patch("src.output_writer.parse_upcoming_fixtures")
    @patch("src.output_writer.urllib.request.urlopen")
    def test_calendar_year_midseason_records_remain_eligible(self, mock_urlopen, mock_parser):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"<html>fixtures</html>"
        mock_parser.return_value = [
            {"home_team": "Home FC", "away_team": "Away FC", "date": "2026-08-15"}
        ]
        records = []
        for team, opponent in (("Home FC", "H"), ("Away FC", "A")):
            records.extend(
                [
                    {"team": team, "opponent": f"{opponent} home 1", "date": "2026-07-10", "venue": "home", "xg_for": 2.0, "xg_against": 1.0, "goals_for": 2, "goals_against": 1, "league": "eliteserien"},
                    {"team": team, "opponent": f"{opponent} home 2", "date": "2026-06-10", "venue": "home", "xg_for": 1.0, "xg_against": 2.0, "goals_for": 1, "goals_against": 2, "league": "eliteserien"},
                    {"team": team, "opponent": f"{opponent} away 1", "date": "2026-07-09", "venue": "away", "xg_for": 1.5, "xg_against": 1.5, "goals_for": 1, "goals_against": 1, "league": "eliteserien"},
                    {"team": team, "opponent": f"{opponent} away 2", "date": "2026-06-09", "venue": "away", "xg_for": 1.5, "xg_against": 1.5, "goals_for": 1, "goals_against": 1, "league": "eliteserien"},
                ]
            )

        league = output_writer.process_oddalerts_league(
            "eliteserien", "Eliteserien", "/leagues/norway/eliteserien/fixtures", records
        )

        self.assertEqual(len(league["fixtures"]), 1)
        for history_key in ("home_last_4_matches", "away_last_4_matches"):
            self.assertTrue(
                all(match["date"] >= "2026-01-01" for match in league["fixtures"][0][history_key])
            )


class TestSeasonAwareUnderstatWriter(unittest.TestCase):
    @patch("src.output_writer.get_current_season", return_value="2026")
    @patch("src.output_writer.get_team_matches")
    @patch("src.output_writer.get_upcoming_fixtures")
    def test_new_season_does_not_use_prior_season_understat_history(
        self, mock_upcoming, mock_team_matches, _mock_current_season
    ):
        mock_upcoming.return_value = (
            [{"home_team": "Home FC", "away_team": "Away FC", "date": "2026-08-15"}],
            "success_with_fixtures",
            None,
        )
        mock_team_matches.side_effect = [
            [
                {"opponent": "old home", "date": "2026-05-10", "venue": "home", "xg_for": 2.0, "xg_against": 1.0},
                {"opponent": "old away", "date": "2026-05-03", "venue": "away", "xg_for": 1.0, "xg_against": 2.0},
                {"opponent": "current home", "date": "2026-08-08", "venue": "home", "xg_for": 1.5, "xg_against": 1.5},
                {"opponent": "current away", "date": "2026-08-07", "venue": "away", "xg_for": 1.5, "xg_against": 1.5},
            ],
            [
                {"opponent": "old home", "date": "2026-05-10", "venue": "home", "xg_for": 2.0, "xg_against": 1.0},
                {"opponent": "old away", "date": "2026-05-03", "venue": "away", "xg_for": 1.0, "xg_against": 2.0},
                {"opponent": "current home", "date": "2026-08-08", "venue": "home", "xg_for": 1.5, "xg_against": 1.5},
                {"opponent": "current away", "date": "2026-08-07", "venue": "away", "xg_for": 1.5, "xg_against": 1.5},
            ],
        ]
        source_health = []

        league = output_writer.process_understat_league(
            "EPL", "Premier League", "premier_league", source_health
        )

        self.assertEqual(league["fixtures"], [])
        self.assertTrue(
            any(item["status"] == "prior_season_history_filtered" for item in source_health)
        )
        self.assertTrue(
            any(item["status"] == "current_season_history_insufficient" for item in source_health)
        )


if __name__ == "__main__":
    unittest.main()
