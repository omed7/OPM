import json
import re
import unicodedata
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone

def resolve_oddalerts_dates(dates, current_dt=None, is_forward=False):
    if not current_dt:
        current_dt = datetime.now()

    months = {'Jan': 1, 'Feb': 2, 'Mar': 3, 'Apr': 4, 'May': 5, 'Jun': 6, 'Jul': 7, 'Aug': 8, 'Sep': 9, 'Oct': 10, 'Nov': 11, 'Dec': 12}

    resolved = {}
    last_month_num = None
    year = current_dt.year

    for idx, (pos, d_str) in enumerate(dates):
        # Match e.g. "Fri, Jul 31" or just "Jul 31" or "31 Jul"
        m = re.search(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b\s+(\d+)', d_str)
        if not m:
            m = re.search(r'\b(\d+)\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b', d_str)
            if m:
                mon_str, day_str = m.group(2), m.group(1)
            else:
                resolved[pos] = d_str
                continue
        else:
            mon_str, day_str = m.group(1), m.group(2)

        mon_num = months[mon_str]
        day_num = int(day_str)

        if not is_forward:
            # Reverse-chronological (Recent Results)
            if idx == 0:
                if mon_num > current_dt.month or (mon_num == current_dt.month and day_num > current_dt.day):
                    year -= 1
            else:
                if last_month_num is not None and mon_num > last_month_num:
                    year -= 1
        else:
            # Forward-chronological (Upcoming Fixtures)
            if idx == 0:
                if mon_num < current_dt.month:
                    year += 1
            else:
                if last_month_num is not None and mon_num < last_month_num:
                    year += 1

        last_month_num = mon_num
        formatted = f"{year:04d}-{mon_num:02d}-{day_num:02d}"
        resolved[pos] = formatted

    return resolved

UTC_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def normalize_team_name(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", normalized.casefold())


def parse_score(score):
    if not isinstance(score, str) or " - " not in score:
        return None
    try:
        home_goals, away_goals = score.split(" - ", 1)
        return int(home_goals.strip()), int(away_goals.strip())
    except ValueError:
        return None


def extract_xg_page_data(html):
    marker = "window.xgPageData ="
    marker_index = html.find(marker)
    if marker_index < 0:
        return None
    start = html.find("{", marker_index + len(marker))
    if start < 0:
        return None

    depth = 0
    in_string = False
    escaped = False
    end = None
    for index in range(start, len(html)):
        character = html[index]
        if in_string:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == '"':
                in_string = False
            continue
        if character == '"':
            in_string = True
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    if end is None:
        return None

    raw_payload = html[start:end]
    json_payload = re.sub(
        r"(^|[,{]\s*)(upcomingFixtures|teamStats)\s*:",
        r'\1"\2":',
        raw_payload,
    )
    try:
        payload = json.loads(json_payload)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload.get("teamStats"), dict):
        return None
    return payload


def has_utc_epoch_evidence(payload):
    for fixture in payload.get("upcomingFixtures", []):
        date_value = fixture.get("date") if isinstance(fixture, dict) else None
        timestamp = fixture.get("timestamp") if isinstance(fixture, dict) else None
        if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
            continue
        try:
            date_utc = datetime.strptime(date_value, UTC_DATETIME_FORMAT).replace(tzinfo=timezone.utc)
            epoch_utc = datetime.fromtimestamp(timestamp, timezone.utc)
        except (TypeError, ValueError, OverflowError, OSError):
            continue
        if date_utc == epoch_utc:
            return True
    return False


def completed_fixture_timestamps(html):
    payload = extract_xg_page_data(html)
    if not payload or not has_utc_epoch_evidence(payload):
        return []

    observed = defaultdict(list)
    for team in payload["teamStats"].values():
        if not isinstance(team, dict):
            continue
        owner_name = team.get("name")
        owner_id = team.get("id")
        for match in team.get("matches", []):
            if not isinstance(match, dict) or match.get("location") not in {"home", "away"}:
                continue
            try:
                match_datetime = datetime.strptime(match.get("date"), UTC_DATETIME_FORMAT)
                fixture_id = match["fixture_id"]
                league_id = match["league_id"]
                opponent_name = match["opponent"]
                opponent_id = match["opponent_id"]
                goals_for = int(match["goals_for"])
                goals_against = int(match["goals_against"])
            except (KeyError, TypeError, ValueError):
                continue
            if not isinstance(owner_name, str) or not isinstance(opponent_name, str):
                continue
            if match["location"] == "home":
                home = (owner_id, owner_name, goals_for)
                away = (opponent_id, opponent_name, goals_against)
            else:
                home = (opponent_id, opponent_name, goals_against)
                away = (owner_id, owner_name, goals_for)
            observed[(league_id, fixture_id)].append(
                (match_datetime, home, away)
            )

    fixtures = []
    for copies in observed.values():
        if len(copies) != 2:
            continue
        first_datetime, first_home, first_away = copies[0]
        if any(copy != copies[0] for copy in copies[1:]):
            continue
        fixtures.append({
            "home_team": first_home[1],
            "away_team": first_away[1],
            "home_goals": first_home[2],
            "away_goals": first_away[2],
            "date": first_datetime.strftime("%Y-%m-%d"),
            "kickoff_at": first_datetime.replace(tzinfo=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            ),
        })
    return fixtures


def enrich_completed_results_with_timestamps(results, html):
    candidates = completed_fixture_timestamps(html)
    for result in results:
        score = parse_score(result.get("score"))
        if not score:
            continue
        matching_candidates = [
            candidate
            for candidate in candidates
            if candidate["date"] == result.get("date")
            and candidate["home_goals"] == score[0]
            and candidate["away_goals"] == score[1]
            and normalize_team_name(candidate["home_team"])
            == normalize_team_name(result.get("home_team"))
            and normalize_team_name(candidate["away_team"])
            == normalize_team_name(result.get("away_team"))
        ]
        if len(matching_candidates) == 1:
            result["kickoff_at"] = matching_candidates[0]["kickoff_at"]
    return results


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
    resolved_dates = resolve_oddalerts_dates(dates, is_forward=False)

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

            xg_val = xg_m.group(1).strip() if xg_m else None
            name_val = name_m.group(1).strip() if name_m else ""

            if name_val and xg_val is not None:
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
                        "home_team": h_name,
                        "away_team": a_name,
                        "home_xg": h_xg,
                        "away_xg": a_xg,
                        "score": status_text,
                        "date": current_date
                    })
                except ValueError:
                    pass

    return enrich_completed_results_with_timestamps(matches, html)

