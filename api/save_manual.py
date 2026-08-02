import json
import os
import base64
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

# Path to the shared match database for local fallback
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'public', 'match_database.json'))

def get_github_config():
    token = os.environ.get("GITHUB_API_TOKEN")
    if not token:
        return None
    # Use branch from Vercel env, fallback to 'main'
    branch = os.environ.get("VERCEL_GIT_COMMIT_REF", "main")
    return {
        "token": token,
        "branch": branch,
        "owner": "omed7",
        "repo": "OPM",
        "path": "public/match_database.json"
    }

def github_api_request(url, method="GET", data=None, token=None):
    headers = {
        "User-Agent": "OPM-Vercel-Serverless",
        "Accept": "application/vnd.github.v3+json",
    }
    if token:
        headers["Authorization"] = f"token {token}"

    req_data = None
    if data is not None:
        req_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            res_data = response.read()
            if response.getheader("Content-Type", "").startswith("application/json"):
                return json.loads(res_data.decode("utf-8")), response.status
            return res_data, response.status
    except urllib.error.HTTPError as e:
        try:
            error_body = e.read().decode("utf-8")
            try:
                error_json = json.loads(error_body)
                error_msg = error_json.get("message", error_body)
            except Exception:
                error_msg = error_body
        except Exception:
            error_msg = str(e)
        raise Exception(f"GitHub API Error ({e.code}): {error_msg}")
    except Exception as e:
        raise Exception(f"Request failed: {str(e)}")

def load_match_database():
    """
    Loads match database either from GitHub (if GITHUB_API_TOKEN is available)
    or from the local file path (fallback).
    Returns (database_list, sha)
    """
    config = get_github_config()
    if not config:
        # Local fallback
        if not os.path.exists(DB_PATH):
            return [], None
        try:
            with open(DB_PATH, 'r') as f:
                return json.load(f), None
        except Exception:
            return [], None

    # Fetch via GitHub
    token = config["token"]
    owner = config["owner"]
    repo = config["repo"]
    path = config["path"]
    branch = config["branch"]

    meta_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={branch}"
    try:
        meta, _ = github_api_request(meta_url, token=token)
        sha = meta.get("sha")
        download_url = meta.get("download_url") or f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"

        # Avoid cache by adding custom headers
        content_req = urllib.request.Request(
            download_url,
            headers={
                "Authorization": f"token {token}",
                "User-Agent": "OPM-Vercel-Serverless",
                "Cache-Control": "no-cache"
            }
        )
        with urllib.request.urlopen(content_req, timeout=15) as res:
            return json.loads(res.read().decode("utf-8")), sha
    except Exception as e:
        if "404" in str(e):
            return [], None
        raise e

def save_match_database(database, sha=None):
    """
    Saves match database either to GitHub (if GITHUB_API_TOKEN is available)
    or to the local file path (fallback).
    Returns (success_boolean, extra_info_dict)
    """
    config = get_github_config()
    if not config:
        # Local fallback
        try:
            with open(DB_PATH, 'w') as f:
                json.dump(database, f, indent=2)
            return True, {}
        except Exception as e:
            return False, {"error": str(e)}

    # Save via GitHub API
    token = config["token"]
    owner = config["owner"]
    repo = config["repo"]
    path = config["path"]
    branch = config["branch"]

    try:
        updated_content_str = json.dumps(database, indent=2)
        updated_content_b64 = base64.b64encode(updated_content_str.encode("utf-8")).decode("utf-8")

        put_payload = {
            "message": "chore: append manual matches via save_manual.py",
            "content": updated_content_b64,
            "branch": branch
        }
        if sha:
            put_payload["sha"] = sha

        put_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        res, _ = github_api_request(put_url, method="PUT", data=put_payload, token=token)

        commit_sha = res.get("commit", {}).get("sha", "")
        return True, {"commit_sha": commit_sha, "branch": branch}
    except Exception as e:
        return False, {"error": str(e)}

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

            database, sha = load_match_database()

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

            success = True
            save_info = {}
            if new_records:
                database.extend(new_records)
                success, save_info = save_match_database(database, sha)

            if success:
                response_data = {"success": True, "saved_count": len(new_records)}
                if save_info:
                    response_data.update(save_info)
                self.send_json(response_data, 200)
            else:
                error_msg = save_info.get("error", "Failed to save match database")
                self.send_json({"error": "Failed to save manual matches", "details": error_msg}, 500)

        except Exception as e:
            self.send_json({"error": "Failed to save manual matches", "details": str(e)}, 500)

    def send_json(self, data, status_code):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
