import json
import unittest
from pathlib import Path

from src import team_badges


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "public" / "data.json"
MANIFEST_PATH = ROOT / "public" / "team_badges.json"


class TeamBadgeManifestTests(unittest.TestCase):
    def test_current_roster_manifest_has_valid_api_football_records(self):
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        team_badges.validate_badge_manifest(manifest)
        self.assertEqual(set(manifest["badges"]), set(team_badges.PROVIDER_LEAGUES))
        self.assertGreater(
            sum(len(league_badges) for league_badges in manifest["badges"].values()),
            0,
        )

    def test_fixture_coverage_is_reviewed_as_initials_fallback_not_a_failure(self):
        data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))

        unresolved = team_badges.badge_coverage(data["leagues"], manifest)
        self.assertIsInstance(unresolved, list)
        for item in unresolved:
            self.assertEqual(set(item), {"league", "team"})
            self.assertTrue(item["league"])
            self.assertTrue(item["team"])


if __name__ == "__main__":
    unittest.main()
