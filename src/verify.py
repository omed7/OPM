import os
from fetch.understat_common import get_team_matches, get_current_season
from compute.xg_formula import calculate_expected_xg

def verify():
    # Let's verify each of the 5 leagues on historical data to confirm they work
    season = "2024"  # Use a completed season to ensure data is populated on Understat
    print(f"--- Verifying Understat Integration for season {season} ---")

    leagues_to_test = [
        {"code": "EPL", "team1": "Arsenal", "team2": "Liverpool"},
        {"code": "La_Liga", "team1": "Real Madrid", "team2": "Barcelona"},
        {"code": "Serie_A", "team1": "Juventus", "team2": "AC Milan"},
        {"code": "Bundesliga", "team1": "Bayern Munich", "team2": "Borussia Dortmund"},
        {"code": "Ligue_1", "team1": "Paris Saint Germain", "team2": "Monaco"},
    ]

    for item in leagues_to_test:
        code = item["code"]
        team1 = item["team1"]
        team2 = item["team2"]
        print(f"\nTesting League: {code}")
        try:
            print(f"Fetching matches for {team1}...")
            team1_matches = get_team_matches(code, team1, total_matches=4, season=season)
            print(f"Found {len(team1_matches)} matches.")
            for m in team1_matches[:2]:
                print(f"  {m['date']} ({m['venue']}) vs {m['opponent']}: xG For: {m['xg_for']:.2f}, xG Against: {m['xg_against']:.2f}")

            print(f"Fetching matches for {team2}...")
            team2_matches = get_team_matches(code, team2, total_matches=4, season=season)
            print(f"Found {len(team2_matches)} matches.")
            for m in team2_matches[:2]:
                print(f"  {m['date']} ({m['venue']}) vs {m['opponent']}: xG For: {m['xg_for']:.2f}, xG Against: {m['xg_against']:.2f}")

            print("Calculating expected xG...")
            result = calculate_expected_xg(team1_matches, team2_matches)
            print(f"Results: {team1} expected xG: {result['team_a_expected_xg']:.2f}, {team2} expected xG: {result['team_b_expected_xg']:.2f}")
        except Exception as e:
            print(f"Verification failed for league {code}: {e}")

if __name__ == "__main__":
    verify()
