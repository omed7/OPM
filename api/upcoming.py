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
                except json.JSONDecodeError:
                    html_content = body
            except Exception as e:
                pass

        # Validate league
        if not league:
            self.send_json({"error": "league parameter is required"}, 400)
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
                # If we get blocked (Cloudflare 403), return structured error indicating pasting is supported
                self.send_json({
                    "error": "Failed to fetch from OddAlerts directly (e.g. Cloudflare restriction). Please use Paste HTML Box below.",
                    "details": str(e),
                    "blocked": True
                }, 403)
                return

        try:
            fixtures = self.parse_upcoming_fixtures(html_content)
            self.send_json({"league": league, "fixtures": fixtures}, 200)
        except Exception as e:
            self.send_json({"error": "Failed to parse fixtures", "details": str(e)}, 500)

    def parse_upcoming_fixtures(self, html):
        # Let's do HTML markup parsing for "Recent Results with xG" and "Upcoming Fixtures"
        # First, find dates and their positions
        dates = []
        for m in re.finditer(r'<div class="fixture heading">.*?<span class="status-text">(.*?)</span>.*?</div>', html, re.DOTALL):
            dates.append((m.start(), m.group(1).strip()))

        if not dates:
            for m in re.finditer(r'<div class="fixture heading">.*?class="status-text">(.*?)<', html, re.DOTALL):
                dates.append((m.start(), m.group(1).strip()))

        fixtures = []

        # We can extract all <div class="fixture"> blocks. To avoid the greedy match,
        # we parse each block up to the very next <div class="fixture" or the end of the container.
        # An elegant way to do this is splitting or finding matches of <div class="fixture"> that do not contain nested <div class="fixture">
        # In OddAlerts markup, we can split the text by '<div class="fixture' and parse each segment.
        parts = html.split('<div class="fixture')
        current_pos = len(parts[0])

        # First part is before any fixture div, skip it
        for part in parts[1:]:
            # Reconstruct the block. If it starts with ' heading', it is a heading/divider.
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

            # Now parse teams in this fixture part
            # Each team: <span class="xg">value</span> + <div class="name">Team</div>
            # Or <div class="name">Team</div> + <span class="xg">value</span>
            teams_data = []

            # Let's look for team blocks inside this segment.
            # In our part, we have two <div class="team"> blocks. Let's find them.
            team_parts = part.split('<div class="team">')
            for tp in team_parts[1:3]: # Exactly up to two teams
                # Inside team part, we look for xg and name
                xg_m = re.search(r'<span class="xg"[^>]*>(.*?)</span>', tp, re.DOTALL)
                name_m = re.search(r'<div class="name">(.*?)</div>', tp, re.DOTALL)

                xg_val = xg_m.group(1).strip() if xg_m else "0.0"
                name_val = name_m.group(1).strip() if name_m else ""

                if name_val:
                    teams_data.append({"name": name_val, "xg": xg_val})

            # Parse status/score/time from this segment
            status_match = re.search(r'<div class="status">.*?<span class="status-text">(.*?)</span>', part, re.DOTALL)
            status_text = status_match.group(1).strip() if status_match else ""

            def clean_name(name):
                name = name.replace('&amp;', '&').replace('&nbsp;', ' ')
                name = re.sub(r'<[^>]*>', '', name)
                return name.strip()

            if len(teams_data) >= 2:
                home_team = clean_name(teams_data[0]["name"])
                away_team = clean_name(teams_data[1]["name"])

                # Check if this is a result or upcoming
                is_result = False
                if "-" in status_text and not ":" in status_text:
                    is_result = True

                fixtures.append({
                    "date": current_date,
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_xg": teams_data[0]["xg"],
                    "away_xg": teams_data[1]["xg"],
                    "status": status_text,
                    "is_result": is_result
                })

        return fixtures

    def send_json(self, data, status_code):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
