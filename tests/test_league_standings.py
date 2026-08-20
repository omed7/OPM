import unittest

from src.compute.league_standings import build_standings_artifact
from src.validate_league_standings import validate


class TestLeagueStandingsArtifact(unittest.TestCase):
    def test_aggregates_signed_metrics_for_each_view_and_averages_combined_pa(self):
        matches = [
            {
                "team": "Home FC",
                "opponent": "Away FC",
                "date": "2026-08-15",
                "venue": "home",
                "league": "premier_league",
                "goals_for": 2,
                "goals_against": 2,
                "xg_for": 2.0,
                "xg_against": 2.0,
            }
        ]
        predictions = [
            {
                "home_team": "Home FC",
                "away_team": "Away FC",
                "date": "2026-08-15",
                "league": "premier_league",
                "home_expected_xg": 2.1,
                "away_expected_xg": 1.5,
                "home_expected_goals": 1.5,
                "away_expected_goals": 1.0,
            }
        ]

        artifact = build_standings_artifact(
            matches,
            predictions,
            {"premier_league": "Premier League"},
            version="test-version",
            generated_at="2026-08-16T00:00:00Z",
        )

        validate(artifact)
        season = artifact["leagues"][0]["seasons"][0]
        self.assertEqual(season["prediction_provenance"], "stored_pre_match")
        home = next(team for team in season["teams"] if team["name"] == "Home FC")
        away = next(team for team in season["teams"] if team["name"] == "Away FC")

        self.assertEqual(season["label"], "2026/27")
        self.assertEqual(home["matches_played"], 1)
        self.assertEqual(home["views"]["for"]["xg"], {
            "total": -0.1,
            "average": -0.1,
            "eligible_matches": 1,
        })
        self.assertEqual(home["views"]["against"]["xg"], {
            "total": 0.5,
            "average": 0.5,
            "eligible_matches": 1,
        })
        self.assertEqual(home["views"]["overall"]["xg"], {
            "total": 0.4,
            "average": 0.4,
            "eligible_matches": 1,
        })
        self.assertEqual(home["views"]["overall"]["goals"], {
            "total": 1.5,
            "average": 1.5,
            "eligible_matches": 1,
        })
        self.assertEqual(home["views"]["overall"]["xg_goals"], {
            "total": 0.95,
            "average": 0.95,
        })
        self.assertEqual(away["views"]["overall"]["xg"]["total"], 0.4)
        self.assertEqual(away["views"]["for"]["xg"]["total"], 0.5)
        self.assertEqual(away["views"]["against"]["xg"]["total"], -0.1)

    def test_keeps_historical_teams_and_matches_when_predictions_are_unavailable(self):
        matches = [
            {
                "team": "Historic Home",
                "opponent": "Historic Away",
                "date": "2025-08-15",
                "venue": "home",
                "league": "premier_league",
                "goals_for": 1,
                "goals_against": 0,
                "xg_for": 0.8,
                "xg_against": 0.3,
            },
            {
                "team": "Current Home",
                "opponent": "Current Away",
                "date": "2026-08-15",
                "venue": "home",
                "league": "premier_league",
                "goals_for": 1,
                "goals_against": 1,
                "xg_for": 1.1,
                "xg_against": 0.9,
            },
        ]
        predictions = [
            {
                "home_team": "Current Home",
                "away_team": "Current Away",
                "date": "2026-08-15",
                "league": "premier_league",
                "home_expected_xg": 1.0,
                "away_expected_xg": 1.0,
                "home_expected_goals": 1.0,
                "away_expected_goals": 1.0,
            }
        ]

        artifact = build_standings_artifact(
            matches,
            predictions,
            {"premier_league": "Premier League"},
            version="test-version",
            generated_at="2026-08-16T00:00:00Z",
        )

        seasons = artifact["leagues"][0]["seasons"]
        self.assertEqual([season["label"] for season in seasons], ["2026/27", "2025/26"])
        historic = seasons[1]["teams"]
        historic_home = next(team for team in historic if team["name"] == "Historic Home")
        self.assertEqual(historic_home["matches_played"], 1)
        self.assertIsNone(historic_home["views"]["overall"]["xg"])
        self.assertIsNone(historic_home["views"]["overall"]["goals"])
        self.assertIsNone(historic_home["views"]["overall"]["xg_goals"])

    def test_ignores_non_home_rows_in_the_team_perspective_storage_model(self):
        matches = [
            {
                "team": "Away FC",
                "opponent": "Home FC",
                "date": "2026-08-15",
                "venue": "away",
                "league": "premier_league",
                "goals_for": 1,
                "goals_against": 2,
                "xg_for": 1.0,
                "xg_against": 2.0,
            }
        ]

        artifact = build_standings_artifact(
            matches,
            [],
            {"premier_league": "Premier League"},
            version="test-version",
            generated_at="2026-08-16T00:00:00Z",
        )

        self.assertEqual(artifact["leagues"], [])

    def test_reconstructs_historical_pa_from_only_earlier_calendar_dates(self):
        def fixture(date, home, away, home_xg, away_xg, home_goals, away_goals):
            return {
                "team": home,
                "opponent": away,
                "date": date,
                "venue": "home",
                "league": "premier_league",
                "xg_for": home_xg,
                "xg_against": away_xg,
                "goals_for": home_goals,
                "goals_against": away_goals,
            }

        matches = [
            fixture("2021-08-01", "Alpha", "Alpha Home One", 1, 1, 1, 1),
            fixture("2021-08-01", "Beta", "Beta Home One", 4, 1, 4, 1),
            fixture("2021-08-02", "Alpha Away One", "Alpha", 1, 2, 1, 2),
            fixture("2021-08-02", "Beta Away One", "Beta", 1, 2, 1, 2),
            fixture("2021-08-03", "Alpha", "Alpha Home Two", 3, 1, 3, 1),
            fixture("2021-08-03", "Beta", "Beta Home Two", 4, 1, 4, 1),
            fixture("2021-08-04", "Alpha Away Two", "Alpha", 1, 4, 1, 4),
            fixture("2021-08-04", "Beta Away Two", "Beta", 1, 2, 1, 2),
            fixture("2021-08-05", "Same Day Host", "Beta", 99, 99, 9, 9),
            fixture("2021-08-05", "Alpha", "Beta", 2, 1, 2, 1),
        ]

        artifact = build_standings_artifact(
            matches,
            [],
            {"premier_league": "Premier League"},
            version="test-version",
            generated_at="2026-08-16T00:00:00Z",
        )

        season = artifact["leagues"][0]["seasons"][0]
        alpha = next(team for team in season["teams"] if team["name"] == "Alpha")
        self.assertEqual(season["prediction_provenance"], "reconstructed_historical")
        self.assertEqual(alpha["views"]["for"]["xg"], {
            "total": 0.25,
            "average": 0.25,
            "eligible_matches": 1,
        })
        self.assertEqual(alpha["views"]["against"]["xg"], {
            "total": -1.0,
            "average": -1.0,
            "eligible_matches": 1,
        })
        self.assertEqual(alpha["views"]["overall"]["xg"], {
            "total": -0.75,
            "average": -0.75,
            "eligible_matches": 1,
        })
        self.assertEqual(alpha["views"]["for"]["goals"], {
            "total": 0.25,
            "average": 0.25,
            "eligible_matches": 1,
        })


    def test_reconstructs_goals_pa_for_score_only_fixture_without_xg_or_combined_pa(self):
        def fixture(date, home, away, home_goals, away_goals, home_xg=1.0, away_xg=1.0):
            return {
                "team": home,
                "opponent": away,
                "date": date,
                "venue": "home",
                "league": "premier_league",
                "xg_for": home_xg,
                "xg_against": away_xg,
                "goals_for": home_goals,
                "goals_against": away_goals,
            }

        matches = [
            fixture("2026-08-01", "Alpha", "Alpha Home One", 2, 1),
            fixture("2026-08-01", "Beta", "Beta Home One", 1, 2),
            fixture("2026-08-02", "Alpha Away One", "Alpha", 1, 1),
            fixture("2026-08-02", "Beta Away One", "Beta", 1, 1),
            fixture("2026-08-03", "Alpha", "Alpha Home Two", 2, 1),
            fixture("2026-08-03", "Beta", "Beta Home Two", 3, 2),
            fixture("2026-08-04", "Alpha Away Two", "Alpha", 3, 2),
            fixture("2026-08-04", "Beta Away Two", "Beta", 3, 2),
            fixture("2026-08-05", "Alpha", "Beta", 2, 1, None, None),
            fixture("2026-08-06", "Alpha", "Beta", 2, 0, 2.1, 1.1),
        ]

        artifact = build_standings_artifact(
            matches,
            [],
            {"premier_league": "Premier League"},
            version="test-version",
            generated_at="2026-08-16T00:00:00Z",
        )

        validate(artifact)
        season = artifact["leagues"][0]["seasons"][0]
        alpha = next(team for team in season["teams"] if team["name"] == "Alpha")
        self.assertEqual(alpha["views"]["overall"]["xg"], {
            "total": 1.2,
            "average": 1.2,
            "eligible_matches": 1,
        })
        self.assertEqual(alpha["views"]["for"]["goals"], {
            "total": 0.125,
            "average": 0.0625,
            "eligible_matches": 2,
        })
        self.assertEqual(alpha["views"]["against"]["goals"], {
            "total": -2.25,
            "average": -1.125,
            "eligible_matches": 2,
        })
        self.assertEqual(alpha["views"]["overall"]["goals"], {
            "total": -2.125,
            "average": -1.0625,
            "eligible_matches": 2,
        })
        self.assertEqual(alpha["views"]["overall"]["xg_goals"], {
            "total": -0.2125,
            "average": -0.2125,
        })


if __name__ == "__main__":
    unittest.main()
