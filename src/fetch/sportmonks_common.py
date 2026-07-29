import os
import requests
from datetime import datetime, timedelta

API_BASE_URL = "https://api.sportmonks.com/v3/football/"

def fetch_sportmonks_league(league_id, league_name, season, total_matches=4):
    """
    Fetches matches for a given league and season from Sportmonks v3 API.
    Auth is performed via query parameter 'api_token' or 'Authorization' header.
    Requires 'SPORTMONKS_API_KEY' environment variable.
    """
    api_key = os.environ.get('SPORTMONKS_API_KEY')
    if not api_key:
        raise ValueError("SPORTMONKS_API_KEY environment variable is required")

    headers = {
        "Authorization": api_key
    }

    # Calculate a date range to fetch fixtures: from 30 days ago to 30 days from now
    today = datetime.now()
    start_date = (today - timedelta(days=30)).strftime('%Y-%m-%d')
    end_date = (today + timedelta(days=30)).strftime('%Y-%m-%d')

    # Sportmonks v3 fixtures between dates endpoint: /v3/football/fixtures/between/{start}/{end}
    url = f"{API_BASE_URL}fixtures/between/{start_date}/{end_date}"

    # We include team names, scores, stage, etc., and filter by league using key:value filters syntax.
    # In Sportmonks v3, filters can be supplied as a query parameter string: filters=fixtureLeagues:8
    params = {
        "include": "participants;scores;state;round;venue",
        "filters": f"fixtureLeagues:{league_id}"
    }

    print(f"Fetching {league_name} data from Sportmonks for season {season} between {start_date} and {end_date}...")
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"Sportmonks API request failed with status {response.status_code}: {response.text}")

    data = response.json()
    fixtures = data.get('data', [])

    played_matches = []
    upcoming_matches = []

    for item in fixtures:
        state_info = item.get('state', {})
        state_name = state_info.get('name') if isinstance(state_info, dict) else state_info

        # State name is "FINISHED" for played matches, or check scores / results.
        if state_name == "FINISHED":
            played_matches.append(item)
        else:
            upcoming_matches.append(item)

    # MOCK_UPCOMING FOR TESTING
    if not upcoming_matches and os.environ.get('MOCK_UPCOMING') == '1':
        print(f"MOCK_UPCOMING is set. Using last 5 matches as upcoming for {league_name}.")
        # Sort by starting_at descending
        played_matches.sort(key=lambda x: x.get('starting_at', ''), reverse=True)
        upcoming_matches = played_matches[:5]
        played_matches = played_matches[5:]
        # Reverse upcoming back to chronological
        upcoming_matches.sort(key=lambda x: x.get('starting_at', ''))

    # Sort played matches by starting_at descending
    played_matches.sort(key=lambda x: x.get('starting_at', ''), reverse=True)

    # Sort upcoming matches by starting_at ascending
    upcoming_matches.sort(key=lambda x: x.get('starting_at', ''))

    if upcoming_matches:
        first_date_str = upcoming_matches[0].get('starting_at', '').split(' ')[0]

        filtered_upcoming = []
        for m in upcoming_matches:
            m_date = m.get('starting_at', '').split(' ')[0]
            if m_date == first_date_str:
                filtered_upcoming.append(m)
            else:
                break
        upcoming_matches = filtered_upcoming

    team_histories = {}

    def get_history_for_team(team_id, team_name):
        if team_id in team_histories:
            return team_histories[team_id]

        home_count = 0
        away_count = 0
        home_needed = total_matches // 2
        away_needed = total_matches // 2

        selected = []

        for m in played_matches:
            if home_count == home_needed and away_count == away_needed:
                break

            participants = m.get('participants', [])
            home_part = None
            away_part = None
            for p in participants:
                meta = p.get('meta', {})
                if meta.get('location') == 'home':
                    home_part = p
                elif meta.get('location') == 'away':
                    away_part = p

            if not home_part or not away_part:
                continue

            home_id = home_part.get('id')
            away_id = away_part.get('id')

            is_home = str(home_id) == str(team_id)
            is_away = str(away_id) == str(team_id)

            if not is_home and not is_away:
                continue

            match_date = m.get('starting_at', '').split(' ')[0]

            # Extract goals from scores
            scores = m.get('scores', [])
            goals_home = 0
            goals_away = 0
            for s in scores:
                score_meta = s.get('meta', {})
                if score_meta.get('type') == 'current': # current or overall fulltime score
                    if str(s.get('participant_id')) == str(home_id):
                        goals_home = s.get('score', {}).get('goals', 0)
                    elif str(s.get('participant_id')) == str(away_id):
                        goals_away = s.get('score', {}).get('goals', 0)

            if is_home and home_count < home_needed:
                selected.append({
                    'opponent': away_part.get('name'),
                    'date': match_date,
                    'venue': 'home',
                    'goals_for': goals_home,
                    'goals_against': goals_away
                })
                home_count += 1
            elif is_away and away_count < away_needed:
                selected.append({
                    'opponent': home_part.get('name'),
                    'date': match_date,
                    'venue': 'away',
                    'goals_for': goals_away,
                    'goals_against': goals_home
                })
                away_count += 1

        if home_count < home_needed or away_count < away_needed:
            print(f"Warning: Could not find enough matches for {team_name}. Found {home_count} home and {away_count} away.")

        team_histories[team_id] = selected
        return selected

    processed_upcoming = []

    for m in upcoming_matches:
        participants = m.get('participants', [])
        home_part = None
        away_part = None
        for p in participants:
            meta = p.get('meta', {})
            if meta.get('location') == 'home':
                home_part = p
            elif meta.get('location') == 'away':
                away_part = p

        if not home_part or not away_part:
            continue

        home_team_id = home_part.get('id')
        home_team_name = home_part.get('name')
        away_team_id = away_part.get('id')
        away_team_name = away_part.get('name')

        match_date = m.get('starting_at', '').split(' ')[0]

        home_history = get_history_for_team(home_team_id, home_team_name)
        away_history = get_history_for_team(away_team_id, away_team_name)

        processed_upcoming.append({
            'home_team': home_team_name,
            'away_team': away_team_name,
            'date': match_date,
            'home_history': home_history,
            'away_history': away_history
        })

    return processed_upcoming
