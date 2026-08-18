import unittest

from src.compute.season_policy import (
    LEAGUE_SEASON_POLICIES,
    SeasonConfigurationError,
    filter_history_for_fixture,
    provider_season_label,
    season_start_date,
    validate_season_configuration,
)
from src.output_writer import ODDALERTS_LEAGUES, UNDERSTAT_LEAGUES


class TestSeasonPolicy(unittest.TestCase):
    def test_new_cross_year_season_filters_last_season_history(self):
        history = [
            {"date": "2026-05-18", "id": "last-season"},
            {"date": "2026-08-03", "id": "current-season"},
            {"date": "2026-08-20", "id": "future"},
        ]

        eligible = filter_history_for_fixture(
            history, "eredivisie", "2026-08-15"
        )

        self.assertEqual([record["id"] for record in eligible], ["current-season"])
        self.assertEqual(season_start_date("eredivisie", "2026-08-15"), "2026-07-01")

    def test_january_cross_year_fixture_keeps_same_season_previous_calendar_year(self):
        history = [
            {"date": "2026-05-18", "id": "previous-season"},
            {"date": "2026-07-20", "id": "same-season-start"},
            {"date": "2026-12-29", "id": "same-season-december"},
        ]

        eligible = filter_history_for_fixture(
            history, "premier_league", "2027-01-15"
        )

        self.assertEqual(
            [record["id"] for record in eligible],
            ["same-season-start", "same-season-december"],
        )
        self.assertEqual(season_start_date("premier_league", "2027-01-15"), "2026-07-01")

    def test_calendar_year_league_keeps_current_year_midseason_history(self):
        history = [
            {"date": "2025-11-01", "id": "previous-calendar-year"},
            {"date": "2026-03-16", "id": "current-season"},
            {"date": "2026-08-21", "id": "future"},
        ]

        eligible = filter_history_for_fixture(
            history, "eliteserien", "2026-08-15"
        )

        self.assertEqual([record["id"] for record in eligible], ["current-season"])
        self.assertEqual(season_start_date("eliteserien", "2026-08-15"), "2026-01-01")

    def test_split_year_league_uses_verified_july_boundary(self):
        history = [
            {"date": "2026-05-15", "id": "earlier-stage"},
            {"date": "2026-07-26", "id": "current-stage"},
        ]

        eligible = filter_history_for_fixture(
            history, "superliga-argentina", "2026-08-17"
        )

        self.assertEqual([record["id"] for record in eligible], ["current-stage"])
        self.assertEqual(season_start_date("superliga-argentina", "2026-08-17"), "2026-07-01")

    def test_understat_provider_label_uses_derived_start_year(self):
        self.assertEqual(provider_season_label("premier_league", "2026-08-15"), "2026")
        self.assertEqual(provider_season_label("premier_league", "2027-01-15"), "2026")
        self.assertEqual(provider_season_label("eliteserien", "2026-08-15"), "2026")

    def test_supported_league_registries_are_fully_covered(self):
        configured = set(LEAGUE_SEASON_POLICIES)
        supported = {league["id"] for league in ODDALERTS_LEAGUES}
        supported.update(league["output_id"] for league in UNDERSTAT_LEAGUES)

        self.assertEqual(configured, supported)

    def test_rejects_unknown_league_and_invalid_configuration(self):
        with self.assertRaises(SeasonConfigurationError):
            season_start_date("unknown-league", "2026-08-15")
        with self.assertRaises(SeasonConfigurationError):
            validate_season_configuration({"bad": {"season_start_month": 13}})


if __name__ == "__main__":
    unittest.main()
