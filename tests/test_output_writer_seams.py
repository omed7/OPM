import unittest
from datetime import datetime, timezone
from unittest.mock import call, patch

from src import output_writer


class TestOddAlertsHistoryFetcher(unittest.TestCase):
    @patch("src.output_writer.parse_recent_results")
    @patch("src.output_writer.urllib.request.urlopen")
    def test_returns_parser_output_for_requested_league(self, mock_urlopen, mock_parser):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"<html>history</html>"
        expected_matches = [
            {
                "home_team": "Home Team",
                "away_team": "Away Team",
                "home_xg": 1.25,
                "away_xg": 0.75,
                "score": "1 - 0",
                "date": "2026-08-14",
            }
        ]
        mock_parser.return_value = expected_matches

        matches = output_writer.fetch_and_parse_oddalerts_league(
            "mls", "major-league-soccer", "Major League Soccer"
        )

        self.assertEqual(matches, expected_matches)
        request = mock_urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://www.oddalerts.com/xg/major-league-soccer",
        )
        mock_parser.assert_called_once_with("<html>history</html>")

    @patch("src.output_writer.parse_recent_results")
    @patch("src.output_writer.urllib.request.urlopen", side_effect=OSError("network down"))
    def test_returns_empty_when_history_fetch_fails(self, _mock_urlopen, mock_parser):
        matches = output_writer.fetch_and_parse_oddalerts_league(
            "mls", "major-league-soccer", "Major League Soccer"
        )

        self.assertEqual(matches, [])
        mock_parser.assert_not_called()

    @patch("src.output_writer.parse_recent_results", side_effect=ValueError("bad markup"))
    @patch("src.output_writer.urllib.request.urlopen")
    def test_returns_empty_when_history_parser_fails(self, mock_urlopen, _mock_parser):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"<html>history</html>"

        matches = output_writer.fetch_and_parse_oddalerts_league(
            "mls", "major-league-soccer", "Major League Soccer"
        )

        self.assertEqual(matches, [])


