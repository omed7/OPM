import os
import json
import subprocess
from datetime import datetime, timezone

from fetch.premier_league import get_upcoming_fixtures, get_team_matches, get_current_season
from compute.xg_formula import calculate_expected_xg, SAMPLE_SIZE as XG_SAMPLE_SIZE
from fetch.besta_deild import get_besta_deild_data
from compute.goals_formula import calculate_expected_goals, SAMPLE_SIZE as GOALS_SAMPLE_SIZE
from fetch.api_football_common import fetch_api_football_league

OTHER_LEAGUES = [
    {"id": 71, "name": "Brazilian Serie A", "output_id": "brazilian_serie_a", "default_season": "2026"},
    {"id": 253, "name": "MLS", "output_id": "mls", "default_season": "2026"},
    {"id": 479, "name": "Canadian Premier League", "output_id": "canadian_premier_league", "default_season": "2026"},
    {"id": 103, "name": "Norway Eliteserien", "output_id": "norway_eliteserien", "default_season": "2026"},
    {"id": 179, "name": "Scotland Premiership", "output_id": "scotland_premiership", "default_season": "2026"},
    {"id": 244, "name": "Finland Veikkausliiga", "output_id": "finland_veikkausliiga", "default_season": "2026"},
    {"id": 119, "name": "Denmark Superliga", "output_id": "denmark_superliga", "default_season": "2026"},
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

def process_api_football_league(league_id, league_name, output_id, default_season, fetch_fn):
    print(f"Fetching {league_name} fixtures...")
    season = os.environ.get('SEASON', default_season)

    try:
        fixtures = fetch_fn(season=season, total_matches=GOALS_SAMPLE_SIZE)
    except Exception as e:
        print(f"Error fetching {league_name} fixtures: {e}")
        fixtures = []

    if not fixtures:
        print(f"No upcoming {league_name} fixtures found.")

    output_fixtures = []

    for fixture in fixtures:
        home_team = fixture['home_team']
        away_team = fixture['away_team']
        print(f"Processing {league_name}: {home_team} vs {away_team}...")

        try:
            home_matches = fixture['home_history']
            away_matches = fixture['away_history']

            stats = calculate_expected_goals(home_matches, away_matches)

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
            print(f"Error processing {league_name} fixture {home_team} vs {away_team}: {e}")

    return {
        "id": output_id,
        "name": league_name,
        "metric": "goals",
        "fixtures": output_fixtures
    }

def process_besta_deild():
    return process_api_football_league(
        164, "Besta deild karla", "besta_deild_karla", "2026",
        fetch_fn=get_besta_deild_data
    )

def main():
    pl_data = process_premier_league()

    leagues_data = [pl_data]

    # Process Besta deild karla
    try:
        bd_data = process_besta_deild()
        leagues_data.append(bd_data)
    except Exception as e:
        print(f"Failed to process Besta deild karla: {e}")

    # Process all other 7 API-Football leagues
    for league in OTHER_LEAGUES:
        try:
            fetch_fn = lambda season, total_matches, lid=league["id"], lname=league["name"]: fetch_api_football_league(
                league_id=lid,
                league_name=lname,
                season=season,
                total_matches=total_matches
            )
            data = process_api_football_league(
                league["id"], league["name"], league["output_id"], league["default_season"],
                fetch_fn=fetch_fn
            )
            leagues_data.append(data)
        except Exception as e:
            print(f"Failed to process league {league['name']}: {e}")

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
