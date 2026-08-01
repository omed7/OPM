import os
import json
import sys
import subprocess
import urllib.request
from datetime import datetime, timezone

# Add the project root to sys.path so we can import from api
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fetch.understat_common import get_upcoming_fixtures, get_team_matches, get_played_matches, get_current_season
from compute.xg_formula import calculate_expected_xg, SAMPLE_SIZE as XG_SAMPLE_SIZE

UNDERSTAT_LEAGUES = [
    {"code": "EPL", "name": "Premier League", "output_id": "premier_league"},
    {"code": "La_Liga", "name": "La Liga", "output_id": "la_liga"},
    {"code": "Serie_A", "name": "Serie A", "output_id": "serie_a"},
    {"code": "Bundesliga", "name": "Bundesliga", "output_id": "bundesliga"},
    {"code": "Ligue_1", "name": "Ligue 1", "output_id": "ligue_1"},
]

ODDALERTS_LEAGUES = [
    {"id": "mls", "name": "Major League Soccer", "slug": "mls"},
    {"id": "eliteserien", "name": "Eliteserien", "slug": "eliteserien"},
    {"id": "premiership", "name": "Premiership", "slug": "premiership"},
    {"id": "superliga-denmark", "name": "Superliga", "slug": "superliga-denmark"}
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

def fetch_and_parse_oddalerts_league(league_id, slug, name):
    print(f"Fetching {name} ({league_id}) matches from OddAlerts...")
    url = f"https://www.oddalerts.com/xg/{slug}"
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
    )

    html_content = ""
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8')
            print(f"Fetch for {league_id} succeeded.")
    except Exception as e:
        print(f"Fetch for {league_id} failed: {e}")

    parsed_matches = []
    if html_content:
        from api.predict import parse_recent_results
        try:
            parsed_matches = parse_recent_results(html_content)
            print(f"Parsed {len(parsed_matches)} matches for {league_id} successfully.")
        except Exception as e:
            print(f"Error parsing matches for {league_id}: {e}")
    return parsed_matches

def map_oddalerts_to_db(matches, league_id):
    records = []
    for m in matches:
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
        # Ensure we parse float safely if possible
        try:
            if home_xg is not None:
                home_xg = float(home_xg)
        except ValueError:
            home_xg = None
        try:
            if away_xg is not None:
                away_xg = float(away_xg)
        except ValueError:
            away_xg = None

        date = m.get("date")
        home_team = m.get("home_team")
        away_team = m.get("away_team")

        # Home team record
        records.append({
            "team": home_team,
            "opponent": away_team,
            "date": date,
            "venue": "home",
            "goals_for": home_goals,
            "goals_against": away_goals,
            "xg_for": home_xg,
            "xg_against": away_xg,
            "source": "oddalerts",
            "league": league_id,
            "weight": 1.0
        })

        # Away team record
        records.append({
            "team": away_team,
            "opponent": home_team,
            "date": date,
            "venue": "away",
            "goals_for": away_goals,
            "goals_against": home_goals,
            "xg_for": away_xg,
            "xg_against": home_xg,
            "source": "oddalerts",
            "league": league_id,
            "weight": 1.0
        })

    return records

def map_understat_to_db(matches, league_id):
    records = []
    for m in matches:
        # Expected structure of played match from understatapi:
        # {
        #   'id': '26602', 'isResult': True,
        #   'h': {'id': '89', 'title': 'Manchester United', 'short_title': 'MUN'},
        #   'a': {'id': '228', 'title': 'Fulham', 'short_title': 'FLH'},
        #   'goals': {'h': '1', 'a': '0'},
        #   'xG': {'h': '2.04268', 'a': '0.418711'},
        #   'datetime': '2024-08-16 19:00:00'
        # }
        home_team = m['h']['title']
        away_team = m['a']['title']

        home_goals = None
        away_goals = None
        if 'goals' in m and m['goals']:
            try:
                home_goals = int(m['goals'].get('h'))
            except (ValueError, TypeError):
                pass
            try:
                away_goals = int(m['goals'].get('a'))
            except (ValueError, TypeError):
                pass

        home_xg = None
        away_xg = None
        if 'xG' in m and m['xG']:
            try:
                home_xg = float(m['xG'].get('h'))
            except (ValueError, TypeError):
                pass
            try:
                away_xg = float(m['xG'].get('a'))
            except (ValueError, TypeError):
                pass

        date = m.get('datetime', '')
        if ' ' in date:
            date = date.split(' ')[0]

        # Home team record
        records.append({
            "team": home_team,
            "opponent": away_team,
            "date": date,
            "venue": "home",
            "goals_for": home_goals,
            "goals_against": away_goals,
            "xg_for": home_xg,
            "xg_against": away_xg,
            "source": "understat",
            "league": league_id,
            "weight": 1.0
        })

        # Away team record
        records.append({
            "team": away_team,
            "opponent": home_team,
            "date": date,
            "venue": "away",
            "goals_for": away_goals,
            "goals_against": home_goals,
            "xg_for": away_xg,
            "xg_against": home_xg,
            "source": "understat",
            "league": league_id,
            "weight": 1.0
        })

    return records

def main():
    db_records = []

    # 1. Fetch OddAlerts leagues
    for league in ODDALERTS_LEAGUES:
        try:
            matches = fetch_and_parse_oddalerts_league(league["id"], league["slug"], league["name"])
            db_records.extend(map_oddalerts_to_db(matches, league["id"]))
        except Exception as e:
            print(f"Failed to fetch or parse OddAlerts league {league['name']}: {e}")

    leagues_data = []

    # 2. Fetch Understat leagues
    for league in UNDERSTAT_LEAGUES:
        # Process for existing data.json output
        try:
            data = process_understat_league(league["code"], league["name"], league["output_id"])
            leagues_data.append(data)
        except Exception as e:
            print(f"Failed to process Understat league {league['name']} for data.json: {e}")

        # Fetch and process for the match database
        try:
            season = os.environ.get('SEASON', get_current_season())
            print(f"Fetching all played matches for Understat league {league['name']} (season {season})...")
            played_matches = get_played_matches(league["code"], season=season)
            db_records.extend(map_understat_to_db(played_matches, league["output_id"]))
            print(f"Mapped {len(played_matches)} played matches for Understat league {league['name']}.")
        except Exception as e:
            print(f"Failed to process Understat league {league['name']} for match database: {e}")

    # Ensure public directory exists
    os.makedirs('public', exist_ok=True)

    # 3. Write consolidated match database
    try:
        with open('public/match_database.json', 'w') as f:
            json.dump(db_records, f, indent=2)
        print(f"Successfully wrote {len(db_records)} records to public/match_database.json")
    except Exception as e:
        print(f"Failed to write match database: {e}")

    # 4. Remove public/oddalerts_mls.json if it exists (since it is superseded)
    if os.path.exists('public/oddalerts_mls.json'):
        try:
            os.remove('public/oddalerts_mls.json')
            print("Successfully deleted public/oddalerts_mls.json (superseded).")
        except Exception as e:
            print(f"Failed to delete public/oddalerts_mls.json: {e}")

    # 5. Prepare and write final data.json output structure (preserving original behavior)
    output = {
        "meta": {
            "version": get_version(),
            "generated_at": datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        },
        "leagues": leagues_data
    }

    with open('public/data.json', 'w') as f:
        json.dump(output, f, indent=2)

    total_fixtures = sum(len(l['fixtures']) for l in leagues_data)
    print(f"Successfully wrote {total_fixtures} total fixtures to public/data.json")

if __name__ == "__main__":
    main()
