import os
import json
import subprocess
from datetime import datetime, timezone
from fetch import get_upcoming_fixtures, get_team_matches, get_current_season
from compute import calculate_expected_xg, SAMPLE_SIZE

def get_version():
    sha = os.environ.get('GITHUB_SHA')
    if sha:
        return sha[:7]
    try:
        # Try to get the short commit SHA from git
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], stderr=subprocess.STDOUT).decode('ascii').strip()
    except Exception:
        return "local"

def main():
    # Check if a season is provided as an environment variable, otherwise use current
    season = os.environ.get('SEASON', get_current_season())
    print(f"Fetching upcoming fixtures for season {season}...")

    try:
        fixtures = get_upcoming_fixtures(season=season)
    except Exception as e:
        print(f"Error fetching upcoming fixtures: {e}")
        fixtures = []

    if not fixtures:
        print("No upcoming fixtures found.")

    output_fixtures = []

    for fixture in fixtures:
        home_team = fixture['home_team']
        away_team = fixture['away_team']
        print(f"Processing {home_team} vs {away_team}...")

        try:
            # Fetch last N matches for each team
            home_matches = get_team_matches(home_team, total_matches=SAMPLE_SIZE, season=season)
            away_matches = get_team_matches(away_team, total_matches=SAMPLE_SIZE, season=season)

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
                f"home_last_{SAMPLE_SIZE}_matches": home_matches,
                f"away_last_{SAMPLE_SIZE}_matches": away_matches
            })
        except Exception as e:
            print(f"Error processing fixture {home_team} vs {away_team}: {e}")

    # Prepare final output structure
    output = {
        "meta": {
            "version": get_version(),
            "generated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        },
        "fixtures": output_fixtures
    }

    # Ensure public directory exists
    os.makedirs('public', exist_ok=True)

    # Write to public/data.json
    with open('public/data.json', 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Successfully wrote {len(output_fixtures)} fixtures to public/data.json")

if __name__ == "__main__":
    main()
