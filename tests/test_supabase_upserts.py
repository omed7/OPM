import json
import os
import unittest
from unittest.mock import MagicMock, patch

from src import output_writer


class TestSupabaseUpserts(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
