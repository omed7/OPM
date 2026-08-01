import json
import re
import urllib.request
import urllib.parse
import sys
import os
from http.server import BaseHTTPRequestHandler
from datetime import datetime

# Add the project root to sys.path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.compute.methodology import load_match_database, predict_fixture, compute_all_comparisons

def resolve_oddalerts_dates(dates, current_dt=None):
    if not current_dt:
        current_dt = datetime.now()

    months = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

    resolved = {}
    last_month_num = None
    year = current_dt.year

    for idx, (pos, d_str) in enumerate(dates):
        # Match e.g. "Fri, Jul 31" or just "Jul 31"
        m = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\s+(\d+)', d_str)
        if not m:
            resolved[pos] = d_str
            continue

        mon_str, day_str = m.group(1), m.group(2)
        mon_num = months[mon_str]
        day_num = int(day_str)

        if idx == 0:
            # First element (most recent date)
            if mon_num > current_dt.month or (mon_num == current_dt.month and day_num > current_dt.day):
                year -= 1
        else:
            if last_month_num is not None and mon_num > last_month_num:
                year -= 1

        last_month_num = mon_num
        formatted = f"{year:04d}-{mon_num:02d}-{day_num:02d}"
        resolved[pos] = formatted

    return resolved

def parse_recent_results(html):
    # Normalize single quotes to double quotes for class names to support direct server fetch (OddAlerts uses single quotes)
    html = re.sub(r"class='([^']*)'", r'class="\1"', html)

    # 1. Parse all played match results from the HTML page
    matches = []

    # Parse date groupings
    dates = []
    for m in re.finditer(r'<div class="fixture heading">.*?<span class="status-text">(.*?)</span>.*?</div>', html, re.DOTALL):
        dates.append((m.start(), m.group(1).strip()))

    if not dates:
        for m in re.finditer(r'<div class="fixture heading">.*?class="status-text">(.*?)<', html, re.DOTALL):
            dates.append((m.start(), m.group(1).strip()))

    # Resolve date strings to formatted YYYY-MM-DD
    resolved_dates = resolve_oddalerts_dates(dates)

    parts = html.split('<div class="fixture')
    current_pos = len(parts[0])

    for part in parts[1:]:
        is_heading = part.startswith(' heading')

        # Find the actual date that corresponds to this position
        current_date = "Unknown Date"
        for pos, date_str in reversed(dates):
            if pos < current_pos:
                current_date = resolved_dates.get(pos, date_str)
                break

        # Update current_pos for the next iteration
        current_pos += len('<div class="fixture') + len(part)

        if is_heading:
            continue

        teams_data = []
        team_parts = part.split('<div class="team">')
        for tp in team_parts[1:3]:
            xg_m = re.search(r'<span class="xg[^\"]*\"[^>]*>(.*?)</span>', tp, re.DOTALL)
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
    return matches

def map_parsed_to_db_schema(parsed_matches, league_id):
    records = []
    for m in parsed_matches:
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
        records.append({
            "team": m["home_team"],
            "opponent": m["away_team"],
            "date": m["date"],
            "venue": "home",
            "goals_for": home_goals,
            "goals_against": away_goals,
            "xg_for": m["home_xg"],
            "xg_against": m["away_xg"],
            "source": "pasted_html",
            "league": league_id,
            "weight": 1.0
        })
        records.append({
            "team": m["away_team"],
            "opponent": m["home_team"],
            "date": m["date"],
            "venue": "away",
            "goals_for": away_goals,
            "goals_against": home_goals,
            "xg_for": m["away_xg"],
            "xg_against": m["home_xg"],
            "source": "pasted_html",
            "league": league_id,
            "weight": 1.0
        })
    return records

