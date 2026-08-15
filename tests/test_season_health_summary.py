import unittest
from unittest.mock import patch

from src import output_writer


class TestSeasonHealthSummary(unittest.TestCase):
    def test_reports_filtering_and_insufficient_current_season_history(self):
        results = [
            {
                "provider": "oddalerts_history",
                "league": "eredivisie",
                "status": "prior_season_history_filtered",
                "detail": "4 records",
            },
            {
                "provider": "understat_history",
                "league": "premier_league",
                "status": "current_season_history_insufficient",
                "detail": "Home FC vs Away FC: Expected 2 home matches, found 1.",
            },
        ]

        with patch("builtins.print") as mock_print:
            output_writer.print_source_health_summary(results)

        lines = [call.args[0] for call in mock_print.call_args_list]
        self.assertIn(
            "Season history: oddalerts_history eredivisie prior_season_history_filtered: 4 records",
            lines,
        )
        self.assertIn(
            "Season history: understat_history premier_league current_season_history_insufficient: Home FC vs Away FC: Expected 2 home matches, found 1.",
            lines,
        )


if __name__ == "__main__":
    unittest.main()
