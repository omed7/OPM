import os
import json
import subprocess
from datetime import datetime, timezone

from fetch.understat_common import get_upcoming_fixtures, get_team_matches, get_current_season
from compute.xg_formula import calculate_expected_xg, SAMPLE_SIZE as XG_SAMPLE_SIZE

UNDERSTAT_LEAGUES = [
    {"code": "EPL", "name": "Premier League", "output_id": "premier_league"},
    {"code": "La_Liga", "name": "La Liga", "output_id": "la_liga"},
    {"code": "Serie_A", "name": "Serie A", "output_id": "serie_a"},
    {"code": "Bundesliga", "name": "Bundesliga", "output_id": "bundesliga"},
    {"code": "Ligue_1", "name": "Ligue 1", "output_id": "ligue_1"},
]

def get_version():
    sha = os.environ.get('GITHUB_SHA')
    if sha:
        return sha[:7]
    try:
        # Try to get the short commit SHA from git
        return subprocess.check_output(['git', 'rev-parse', '--short', 'HEAD'], stderr=subprocess.STDOUT).decode('ascii').strip()
    except Exception:
        return "local"

def process_understat_league(league_code, league_name, output_id):
    season = os.environ.get('SEASON', get_current_season())
    print(f"Fetching upcoming {league_name} fixtures for season {season}...")

    try:
        fixtures = get_upcoming_fixtures(league_code, season=season)
    except Exception as e:
        print(f"Error fetching upcoming fixtures for {league_name}: {e}")
        fixtures = []

    if not fixtures:
        print(f"No upcoming {league_name} fixtures found.")

    output_fixtures = []

    for fixture in fixtures:
        home_team = fixture['home_team']
        away_team = fixture['away_team']
        print(f"Processing {league_code}: {home_team} vs {away_team}...")

        try:
            # Fetch last N matches for each team
            home_matches = get_team_matches(league_code, home_team, total_matches=XG_SAMPLE_SIZE, season=season)
            away_matches = get_team_matches(league_code, away_team, total_matches=XG_SAMPLE_SIZE, season=season)

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
            print(f"Error processing {league_name} fixture {home_team} vs {away_team}: {e}")

    return {
        "id": output_id,
        "name": league_name,
        "metric": "xg",
        "fixtures": output_fixtures
    }

def main():
    leagues_data = []

    for league in UNDERSTAT_LEAGUES:
        try:
            data = process_understat_league(league["code"], league["name"], league["output_id"])
            leagues_data.append(data)
        except Exception as e:
            print(f"Failed to process {league['name']}: {e}")

    # Prepare final output structure
    output = {
        "meta": {
            "version": get_version(),
            "generated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        },
        "leagues": leagues_data
    }

    # Ensure public directory exists
    os.makedirs('public', exist_ok=True)

    # Write to public/data.json
    with open('public/data.json', 'w') as f:
        json.dump(output, f, indent=2)

    total_fixtures = sum(len(l['fixtures']) for l in leagues_data)
    print(f"Successfully wrote {total_fixtures} total fixtures to public/data.json")

if __name__ == "__main__":
    main()
