import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src import output_writer


class TestHistoricalSourceHealth(unittest.TestCase):
    def setUp(self):
        self.original_predictions = output_writer.global_db_predictions
        output_writer.global_db_predictions = []

    def tearDown(self):
        output_writer.global_db_predictions = self.original_predictions

    @staticmethod
    def healthy_league():
        return {
            "id": "mls",
            "name": "Major League Soccer",
            "metric": "xg",
            "fixtures": [
                {
                    "home_team": "Home FC",
                    "away_team": "Away FC",
                    "date": "2026-08-16",
                    "home_expected_xg": 1.25,
                    "away_expected_xg": 0.75,
                    "combined_expected_xg": 2.0,
                }
            ],
        }

    def test_main_reports_oddalerts_history_fetch_failure_but_publishes_healthy_fixture(self):
        league = {
            "id": "mls",
            "name": "Major League Soccer",
            "slug": "mls",
            "fixtures_path": "/leagues/us/mls/fixtures",
        }

        def healthy_fixture_source(_id, _name, _path, _records, source_health):
            output_writer.record_source_health(
                source_health, "oddalerts", "mls", "success_with_fixtures"
            )
            return self.healthy_league()

        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                with (
                    patch.object(output_writer, "ODDALERTS_LEAGUES", [league]),
                    patch.object(output_writer, "UNDERSTAT_LEAGUES", []),
                    patch.object(
                        output_writer.urllib.request,
                        "urlopen",
                        side_effect=OSError("history down"),
                    ),
                    patch.object(
                        output_writer,
                        "process_oddalerts_league",
                        side_effect=healthy_fixture_source,
                    ),
                    patch.object(output_writer, "get_past_matches", return_value=[]),
                    patch.object(output_writer, "save_matches_to_supabase") as save_matches,
                    patch.object(output_writer, "save_predictions_to_supabase") as save_predictions,
                    patch.object(output_writer, "get_version", return_value="test-version"),
                    patch("sys.stdout", new_callable=io.StringIO) as stdout,
                ):
                    output_writer.main()

                self.assertIn("oddalerts_history:history_fetch_failed=1", stdout.getvalue())
                self.assertIn(
                    "Warning: oddalerts_history mls history_fetch_failed: history down",
                    stdout.getvalue(),
                )
                save_matches.assert_called_once_with([])
                save_predictions.assert_called_once_with([])
                with open("public/data.json", encoding="utf-8") as artifact:
                    payload = json.load(artifact)
                self.assertEqual(payload["leagues"], [self.healthy_league()])
            finally:
                os.chdir(original_cwd)

    @patch("src.output_writer.get_current_season", return_value="2025")
    def test_main_reports_understat_history_fetch_failure_but_publishes_healthy_fixture(
        self, _mock_current_season
    ):
        league = {"code": "EPL", "name": "Premier League", "output_id": "premier_league"}

        def healthy_fixture_source(_code, _name, _output_id, source_health):
            output_writer.record_source_health(
                source_health, "understat", "premier_league", "success_with_fixtures"
            )
            return self.healthy_league()

        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                with (
                    patch.object(output_writer, "ODDALERTS_LEAGUES", []),
                    patch.object(output_writer, "UNDERSTAT_LEAGUES", [league]),
                    patch.object(
                        output_writer,
                        "process_understat_league",
                        side_effect=healthy_fixture_source,
                    ),
                    patch.object(
                        output_writer,
                        "get_played_matches",
                        side_effect=RuntimeError("history down"),
                    ),
                    patch.object(output_writer, "get_past_matches", return_value=[]),
                    patch.object(output_writer, "save_matches_to_supabase") as save_matches,
                    patch.object(output_writer, "save_predictions_to_supabase") as save_predictions,
                    patch.object(output_writer, "get_version", return_value="test-version"),
                    patch("sys.stdout", new_callable=io.StringIO) as stdout,
                ):
                    output_writer.main()

                self.assertIn("understat_history:history_fetch_failed=1", stdout.getvalue())
                self.assertIn(
                    "Warning: understat_history premier_league history_fetch_failed: history down",
                    stdout.getvalue(),
                )
                save_matches.assert_called_once_with([])
                save_predictions.assert_called_once_with([])
                with open("public/data.json", encoding="utf-8") as artifact:
                    payload = json.load(artifact)
                self.assertEqual(payload["leagues"], [self.healthy_league()])
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
