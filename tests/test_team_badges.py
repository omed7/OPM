import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import team_badges


LA_LIGA = {"espn_slug": "esp.1"}


def provider_team(team_id, name):
    return {
        "id": str(team_id),
        "displayName": name,
        "logos": [
            {
                "href": f"https://a.espncdn.com/i/teamlogos/soccer/500/{team_id}.png",
                "rel": ["full", "default"],
            }
        ],
    }


def provider_payload(*teams):
    return {"sports": [{"leagues": [{"teams": [{"team": team} for team in teams]}]}]}


def source_metadata():
    return {
        "name": team_badges.ESPN_SOURCE_NAME,
        "url": team_badges.ESPN_SOURCE_URL,
        "attribution": team_badges.ESPN_ATTRIBUTION,
        "reviewed_at": "2026-08-20",
    }


class TeamBadgeTests(unittest.TestCase):
    def test_normalizes_accents_without_fuzzy_matching(self):
        self.assertEqual(
            team_badges.normalize_team_name("Atlético Madrid"),
            team_badges.normalize_team_name("Atletico Madrid"),
        )
        self.assertNotEqual(
            team_badges.normalize_team_name("Atletico Madrid"),
            team_badges.normalize_team_name("Atletico San Luis"),
        )

    def test_fetches_current_roster_from_the_configured_league_feed(self):
        observed = {}

        def payload_fetcher(url):
            observed["url"] = url
            return provider_payload(provider_team(530, "Atlético Madrid")), None

        records, error = team_badges.fetch_provider_league_teams(
            LA_LIGA, payload_fetcher=payload_fetcher
        )

        self.assertIsNone(error)
        self.assertEqual(records, [provider_team(530, "Atlético Madrid")])
        self.assertEqual(
            observed["url"],
            "https://site.api.espn.com/apis/site/v2/sports/soccer/esp.1/teams",
        )

    def test_provider_failure_is_returned_as_non_blocking_data(self):
        records, error = team_badges.fetch_provider_league_teams(
            LA_LIGA,
            payload_fetcher=lambda _url: (None, "network unavailable"),
        )

        self.assertEqual(records, [])
        self.assertEqual(error, "network unavailable")

    def test_builds_current_roster_records_and_marks_unmatched_fixture_for_initials(self):
        leagues = [
            {
                "id": "la_liga",
                "fixtures": [{"home_team": "Atletico Madrid", "away_team": "Unknown FC"}],
            }
        ]
        with patch.dict(team_badges.PROVIDER_LEAGUES, {"la_liga": LA_LIGA}, clear=True):
            manifest, report = team_badges.build_bootstrap_manifest(
                {},
                leagues,
                roster_fetcher=lambda _league: ([provider_team(530, "Atlético Madrid")], None),
                generated_at="2026-08-20",
            )

        team_badges.validate_badge_manifest(manifest)
        record = manifest["badges"]["la_liga"]["Atlético Madrid"]
        self.assertEqual(record["provider_id"], "530")
        self.assertEqual(
            record["badge_url"], "https://a.espncdn.com/i/teamlogos/soccer/500/530.png"
        )
        self.assertEqual(record["mapping_method"], "espn_current_roster")
        self.assertEqual(manifest["unmapped"], {"la_liga": ["Unknown FC"]})
        self.assertIn(
            {"league": "la_liga", "team": "Unknown FC", "reason": "no_current_roster_match"},
            report["pending"],
        )
        self.assertIsNotNone(
            team_badges.resolve_manifest_badge(manifest["badges"]["la_liga"], "Atletico Madrid")
        )

    def test_rejects_ambiguous_normalized_provider_names(self):
        leagues = [{"id": "la_liga", "fixtures": [{"home_team": "Malaga", "away_team": "Other FC"}]}]
        with patch.dict(team_badges.PROVIDER_LEAGUES, {"la_liga": LA_LIGA}, clear=True):
            manifest, report = team_badges.build_bootstrap_manifest(
                {},
                leagues,
                roster_fetcher=lambda _league: (
                    [provider_team(529, "Málaga"), provider_team(999, "Malaga")],
                    None,
                ),
                generated_at="2026-08-20",
            )

        self.assertNotIn("la_liga", manifest["badges"])
        self.assertEqual(manifest["unmapped"], {"la_liga": ["Malaga", "Other FC"]})
        self.assertEqual(
            [item for item in report["pending"] if item["reason"] == "ambiguous_provider_roster_name"],
            [
                {"league": "la_liga", "team": "Málaga", "reason": "ambiguous_provider_roster_name"},
                {"league": "la_liga", "team": "Malaga", "reason": "ambiguous_provider_roster_name"},
            ],
        )

    def test_validates_manifest_and_rejects_incorrect_provider_url(self):
        manifest = {
            "schema_version": 1,
            "source": source_metadata(),
            "badges": {
                "la_liga": {
                    "Atlético Madrid": {
                        "provider_id": "530",
                        "provider_name": "Atlético Madrid",
                        "provider_league": "esp.1",
                        "badge_url": "https://a.espncdn.com/i/teamlogos/soccer/500/530.png",
                        "source_url": "https://www.espn.com/soccer/teams/_/league/esp.1",
                        "mapping_method": "espn_current_roster",
                    }
                }
            },
            "unmapped": {},
        }
        team_badges.validate_badge_manifest(manifest)
        manifest["badges"]["la_liga"]["Atlético Madrid"]["badge_url"] = "https://wrong/530.png"
        with self.assertRaisesRegex(ValueError, "badge URL is invalid"):
            team_badges.validate_badge_manifest(manifest)

    def test_coverage_and_warning_are_non_blocking_for_new_fixture_team(self):
        manifest = {"schema_version": 1, "source": source_metadata(), "badges": {}, "unmapped": {}}
        leagues = [{"id": "la_liga", "fixtures": [{"home_team": "Unknown FC", "away_team": "Other FC"}]}]

        unresolved = team_badges.badge_coverage(leagues, manifest)
        self.assertEqual(
            unresolved,
            [
                {"league": "la_liga", "team": "Other FC"},
                {"league": "la_liga", "team": "Unknown FC"},
            ],
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            summary_path = Path(temporary_directory) / "summary.md"
            with patch.dict("os.environ", {"GITHUB_STEP_SUMMARY": str(summary_path)}):
                with patch("builtins.print") as print_mock:
                    team_badges.print_coverage_summary(unresolved)
            summary = summary_path.read_text(encoding="utf-8")

        print_mock.assert_called_once_with(
            "::warning title=Badge initials fallback::la_liga:Other FC, la_liga:Unknown FC"
        )
        self.assertIn("Unknown FC", summary)

    def test_write_manifest_keeps_published_json_valid(self):
        manifest = {"schema_version": 1, "source": source_metadata(), "badges": {}, "unmapped": {}}
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "team_badges.json"
            team_badges.write_manifest(path, manifest)
            persisted = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(persisted, manifest)


if __name__ == "__main__":
    unittest.main()
