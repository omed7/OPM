import unittest

from src.fetch.oddalerts import parse_upcoming_fixtures


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


if __name__ == "__main__":
    unittest.main()
