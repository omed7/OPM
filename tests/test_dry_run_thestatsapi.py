import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import dry_run_thestatsapi


class TestDryRunCommand(unittest.TestCase):
    @patch("src.dry_run_thestatsapi.build_coverage_report")
    @patch("src.dry_run_thestatsapi.TheStatsAPIClient")
    def test_writes_explicit_non_public_report(self, mock_client, mock_report):
        mock_report.return_value = {"mode": "dry_run", "leagues": []}
        with tempfile.TemporaryDirectory() as temp_directory:
            output = Path(temp_directory) / "coverage.json"
            dry_run_thestatsapi.main(["--leagues", "mls", "--output", str(output)])

            self.assertEqual(json.loads(output.read_text()), mock_report.return_value)
        mock_client.assert_called_once_with()
        mock_report.assert_called_once()
        self.assertEqual(mock_report.call_args.kwargs["league_ids"], ("mls",))

    @patch("src.dry_run_thestatsapi.build_coverage_report")
    @patch("src.dry_run_thestatsapi.TheStatsAPIClient")
    def test_rejects_public_artifact_path_before_constructing_client(
        self, mock_client, mock_report
    ):
        with self.assertRaises(ValueError):
            dry_run_thestatsapi.main(["--output", "public/coverage.json"])

        mock_client.assert_not_called()
        mock_report.assert_not_called()


if __name__ == "__main__":
    unittest.main()
