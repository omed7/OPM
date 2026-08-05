import unittest
import sys
import os
from datetime import datetime

# Add src and root to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.fetch.oddalerts import resolve_oddalerts_dates, parse_recent_results

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

if __name__ == "__main__":
    unittest.main()
