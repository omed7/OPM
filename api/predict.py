import json
import re
import urllib.request
import urllib.parse
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()

    def handle_request(self):
        # Parse query params
        parsed_url = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_url.query)

        league = query_params.get('league', [None])[0]
        home_team = query_params.get('home_team', [None])[0]
        away_team = query_params.get('away_team', [None])[0]

        html_content = ""

        # If POST request, check if we received HTML content in the body
        if self.command == 'POST':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8')
                try:
                    payload = json.loads(body)
                    html_content = payload.get('html', '')
                    if not league:
                        league = payload.get('league')
                    if not home_team:
                        home_team = payload.get('home_team')
                    if not away_team:
                        away_team = payload.get('away_team')
                except json.JSONDecodeError:
                    html_content = body
            except Exception as e:
                pass

        # Validate inputs
        if not league or not home_team or not away_team:
            self.send_json({"error": "league, home_team, and away_team parameters are required"}, 400)
            return

        # If no HTML content was provided via POST, fetch from OddAlerts
        if not html_content:
            url = f"https://www.oddalerts.com/xg/{league}"
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    html_content = response.read().decode('utf-8')
            except Exception as e:
                self.send_json({
                    "error": "Failed to fetch from OddAlerts directly (e.g. Cloudflare restriction). Please use Paste HTML Box below.",
                    "details": str(e),
                    "blocked": True
                }, 403)
                return

        try:
            prediction = self.calculate_predictions(html_content, home_team, away_team)
            self.send_json(prediction, 200)
        except Exception as e:
            self.send_json({"error": "Failed to calculate predictions", "details": str(e)}, 500)

    def calculate_predictions(self, html, home_team, away_team):
        # 1. Parse all played match results from the HTML page
        matches = []

        # Parse date groupings
        dates = []
        for m in re.finditer(r'<div class="fixture heading">.*?<span class="status-text">(.*?)</span>.*?</div>', html, re.DOTALL):
            dates.append((m.start(), m.group(1).strip()))

        if not dates:
            for m in re.finditer(r'<div class="fixture heading">.*?class="status-text">(.*?)<', html, re.DOTALL):
                dates.append((m.start(), m.group(1).strip()))

        parts = html.split('<div class="fixture')
        current_pos = len(parts[0])

        for part in parts[1:]:
            is_heading = part.startswith(' heading')

            # Find the actual date that corresponds to this position
            current_date = "Unknown Date"
            for pos, date_str in reversed(dates):
                if pos < current_pos:
                    current_date = date_str
                    break

            # Update current_pos for the next iteration
            current_pos += len('<div class="fixture') + len(part)

            if is_heading:
                continue

            teams_data = []
            team_parts = part.split('<div class="team">')
            for tp in team_parts[1:3]:
                xg_m = re.search(r'<span class="xg"[^>]*>(.*?)</span>', tp, re.DOTALL)
                name_m = re.search(r'<div class="name">(.*?)</div>', tp, re.DOTALL)

                xg_val = xg_m.group(1).strip() if xg_m else "0.0"
                name_val = name_m.group(1).strip() if name_m else ""

                if name_val:
                    teams_data.append({"name": name_val, "xg": xg_val})

            status_match = re.search(r'<div class="status">.*?<span class="status-text">(.*?)</span>', part, re.DOTALL)
            status_text = status_match.group(1).strip() if status_match else ""

            def clean_name(name):
                name = name.replace('&amp;', '&').replace('&nbsp;', ' ')
                name = re.sub(r'<[^>]*>', '', name)
                return name.strip()

            if len(teams_data) >= 2:
                h_name = clean_name(teams_data[0]["name"])
                a_name = clean_name(teams_data[1]["name"])

                # Check if this is a result
                is_result = False
                if "-" in status_text and not ":" in status_text:
                    is_result = True

                if is_result:
                    try:
                        h_xg = float(teams_data[0]["xg"])
                        a_xg = float(teams_data[1]["xg"])
                        matches.append({
                            "date": current_date,
                            "home_team": h_name,
                            "away_team": a_name,
                            "home_xg": h_xg,
                            "away_xg": a_xg,
                            "score": status_text
                        })
                    except ValueError:
                        pass

        # 2. Extract match history for home_team and away_team
        # For a fixture between Team A (home) and Team B (away), using each team's last 4 matches (2 home + 2 away):
        # We need Team A's last 2 home matches and last 2 away matches.
        # We need Team B's last 2 home matches and last 2 away matches.

        home_team_home_matches = [m for m in matches if m["home_team"].lower() == home_team.lower()][:2]
        home_team_away_matches = [m for m in matches if m["away_team"].lower() == home_team.lower()][:2]

        away_team_home_matches = [m for m in matches if m["home_team"].lower() == away_team.lower()][:2]
        away_team_away_matches = [m for m in matches if m["away_team"].lower() == away_team.lower()][:2]

        # Combine them to verify we have enough matches
        # The prompt says "using each team's last 4 matches (2 home + 2 away)"
        # Let's ensure we find what is available, but if we don't find exactly 2, we fallback gracefully or use what's found.
        # For full formula execution:
        home_team_history = []
        for m in home_team_home_matches:
            home_team_history.append({
                "xg_for": m["home_xg"],
                "xg_against": m["away_xg"],
                "opponent": m["away_team"],
                "venue": "home"
            })
        for m in home_team_away_matches:
            home_team_history.append({
                "xg_for": m["away_xg"],
                "xg_against": m["home_xg"],
                "opponent": m["home_team"],
                "venue": "away"
            })

        away_team_history = []
        for m in away_team_home_matches:
            away_team_history.append({
                "xg_for": m["home_xg"],
                "xg_against": m["away_xg"],
                "opponent": m["away_team"],
                "venue": "home"
            })
        for m in away_team_away_matches:
            away_team_history.append({
                "xg_for": m["away_xg"],
                "xg_against": m["home_xg"],
                "opponent": m["home_team"],
                "venue": "away"
            })

        # Calculate Averages (fallback to 0 if list is empty)
        def avg(lst):
            return sum(lst) / len(lst) if lst else 0.0

        home_avg_for = avg([m["xg_for"] for m in home_team_history])
        home_avg_against = avg([m["xg_against"] for m in home_team_history])

        away_avg_for = avg([m["xg_for"] for m in away_team_history])
        away_avg_against = avg([m["xg_against"] for m in away_team_history])

        # Omed's personal football xG prediction formula:
        # Expected A xG = (A's AVG xG FOR + B's AVG xG AGAINST) / 2
        # Expected B xG = (B's AVG xG FOR + A's AVG xG AGAINST) / 2
        expected_home_xg = (home_avg_for + away_avg_against) / 2
        expected_away_xg = (away_avg_for + home_avg_against) / 2
        combined_expected_xg = expected_home_xg + expected_away_xg

        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_expected_xg": expected_home_xg,
            "away_expected_xg": expected_away_xg,
            "combined_expected_xg": combined_expected_xg,
            "home_last_xg_matches": home_team_history,
            "away_last_xg_matches": away_team_history,
            "meta": {
                "home_avg_for": home_avg_for,
                "home_avg_against": home_avg_against,
                "away_avg_for": away_avg_for,
                "away_avg_against": away_avg_against,
                "home_matches_count": len(home_team_history),
                "away_matches_count": len(away_team_history)
            }
        }

    def send_json(self, data, status_code):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