def parse_overrides(overrides_input):
    if not overrides_input:
        return None
    if isinstance(overrides_input, dict):
        return {int(k): float(v) for k, v in overrides_input.items()}
    if isinstance(overrides_input, str):
        try:
            parsed = json.loads(overrides_input)
            if isinstance(parsed, dict):
                return {int(k): float(v) for k, v in parsed.items()}
        except Exception:
            pass
    return None

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
        methodology_param = query_params.get('methodology', [None])[0] or query_params.get('methodology_id', [None])[0]
        metric_param = query_params.get('metric', [None])[0]

        home_overrides_param = query_params.get('home_overrides', [None])[0]
        away_overrides_param = query_params.get('away_overrides', [None])[0]

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
                    if not methodology_param:
                        methodology_param = payload.get('methodology') or payload.get('methodology_id')
                    if not metric_param:
                        metric_param = payload.get('metric')
                    if not home_overrides_param:
                        home_overrides_param = payload.get('home_overrides')
                    if not away_overrides_param:
                        away_overrides_param = payload.get('away_overrides')
                except json.JSONDecodeError:
                    html_content = body
            except Exception as e:
                pass

        # Validate league
        if not league:
            self.send_json({"error": "league parameter is required"}, 400)
            return

        # Defaults
        try:
            methodology_id = int(methodology_param) if methodology_param else 2
        except ValueError:
            methodology_id = 2

        metric = metric_param if metric_param else "xg"
        metric = metric.strip().lower()

        home_overrides = parse_overrides(home_overrides_param)
        away_overrides = parse_overrides(away_overrides_param)

        # 1. Load database
        database = load_match_database()

        # 2. Check if we should fall back to fetching/parsing HTML
        has_league_in_db = any(m.get("league", "").lower() == league.lower() for m in database)

        if not has_league_in_db and not html_content:
            # Try to fetch from OddAlerts directly
            url = f"https://www.oddalerts.com/xg/{league}"
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36'}
            )
            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    html_content = response.read().decode('utf-8')
            except Exception as e:
                pass

        # Parse HTML if league is not in DB and HTML is available
        if not has_league_in_db and html_content:
            try:
                parsed = parse_recent_results(html_content)
                database = map_parsed_to_db_schema(parsed, league)
            except Exception as e:
                pass

        # Check if we should extract teams or run prediction
        if not home_team or not away_team:
            # Get list of unique teams
            teams = sorted(list(set(m["team"] for m in database if m.get("league", "").lower() == league.lower())))
            if not teams and html_content:
                teams = self.extract_teams(html_content)

            self.send_json({"league": league, "teams": teams}, 200)
            return

        # Perform prediction
        try:
            # Active prediction
            # We fetch prediction for both metrics to be completely comprehensive and backwards compatible
            pred_xg = None
            pred_goals = None

            try:
                pred_xg = predict_fixture(
                    database, home_team, away_team, league,
                    methodology_id=methodology_id, metric="xg",
                    home_overrides=home_overrides, away_overrides=away_overrides
                )
            except Exception as e:
                pass

            try:
                pred_goals = predict_fixture(
                    database, home_team, away_team, league,
                    methodology_id=methodology_id, metric="goals",
                    home_overrides=home_overrides, away_overrides=away_overrides
                )
            except Exception as e:
                pass

            if not pred_xg and not pred_goals:
                raise ValueError("Could not calculate prediction for either xG or Goals.")

            # Silent comparisons
            comparisons = compute_all_comparisons(database, home_team, away_team, league)

            # Build response
            response_data = {
                "home_team": home_team,
                "away_team": away_team,
                "active_methodology": methodology_id,
                "active_metric": metric,
                "comparisons": comparisons
            }

            # Add xg-specific fields
            if pred_xg:
                # Update match dict weights
                home_matches_copied = [dict(m) for m in pred_xg["home_matches"]]
                away_matches_copied = [dict(m) for m in pred_xg["away_matches"]]
                for m, w in zip(home_matches_copied, pred_xg["home_weights"]):
                    m["weight"] = w
                for m, w in zip(away_matches_copied, pred_xg["away_weights"]):
                    m["weight"] = w

                response_data.update({
                    "home_expected_xg": pred_xg["home_expected"],
                    "away_expected_xg": pred_xg["away_expected"],
                    "combined_expected_xg": pred_xg["home_expected"] + pred_xg["away_expected"],
                    "home_last_xg_matches": home_matches_copied,
                    "away_last_xg_matches": away_matches_copied,
                })

            # Add goals-specific fields
            if pred_goals:
                # Update match dict weights
                home_matches_copied = [dict(m) for m in pred_goals["home_matches"]]
                away_matches_copied = [dict(m) for m in pred_goals["away_matches"]]
                for m, w in zip(home_matches_copied, pred_goals["home_weights"]):
                    m["weight"] = w
                for m, w in zip(away_matches_copied, pred_goals["away_weights"]):
                    m["weight"] = w

                response_data.update({
                    "home_expected_goals": pred_goals["home_expected"],
                    "away_expected_goals": pred_goals["away_expected"],
                    "combined_expected_goals": pred_goals["home_expected"] + pred_goals["away_expected"],
                    "home_last_goals_matches": home_matches_copied,
                    "away_last_goals_matches": away_matches_copied,
                })

            # Set default top-level expected fields matching the active metric
            active_pred = pred_xg if metric == "xg" else pred_goals
            if not active_pred:
                active_pred = pred_xg or pred_goals # fallback

            response_data.update({
                "home_expected": active_pred["home_expected"],
                "away_expected": active_pred["away_expected"],
                "combined_expected": active_pred["home_expected"] + active_pred["away_expected"],
                "meta": {
                    "home_avg_for": active_pred["home_avg_for"],
                    "home_avg_against": active_pred["home_avg_against"],
                    "away_avg_for": active_pred["away_avg_for"],
                    "away_avg_against": active_pred["away_avg_against"],
                    "home_matches_count": active_pred["home_matches_count"],
                    "away_matches_count": active_pred["away_matches_count"]
                }
            })

            self.send_json(response_data, 200)

        except Exception as e:
            self.send_json({"error": "Failed to calculate predictions", "details": str(e)}, 500)

    def extract_teams(self, html):
        # Normalize single quotes to double quotes for class names
        html = re.sub(r"class='([^']*)'", r'class="\1"', html)
        teams = set()

        def clean_name(name):
            name = name.replace('&amp;', '&').replace('&nbsp;', ' ')
            name = re.sub(r'<[^>]*>', '', name)
            return name.strip()

        parts = html.split('<div class="fixture')
        for part in parts[1:]:
            if part.startswith(' heading'):
                continue

            team_parts = part.split('<div class="team">')
            for tp in team_parts[1:3]:
                name_m = re.search(r'<div class="name">(.*?)</div>', tp, re.DOTALL)
                if name_m:
                    cleaned = clean_name(name_m.group(1))
                    if cleaned:
                        teams.add(cleaned)

        return sorted(list(teams))

    def send_json(self, data, status_code):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
