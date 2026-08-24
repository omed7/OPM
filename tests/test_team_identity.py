import unittest

from src.compute.team_identity import canonical_team_name


class TestTeamIdentity(unittest.TestCase):
    def test_canonicalizes_reviewed_cross_provider_aliases(self):
        cases = (
            ("2-bundesliga", "1. FC Heidenheim", "FC Heidenheim"),
            ("2-bundesliga", "Heidenheim", "FC Heidenheim"),
            ("admiral-bundesliga", "Red Bull Salzburg", "Salzburg"),
            ("eerste-divisie", "Jong FC Utrecht Youth", "Jong FC Utrecht"),
            ("eliteserien", "Rosenborg BK", "Rosenborg"),
            ("eredivisie", "PSV Eindhoven", "PSV"),
            ("liga-mx", "Club América", "América"),
            ("liga-portugal", "Vitória SC", "Vitória Guimarães"),
            ("mls", "New York Red Bulls", "New York RB"),
            ("premiership", "Dundee FC", "Dundee"),
            ("pro-league-belgium", "Oud-Heverlee Leuven", "OH Leuven"),
            ("serie-a-brazil", "Red Bull Bragantino", "Bragantino"),
            ("superliga-denmark", "Odense Boldklub", "Odense BK"),
        )
        for league_id, provider_name, expected_name in cases:
            with self.subTest(league=league_id, provider_name=provider_name):
                self.assertEqual(
                    canonical_team_name(league_id, provider_name),
                    expected_name,
                )

    def test_preserves_unknown_name(self):
        self.assertEqual(
            canonical_team_name("mls", "Unreviewed Club"),
            "Unreviewed Club",
        )


if __name__ == "__main__":
    unittest.main()
