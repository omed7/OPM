import io
import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, call, patch

from src import output_writer


class TestSupabaseUpserts(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    @patch("src.output_writer.urllib.request.urlopen")
    def test_missing_credentials_do_not_issue_persistence_requests(self, mock_urlopen):
        records = [
            {
                "team": "Home Team",
                "opponent": "Away Team",
                "date": "2026-08-14",
                "venue": "home",
                "league": "league-id",
            }
        ]
        predictions = [
            {
                "home_team": "Home Team",
                "away_team": "Away Team",
                "date": "2026-08-14",
                "league": "league-id",
            }
        ]

        output_writer.save_matches_to_supabase(records)
        output_writer.save_predictions_to_supabase(predictions)

        mock_urlopen.assert_not_called()

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://example.supabase.co/",
            "SUPABASE_KEY": "test-key",
        },
        clear=True,
    )
    @patch("src.output_writer.urllib.request.urlopen")
    def test_repeated_match_write_reuses_natural_key_request(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value = MagicMock()
        records = [
            {
                "team": "Home Team",
                "opponent": "Away Team",
                "date": "2026-08-14",
                "venue": "home",
                "league": "league-id",
            }
        ]

        output_writer.save_matches_to_supabase(records)
        output_writer.save_matches_to_supabase(records)

        requests = [call.args[0] for call in mock_urlopen.call_args_list]
        self.assertEqual(len(requests), 2)
        self.assertEqual(
            [request.full_url for request in requests],
            [
                "https://example.supabase.co/rest/v1/matches?on_conflict=team,opponent,date,venue,league",
                "https://example.supabase.co/rest/v1/matches?on_conflict=team,opponent,date,venue,league",
            ],
        )
        self.assertEqual([json.loads(request.data.decode("utf-8")) for request in requests], [records, records])
        self.assertTrue(all(request.get_header("Prefer") == "resolution=ignore-duplicates" for request in requests))

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://example.supabase.co/",
            "SUPABASE_KEY": "test-key",
        },
        clear=True,
    )
    @patch("src.output_writer.urllib.request.urlopen")
    def test_changed_prediction_write_reuses_identity_and_merges_new_values(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value = MagicMock()
        original_prediction = {
            "home_team": "Home Team",
            "away_team": "Away Team",
            "date": "2026-08-14",
            "league": "league-id",
            "home_expected_xg": 1.25,
            "away_expected_xg": 0.75,
        }
        updated_prediction = {**original_prediction, "home_expected_xg": 1.5}

        output_writer.save_predictions_to_supabase([original_prediction])
        output_writer.save_predictions_to_supabase([updated_prediction])

        requests = [call.args[0] for call in mock_urlopen.call_args_list]
        payloads = [json.loads(request.data.decode("utf-8"))[0] for request in requests]
        self.assertEqual(len(requests), 2)
        self.assertTrue(
            all(
                request.full_url
                == "https://example.supabase.co/rest/v1/predictions?on_conflict=home_team,away_team,date,league"
                for request in requests
            )
        )
        self.assertTrue(all(request.get_header("Prefer") == "resolution=merge-duplicates" for request in requests))
        self.assertEqual(
            [{key: payload[key] for key in ("home_team", "away_team", "date", "league")} for payload in payloads],
            [
                {key: original_prediction[key] for key in ("home_team", "away_team", "date", "league")},
                {key: original_prediction[key] for key in ("home_team", "away_team", "date", "league")},
            ],
        )
        self.assertEqual([payload["home_expected_xg"] for payload in payloads], [1.25, 1.5])

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://example.supabase.co/",
            "SUPABASE_KEY": "test-key",
        },
        clear=True,
    )
    @patch("src.output_writer.urllib.request.urlopen")
    def test_match_upsert_uses_natural_key_conflict_target(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value = MagicMock()
        records = [
            {
                "team": "Home Team",
                "opponent": "Away Team",
                "date": "2026-08-14",
                "venue": "home",
                "league": "league-id",
            }
        ]

        output_writer.save_matches_to_supabase(records)

        request = mock_urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://example.supabase.co/rest/v1/matches?on_conflict=team,opponent,date,venue,league",
        )
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Prefer"), "resolution=ignore-duplicates")
        self.assertEqual(json.loads(request.data.decode("utf-8")), records)

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://example.supabase.co/",
            "SUPABASE_KEY": "test-key",
        },
        clear=True,
    )
    @patch("src.output_writer.urllib.request.urlopen")
    def test_prediction_upsert_uses_natural_key_conflict_target(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value = MagicMock()
        predictions = [
            {
                "home_team": "Home Team",
                "away_team": "Away Team",
                "date": "2026-08-14",
                "league": "league-id",
                "home_expected_xg": 1.25,
                "away_expected_xg": 0.75,
            }
        ]

        output_writer.save_predictions_to_supabase(predictions)

        request = mock_urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://example.supabase.co/rest/v1/predictions?on_conflict=home_team,away_team,date,league",
        )
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Prefer"), "resolution=merge-duplicates")
        self.assertEqual(json.loads(request.data.decode("utf-8")), predictions)

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://example.supabase.co/",
            "SUPABASE_KEY": "test-key",
        },
        clear=True,
    )
    @patch("src.output_writer.urllib.request.urlopen", side_effect=OSError("network down"))
    def test_failed_match_upsert_raises(self, _mock_urlopen):
        records = [
            {
                "team": "Home Team",
                "opponent": "Away Team",
                "date": "2026-08-14",
                "venue": "home",
                "league": "league-id",
            }
        ]

        with self.assertRaisesRegex(RuntimeError, "matches"):
            output_writer.save_matches_to_supabase(records)

    @patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://example.supabase.co/",
            "SUPABASE_KEY": "test-key",
        },
        clear=True,
    )
    @patch("src.output_writer.urllib.request.urlopen", side_effect=OSError("network down"))
    def test_failed_prediction_upsert_raises(self, _mock_urlopen):
        predictions = [
            {
                "home_team": "Home Team",
                "away_team": "Away Team",
                "date": "2026-08-14",
                "league": "league-id",
            }
        ]

        with self.assertRaisesRegex(RuntimeError, "predictions"):
            output_writer.save_predictions_to_supabase(predictions)

    @patch("src.output_writer.urllib.request.urlopen")
    def test_empty_upserts_are_no_ops(self, mock_urlopen):
        output_writer.save_matches_to_supabase([])
        output_writer.save_predictions_to_supabase([])

        mock_urlopen.assert_not_called()

    @patch.object(output_writer, "UNDERSTAT_LEAGUES", [])
    @patch.object(output_writer, "ODDALERTS_LEAGUES", [])
    @patch.object(
        output_writer,
        "save_matches_to_supabase",
        side_effect=RuntimeError("matches persistence failed"),
    )
    def test_main_propagates_match_persistence_failure(self, _mock_save_matches):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                with self.assertRaisesRegex(RuntimeError, "matches persistence failed"):
                    output_writer.main()
            finally:
                os.chdir(original_cwd)

    @patch.object(output_writer, "UNDERSTAT_LEAGUES", [])
    @patch.object(output_writer, "ODDALERTS_LEAGUES", [])
    @patch.object(output_writer, "save_predictions_to_supabase")
    @patch.object(output_writer, "save_matches_to_supabase")
    def test_main_rejects_populated_to_zero_before_persistence(
        self, mock_save_matches, mock_save_predictions
    ):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                os.makedirs("public")
                with open("public/data.json", "w", encoding="utf-8") as artifact:
                    json.dump(
                        {
                            "meta": {"version": "previous", "generated_at": "2026-08-14T00:00:00Z"},
                            "leagues": [
                                {
                                    "id": "mls",
                                    "name": "Major League Soccer",
                                    "metric": "xg",
                                    "fixtures": [
                                        {
                                            "home_team": "Home FC",
                                            "away_team": "Away FC",
                                            "date": "2026-08-16",
                                        }
                                    ],
                                }
                            ],
                        },
                        artifact,
                    )

                with self.assertRaisesRegex(RuntimeError, "zero fixtures"):
                    output_writer.main()

                mock_save_matches.assert_not_called()
                mock_save_predictions.assert_not_called()
            finally:
                os.chdir(original_cwd)

    @patch.dict(os.environ, {"ALLOW_EMPTY_FIXTURES": "true"}, clear=True)
    @patch.object(output_writer, "UNDERSTAT_LEAGUES", [])
    @patch.object(output_writer, "ODDALERTS_LEAGUES", [])
    @patch.object(output_writer, "save_predictions_to_supabase")
    @patch.object(output_writer, "save_matches_to_supabase")
    def test_main_allows_populated_to_zero_with_manual_override(
        self, mock_save_matches, mock_save_predictions
    ):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                os.makedirs("public")
                with open("public/data.json", "w", encoding="utf-8") as artifact:
                    json.dump(
                        {
                            "meta": {"version": "previous", "generated_at": "2026-08-14T00:00:00Z"},
                            "leagues": [{"id": "mls", "name": "Major League Soccer", "metric": "xg", "fixtures": [{"home_team": "Home FC", "away_team": "Away FC", "date": "2026-08-16"}]}],
                        },
                        artifact,
                    )

                output_writer.main()

                mock_save_matches.assert_called_once_with([])
                mock_save_predictions.assert_called_once_with([])
                with open("public/data.json", encoding="utf-8") as artifact:
                    self.assertEqual(json.load(artifact)["leagues"], [])
            finally:
                os.chdir(original_cwd)

    @patch.dict(os.environ, {"SEASON": "2025"}, clear=True)
    @patch.object(output_writer, "ODDALERTS_LEAGUES", [])
    @patch.object(
        output_writer,
        "UNDERSTAT_LEAGUES",
        [
            {"code": "EPL", "name": "Premier League", "output_id": "premier_league"},
            {"code": "La_Liga", "name": "La Liga", "output_id": "la_liga"},
        ],
    )
    @patch.object(output_writer, "get_past_matches", return_value=[])
    @patch.object(output_writer, "get_played_matches", return_value=[])
    @patch.object(
        output_writer,
        "get_upcoming_fixtures",
        side_effect=[
            ([], "fetch_failed", "network down"),
            ([], "success_empty", None),
        ],
    )
    @patch.object(output_writer, "save_predictions_to_supabase")
    @patch.object(output_writer, "save_matches_to_supabase")
    def test_main_warns_but_continues_when_one_league_fails_and_another_is_empty(
        self,
        mock_save_matches,
        mock_save_predictions,
        _mock_upcoming,
        _mock_played_matches,
        _mock_past_matches,
    ):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                    output_writer.main()

                self.assertIn("understat:fetch_failed=1", stdout.getvalue())
                self.assertIn("understat:success_empty=1", stdout.getvalue())
                self.assertIn("Warning: understat premier_league fetch_failed: network down", stdout.getvalue())
                mock_save_matches.assert_called_once_with([])
                mock_save_predictions.assert_called_once_with([])
            finally:
                os.chdir(original_cwd)

    @patch.dict(os.environ, {"SEASON": "2025"}, clear=True)
    @patch.object(output_writer, "ODDALERTS_LEAGUES", [])
    @patch.object(
        output_writer,
        "UNDERSTAT_LEAGUES",
        [{"code": "EPL", "name": "Premier League", "output_id": "premier_league"}],
    )
    @patch.object(output_writer, "get_played_matches", return_value=[])
    @patch.object(
        output_writer,
        "get_upcoming_fixtures",
        return_value=([], "fetch_failed", "network down"),
    )
    @patch.object(output_writer, "save_predictions_to_supabase")
    @patch.object(output_writer, "save_matches_to_supabase")
    def test_main_rejects_all_fixture_source_groups_failing(
        self,
        mock_save_matches,
        mock_save_predictions,
        _mock_upcoming,
        _mock_played_matches,
    ):
        original_cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                with self.assertRaisesRegex(RuntimeError, "All configured fixture source groups failed"):
                    output_writer.main()

                mock_save_matches.assert_not_called()
                mock_save_predictions.assert_not_called()
            finally:
                os.chdir(original_cwd)


if __name__ == "__main__":
    unittest.main()
