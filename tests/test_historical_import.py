import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import historical_import


MANUAL_FIXTURE = {
    "provider_match_id": "mt_manual",
    "league": "pro-league-saudi",
    "season": "Saudi Pro League 2025/26",
    "date": "2025-09-25",
    "home_team": "Al-Shabab",
    "away_team": "Al-Kholood",
    "home_goals": 1,
    "away_goals": 2,
    "provider_xg_available": False,
    "manual_xg": {"home": 1.62, "away": 1.91},
}

PROVIDER_FIXTURE = {
    "provider_match_id": "mt_provider",
    "league": "mls",
    "season": "MLS 2025",
    "date": "2025-06-01",
    "home_team": "Home FC",
    "away_team": "Away FC",
    "home_goals": 2,
    "away_goals": 1,
    "provider_xg_available": True,
    "manual_xg": None,
}

SCORE_ONLY_FIXTURE = {
    **PROVIDER_FIXTURE,
    "provider_match_id": "mt_goals_only",
    "provider_xg_available": False,
}


class TestHistoricalImportRecords(unittest.TestCase):
    def test_manual_pair_becomes_two_team_records_with_approved_score(self):
        records = historical_import.fixture_to_match_records(MANUAL_FIXTURE)

        self.assertEqual(len(records), 2)
        self.assertEqual(
            records[0],
            {
                "team": "Al-Shabab",
                "opponent": "Al-Kholood",
                "date": "2025-09-25",
                "venue": "home",
                "goals_for": 1,
                "goals_against": 2,
                "xg_for": 1.62,
                "xg_against": 1.91,
                "source": "thestatsapi_manual_override",
                "league": "pro-league-saudi",
                "weight": 1.0,
            },
        )
        self.assertEqual(records[1]["team"], "Al-Kholood")
        self.assertEqual(records[1]["xg_for"], 1.91)
        self.assertEqual(records[1]["xg_against"], 1.62)

    def test_provider_pair_fetches_stats_once_and_becomes_two_records(self):
        class Client:
            def __init__(self):
                self.match_ids = []

            def get_match_stats(self, match_id):
                self.match_ids.append(match_id)
                return {
                    "overview": {
                        "expected_goals": {"all": {"home": 2.25, "away": 0.75}}
                    }
                }

        client = Client()
        records = historical_import.fixture_to_match_records(PROVIDER_FIXTURE, client=client)

        self.assertEqual(client.match_ids, ["mt_provider"])
        self.assertEqual([record["xg_for"] for record in records], [2.25, 0.75])
        self.assertEqual({record["source"] for record in records}, {"thestatsapi"})

    def test_rejects_thestatsapi_record_on_or_after_cutoff(self):
        fixture = {**PROVIDER_FIXTURE, "date": "2026-08-10"}
        with self.assertRaisesRegex(historical_import.HistoricalImportError, "source boundary"):
            historical_import.fixture_to_match_records(fixture, client=object())

    def test_score_only_pair_becomes_two_records_with_null_xg(self):
        records = historical_import.fixture_to_match_records(SCORE_ONLY_FIXTURE)

        self.assertEqual([record["goals_for"] for record in records], [2, 1])
        self.assertEqual([record["goals_against"] for record in records], [1, 2])
        self.assertEqual([record["xg_for"] for record in records], [None, None])
        self.assertEqual([record["xg_against"] for record in records], [None, None])
        self.assertEqual({record["source"] for record in records}, {"thestatsapi_goals_only"})

    def test_rejects_fixture_with_unresolved_xg_availability(self):
        fixture = {**PROVIDER_FIXTURE, "provider_xg_available": None}
        with self.assertRaisesRegex(historical_import.HistoricalImportError, "unresolved xG"):
            historical_import.fixture_to_match_records(fixture, client=object())


