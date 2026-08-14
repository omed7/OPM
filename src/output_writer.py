import os
import json
import sys
import subprocess
import urllib.request
from datetime import datetime, timezone

# Add the project root to sys.path so we can import from api and src modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.fetch.understat_common import get_upcoming_fixtures, get_team_matches, get_played_matches, get_current_season
from src.fetch.oddalerts import parse_upcoming_fixtures, parse_recent_results
from src.compute.xg_formula import calculate_expected_xg, SAMPLE_SIZE as XG_SAMPLE_SIZE
from src.compute.goals_formula import calculate_expected_goals
from src.supabase_client import supabase_request

UNDERSTAT_LEAGUES = [
    {"code": "EPL", "name": "Premier League", "output_id": "premier_league"},
    {"code": "La_Liga", "name": "La Liga", "output_id": "la_liga"},
    {"code": "Serie_A", "name": "Serie A", "output_id": "serie_a"},
    {"code": "Bundesliga", "name": "Bundesliga", "output_id": "bundesliga"},
    {"code": "Ligue_1", "name": "Ligue 1", "output_id": "ligue_1"},
]

ODDALERTS_LEAGUES = [
    {"id": "superliga-argentina", "name": "Superliga", "slug": "superliga-argentina", "fixtures_path": "/leagues/argentina/liga-profesional-de-futbol/fixtures"},
    {"id": "admiral-bundesliga", "name": "Admiral Bundesliga", "slug": "admiral-bundesliga", "fixtures_path": "/leagues/austria/admiral-bundesliga/fixtures"},
    {"id": "pro-league-belgium", "name": "Pro League", "slug": "pro-league-belgium", "fixtures_path": "/leagues/belgium/pro-league/fixtures"},
    {"id": "serie-a-brazil", "name": "Serie A Brazil", "slug": "serie-a-brazil", "fixtures_path": "/leagues/brazil/serie-a/fixtures"},
    {"id": "superliga-denmark", "name": "Superliga Denmark", "slug": "superliga-denmark", "fixtures_path": "/leagues/denmark/superliga/fixtures"},
    {"id": "league-one", "name": "League One", "slug": "league-one", "fixtures_path": "/leagues/scotland/league-one/fixtures"},
    {"id": "2-bundesliga", "name": "2. Bundesliga", "slug": "2-bundesliga", "fixtures_path": "/leagues/germany/2.-bundesliga/fixtures"},
    {"id": "copa-libertadores", "name": "Copa Libertadores", "slug": "copa-libertadores", "fixtures_path": "/leagues/south-america/copa-libertadores/fixtures"},
    {"id": "j-league", "name": "J-League", "slug": "j-league", "fixtures_path": "/leagues/japan/j1-league/fixtures"},
    {"id": "liga-mx", "name": "Liga MX", "slug": "liga-mx", "fixtures_path": "/leagues/mexico/liga-mx/fixtures"},
    {"id": "eredivisie", "name": "Eredivisie", "slug": "eredivisie", "fixtures_path": "/leagues/netherlands/eredivisie/fixtures"},
    {"id": "eerste-divisie", "name": "Eerste Divisie", "slug": "eerste-divisie", "fixtures_path": "/leagues/netherlands/eerste-divisie/fixtures"},
    {"id": "eliteserien", "name": "Eliteserien", "slug": "eliteserien", "fixtures_path": "/leagues/norway/eliteserien/fixtures"},
    {"id": "liga-portugal", "name": "Liga Portugal", "slug": "liga-portugal", "fixtures_path": "/leagues/portugal/liga-portugal/fixtures"},
    {"id": "pro-league-saudi", "name": "Pro League Saudi", "slug": "pro-league-saudi", "fixtures_path": "/leagues/saudi-arabia/pro-league/fixtures"},
    {"id": "premiership", "name": "Premiership", "slug": "premiership", "fixtures_path": "/leagues/scotland/premiership/fixtures"},
    {"id": "allsvenskan", "name": "Allsvenskan", "slug": "allsvenskan", "fixtures_path": "/leagues/sweden/allsvenskan/fixtures"},
    {"id": "super-lig", "name": "Super Lig", "slug": "super-lig", "fixtures_path": "/leagues/turkiye/super-lig/fixtures"},
    {"id": "mls", "name": "Major League Soccer", "slug": "mls", "fixtures_path": "/leagues/united-states/major-league-soccer/fixtures"},
    {"id": "veikkausliiga", "name": "Veikkausliiga", "slug": "veikkausliiga", "fixtures_path": "/leagues/finland/veikkausliiga/fixtures"}
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

            # Calculate expected metrics
            xg_stats = calculate_expected_xg(home_matches, away_matches)

            # Since Understat matches don't have 'goals_for' explicitly in the dictionary returned by get_team_matches...
            # Wait, let's check if they do. Let's look at get_team_matches. No, it only has xg_for/xg_against.
            # So for understat we might only have xG unless we fetch goals. Let's just wrap it.
            try:
                goals_stats = calculate_expected_goals(home_matches, away_matches)
            except Exception:
                goals_stats = None

            home_expected_xg = round(xg_stats['team_a_expected_xg'], 2)
            away_expected_xg = round(xg_stats['team_b_expected_xg'], 2)
            combined_expected_xg = round(xg_stats['team_a_expected_xg'] + xg_stats['team_b_expected_xg'], 2)

            home_expected_goals = round(goals_stats['team_a_expected_goals'], 2) if goals_stats else None
            away_expected_goals = round(goals_stats['team_b_expected_goals'], 2) if goals_stats else None
            combined_expected_goals = round(goals_stats['team_a_expected_goals'] + goals_stats['team_b_expected_goals'], 2) if goals_stats else None

            # Collect prediction to db_predictions globally
            global_db_predictions.append({
                "home_team": home_team,
                "away_team": away_team,
                "date": fixture['date'],
                "league": league_code,
                "home_expected_xg": home_expected_xg,
                "away_expected_xg": away_expected_xg,
                "combined_expected_xg": combined_expected_xg,
                "home_expected_goals": home_expected_goals,
                "away_expected_goals": away_expected_goals,
                "combined_expected_goals": combined_expected_goals
            })

            # Assemble fixture data
            output_fixtures.append({
                "home_team": home_team,
                "away_team": away_team,
                "date": fixture['date'],
                "combined_expected_xg": combined_expected_xg,
                "home_expected_xg": home_expected_xg,
                "away_expected_xg": away_expected_xg,
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


def process_oddalerts_league(league_id, league_name, fixtures_path, db_records):
    print(f"Fetching upcoming {league_name} fixtures from OddAlerts...")

    fixtures = []
    try:
        url = f"https://www.oddalerts.com{fixtures_path}"
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8')
            fixtures = parse_upcoming_fixtures(html_content)
    except Exception as e:
        pass

    output_fixtures = []
    league_matches = [m for m in db_records if m.get('league') == league_id]

    for fixture in fixtures:
        home_team = fixture['home_team']
        away_team = fixture['away_team']
        try:
            home_team_matches = [m for m in league_matches if m['team'] == home_team]
            away_team_matches = [m for m in league_matches if m['team'] == away_team]
            home_team_matches.sort(key=lambda x: x['date'], reverse=True)
            away_team_matches.sort(key=lambda x: x['date'], reverse=True)

            home_matches_needed = XG_SAMPLE_SIZE // 2
            away_matches_needed = XG_SAMPLE_SIZE // 2

            def get_balanced(team_matches, h_need, a_need):
                s = []
                h = 0
                a = 0
                for m in team_matches:
                    if h == h_need and a == a_need: break
                    if m['venue'] == 'home' and h < h_need:
                        s.append(m)
                        h += 1
                    elif m['venue'] == 'away' and a < a_need:
                        s.append(m)
                        a += 1
                return s

            home_matches = get_balanced(home_team_matches, home_matches_needed, away_matches_needed)
            away_matches = get_balanced(away_team_matches, home_matches_needed, away_matches_needed)

            formatted_home = []
            for m in home_matches:
                formatted_home.append({'opponent': m['opponent'], 'date': m['date'], 'venue': m['venue'], 'xg_for': m['xg_for'], 'xg_against': m['xg_against']})

            formatted_away = []
            for m in away_matches:
                formatted_away.append({'opponent': m['opponent'], 'date': m['date'], 'venue': m['venue'], 'xg_for': m['xg_for'], 'xg_against': m['xg_against']})

            xg_stats = calculate_expected_xg(formatted_home, formatted_away)
            try:
                goals_stats = calculate_expected_goals(home_matches, away_matches)
            except Exception:
                goals_stats = None

            home_expected_xg = round(xg_stats['team_a_expected_xg'], 2)
            away_expected_xg = round(xg_stats['team_b_expected_xg'], 2)
            combined_expected_xg = round(xg_stats['team_a_expected_xg'] + xg_stats['team_b_expected_xg'], 2)

            home_expected_goals = round(goals_stats['team_a_expected_goals'], 2) if goals_stats else None
            away_expected_goals = round(goals_stats['team_b_expected_goals'], 2) if goals_stats else None
            combined_expected_goals = round(goals_stats['team_a_expected_goals'] + goals_stats['team_b_expected_goals'], 2) if goals_stats else None

            global_db_predictions.append({
                "home_team": home_team,
                "away_team": away_team,
                "date": fixture['date'],
                "league": league_id,
                "home_expected_xg": home_expected_xg,
                "away_expected_xg": away_expected_xg,
                "combined_expected_xg": combined_expected_xg,
                "home_expected_goals": home_expected_goals,
                "away_expected_goals": away_expected_goals,
                "combined_expected_goals": combined_expected_goals
            })

            output_fixtures.append({
                "home_team": home_team, "away_team": away_team, "date": fixture['date'],
                "combined_expected_xg": combined_expected_xg,
                "home_expected_xg": home_expected_xg,
                "away_expected_xg": away_expected_xg,
                f"home_last_{XG_SAMPLE_SIZE}_matches": formatted_home,
                f"away_last_{XG_SAMPLE_SIZE}_matches": formatted_away
            })
        except:
            pass

    return {"id": league_id, "name": league_name, "metric": "xg", "fixtures": output_fixtures}

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

def save_matches_to_supabase(db_records):
    """
    Saves a list of match records to Supabase.
    Uses UPSERT (ON CONFLICT DO NOTHING) via Prefer header to avoid duplicates.
    Requires a unique constraint on (team, opponent, date, league, venue) in Supabase.
    """
    if not db_records:
        return

    # Send in chunks of 1000 to avoid request size limits
    chunk_size = 1000
    for i in range(0, len(db_records), chunk_size):
        chunk = db_records[i:i + chunk_size]

        url, key = os.environ.get("SUPABASE_URL") or os.environ.get("SUPERBASE_URL"), os.environ.get("SUPABASE_KEY") or os.environ.get("SUPERBASE_KEY")
        if not url or not key:
            print("Supabase credentials missing, skipping match sync.")
            return

        url = url.rstrip('/')
        full_url = url + "/rest/v1/matches?on_conflict=team,opponent,date,venue,league"

        # Prefer: resolution=ignore-duplicates instructs Supabase to ignore conflicts
        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=ignore-duplicates"
        }

        req_data = json.dumps(chunk).encode("utf-8")
        req = urllib.request.Request(full_url, data=req_data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                print(f"Successfully upserted chunk of {len(chunk)} matches to Supabase.")
        except Exception as e:
            print(f"Failed to upsert chunk to Supabase: {e}")



def save_predictions_to_supabase(predictions):
    if not predictions:
        return

    chunk_size = 1000
    for i in range(0, len(predictions), chunk_size):
        chunk = predictions[i:i + chunk_size]

        url, key = os.environ.get("SUPABASE_URL") or os.environ.get("SUPERBASE_URL"), os.environ.get("SUPABASE_KEY") or os.environ.get("SUPERBASE_KEY")
        if not url or not key:
            print("Supabase credentials missing, skipping predictions sync.")
            return

        url = url.rstrip('/')
        full_url = url + "/rest/v1/predictions?on_conflict=home_team,away_team,date,league"

        headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Prefer": "resolution=merge-duplicates"
        }

        req_data = json.dumps(chunk).encode("utf-8")
        req = urllib.request.Request(full_url, data=req_data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                print(f"Successfully upserted chunk of {len(chunk)} predictions to Supabase.")
        except Exception as e:
            print(f"Failed to upsert predictions chunk to Supabase: {e}")

from datetime import timedelta

def get_past_matches(db_records, league_id):
    now = datetime.now(timezone.utc)
    # We want matches from today-4 to today+1 (to account for timezones)
    start_date = (now - timedelta(days=4)).strftime('%Y-%m-%d')
    end_date = (now + timedelta(days=1)).strftime('%Y-%m-%d')

    past_matches = []

    # 1. Fetch predictions for this league and timeframe
    predictions_endpoint = f"/predictions?league=eq.{league_id}&date=gte.{start_date}&date=lte.{end_date}"
    pred_res, pred_err = supabase_request(predictions_endpoint)
    predictions_map = {}
    if pred_err is None and pred_res:
        for p in pred_res:
            key = f"{p['home_team']}-{p['away_team']}-{p['date'][:10]}"
            predictions_map[key] = p

    # 2. Check supabase first if available
    endpoint = f"/matches?league=eq.{league_id}&venue=eq.home&date=gte.{start_date}&date=lte.{end_date}&goals_for=not.is.null"
    res, err = supabase_request(endpoint)
    if err is None and res:
        for r in res:
            key = f"{r['team']}-{r['opponent']}-{r['date'][:10]}"
            pred = predictions_map.get(key, {})
            past_matches.append({
                "home_team": r["team"],
                "away_team": r["opponent"],
                "date": r["date"],
                "home_goals": r["goals_for"],
                "away_goals": r["goals_against"],
                "home_xg": r.get("xg_for"),
                "away_xg": r.get("xg_against"),
                "home_expected_xg": pred.get("home_expected_xg"),
                "away_expected_xg": pred.get("away_expected_xg"),
                "combined_expected_xg": pred.get("combined_expected_xg"),
                "home_expected_goals": pred.get("home_expected_goals"),
                "away_expected_goals": pred.get("away_expected_goals"),
                "combined_expected_goals": pred.get("combined_expected_goals"),
                "status": "FINISHED"
            })
        return past_matches

    # Fallback to local db_records if supabase fetch fails
    for r in db_records:
        if r.get("league") == league_id and r.get("venue") == "home" and r.get("goals_for") is not None and r.get("date"):
            date_str = r["date"][:10]
            if start_date <= date_str <= end_date:
                key = f"{r['team']}-{r['opponent']}-{date_str}"
                pred = predictions_map.get(key, {})
                past_matches.append({
                    "home_team": r["team"],
                    "away_team": r["opponent"],
                    "date": r["date"],
                    "home_goals": r["goals_for"],
                    "away_goals": r["goals_against"],
                    "home_xg": r.get("xg_for"),
                    "away_xg": r.get("xg_against"),
                    "home_expected_xg": pred.get("home_expected_xg"),
                    "away_expected_xg": pred.get("away_expected_xg"),
                    "combined_expected_xg": pred.get("combined_expected_xg"),
                    "home_expected_goals": pred.get("home_expected_goals"),
                    "away_expected_goals": pred.get("away_expected_goals"),
                    "combined_expected_goals": pred.get("combined_expected_goals"),
                    "status": "FINISHED"
                })

    # Deduplicate fallback matches
    unique_matches = {}
    for m in past_matches:
        key = f"{m['home_team']}-{m['away_team']}-{m['date'][:10]}"
        unique_matches[key] = m
    return list(unique_matches.values())


global_db_predictions = []

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

    for league in ODDALERTS_LEAGUES:
        try:
            data = process_oddalerts_league(league["id"], league["name"], league["fixtures_path"], db_records)
            if data["fixtures"]:
                leagues_data.append(data)
        except: pass

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


    # 3. Add past matches to each league from db_records
    for league_data in leagues_data:
        league_id = league_data["id"]
        past_fixtures = get_past_matches(db_records, league_id)
        # Append to existing upcoming fixtures
        league_data["fixtures"].extend(past_fixtures)

    # Ensure public directory exists
    os.makedirs('public', exist_ok=True)

    # 3. Write consolidated match database to Supabase (instead of local JSON)
    try:
        print(f"Upserting {len(db_records)} match records to Supabase...")
        save_matches_to_supabase(db_records)
    except Exception as e:
        print(f"Failed to write match database to Supabase: {e}")

    try:
        print(f"Upserting {len(global_db_predictions)} predictions to Supabase...")
        save_predictions_to_supabase(global_db_predictions)
    except Exception as e:
        print(f"Failed to write predictions to Supabase: {e}")

    # 4. Remove public/match_database.json if it exists (since it is migrated)
    if os.path.exists('public/match_database.json'):
        try:
            os.remove('public/match_database.json')
            print("Successfully deleted public/match_database.json (migrated to Supabase).")
        except Exception as e:
            print(f"Failed to delete public/match_database.json: {e}")

    # Remove public/oddalerts_mls.json if it exists (since it is superseded)
    if os.path.exists('public/oddalerts_mls.json'):
        try:
            os.remove('public/oddalerts_mls.json')
            print("Successfully deleted public/oddalerts_mls.json (superseded).")
        except Exception as e:
            pass

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
