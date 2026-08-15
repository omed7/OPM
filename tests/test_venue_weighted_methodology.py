import json
import unittest
from pathlib import Path

from src.compute.methodology_config import validate_methodology_configuration
from src.compute.venue_weighted_methodology import (
    IncompleteHistoryError,
    MethodologyConfigurationError,
    calculate_fixture_expectation,
    validate_last_8_shares,
)


class TestVenueWeightedMethodology(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixture_path = (
            Path(__file__).parent
            / "fixtures"
            / "methodology"
            / "venue_weighted_baseline.json"
        )
        cls.baseline = json.loads(fixture_path.read_text(encoding="utf-8"))

    def assertPrediction(self, actual, expected):
        self.assertAlmostEqual(actual["home_expected"], expected["home_expected"], places=8)
        self.assertAlmostEqual(actual["away_expected"], expected["away_expected"], places=8)
        self.assertAlmostEqual(actual["combined_expected"], expected["combined_expected"], places=8)

    def test_main_last_4_xg_matches_independent_baseline(self):
        prediction = calculate_fixture_expectation(
            self.baseline["home_history"],
            self.baseline["away_history"],
            methodology="main_last_4",
            metric="xg",
        )

        self.assertPrediction(prediction, self.baseline["expected"]["main_last_4"]["xg"])

    def test_main_last_4_goals_matches_independent_baseline(self):
        prediction = calculate_fixture_expectation(
            self.baseline["home_history"],
            self.baseline["away_history"],
            methodology="main_last_4",
            metric="goals",
        )

        self.assertPrediction(prediction, self.baseline["expected"]["main_last_4"]["goals"])

    def test_last_8_xg_applies_70_30_inside_each_venue_group(self):
        prediction = calculate_fixture_expectation(
            self.baseline["home_history"],
            self.baseline["away_history"],
            methodology="last_8",
            metric="xg",
            recent_share=0.70,
            older_share=0.30,
        )

        self.assertPrediction(prediction, self.baseline["expected"]["last_8"]["xg"])

    def test_last_8_goals_uses_same_venue_group_weights(self):
        prediction = calculate_fixture_expectation(
            self.baseline["home_history"],
            self.baseline["away_history"],
            methodology="last_8",
            metric="goals",
            recent_share=0.70,
            older_share=0.30,
        )

        self.assertPrediction(prediction, self.baseline["expected"]["last_8"]["goals"])

    def test_last_8_accepts_changed_valid_percentages(self):
        prediction = calculate_fixture_expectation(
            self.baseline["home_history"],
            self.baseline["away_history"],
            methodology="last_8",
            metric="xg",
            recent_share=0.60,
            older_share=0.40,
        )

        self.assertAlmostEqual(prediction["home_expected"], 1.6375, places=8)
        self.assertAlmostEqual(prediction["away_expected"], 1.125, places=8)
        self.assertAlmostEqual(prediction["combined_expected"], 2.7625, places=8)

    def test_last_8_rejects_invalid_percentages(self):
        with self.assertRaises(MethodologyConfigurationError):
            validate_last_8_shares(0.70, 0.20)
        with self.assertRaises(MethodologyConfigurationError):
            validate_last_8_shares(-0.10, 1.10)

    def test_version_controlled_configuration_defaults_to_main_last_4(self):
        configuration = validate_methodology_configuration()

        self.assertEqual(configuration["active_methodology"], "main_last_4")
        self.assertEqual(configuration["recent_share"], 0.70)
        self.assertEqual(configuration["older_share"], 0.30)

        with self.assertRaises(MethodologyConfigurationError):
            validate_methodology_configuration(active_methodology="unsupported")

    def test_requires_complete_venue_balanced_history(self):
        incomplete_home_history = {
            "home": self.baseline["home_history"]["home"][:2],
            "away": self.baseline["home_history"]["away"][:1],
        }

        with self.assertRaises(IncompleteHistoryError):
            calculate_fixture_expectation(
                incomplete_home_history,
                self.baseline["away_history"],
                methodology="main_last_4",
                metric="xg",
            )


if __name__ == "__main__":
    unittest.main()
