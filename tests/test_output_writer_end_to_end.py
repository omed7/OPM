import json
import os
import tempfile
import unittest
from unittest.mock import patch

from src import output_writer


class TestOutputWriterMainTracer(unittest.TestCase):
    def setUp(self):
        self.original_predictions = output_writer.global_db_predictions
        output_writer.global_db_predictions = []

    def tearDown(self):
        output_writer.global_db_predictions = self.original_predictions

    @patch.dict(os.environ, {"SEASON": "2025"}, clear=True)
    def test_main_writes_predicted_fixture_and_persists_records_in_order(self):
        league = {
            "id": "mls",
            "name": "Major League Soccer",
            "slug": "major-league-soccer",
            "fixtures_path": "/leagues/united-states/major-league-soccer/fixtures",
        }
        raw_matches = [
            {"home_team": "Home FC", "away_team": "Opposition 1", "home_xg": 2.0, "away_xg": 1.0, "score": "2 - 1", "date": "2026-08-10"},
            {"home_team": "Opposition 2", "away_team": "Home FC", "home_xg": 2.0, "away_xg": 1.0, "score": "2 - 1", "date": "2026-08-11"},
            {"home_team": "Home FC", "away_team": "Opposition 3", "home_xg": 4.0, "away_xg": 3.0, "score": "4 - 3", "date": "2026-08-12"},
            {"home_team": "Opposition 4", "away_team": "Home FC", "home_xg": 4.0, "away_xg": 3.0, "score": "4 - 3", "date": "2026-08-13"},
            {"home_team": "Away FC", "away_team": "Opposition 5", "home_xg": 1.0, "away_xg": 1.5, "score": "1 - 2", "date": "2026-08-11"},
            {"home_team": "Opposition 6", "away_team": "Away FC", "home_xg": 1.0, "away_xg": 3.0, "score": "1 - 3", "date": "2026-08-10"},
            {"home_team": "Away FC", "away_team": "Opposition 7", "home_xg": 2.0, "away_xg": 2.0, "score": "2 - 2", "date": "2026-08-11"},
            {"home_team": "Opposition 8", "away_team": "Away FC", "home_xg": 3.0, "away_xg": 4.0, "score": "3 - 4", "date": "2026-08-12"},
        ]
        upcoming_fixture = [{"home_team": "Home FC", "away_team": "Away FC", "date": "2026-08-16"}]
        persistence_order = []

        def save_matches(records):
            persistence_order.append(("matches", len(records)))

        def save_predictions(predictions):
            persistence_order.append(("predictions", len(predictions)))

        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                with (
                    patch.object(output_writer, "ODDALERTS_LEAGUES", [league]),
                    patch.object(output_writer, "UNDERSTAT_LEAGUES", []),
                    patch.object(output_writer, "fetch_and_parse_oddalerts_league", return_value=raw_matches),
                    patch.object(output_writer, "parse_upcoming_fixtures", return_value=upcoming_fixture),
                    patch.object(output_writer.urllib.request, "urlopen") as mock_urlopen,
                    patch.object(output_writer, "get_past_matches", return_value=[]),
                    patch.object(
                        output_writer,
                        "fetch_historical_standings_records",
                        return_value=([], [], None),
                    ),
                    patch.object(output_writer, "save_matches_to_supabase", side_effect=save_matches),
                    patch.object(output_writer, "save_predictions_to_supabase", side_effect=save_predictions),
                    patch.object(output_writer, "get_version", return_value="test-version"),
                ):
                    mock_urlopen.return_value.__enter__.return_value.read.return_value = b"<html>fixtures</html>"
                    output_writer.main()

                self.assertEqual(persistence_order, [("matches", 16), ("predictions", 1)])
                with open("public/data.json", encoding="utf-8") as artifact:
                    payload = json.load(artifact)

                self.assertEqual(payload["meta"]["version"], "test-version")
                self.assertEqual(len(payload["leagues"]), 1)
                self.assertEqual(payload["leagues"][0]["id"], "mls")
                self.assertEqual(len(payload["leagues"][0]["fixtures"]), 1)
                fixture = payload["leagues"][0]["fixtures"][0]
                self.assertEqual(fixture["home_team"], "Home FC")
                self.assertEqual(fixture["away_team"], "Away FC")
                self.assertEqual(fixture["date"], "2026-08-16")
                self.assertEqual(fixture["home_expected_xg"], 2.19)
                self.assertEqual(fixture["away_expected_xg"], 2.5)
                self.assertEqual(fixture["combined_expected_xg"], 4.69)
                self.assertEqual(len(fixture["home_last_4_matches"]), 4)
                self.assertEqual(len(fixture["away_last_4_matches"]), 4)
                with open("public/league_standings.json", encoding="utf-8") as artifact:
                    standings = json.load(artifact)
                self.assertEqual(standings["schema_version"], 2)
                self.assertEqual(standings["meta"]["version"], "test-version")
                self.assertEqual(standings["leagues"], [])
            finally:
                os.chdir(original_cwd)


    def test_main_publishes_finished_oddalerts_results_without_forecast_ready_fixtures(self):
        league = {
            "id": "generic-oddalerts-league",
            "name": "Generic OddAlerts League",
            "slug": "generic-oddalerts-league",
            "fixtures_path": "/leagues/example/generic/fixtures",
        }
        finished_fixture = {
            "home_team": "Result Home",
            "away_team": "Result Away",
            "date": "2026-08-23",
            "home_goals": 2,
            "away_goals": 1,
            "home_xg": 1.41,
            "away_xg": 0.62,
            "home_expected_xg": None,
            "away_expected_xg": None,
            "combined_expected_xg": None,
            "home_expected_goals": None,
            "away_expected_goals": None,
            "combined_expected_goals": None,
            "status": "FINISHED",
        }

        def healthy_empty_fixture_source(_id, _name, _path, _records, source_health):
            output_writer.record_source_health(source_health, "oddalerts", league["id"], "success_empty")
            return {"id": league["id"], "name": league["name"], "metric": "xg", "fixtures": []}

        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                with (
                    patch.object(output_writer, "ODDALERTS_LEAGUES", [league]),
                    patch.object(output_writer, "UNDERSTAT_LEAGUES", []),
                    patch.object(output_writer, "fetch_and_parse_oddalerts_league", return_value=[]),
                    patch.object(output_writer, "process_oddalerts_league", side_effect=healthy_empty_fixture_source),
                    patch.object(output_writer, "get_past_matches", return_value=[finished_fixture]),
                    patch.object(
                        output_writer,
                        "fetch_historical_standings_records",
                        return_value=([], [], None),
                    ),
                    patch.object(output_writer, "save_matches_to_supabase"),
                    patch.object(output_writer, "save_predictions_to_supabase"),
                    patch.object(output_writer, "get_version", return_value="test-version"),
                ):
                    output_writer.main()

                with open("public/data.json", encoding="utf-8") as artifact:
                    payload = json.load(artifact)
                self.assertEqual([league_data["id"] for league_data in payload["leagues"]], [league["id"]])
                self.assertEqual(payload["leagues"][0]["fixtures"], [finished_fixture])
            finally:
                os.chdir(original_cwd)

    def test_main_omits_empty_oddalerts_league_without_forecasts_or_results(self):
        league = {
            "id": "generic-oddalerts-league",
            "name": "Generic OddAlerts League",
            "slug": "generic-oddalerts-league",
            "fixtures_path": "/leagues/example/generic/fixtures",
        }

        def healthy_empty_fixture_source(_id, _name, _path, _records, source_health):
            output_writer.record_source_health(source_health, "oddalerts", league["id"], "success_empty")
            return {"id": league["id"], "name": league["name"], "metric": "xg", "fixtures": []}

        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                with (
                    patch.object(output_writer, "ODDALERTS_LEAGUES", [league]),
                    patch.object(output_writer, "UNDERSTAT_LEAGUES", []),
                    patch.object(output_writer, "fetch_and_parse_oddalerts_league", return_value=[]),
                    patch.object(output_writer, "process_oddalerts_league", side_effect=healthy_empty_fixture_source),
                    patch.object(output_writer, "get_past_matches", return_value=[]),
                    patch.object(
                        output_writer,
                        "fetch_historical_standings_records",
                        return_value=([], [], None),
                    ),
                    patch.object(output_writer, "save_matches_to_supabase"),
                    patch.object(output_writer, "save_predictions_to_supabase"),
                    patch.object(output_writer, "get_version", return_value="test-version"),
                ):
                    output_writer.main()

                with open("public/data.json", encoding="utf-8") as artifact:
                    payload = json.load(artifact)
                self.assertEqual(payload["leagues"], [])
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