class TestOddAlertsFixtureProcessing(unittest.TestCase):
    def setUp(self):
        self.original_predictions = output_writer.global_db_predictions
        output_writer.global_db_predictions = []

    def tearDown(self):
        output_writer.global_db_predictions = self.original_predictions

    @patch("src.output_writer.parse_upcoming_fixtures")
    @patch("src.output_writer.urllib.request.urlopen")
    def test_builds_balanced_fixture_and_stages_prediction(self, mock_urlopen, mock_parser):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = b"<html>fixtures</html>"
        mock_parser.return_value = [
            {
                "home_team": "Home FC",
                "away_team": "Away FC",
                "date": "2026-08-16",
                "kickoff_time": "21:30",
            }
        ]
        records = [
            {
                "team": "Home FC",
                "opponent": "Opposition 1",
                "date": "2026-08-10",
                "venue": "home",
                "xg_for": 2.0,
                "xg_against": 1.0,
                "league": "mls",
            },
            {
                "team": "Home FC",
                "opponent": "Opposition 2",
                "date": "2026-08-09",
                "venue": "away",
                "xg_for": 1.0,
                "xg_against": 2.0,
                "league": "mls",
            },
            {
                "team": "Home FC",
                "opponent": "Opposition 3",
                "date": "2026-08-08",
                "venue": "home",
                "xg_for": 4.0,
                "xg_against": 3.0,
                "league": "mls",
            },
            {
                "team": "Home FC",
                "opponent": "Opposition 4",
                "date": "2026-08-07",
                "venue": "away",
                "xg_for": 3.0,
                "xg_against": 4.0,
                "league": "mls",
            },
            {
                "team": "Away FC",
                "opponent": "Opposition 5",
                "date": "2026-08-11",
                "venue": "home",
                "xg_for": 1.0,
                "xg_against": 1.5,
                "league": "mls",
            },
            {
                "team": "Away FC",
                "opponent": "Opposition 6",
                "date": "2026-08-10",
                "venue": "away",
                "xg_for": 3.0,
                "xg_against": 1.0,
                "league": "mls",
            },
            {
                "team": "Away FC",
                "opponent": "Opposition 7",
                "date": "2026-08-09",
                "venue": "home",
                "xg_for": 2.0,
                "xg_against": 2.0,
                "league": "mls",
            },
            {
                "team": "Away FC",
                "opponent": "Opposition 8",
                "date": "2026-08-08",
                "venue": "away",
                "xg_for": 4.0,
                "xg_against": 3.0,
                "league": "mls",
            },
            {
                "team": "Home FC",
                "opponent": "Wrong League",
                "date": "2026-08-12",
                "venue": "home",
                "xg_for": 99.0,
                "xg_against": 99.0,
                "league": "other-league",
            },
            {
                "team": "Other FC",
                "opponent": "Home FC",
                "date": "2026-08-13",
                "venue": "home",
                "xg_for": 99.0,
                "xg_against": 99.0,
                "league": "mls",
            },
        ]

        league = output_writer.process_oddalerts_league(
            "mls", "Major League Soccer", "/leagues/us/mls/fixtures", records
        )

        self.assertEqual(league["id"], "mls")
        self.assertEqual(league["name"], "Major League Soccer")
        self.assertEqual(league["metric"], "xg")
        self.assertEqual(len(league["fixtures"]), 1)

        fixture = league["fixtures"][0]
        self.assertEqual(fixture["home_team"], "Home FC")
        self.assertEqual(fixture["away_team"], "Away FC")
        self.assertEqual(fixture["date"], "2026-08-16")
        self.assertEqual(fixture["kickoff_time"], "21:30")
        self.assertEqual(fixture["home_expected_xg"], 2.19)
        self.assertEqual(fixture["away_expected_xg"], 2.5)
        self.assertEqual(fixture["combined_expected_xg"], 4.69)
        self.assertEqual(
            [match["opponent"] for match in fixture["home_last_4_matches"]],
            ["Opposition 1", "Opposition 2", "Opposition 3", "Opposition 4"],
        )
        self.assertEqual(
            [match["opponent"] for match in fixture["away_last_4_matches"]],
            ["Opposition 5", "Opposition 6", "Opposition 7", "Opposition 8"],
        )

        self.assertEqual(
            output_writer.global_db_predictions,
            [
                {
                    "home_team": "Home FC",
                    "away_team": "Away FC",
                    "date": "2026-08-16",
                    "league": "mls",
                    "home_expected_xg": 2.19,
                    "away_expected_xg": 2.5,
                    "combined_expected_xg": 4.69,
                    "home_expected_goals": None,
                    "away_expected_goals": None,
                    "combined_expected_goals": None,
                }
            ],
        )


