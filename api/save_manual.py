import json
import os
import urllib.parse
from http.server import BaseHTTPRequestHandler

# Path to the shared match database
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'public', 'match_database.json'))

def load_match_database():
    if not os.path.exists(DB_PATH):
        return []
    try:
        with open(DB_PATH, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def save_match_database(database):
    try:
        with open(DB_PATH, 'w') as f:
            json.dump(database, f, indent=2)
        return True
    except Exception:
        return False

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            payload = json.loads(body)

            league_id = payload.get('league_id', '').strip().lower()
            league_name = payload.get('league_name', '').strip()
            home_team = payload.get('home_team', '').strip()
            away_team = payload.get('away_team', '').strip()
            skip_xg = payload.get('skip_xg', False)
            home_matches = payload.get('home_matches', [])
            away_matches = payload.get('away_matches', [])

            if not league_id or not home_team or not away_team:
                self.send_json({"error": "Missing required fields"}, 400)
                return

            database = load_match_database()

            # Helper to check if a match matches league, team, opponent, date, and venue
            def match_exists(team, opponent, date, venue):
                for entry in database:
                    if (entry.get("league", "").strip().lower() == league_id and
                        entry.get("team", "").strip().lower() == team.strip().lower() and
                        entry.get("opponent", "").strip().lower() == opponent.strip().lower() and
                        entry.get("date", "") == date and
                        entry.get("venue", "").strip().lower() == venue.strip().lower()):
                        return True
                return False

            new_records = []

            # 1. Process Home Team parsed matches
            for m in home_matches:
                opponent = m['opponent']
                date = m['date']
                venue = m['venue']
                val_for = m['valFor']
                val_against = m['valAgainst']

                goals_for = int(val_for) if skip_xg else None
                goals_against = int(val_against) if skip_xg else None
                xg_for = None if skip_xg else float(val_for)
                xg_against = None if skip_xg else float(val_against)

                # Team entry (Ajax vs Feyenoord - venue: away means Ajax is away, Feyenoord is home)
                if not match_exists(home_team, opponent, date, venue):
                    new_records.append({
                        "team": home_team,
                        "opponent": opponent,
                        "date": date,
                        "venue": venue,
                        "goals_for": goals_for,
                        "goals_against": goals_against,
                        "xg_for": xg_for,
                        "xg_against": xg_against,
                        "source": "manual",
                        "league": league_id,
                        "weight": 1.0
                    })

                # Opponent entry (Feyenoord vs Ajax - venue: home)
                opp_venue = "away" if venue == "home" else "home"
                if not match_exists(opponent, home_team, date, opp_venue):
                    new_records.append({
                        "team": opponent,
                        "opponent": home_team,
                        "date": date,
                        "venue": opp_venue,
                        "goals_for": goals_against,
                        "goals_against": goals_for,
                        "xg_for": xg_against,
                        "xg_against": xg_for,
                        "source": "manual",
                        "league": league_id,
                        "weight": 1.0
                    })

            # 2. Process Away Team parsed matches
            for m in away_matches:
                opponent = m['opponent']
                date = m['date']
                venue = m['venue']
                val_for = m['valFor']
                val_against = m['valAgainst']

                goals_for = int(val_for) if skip_xg else None
                goals_against = int(val_against) if skip_xg else None
                xg_for = None if skip_xg else float(val_for)
                xg_against = None if skip_xg else float(val_against)

                # Team entry
                if not match_exists(away_team, opponent, date, venue):
                    new_records.append({
                        "team": away_team,
                        "opponent": opponent,
                        "date": date,
                        "venue": venue,
                        "goals_for": goals_for,
                        "goals_against": goals_against,
                        "xg_for": xg_for,
                        "xg_against": xg_against,
                        "source": "manual",
                        "league": league_id,
                        "weight": 1.0
                    })

                # Opponent entry
                opp_venue = "away" if venue == "home" else "home"
                if not match_exists(opponent, away_team, date, opp_venue):
                    new_records.append({
                        "team": opponent,
                        "opponent": away_team,
                        "date": date,
                        "venue": opp_venue,
                        "goals_for": goals_against,
                        "goals_against": goals_for,
                        "xg_for": xg_against,
                        "xg_against": xg_for,
                        "source": "manual",
                        "league": league_id,
                        "weight": 1.0
                    })

            if new_records:
                database.extend(new_records)
                save_match_database(database)

            self.send_json({"success": True, "saved_count": len(new_records)}, 200)

        except Exception as e:
            self.send_json({"error": "Failed to save manual matches", "details": str(e)}, 500)

    def send_json(self, data, status_code):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
