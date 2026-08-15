import unittest
import sys
from unittest.mock import patch
import os
from datetime import datetime
from pathlib import Path

# Add src and root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.fetch.oddalerts import (
    parse_recent_results,
    parse_upcoming_fixtures,
    resolve_oddalerts_dates,
)

class TestPredictDates(unittest.TestCase):

    def test_resolve_oddalerts_dates_same_year(self):
        # When current date is Aug 1, 2026 and match dates are Jul 31, May 17, May 16
        current_dt = datetime(2026, 8, 1)
        dates = [
            (10, 'Fri, Jul 31'),
            (20, 'Sun, May 17'),
            (30, 'Sat, May 16')
        ]
        resolved = resolve_oddalerts_dates(dates, current_dt)
        self.assertEqual(resolved[10], '2026-07-31')
        self.assertEqual(resolved[20], '2026-05-17')
        self.assertEqual(resolved[30], '2026-05-16')

    def test_resolve_oddalerts_dates_cross_year_first_match_previous_year(self):
        # When current date is Jan 5, 2027 and most recent match is Dec 31
        current_dt = datetime(2027, 1, 5)
        dates = [
            (10, 'Wed, Dec 31'),
            (20, 'Tue, Dec 30')
        ]
        resolved = resolve_oddalerts_dates(dates, current_dt)
        self.assertEqual(resolved[10], '2026-12-31')
        self.assertEqual(resolved[20], '2026-12-30')

    def test_resolve_oddalerts_dates_cross_year_mid_sequence(self):
        # When current date is Feb 1, 2027 and match dates span Jan -> Dec
        current_dt = datetime(2027, 2, 1)
        dates = [
            (10, 'Sat, Jan 10'),
            (20, 'Sun, Jan 4'),
            (30, 'Wed, Dec 31'),
            (40, 'Tue, Dec 30')
        ]
        resolved = resolve_oddalerts_dates(dates, current_dt)
        self.assertEqual(resolved[10], '2027-01-10')
        self.assertEqual(resolved[20], '2027-01-04')
        self.assertEqual(resolved[30], '2026-12-31')
        self.assertEqual(resolved[40], '2026-12-30')

class TestOddAlertsUpcomingFixtures(unittest.TestCase):

    def test_parses_sanitized_live_markup_with_year_rollover_and_gameweek_filter(self):
        fixture_path = (
            Path(__file__).parent
            / "fixtures"
            / "oddalerts"
            / "upcoming_fixtures_trailing_whitespace.html"
        )
        html = fixture_path.read_text(encoding="utf-8")

        with patch("src.fetch.oddalerts.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 12, 28)
            mock_datetime.strptime.side_effect = datetime.strptime
            fixtures = parse_upcoming_fixtures(html)

        self.assertEqual(
            fixtures,
            [
                {
                    "home_team": "CF Montréal",
                    "away_team": "Home & Co",
                    "date": "2026-12-29",
                    "kickoff_time": "19:00",
                },
                {
                    "home_team": "Future United",
                    "away_team": "Away FC",
                    "date": "2027-01-01",
                    "kickoff_time": "20:00",
                },
            ],
        )

    def test_skips_unparseable_fixture_date_but_keeps_valid_fixture(self):
        html = """
        <article class="competition-fixture ">
            <div class="competition-fixture__time">Kick-off TBC</div>
            <div class="competition-fixture__team"><span>TBD Home</span></div>
            <div class="competition-fixture__team"><span>TBD Away</span></div>
        </article>
        <article class="competition-fixture ">
            <div class="competition-fixture__time">Tue 30 Dec, 20:00</div>
            <div class="competition-fixture__team"><span>Scheduled Home</span></div>
            <div class="competition-fixture__team"><span>Scheduled Away</span></div>
        </article>
        """

        with patch("src.fetch.oddalerts.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 12, 28)
            mock_datetime.strptime.side_effect = datetime.strptime
            fixtures = parse_upcoming_fixtures(html)

        self.assertEqual(
            fixtures,
            [
                {
                    "home_team": "Scheduled Home",
                    "away_team": "Scheduled Away",
                    "date": "2026-12-30",
                    "kickoff_time": "20:00",
                }
            ],
        )

    def test_returns_empty_for_empty_fixture_markup(self):
        self.assertEqual(parse_upcoming_fixtures("<main>No fixtures</main>"), [])


class TestOddAlertsRecentResults(unittest.TestCase):

    def test_skips_completed_result_with_missing_xg(self):
        fixture_path = (
            Path(__file__).parent
            / "fixtures"
            / "oddalerts"
            / "recent_results_missing_xg.html"
        )

        with patch("src.fetch.oddalerts.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 8, 17)
            results = parse_recent_results(fixture_path.read_text(encoding="utf-8"))

        self.assertEqual(
            results,
            [
                {
                    "home_team": "Valid Home",
                    "away_team": "Valid Away",
                    "home_xg": 1.25,
                    "away_xg": 0.75,
                    "score": "2 - 1",
                    "date": "2026-08-16",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