class TestPastMatchRetrieval(unittest.TestCase):
    def setUp(self):
        self.fixed_now = datetime(2026, 8, 14, 12, 0, tzinfo=timezone.utc)
        self.prediction_endpoint = (
            "/predictions?league=eq.mls&date=gte.2026-08-10&date=lte.2026-08-15"
        )
        self.match_endpoint = (
            "/matches?league=eq.mls&venue=eq.home&date=gte.2026-08-10&"
            "date=lte.2026-08-15&goals_for=not.is.null"
        )
        self.prediction = {
            "home_team": "Home FC",
            "away_team": "Away FC",
            "date": "2026-08-12",
            "home_expected_xg": 1.25,
            "away_expected_xg": 0.75,
            "combined_expected_xg": 2.0,
            "home_expected_goals": 1.5,
            "away_expected_goals": 1.0,
            "combined_expected_goals": 2.5,
        }
        self.completed_match = {
            "team": "Home FC",
            "opponent": "Away FC",
            "date": "2026-08-12",
            "goals_for": 2,
            "goals_against": 1,
            "xg_for": 1.8,
            "xg_against": 0.9,
        }

    @patch("src.output_writer.supabase_request")
    @patch("src.output_writer.datetime")
    def test_attaches_persisted_prediction_to_completed_result(
        self, mock_datetime, mock_supabase_request
    ):
        mock_datetime.now.return_value = self.fixed_now
        mock_supabase_request.side_effect = [
            ([self.prediction], None),
            ([self.completed_match], None),
        ]

        past_matches = output_writer.get_past_matches([], "mls")

        self.assertEqual(
            mock_supabase_request.call_args_list,
            [call(self.prediction_endpoint), call(self.match_endpoint)],
        )
        self.assertEqual(
            past_matches,
            [
                {
                    "home_team": "Home FC",
                    "away_team": "Away FC",
                    "date": "2026-08-12",
                    "home_goals": 2,
                    "away_goals": 1,
                    "home_xg": 1.8,
                    "away_xg": 0.9,
                    "home_expected_xg": 1.25,
                    "away_expected_xg": 0.75,
                    "combined_expected_xg": 2.0,
                    "home_expected_goals": 1.5,
                    "away_expected_goals": 1.0,
                    "combined_expected_goals": 2.5,
                    "status": "FINISHED",
                }
            ],
        )

    @patch("src.output_writer.supabase_request")
    @patch("src.output_writer.datetime")
    def test_falls_back_to_deduplicated_local_records_when_match_read_fails(
        self, mock_datetime, mock_supabase_request
    ):
        mock_datetime.now.return_value = self.fixed_now
        mock_supabase_request.side_effect = [
            ([self.prediction], None),
            (None, "read failed"),
        ]
        local_record = {**self.completed_match, "league": "mls", "venue": "home"}

        past_matches = output_writer.get_past_matches(
            [local_record, local_record.copy()], "mls"
        )

        self.assertEqual(len(past_matches), 1)
        self.assertEqual(past_matches[0]["status"], "FINISHED")
        self.assertEqual(past_matches[0]["home_expected_xg"], 1.25)
        self.assertEqual(past_matches[0]["combined_expected_goals"], 2.5)

    @patch("src.output_writer.supabase_request")
    @patch("src.output_writer.datetime")
    def test_falls_back_to_eligible_local_record_when_match_read_is_empty(
        self, mock_datetime, mock_supabase_request
    ):
        mock_datetime.now.return_value = self.fixed_now
        mock_supabase_request.side_effect = [
            ([self.prediction], None),
            ([], None),
        ]
        eligible_record = {**self.completed_match, "league": "mls", "venue": "home"}
        outside_window_record = {
            **self.completed_match,
            "date": "2026-08-09",
            "league": "mls",
            "venue": "home",
        }

        past_matches = output_writer.get_past_matches(
            [eligible_record, outside_window_record], "mls"
        )

        self.assertEqual(len(past_matches), 1)
        self.assertEqual(past_matches[0]["date"], "2026-08-12")
        self.assertEqual(past_matches[0]["home_goals"], 2)


    @patch("src.output_writer.supabase_request")
    @patch("src.output_writer.datetime")
    def test_current_run_records_override_and_extend_persisted_results(
        self, mock_datetime, mock_supabase_request
    ):
        mock_datetime.now.return_value = self.fixed_now
        mock_supabase_request.side_effect = [
            ([self.prediction], None),
            ([self.completed_match], None),
        ]
        refreshed_same_fixture = {
            **self.completed_match,
            "league": "generic-oddalerts-league",
            "venue": "home",
            "goals_for": 3,
            "goals_against": 2,
            "xg_for": 2.4,
            "xg_against": 1.1,
        }
        newly_completed_fixture = {
            **self.completed_match,
            "league": "generic-oddalerts-league",
            "venue": "home",
            "team": "New Home FC",
            "opponent": "New Away FC",
            "date": "2026-08-13",
            "goals_for": 1,
            "goals_against": 0,
            "xg_for": 1.2,
            "xg_against": 0.4,
        }

        past_matches = output_writer.get_past_matches(
            [refreshed_same_fixture, newly_completed_fixture], "generic-oddalerts-league"
        )

        self.assertEqual(len(past_matches), 2)
        result_by_date = {match["date"][:10]: match for match in past_matches}
        self.assertEqual(result_by_date["2026-08-12"]["home_goals"], 3)
        self.assertEqual(result_by_date["2026-08-12"]["home_xg"], 2.4)
        self.assertEqual(result_by_date["2026-08-12"]["combined_expected_goals"], 2.5)
        self.assertEqual(result_by_date["2026-08-13"]["home_team"], "New Home FC")
        self.assertIsNone(result_by_date["2026-08-13"]["combined_expected_goals"])


if __name__ == "__main__":
    unittest.main()
