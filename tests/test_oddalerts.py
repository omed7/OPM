import unittest

from src.fetch.oddalerts import (
    enrich_completed_results_with_timestamps,
    parse_upcoming_fixtures,
)


class TestUpcomingFixtureParsing(unittest.TestCase):
    def test_preserves_source_kickoff_time(self):
        html = '''
        <article class="competition-fixture">
          <div class="competition-fixture__time">Sat 16 Aug, 21:30</div>
          <div class="competition-fixture__team"><span>Home FC</span></div>
          <div class="competition-fixture__team"><span>Away FC</span></div>
        </article>
        '''

        fixtures = parse_upcoming_fixtures(html)

        self.assertEqual(len(fixtures), 1)
        self.assertEqual(fixtures[0]["home_team"], "Home FC")
        self.assertEqual(fixtures[0]["away_team"], "Away FC")
        self.assertEqual(fixtures[0]["kickoff_time"], "21:30")
        self.assertRegex(fixtures[0]["date"], r"^\d{4}-08-16$")


class TestCompletedResultTimestampEnrichment(unittest.TestCase):
    def embedded_payload(self, away_goals=0, upcoming_timestamp=1787517000):
        return f'''\
        <script>
        window.xgPageData = {{
          upcomingFixtures: [{{"date":"2026-08-23 20:30:00","timestamp":{upcoming_timestamp}}}],
          teamStats: {{
            "1": {{"id":1,"name":"Home FC","matches":[{{"fixture_id":9,"date":"2026-08-22 23:30:00","league_id":1,"opponent":"Away FC","opponent_id":2,"location":"home","goals_for":1,"goals_against":{away_goals},"xg":1.2,"xga":0.8}}]}},
            "2": {{"id":2,"name":"Away FC","matches":[{{"fixture_id":9,"date":"2026-08-22 23:30:00","league_id":1,"opponent":"Home FC","opponent_id":1,"location":"away","goals_for":{away_goals},"goals_against":1,"xg":0.8,"xga":1.2}}]}}
          }}
        }};
        </script>
        '''

    def result(self):
        return [{
            "home_team": "Home FC",
            "away_team": "Away FC",
            "home_xg": 1.2,
            "away_xg": 0.8,
            "score": "1 - 0",
            "date": "2026-08-22",
        }]

    def test_adds_canonical_utc_timestamp_from_verified_same_source_fixture(self):
        results = self.result()

        enrich_completed_results_with_timestamps(results, self.embedded_payload())

        self.assertEqual(results[0]["kickoff_at"], "2026-08-22T23:30:00Z")
        self.assertEqual(results[0]["date"], "2026-08-22")
        self.assertEqual(results[0]["score"], "1 - 0")
        self.assertEqual(results[0]["home_xg"], 1.2)
        self.assertEqual(results[0]["away_xg"], 0.8)

    def test_leaves_result_without_timestamp_when_source_copies_disagree(self):
        results = self.result()

        enrich_completed_results_with_timestamps(results, self.embedded_payload(away_goals=2))

        self.assertNotIn("kickoff_at", results[0])

    def test_leaves_result_without_timestamp_when_epoch_evidence_disagrees(self):
        results = self.result()

        enrich_completed_results_with_timestamps(results, self.embedded_payload(upcoming_timestamp=1787517001))

        self.assertNotIn("kickoff_at", results[0])


if __name__ == "__main__":
    unittest.main()
