import io
import json
import math
import urllib.error
import unittest
from unittest.mock import patch

from src.compute.source_boundary import (
    RETAINED_ODDALERTS_LEAGUES,
    accepts_provider_record,
    provider_for_historical_date,
)
from src import output_writer
from src.fetch.thestatsapi import (
    THESTATSAPI_COMPETITIONS,
    TheStatsAPIClient,
    TheStatsAPIError,
    build_coverage_report,
    coverage_for_season,
    match_xg,
)


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class TestSourceBoundary(unittest.TestCase):
    def test_retained_registry_matches_provider_mapping(self):
        self.assertEqual(set(THESTATSAPI_COMPETITIONS), RETAINED_ODDALERTS_LEAGUES)

    def test_pre_cutoff_accepts_only_thestatsapi(self):
        self.assertEqual(
            provider_for_historical_date("mls", "2026-08-09"), "thestatsapi"
        )
        self.assertTrue(accepts_provider_record("thestatsapi", "mls", "2026-08-09"))
        self.assertFalse(accepts_provider_record("oddalerts", "mls", "2026-08-09"))

    def test_cutoff_and_later_accept_only_oddalerts(self):
        for match_date in ("2026-08-10", "2026-08-11"):
            self.assertEqual(
                provider_for_historical_date("mls", match_date), "oddalerts"
            )
            self.assertTrue(accepts_provider_record("oddalerts", "mls", match_date))
            self.assertFalse(accepts_provider_record("thestatsapi", "mls", match_date))

    def test_understat_league_has_no_boundary_override(self):
        self.assertIsNone(provider_for_historical_date("premier_league", "2026-08-09"))


class TestOddAlertsBoundaryIntegration(unittest.TestCase):
    def test_mapper_rejects_pre_cutoff_oddalerts_and_keeps_cutoff_day(self):
        records = output_writer.map_oddalerts_to_db(
            [
                {
                    "home_team": "Before Home",
                    "away_team": "Before Away",
                    "date": "2026-08-09",
                    "score": "1 - 0",
                    "home_xg": 1.2,
                    "away_xg": 0.7,
                },
                {
                    "home_team": "Cutoff Home",
                    "away_team": "Cutoff Away",
                    "date": "2026-08-10",
                    "score": "2 - 1",
                    "home_xg": 1.8,
                    "away_xg": 0.9,
                },
            ],
            "mls",
        )

        self.assertEqual(len(records), 2)
        self.assertEqual({record["date"] for record in records}, {"2026-08-10"})
        self.assertEqual({record["source"] for record in records}, {"oddalerts"})


class TestTheStatsAPIClient(unittest.TestCase):
    def test_paginates_finished_matches_with_documented_parameters(self):
        responses = iter(
            [
                {
                    "data": [{"id": "first"}],
                    "meta": {"page": 1, "total_pages": 2},
                },
                {
                    "data": [{"id": "second"}],
                    "meta": {"page": 2, "total_pages": 2},
                },
            ]
        )
        seen_urls = []

        def opener(request, timeout):
            seen_urls.append(request.full_url)
            return FakeResponse(next(responses))

        client = TheStatsAPIClient(api_key="test-key", opener=opener, sleep=lambda _: None)
        matches = client.get_finished_matches("comp_test", "sn_test")

        self.assertEqual([item["id"] for item in matches], ["first", "second"])
        self.assertIn("competition_id=comp_test", seen_urls[0])
        self.assertIn("season_id=sn_test", seen_urls[0])
        self.assertIn("status=finished", seen_urls[0])
        self.assertIn("page=2", seen_urls[1])

    def test_sends_descriptive_user_agent(self):
        seen_headers = {}

        def opener(request, timeout):
            seen_headers.update(dict(request.header_items()))
            return FakeResponse({"data": [], "meta": {}})

        client = TheStatsAPIClient(api_key="test-key", opener=opener, sleep=lambda _: None)
        client.get("/football/competitions")

        self.assertEqual(seen_headers["User-agent"], "OPM historical dry-run/1.0")

    def test_retries_rate_limited_request_then_returns_data(self):
        rate_limit = urllib.error.HTTPError(
            "https://api.thestatsapi.com/api/football/competitions",
            429,
            "Too Many Requests",
            {},
            io.BytesIO(b"rate limited"),
        )
        responses = iter([rate_limit, {"data": [], "meta": {}}])
        sleeps = []

        def opener(_request, timeout):
            result = next(responses)
            if isinstance(result, Exception):
                raise result
            return FakeResponse(result)

        client = TheStatsAPIClient(
            api_key="test-key",
            opener=opener,
            sleep=sleeps.append,
            request_interval_seconds=0.25,
        )

        self.assertEqual(client.get("/football/competitions"), {"data": [], "meta": {}})
        self.assertEqual(sleeps, [15, 0.25])

    def test_extracts_finite_expected_goals(self):
        stats = {
            "overview": {
                "expected_goals": {"all": {"home": 1.25, "away": 0.75}}
            }
        }
        self.assertEqual(match_xg(stats), (1.25, 0.75))

    def test_rejects_non_finite_expected_goals(self):
        stats = {
            "overview": {
                "expected_goals": {"all": {"home": math.nan, "away": 0.75}}
            }
        }
        with self.assertRaises(TheStatsAPIError):
            match_xg(stats)

    def test_build_report_accepts_a_selected_retained_league(self):
        class ReportClient:
            def resolve_competition(self, name, country):
                return {"id": "comp_test", "name": name, "country": country}

            def get_seasons(self, _competition_id):
                return []

        report = build_coverage_report(ReportClient(), league_ids=("mls",))

        self.assertEqual(report["requested_leagues"], ["mls"])
        self.assertEqual([league["league"] for league in report["leagues"]], ["mls"])

    def test_build_report_rejects_unknown_selected_league(self):
        with self.assertRaises(TheStatsAPIError):
            build_coverage_report(object(), league_ids=("not-a-league",))

    def test_coverage_counts_pre_cutoff_candidates_without_fetching_stats(self):
        class CoverageClient:
            def get_finished_matches(self, _competition_id, _season_id):
                return [
                    {"utc_date": "2026-08-09T12:00:00Z", "xg_available": True},
                    {"utc_date": "2026-08-09T14:00:00Z", "xg_available": False},
                    {"utc_date": "2026-08-10T12:00:00Z", "xg_available": True},
                    {"utc_date": "not-a-date", "xg_available": True},
                ]

        report = coverage_for_season(
            CoverageClient(),
            "mls",
            {"id": "comp_test", "name": "MLS"},
            {"id": "sn_test", "name": "MLS 2026"},
        )

        self.assertEqual(report["finished_matches"], 4)
        self.assertEqual(report["before_cutoff"], 2)
        self.assertEqual(report["xg_candidates"], 1)
        self.assertEqual(report["xg_unavailable"], 1)
        self.assertEqual(report["post_cutoff_excluded"], 1)
        self.assertEqual(report["invalid_date"], 1)


if __name__ == "__main__":
    unittest.main()