def parse_upcoming_fixtures(html):
    dates_matches = []

    # Extract date strings and positions from fixtures
    for m in re.finditer(r'<article\b[^>]*\bclass="[^"]*\bcompetition-fixture\b[^"]*"[^>]*>(.*?)</article>', html, re.DOTALL):
        article_html = m.group(1)

        time_m = re.search(r'<div class="competition-fixture__time">\s*(.*?)\s*</div>', article_html, re.DOTALL)
        if time_m:
            time_str = time_m.group(1).strip()
            # It usually looks like "Sat 08 Aug, 21:30". Preserve the source
            # clock separately while retaining the date-only writer key.
            date_str = time_str.split(',')[0].strip()
            kickoff_match = re.search(r",\s*(\d{1,2}:\d{2})\b", time_str)
            kickoff_time = None
            if kickoff_match:
                hours, minutes = kickoff_match.group(1).split(":")
                kickoff_time = f"{int(hours):02d}:{minutes}"

            teams = []
            for team_m in re.finditer(r'<div class="competition-fixture__team">.*?<span>(.*?)</span>', article_html, re.DOTALL):
                team_name = team_m.group(1).strip()
                team_name = team_name.replace('&amp;', '&').replace('&nbsp;', ' ')
                team_name = re.sub(r'<[^>]*>', '', team_name).strip()
                teams.append(team_name)

            if len(teams) >= 2:
                dates_matches.append({
                    "pos": m.start(),
                    "date_str": date_str,
                    "kickoff_time": kickoff_time,
                    "home_team": teams[0],
                    "away_team": teams[1]
                })

    if not dates_matches:
        return []

    dates_for_resolver = [(dm["pos"], dm["date_str"]) for dm in dates_matches]
    resolved_dates = resolve_oddalerts_dates(dates_for_resolver, is_forward=True)

    fixtures = []
    for dm in dates_matches:
        date = resolved_dates.get(dm["pos"], dm["date_str"])
        try:
            datetime.strptime(date, '%Y-%m-%d')
        except ValueError:
            continue
        # Standardize format for output writer while retaining the source clock.
        fixture = {
            "home_team": dm["home_team"],
            "away_team": dm["away_team"],
            "date": date,
        }
        if dm.get("kickoff_time"):
            fixture["kickoff_time"] = dm["kickoff_time"]
        fixtures.append(fixture)

    if not fixtures:
        return []

    # Filter to next gameweek (within 7 days of the first upcoming match)
    try:
        first_match_dt = datetime.strptime(fixtures[0]['date'], '%Y-%m-%d')
    except ValueError:
        return fixtures  # fallback if parsing fails

    end_date = first_match_dt + timedelta(days=7)

    next_gameweek_matches = []
    for f in fixtures:
        try:
            match_dt = datetime.strptime(f['date'], '%Y-%m-%d')
            if match_dt <= end_date:
                next_gameweek_matches.append(f)
        except ValueError:
            next_gameweek_matches.append(f)

    return next_gameweek_matches
