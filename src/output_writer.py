import os
import json
import sys
import subprocess
import urllib.request
from datetime import datetime, timezone

# Add the project root to sys.path so we can import from api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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

def fetch_and_parse_oddalerts_mls():
    print("Fetching MLS matches from OddAlerts (proof of concept)...")
    url = "https://www.oddalerts.com/xg/mls"
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
    )

    html_content = ""
    status = "unknown"
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8')
            status = "succeeded"
            print("Fetch succeeded.")
    except Exception as e:
        status = f"blocked or failed: {e}"
        print(f"Fetch blocked or failed: {e}")

    parsed_matches = []
    team_records = []

    if html_content:
        # Reuse existing parsing logic
        from api.predict import parse_recent_results
        try:
            matches = parse_recent_results(html_content)
            print(f"Parsed {len(matches)} matches successfully.")

            for m in matches:
                # Extract goals from score e.g. "1 - 1"
                home_goals = None
                away_goals = None
                score = m.get("score", "")
                if " - " in score:
                    try:
                        pts = score.split(" - ")
                        home_goals = int(pts[0].strip())
                        away_goals = int(pts[1].strip())
                    except ValueError:
                        pass

                home_xg = m.get("home_xg")
                away_xg = m.get("away_xg")
                date = m.get("date")
                home_team = m.get("home_team")
                away_team = m.get("away_team")

                parsed_matches.append({
                    "date": date,
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_goals": home_goals,
                    "away_goals": away_goals,
                    "home_xg": home_xg,
                    "away_xg": away_xg,
                    "score": score
                })

                # Team-centric records: home team
                team_records.append({
                    "team": home_team,
                    "date": date,
                    "venue": "home",
                    "goals": home_goals,
                    "xg": home_xg,
                    "opponent": away_team,
                    "opponent_goals": away_goals,
                    "opponent_xg": away_xg
                })

                # Team-centric records: away team
                team_records.append({
                    "team": away_team,
                    "date": date,
                    "venue": "away",
                    "goals": away_goals,
                    "xg": away_xg,
                    "opponent": home_team,
                    "opponent_goals": home_goals,
                    "opponent_xg": home_xg
                })
        except Exception as e:
            print(f"Error parsing matches: {e}")

    # Prepare output
    output_data = {
        "meta": {
            "fetch_status": status,
            "fetched_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
            "matches_parsed_count": len(parsed_matches)
        },
        "matches": parsed_matches,
        "team_records": team_records
    }

    # Ensure public directory exists
    os.makedirs('public', exist_ok=True)

    # Store the parsed matches as simple structured data
    with open('public/oddalerts_mls.json', 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"Stored OddAlerts MLS proof of concept data to public/oddalerts_mls.json (parsed matches: {len(parsed_matches)})")

def main():
    # Run the MLS OddAlerts fetch proof of concept
    try:
        fetch_and_parse_oddalerts_mls()
    except Exception as e:
        print(f"OddAlerts MLS fetch failed: {e}")

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
