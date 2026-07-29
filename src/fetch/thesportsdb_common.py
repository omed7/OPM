import datetime
import os
import requests

LEAGUE_LOOKUP_MAP = {
    "MLS": {"country": "United States", "target": "American Major League Soccer"},
    "Canadian Premier League": {"country": "Canada", "target": "Canadian Premier League"},
    "Norway Eliteserien": {"country": "Norway", "target": "Norwegian Eliteserien"},
    "Finland Veikkausliiga": {"country": "Finland", "target": "Finnish Veikkausliiga"}
}

ACTIVE_TEAMS = {
    "MLS": {
        "Inter Miami", "Columbus Crew", "Los Angeles FC", "LA Galaxy", "Seattle Sounders FC",
        "New York City FC", "Toronto FC", "New York Red Bulls", "Atlanta United", "Orlando City",
        "Philadelphia Union", "CF Montréal", "Austin FC", "Minnesota United", "FC Dallas",
        "San Jose Earthquakes", "Houston Dynamo", "Sporting Kansas City", "St. Louis City SC",
        "Portland Timbers", "Colorado Rapids", "FC Cincinnati", "Charlotte FC", "New England Revolution",
        "Chicago Fire", "Real Salt Lake", "Nashville SC", "Vancouver Whitecaps"
    },
    "Canadian Premier League": {
        "Atlético Ottawa", "Cavalry FC", "Forge FC", "HFX Wanderers", "Pacific FC", "Valour FC", "Vancouver FC", "York United"
    },
    "Norway Eliteserien": {
        "Bodoe/Glimt", "Brann", "Molde", "Tromso", "Viking", "Fredrikstad", "KFUM", "Rosenborg",
        "Sarpsborg 08", "Hamarkameratene", "Stroemsgodset", "Kristiansund BK", "Sandefjord", "FK Haugesund",
        "Lillestroem", "Odd Ballklubb"
    },
    "Finland Veikkausliiga": {
        "HJK Helsinki", "KuPS", "VPS", "SJK", "Inter Turku", "Gnistan", "Haka", "Lahti", "Mariehamn", "Oulu", "Ilves", "EIF"
    }
}

def fetch_league_id(league_name):
    info = LEAGUE_LOOKUP_MAP.get(league_name)
    if not info:
        raise ValueError(f"Unknown league name: {league_name}")

    country = info["country"]
    target_name = info["target"]

    url = f"https://www.thesportsdb.com/api/v1/json/123/search_all_leagues.php?c={country}&s=Soccer"
    print(f"Searching for league {league_name} (Country: {country}) via TheSportsDB...")
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Failed to search league: {response.status_code} - {response.text}")

    data = response.json()
    leagues = data.get("countries")
    if not leagues:
        raise Exception(f"No leagues found for country {country} in TheSportsDB")

    for l in leagues:
        if l.get("strLeague") == target_name:
            print(f"Found league {league_name} with TheSportsDB ID {l['idLeague']}")
            return l["idLeague"]

    raise Exception(f"League {target_name} not found in search results for {country}")

def check_plausibility(league_name, upcoming_events, played_events, total_matches):
    print(f"[{league_name}] Running plausibility check...")

    if not upcoming_events:
        print(f"[{league_name}] Plausibility check FAILED: No upcoming fixtures found.")
        return False, "No upcoming fixtures found"

    # Get active teams list
    active_teams = ACTIVE_TEAMS.get(league_name)
    if not active_teams:
        print(f"[{league_name}] Plausibility check FAILED: No active team names configured for validation.")
        return False, "No active team names configured"

    today_str = datetime.date.today().isoformat()

    # 1. Check dates and team names for upcoming fixtures
    for event in upcoming_events:
        home_team = event.get("strHomeTeam")
        away_team = event.get("strAwayTeam")
        event_date = event.get("dateEvent")

        if not home_team or not away_team or not event_date:
            print(f"[{league_name}] Plausibility check FAILED: Missing team names or date in upcoming event.")
            return False, "Missing event details"

        # Date check
        if event_date < today_str:
            print(f"[{league_name}] Plausibility check FAILED: Event date {event_date} is in the past (today is {today_str}).")
            return False, f"Stale event date: {event_date}"

        # Team check
        if home_team not in active_teams:
            print(f"[{league_name}] Plausibility check FAILED: Home team '{home_team}' is not recognizable/active.")
            return False, f"Unrecognized team: {home_team}"
        if away_team not in active_teams:
            print(f"[{league_name}] Plausibility check FAILED: Away team '{away_team}' is not recognizable/active.")
            return False, f"Unrecognized team: {away_team}"

    # 2. Check match history completeness for each team in upcoming fixtures
    needed = total_matches // 2
    for event in upcoming_events:
        for team_name in [event["strHomeTeam"], event["strAwayTeam"]]:
            home_count = 0
            away_count = 0
            for pe in played_events:
                is_home = pe.get("strHomeTeam") == team_name
                is_away = pe.get("strAwayTeam") == team_name
                if not is_home and not is_away:
                    continue

                home_score = pe.get("intHomeScore")
                away_score = pe.get("intAwayScore")
                if home_score is None or away_score is None or str(home_score).strip() == "" or str(away_score).strip() == "":
                    continue

                if is_home:
                    home_count += 1
                if is_away:
                    away_count += 1

            if home_count < needed or away_count < needed:
                print(f"[{league_name}] Plausibility check FAILED: Insufficient match history for '{team_name}' (found {home_count} home, {away_count} away; needed {needed} each).")
                return False, f"Insufficient match history for {team_name}"

    print(f"[{league_name}] Plausibility check PASSED!")
    return True, "Passed"

