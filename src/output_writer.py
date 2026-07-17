import os
import json
import subprocess
from datetime import datetime, timezone

from fetch.premier_league import get_upcoming_fixtures, get_team_matches, get_current_season
from compute.xg_formula import calculate_expected_xg, SAMPLE_SIZE as XG_SAMPLE_SIZE
from fetch.besta_deild import get_besta_deild_data
from compute.goals_formula import calculate_expected_goals, SAMPLE_SIZE as GOALS_SAMPLE_SIZE

def get_version():
    sha = os.environ.get('GITHUB_SHA')
    if sha:
        return sha[:7]
    try:
        # Try to get the short commit SHA from git
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], stderr=subprocess.STDOUT).decode('ascii').strip()
    except Exception:
        return "local"

def process_premier_league():
    season = os.environ.get('SEASON', get_current_season())
    print(f"Fetching upcoming Premier League fixtures for season {season}...")

    try:
        fixtures = get_upcoming_fixtures(season=season)
    except Exception as e:
        print(f"Error fetching upcoming fixtures: {e}")
        fixtures = []

    if not fixtures:
        print("No upcoming Premier League fixtures found.")

    output_fixtures = []

    for fixture in fixtures:
        home_team = fixture['home_team']
        away_team = fixture['away_team']
        print(f"Processing PL: {home_team} vs {away_team}...")

        try:
            # Fetch last N matches for each team
            home_matches = get_team_matches(home_team, total_matches=XG_SAMPLE_SIZE, season=season)
            away_matches = get_team_matches(away_team, total_matches=XG_SAMPLE_SIZE, season=season)

            # Format dates to YYYY-MM-DD as per schema
            for m in home_matches:
                if ' ' in m['date']:
                    m['date'] = m['date'].split(' ')[0]
            for m in away_matches:
                if ' ' in m['date']:
                    m['date'] = m['date'].split(' ')[0]

            # Calculate expected xG using existing compute module
            stats = calculate_expected_xg(home_matches, away_matches)

            # Assemble fixture data
            output_fixtures.append({
                "home_team": home_team,
                "away_team": away_team,
                "date": fixture['date'],
                "combined_expected_xg": round(stats['team_a_expected_xg'] + stats['team_b_expected_xg'], 2),
                "home_expected_xg": round(stats['team_a_expected_xg'], 2),
                "away_expected_xg": round(stats['team_b_expected_xg'], 2),
                f"home_last_{XG_SAMPLE_SIZE}_matches": home_matches,
                f"away_last_{XG_SAMPLE_SIZE}_matches": away_matches
            })
        except Exception as e:
            print(f"Error processing PL fixture {home_team} vs {away_team}: {e}")

    return {
        "id": "premier_league",
        "name": "Premier League",
        "metric": "xg",
        "fixtures": output_fixtures
    }

def process_besta_deild():
    print("Fetching Besta deild karla fixtures...")
    season = "2026"  # Per requirements

    try:
        fixtures = get_besta_deild_data(season=season, total_matches=GOALS_SAMPLE_SIZE)
    except Exception as e:
        print(f"Error fetching Besta deild karla fixtures: {e}")
        fixtures = []

    if not fixtures:
        print("No upcoming Besta deild karla fixtures found.")

    output_fixtures = []

    for fixture in fixtures:
        home_team = fixture['home_team']
        away_team = fixture['away_team']
        print(f"Processing Besta deild: {home_team} vs {away_team}...")

        try:
            home_matches = fixture['home_history']
            away_matches = fixture['away_history']

            stats = calculate_expected_goals(home_matches, away_matches)

            # Use identical variable names as the old `xg` schema for the frontend (the prompt said we can optionally keep it if we want less diff)
            # Actually, the prompt says:
            # "generalize the xg-specific field names to metric-neutral ones ... if that keeps things clean, otherwise keep xg/goals-specific names per league, whichever keeps the diff smaller — your call."
            # We will use expected_xg to not break the frontend immediately, or expected_goals but then frontend breaks.
            # I will use expected_goals to make the JSON semantically correct, as the task says "don't touch the frontend... separate follow-up".

            output_fixtures.append({
                "home_team": home_team,
                "away_team": away_team,
                "date": fixture['date'],
                "combined_expected_goals": round(stats['team_a_expected_goals'] + stats['team_b_expected_goals'], 2),
                "home_expected_goals": round(stats['team_a_expected_goals'], 2),
                "away_expected_goals": round(stats['team_b_expected_goals'], 2),
                f"home_last_{GOALS_SAMPLE_SIZE}_matches": home_matches,
                f"away_last_{GOALS_SAMPLE_SIZE}_matches": away_matches
            })
        except Exception as e:
            print(f"Error processing Besta deild fixture {home_team} vs {away_team}: {e}")

    return {
        "id": "besta_deild_karla",
        "name": "Besta deild karla",
        "metric": "goals",
        "fixtures": output_fixtures
    }

def main():
    pl_data = process_premier_league()
    bd_data = process_besta_deild()

    # Prepare final output structure
    output = {
        "meta": {
            "version": get_version(),
            "generated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        },
        "leagues": [
            pl_data,
            bd_data
        ]
    }

    # Ensure public directory exists
    os.makedirs('public', exist_ok=True)

    # Write to public/data.json
    with open('public/data.json', 'w') as f:
        json.dump(output, f, indent=2)

    total_fixtures = len(pl_data['fixtures']) + len(bd_data['fixtures'])
    print(f"Successfully wrote {total_fixtures} total fixtures to public/data.json")

if __name__ == "__main__":
    main()
