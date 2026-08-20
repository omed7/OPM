import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / 'public' / 'data.json'
MANIFEST_PATH = ROOT / 'public' / 'team_badges.json'
EXPECTED_UNMAPPED = {
    'la_liga': {
        'Deportivo La Coruna',
        'Elche',
        'Espanyol',
        'Levante',
        'Racing Santander',
        'Villarreal',
    },
}


class TeamBadgeManifestTests(unittest.TestCase):
    def test_current_fixture_teams_have_reviewed_badges_or_explicit_initials_fallback(self):
        data = json.loads(DATA_PATH.read_text(encoding='utf-8'))
        manifest = json.loads(MANIFEST_PATH.read_text(encoding='utf-8'))

        self.assertEqual(manifest['schema_version'], 1)
        self.assertEqual(manifest['source']['name'], 'TheSportsDB')
        self.assertEqual(manifest['source']['attribution'], 'Team badges: TheSportsDB')
        self.assertEqual(manifest['source']['url'], 'https://www.thesportsdb.com/')

        expected_teams = {}
        for league in data['leagues']:
            teams = {
                team
                for fixture in league.get('fixtures', [])
                for team in (fixture.get('home_team'), fixture.get('away_team'))
                if team
            }
            if teams:
                expected_teams[league['id']] = teams

        manifest_badges = manifest['badges']
        manifest_unmapped = {
            league_id: set(teams)
            for league_id, teams in manifest['unmapped'].items()
        }
        self.assertEqual(manifest_unmapped, EXPECTED_UNMAPPED)

        for league_id, teams in expected_teams.items():
            mapped_teams = set(manifest_badges.get(league_id, {}))
            self.assertEqual(mapped_teams | manifest_unmapped.get(league_id, set()), teams)
            self.assertFalse(mapped_teams & manifest_unmapped.get(league_id, set()))

            for team in mapped_teams:
                record = manifest_badges[league_id][team]
                self.assertTrue(record['provider_id'].isdigit())
                self.assertTrue(record['badge_url'].startswith('https://r2.thesportsdb.com/'))
                self.assertEqual(record['source_url'], f"https://www.thesportsdb.com/team/{record['provider_id']}")

        self.assertEqual(set(manifest_badges), set(expected_teams))


if __name__ == '__main__':
    unittest.main()