def fetch_thesportsdb_league(league_name, season, total_matches=4):
    league_id = fetch_league_id(league_name)

    # Fetch upcoming matches
    next_url = f"https://www.thesportsdb.com/api/v1/json/123/eventsnextleague.php?id={league_id}"
    next_resp = requests.get(next_url)
    if next_resp.status_code != 200:
        raise Exception(f"Failed to fetch upcoming events for {league_name}: {next_resp.status_code}")
    next_data = next_resp.json()
    upcoming_events = next_data.get("events") or []

    # Fetch season matches for history
    season_url = f"https://www.thesportsdb.com/api/v1/json/123/eventsseason.php?id={league_id}&s={season}"
    season_resp = requests.get(season_url)
    if season_resp.status_code != 200:
        raise Exception(f"Failed to fetch season events for {league_name}: {season_resp.status_code}")
    season_data = season_resp.json()
    season_events = season_data.get("events") or []

    played_events = []
    for e in season_events:
        h_score = e.get("intHomeScore")
        a_score = e.get("intAwayScore")
        if h_score is not None and a_score is not None and str(h_score).strip() != "" and str(a_score).strip() != "":
            played_events.append(e)

    print(f"[{league_name}] Upcoming events fetched: {len(upcoming_events)}")
    print(f"[{league_name}] Played events fetched: {len(played_events)}")

    # Run Plausibility Check
    is_plausible, reason = check_plausibility(league_name, upcoming_events, played_events, total_matches)
    if not is_plausible:
        raise Exception(f"Plausibility check failed: {reason}")

    played_events.sort(key=lambda x: x.get("dateEvent", ""), reverse=True)

    team_histories = {}

    def get_history_for_team(team_name):
        if team_name in team_histories:
            return team_histories[team_name]

        home_count = 0
        away_count = 0
        home_needed = total_matches // 2
        away_needed = total_matches // 2

        selected = []
        for pe in played_events:
            if home_count == home_needed and away_count == away_needed:
                break

            is_home = pe.get("strHomeTeam") == team_name
            is_away = pe.get("strAwayTeam") == team_name
            if not is_home and not is_away:
                continue

            match_date = pe.get("dateEvent")

            try:
                goals_for = int(pe.get("intHomeScore")) if is_home else int(pe.get("intAwayScore"))
                goals_against = int(pe.get("intAwayScore")) if is_home else int(pe.get("intHomeScore"))
            except (ValueError, TypeError):
                continue

            if is_home and home_count < home_needed:
                selected.append({
                    'opponent': pe.get("strAwayTeam"),
                    'date': match_date,
                    'venue': 'home',
                    'goals_for': goals_for,
                    'goals_against': goals_against
                })
                home_count += 1
            elif is_away and away_count < away_needed:
                selected.append({
                    'opponent': pe.get("strHomeTeam"),
                    'date': match_date,
                    'venue': 'away',
                    'goals_for': goals_for,
                    'goals_against': goals_against
                })
                away_count += 1

        team_histories[team_name] = selected
        return selected

    processed_upcoming = []
    for ue in upcoming_events:
        home_team = ue.get("strHomeTeam")
        away_team = ue.get("strAwayTeam")
        match_date = ue.get("dateEvent")

        home_history = get_history_for_team(home_team)
        away_history = get_history_for_team(away_team)

        processed_upcoming.append({
            'home_team': home_team,
            'away_team': away_team,
            'date': match_date,
            'home_history': home_history,
            'away_history': away_history
        })

    return processed_upcoming
