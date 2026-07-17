from fetch.premier_league import get_team_matches
from compute.xg_formula import calculate_expected_xg

def verify():
    print("Fetching matches for Arsenal...")
    # Season 2023 for verification to ensure we have matches available to pull
    team_a_matches = get_team_matches("Arsenal", total_matches=4, season="2023")
    print("Arsenal matches:")
    for m in team_a_matches:
        print(f"  {m['date']} ({m['venue']}) vs {m['opponent']}: xG For: {m['xg_for']:.2f}, xG Against: {m['xg_against']:.2f}")

    print("\nFetching matches for Liverpool...")
    team_b_matches = get_team_matches("Liverpool", total_matches=4, season="2023")
    print("Liverpool matches:")
    for m in team_b_matches:
        print(f"  {m['date']} ({m['venue']}) vs {m['opponent']}: xG For: {m['xg_for']:.2f}, xG Against: {m['xg_against']:.2f}")

    print("\nCalculating expected xG...")
    result = calculate_expected_xg(team_a_matches, team_b_matches)

    print("\nResults:")
    print(f"Arsenal Expected xG: {result['team_a_expected_xg']:.2f}")
    print(f"Liverpool Expected xG: {result['team_b_expected_xg']:.2f}")

if __name__ == "__main__":
    verify()

from fetch.besta_deild import get_besta_deild_data
from compute.goals_formula import calculate_expected_goals
print("\nVerifying Besta deild karla...")
bd_data = get_besta_deild_data('2024')
if bd_data:
    fixture = bd_data[0]
    print(f"Fixture: {fixture['home_team']} vs {fixture['away_team']}")
    print("Home History:")
    for match in fixture['home_history']:
        print(f"  {match['date']} ({match['venue']}) vs {match['opponent']}: Goals For: {match['goals_for']}, Goals Against: {match['goals_against']}")
    print("Away History:")
    for match in fixture['away_history']:
        print(f"  {match['date']} ({match['venue']}) vs {match['opponent']}: Goals For: {match['goals_for']}, Goals Against: {match['goals_against']}")

    expected = calculate_expected_goals(fixture['home_history'], fixture['away_history'])
    print(f"\nResults:")
    print(f"{fixture['home_team']} Expected Goals: {expected['team_a_expected_goals']}")
    print(f"{fixture['away_team']} Expected Goals: {expected['team_b_expected_goals']}")