class TestHistoricalImportDryRun(unittest.TestCase):
    @patch("src.historical_import.save_matches_to_supabase")
    @patch("src.historical_import.TheStatsAPIClient")
    def test_dry_run_writes_non_public_summary_without_client_or_persistence(
        self, mock_client, mock_save
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            output = root / "summary.json"
            manifest.write_text(json.dumps([MANUAL_FIXTURE, PROVIDER_FIXTURE]))

            historical_import.main(
                ["--manifest", str(manifest), "--output", str(output)]
            )

            summary = json.loads(output.read_text())
        self.assertEqual(summary["fixture_count"], 2)
        self.assertEqual(summary["team_perspective_row_count"], 4)
        self.assertEqual(summary["manual_xg_pair_count"], 1)
        self.assertEqual(summary["goals_only_fixture_count"], 0)
        mock_client.assert_not_called()
        mock_save.assert_not_called()

    def test_dry_run_counts_reviewed_score_only_fixture(self):
        summary = historical_import.summarize_manifest([SCORE_ONLY_FIXTURE])

        self.assertEqual(summary["fixture_count"], 1)
        self.assertEqual(summary["goals_only_fixture_count"], 1)
        self.assertEqual(summary["provider_xg_fixture_count"], 0)

    def test_rejects_public_output_path_before_loading_manifest(self):
        with self.assertRaises(ValueError):
            historical_import.main(
                ["--manifest", "/tmp/manifest.json", "--output", "public/import.json"]
            )

    @patch("src.historical_import.save_matches_to_supabase")
    @patch("src.historical_import.TheStatsAPIClient")
    @patch("src.historical_import.fetch_existing_match_keys")
    def test_preflight_reports_existing_natural_keys_without_provider_or_persistence(
        self, mock_existing_keys, mock_client, mock_save
    ):
        mock_existing_keys.return_value = {
            ("Al-Shabab", "Al-Kholood", "2025-09-25", "home", "pro-league-saudi"),
            ("Al-Kholood", "Al-Shabab", "2025-09-25", "away", "pro-league-saudi"),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            output = root / "summary.json"
            manifest.write_text(json.dumps([MANUAL_FIXTURE]))

            summary = historical_import.main(
                ["--manifest", str(manifest), "--output", str(output), "--preflight"]
            )

        self.assertEqual(summary["mode"], "preflight")
        self.assertEqual(summary["existing_natural_key_count"], 2)
        self.assertEqual(summary["new_team_perspective_row_count"], 0)
        mock_client.assert_not_called()
        mock_save.assert_not_called()

    @patch("src.historical_import.fetch_existing_match_keys")
    def test_preflight_uses_non_public_existing_key_snapshot(self, mock_existing_keys):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            output = root / "summary.json"
            existing = root / "existing-keys.json"
            manifest.write_text(json.dumps([MANUAL_FIXTURE]))
            existing.write_text(
                json.dumps(
                    [
                        {
                            "team": "Al-Shabab",
                            "opponent": "Al-Kholood",
                            "date": "2025-09-25",
                            "venue": "home",
                            "league": "pro-league-saudi",
                        },
                        {
                            "team": "Al-Kholood",
                            "opponent": "Al-Shabab",
                            "date": "2025-09-25",
                            "venue": "away",
                            "league": "pro-league-saudi",
                        },
                    ]
                )
            )

            summary = historical_import.main(
                [
                    "--manifest",
                    str(manifest),
                    "--output",
                    str(output),
                    "--preflight",
                    "--existing-keys",
                    str(existing),
                ]
            )

        self.assertEqual(summary["existing_natural_key_count"], 2)
        self.assertEqual(summary["new_team_perspective_row_count"], 0)
        mock_existing_keys.assert_not_called()

    @patch("src.historical_import.save_matches_to_supabase")
    @patch("src.historical_import.TheStatsAPIClient")
    def test_write_requires_exact_confirmation_before_constructing_client(
        self, mock_client, mock_save
    ):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            output = root / "summary.json"
            manifest.write_text(json.dumps([MANUAL_FIXTURE]))

            with self.assertRaisesRegex(historical_import.HistoricalImportError, "confirm-production-write"):
                historical_import.main(
                    ["--manifest", str(manifest), "--output", str(output), "--write"]
                )

        mock_client.assert_not_called()
        mock_save.assert_not_called()

    @patch("src.historical_import.supabase_request")
    def test_existing_key_preflight_paginates_with_cutoff_filter(self, mock_request):
        mock_request.side_effect = [
            (
                [
                    {
                        "team": "Home Team",
                        "opponent": "Away Team",
                        "date": "2026-08-09",
                        "venue": "home",
                        "league": "mls",
                    }
                ],
                None,
            ),
            ([], None),
        ]

        keys = historical_import.fetch_existing_match_keys(("mls",), page_size=1)

        self.assertEqual(
            keys,
            {("Home Team", "Away Team", "2026-08-09", "home", "mls")},
        )
        first_endpoint = mock_request.call_args_list[0].args[0]
        self.assertIn("league=in.(mls)", first_endpoint)
        self.assertIn("date=lt.2026-08-10", first_endpoint)
        self.assertIn("limit=1&offset=0", first_endpoint)
        self.assertIn("limit=1&offset=1", mock_request.call_args_list[1].args[0])

    @patch("src.historical_import.save_matches_to_supabase")
    @patch("src.historical_import.fetch_existing_match_keys")
    @patch("src.historical_import.TheStatsAPIClient")
    def test_confirmed_write_filters_existing_natural_keys_before_persistence(
        self, mock_client, mock_existing_keys, mock_save
    ):
        mock_existing_keys.return_value = {
            ("Al-Shabab", "Al-Kholood", "2025-09-25", "home", "pro-league-saudi"),
            ("Al-Kholood", "Al-Shabab", "2025-09-25", "away", "pro-league-saudi"),
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            output = root / "summary.json"
            manifest.write_text(json.dumps([MANUAL_FIXTURE]))

            summary = historical_import.main(
                [
                    "--manifest",
                    str(manifest),
                    "--output",
                    str(output),
                    "--write",
                    "--confirm-production-write",
                    historical_import.CONFIRMATION,
                ]
            )

        self.assertEqual(summary["existing_natural_key_count"], 2)
        self.assertEqual(summary["written_team_perspective_row_count"], 0)
        mock_client.assert_called_once_with()
        mock_save.assert_called_once_with([])


if __name__ == "__main__":
    unittest.main()
