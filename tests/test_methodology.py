import unittest
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.compute.methodology import (
    get_default_weights,
    normalize_weights,
    predict_fixture,
    compute_all_comparisons
)

class TestMethodologyEngine(unittest.TestCase):

    def test_default_weights_methodology_1(self):
        # Methodology 1: Equal weight, last 4
        weights = get_default_weights(methodology_id=1, num_matches=4)
        self.assertEqual(weights, [0.25, 0.25, 0.25, 0.25])

        # When count is fewer
        weights_fewer = get_default_weights(methodology_id=1, num_matches=2)
        self.assertEqual(weights_fewer, [0.5, 0.5])

    def test_default_weights_methodology_2(self):
        # Methodology 2: 70% collectively across most recent 4 (0.175 each)
        # 30% collectively across older matches (0.30 / 4 = 0.075 each)
        weights = get_default_weights(methodology_id=2, num_matches=8)
        self.assertEqual(len(weights), 8)
        self.assertEqual(weights[:4], [0.175, 0.175, 0.175, 0.175])
        self.assertEqual(weights[4:], [0.075, 0.075, 0.075, 0.075])
        self.assertAlmostEqual(sum(weights), 1.0)

        # Methodology 2 with fewer than 4 matches gets equal weights
        weights_fewer = get_default_weights(methodology_id=2, num_matches=3)
        self.assertEqual(weights_fewer, [1.0/3.0, 1.0/3.0, 1.0/3.0])

    def test_proportional_redistribution_single_override_m2(self):
        # Default weights: [0.175, 0.175, 0.175, 0.175, 0.075, 0.075, 0.075, 0.075]
        # Override index 0 to 0.35 in Tier 1.
        # Remaining target weight for Tier 1 = 0.70 - 0.35 = 0.35.
        # Unoverridden indices in Tier 1: 1, 2, 3. Sum of their defaults: 0.175 * 3 = 0.525.
        # Each gets (0.175 / 0.525) * 0.35 = 0.116666...
        defaults = get_default_weights(methodology_id=2, num_matches=8)
        normalized = normalize_weights(8, defaults, {0: 0.35}, methodology_id=2)

        self.assertAlmostEqual(normalized[0], 0.35)
        self.assertAlmostEqual(normalized[1], 0.11666666666666667)
        self.assertAlmostEqual(normalized[2], 0.11666666666666667)
        self.assertAlmostEqual(normalized[3], 0.11666666666666667)

        # Tier 2 is completely untouched
        self.assertEqual(normalized[4:], [0.075, 0.075, 0.075, 0.075])
        self.assertAlmostEqual(sum(normalized), 1.0)

    def test_proportional_redistribution_deletion_m2(self):
        # Override index 0 to 0 (deleted) in Tier 1.
        # Remaining target weight = 0.70.
        # Unoverridden in Tier 1: 1, 2, 3.
        # Each gets (0.175 / 0.525) * 0.70 = 0.233333...
        defaults = get_default_weights(methodology_id=2, num_matches=8)
        normalized = normalize_weights(8, defaults, {0: 0.0}, methodology_id=2)

        self.assertAlmostEqual(normalized[0], 0.0)
        self.assertAlmostEqual(normalized[1], 0.2333333333333333)
        self.assertAlmostEqual(normalized[2], 0.2333333333333333)
        self.assertAlmostEqual(normalized[3], 0.2333333333333333)

        # Tier 2 is untouched
        self.assertEqual(normalized[4:], [0.075, 0.075, 0.075, 0.075])
        self.assertAlmostEqual(sum(normalized), 1.0)

    def test_proportional_redistribution_multiple_overrides_m2(self):
        # Override index 0 to 0.35, index 1 to 0.10.
        # Remaining target weight = 0.70 - 0.45 = 0.25.
        # Unoverridden in Tier 1: 2, 3. Sum of defaults = 0.35.
        # Each gets (0.175 / 0.35) * 0.25 = 0.125.
        defaults = get_default_weights(methodology_id=2, num_matches=8)
        normalized = normalize_weights(8, defaults, {0: 0.35, 1: 0.10}, methodology_id=2)

        self.assertAlmostEqual(normalized[0], 0.35)
        self.assertAlmostEqual(normalized[1], 0.10)
        self.assertAlmostEqual(normalized[2], 0.125)
        self.assertAlmostEqual(normalized[3], 0.125)
        self.assertAlmostEqual(sum(normalized), 1.0)

    def test_overrides_exceeding_target_weight_m2(self):
        # Override index 0 to 0.80. This exceeds Tier 1 target total (0.70).
        # Unoverridden matches in Tier 1 get 0.0.
        # Overridden match index 0 scaled down to 0.70.
        defaults = get_default_weights(methodology_id=2, num_matches=8)
        normalized = normalize_weights(8, defaults, {0: 0.80}, methodology_id=2)

        self.assertAlmostEqual(normalized[0], 0.70)
        self.assertEqual(normalized[1:4], [0.0, 0.0, 0.0])
        self.assertAlmostEqual(sum(normalized), 1.0)

    def test_predict_fixture_basic(self):
        # Create a mock database
        db = [
            {"team": "A", "opponent": "B", "date": "2026-05-01", "venue": "home", "goals_for": 2, "goals_against": 1, "xg_for": 2.5, "xg_against": 1.5, "league": "mls"},
            {"team": "A", "opponent": "C", "date": "2026-04-15", "venue": "home", "goals_for": 1, "goals_against": 0, "xg_for": 1.5, "xg_against": 0.5, "league": "mls"},
            {"team": "A", "opponent": "D", "date": "2026-04-01", "venue": "away", "goals_for": 3, "goals_against": 1, "xg_for": 3.5, "xg_against": 1.1, "league": "mls"},
            {"team": "A", "opponent": "E", "date": "2026-03-15", "venue": "away", "goals_for": 0, "goals_against": 2, "xg_for": 0.5, "xg_against": 2.2, "league": "mls"},

            {"team": "B", "opponent": "A", "date": "2026-05-01", "venue": "away", "goals_for": 1, "goals_against": 2, "xg_for": 1.5, "xg_against": 2.5, "league": "mls"},
            {"team": "B", "opponent": "F", "date": "2026-04-20", "venue": "home", "goals_for": 4, "goals_against": 2, "xg_for": 2.2, "xg_against": 1.8, "league": "mls"},
            {"team": "B", "opponent": "G", "date": "2026-04-10", "venue": "home", "goals_for": 0, "goals_against": 0, "xg_for": 0.8, "xg_against": 0.8, "league": "mls"},
            {"team": "B", "opponent": "H", "date": "2026-03-30", "venue": "away", "goals_for": 2, "goals_against": 3, "xg_for": 1.9, "xg_against": 2.1, "league": "mls"},
        ]

        # Methodology 1: last 2 home + 2 away
        # Team A Home: 2026-05-01 (xg_for: 2.5, xg_against: 1.5), 2026-04-15 (xg_for: 1.5, xg_against: 0.5)
        # Team A Away: 2026-04-01 (xg_for: 3.5, xg_against: 1.1), 2026-03-15 (xg_for: 0.5, xg_against: 2.2)
        # Team A chosen matches: all 4 are the 2 home and 2 away.
        # Equal weights = [0.25, 0.25, 0.25, 0.25]
        # Team A average xg_for = (2.5 + 1.5 + 3.5 + 0.5) / 4 = 2.0
        # Team A average xg_against = (1.5 + 0.5 + 1.1 + 2.2) / 4 = 1.325

        # Team B Home: 2026-04-20 (xg_for: 2.2, xg_against: 1.8), 2026-04-10 (xg_for: 0.8, xg_against: 0.8)
        # Team B Away: 2026-05-01 (xg_for: 1.5, xg_against: 2.5), 2026-03-30 (xg_for: 1.9, xg_against: 2.1)
        # Team B average xg_for = (2.2 + 0.8 + 1.5 + 1.9) / 4 = 1.6
        # Team B average xg_against = (1.8 + 0.8 + 2.5 + 2.1) / 4 = 1.8

        # Expected A = (2.0 + 1.8) / 2 = 1.9
        # Expected B = (1.6 + 1.325) / 2 = 1.4625

        pred = predict_fixture(db, "A", "B", "mls", methodology_id=1, metric="xg")
        self.assertAlmostEqual(pred["home_expected"], 1.9)
        self.assertAlmostEqual(pred["away_expected"], 1.4625)

if __name__ == '__main__':
    unittest.main()
