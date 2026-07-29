import os
import requests
from datetime import datetime, timedelta

API_URL_TEMPLATE = "https://api.football-data.org/v4/competitions/{competition_code}/matches"

def fetch_football_data_league(competition_code, league_name, season, total_matches=4):
    api_key = os.environ.get('FOOTBALL_DATA_API_KEY')
    if not api_key:
        raise ValueError("FOOTBALL_DATA_API_KEY environment variable is required")

    headers = {
        'X-Auth-Token': api_key
    }

    params = {
        'season': season
    }

    url = API_URL_TEMPLATE.format(competition_code=competition_code)

    print(f"Fetching {league_name} data from football-data.org for season {season}...")
    response = requests.get(url, headers=headers, params=params)

    if response.status_code != 200:
        try:
            err_data = response.json()
            err_msg = err_data.get('message', response.text)
        except Exception:
            err_msg = response.text
        raise Exception(f"API Request failed with status {response.status_code}: {err_msg}")

    data = response.json()
    if 'matches' not in data:
        raise Exception(f"Unexpected API response format: {data}")

    fixtures = data['matches']

    status_counts = {}
    for item in fixtures:
        status = item.get('status', 'UNKNOWN')
        status_counts[status] = status_counts.get(status, 0) + 1

    print(f"Total fixtures returned: {len(fixtures)}")
    print(f"Fixture status breakdown: {status_counts}")
    if 'message' in data:
        print(f"API Message: {data['message']}")

    played_matches = []
    upcoming_matches = []

    for item in fixtures:
        status = item.get('status')

        # In football-data.org, 'FINISHED' is the status for played matches
        if status == 'FINISHED':
            played_matches.append(item)
        else: # Treat all non-finished as upcoming (TIMED, SCHEDULED, LIVE, etc.)
            upcoming_matches.append(item)

    # MOCK_UPCOMING FOR TESTING
    if not upcoming_matches and os.environ.get('MOCK_UPCOMING') == '1':
        print(f"MOCK_UPCOMING is set. Using last 5 matches as upcoming for {league_name}.")
        # Reverse chronological
        played_matches.sort(key=lambda x: x['utcDate'], reverse=True)
        upcoming_matches = played_matches[:5]
        played_matches = played_matches[5:]
        # Reverse upcoming back to chronological
        upcoming_matches.sort(key=lambda x: x['utcDate'])

    # Sort played matches by utcDate descending
    played_matches.sort(key=lambda x: x['utcDate'], reverse=True)

    # Sort upcoming matches by utcDate ascending
    upcoming_matches.sort(key=lambda x: x['utcDate'])

    if upcoming_matches:
        try:
            first_match_dt = datetime.strptime(upcoming_matches[0]['utcDate'], '%Y-%m-%dT%H:%M:%SZ')
        except ValueError:
            try:
                first_match_dt = datetime.strptime(upcoming_matches[0]['utcDate'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                first_match_dt = datetime.strptime(upcoming_matches[0]['utcDate'].split('T')[0], '%Y-%m-%d')

        # Filter to fixtures sharing the same date as the earliest one
        earliest_date_str = first_match_dt.strftime('%Y-%m-%d')

        filtered_upcoming = []
        for m in upcoming_matches:
            m_date = m['utcDate'].split('T')[0]
            if m_date == earliest_date_str:
                filtered_upcoming.append(m)
            else:
                break
        upcoming_matches = filtered_upcoming

    team_histories = {}

    # Helper to get match history for a team
    def get_history_for_team(team_id, team_name):
        if team_id in team_histories:
            return team_histories[team_id]

        home_count = 0
        away_count = 0
        home_matches_needed = total_matches // 2
        away_matches_needed = total_matches // 2

        selected_matches = []

        for m in played_matches:
            if home_count == home_matches_needed and away_count == away_matches_needed:
                break

            home_team = m.get('homeTeam') or {}
            away_team = m.get('awayTeam') or {}
            home_id = home_team.get('id')
            away_id = away_team.get('id')

            is_home = home_id == team_id
            is_away = away_id == team_id

            if not is_home and not is_away:
                continue

            match_date = m['utcDate'].split('T')[0]
            score_data = m.get('score', {})
            full_time_score = score_data.get('fullTime', {})
            goals_home = full_time_score.get('home')
            goals_away = full_time_score.get('away')

            if is_home and home_count < home_matches_needed:
                selected_matches.append({
                    'opponent': away_team.get('name'),
                    'date': match_date,
                    'venue': 'home',
                    'goals_for': goals_home,
                    'goals_against': goals_away
                })
                home_count += 1
            elif is_away and away_count < away_matches_needed:
                selected_matches.append({
                    'opponent': home_team.get('name'),
                    'date': match_date,
                    'venue': 'away',
                    'goals_for': goals_away,
                    'goals_against': goals_home
                })
                away_count += 1

        if home_count < home_matches_needed or away_count < away_matches_needed:
            print(f"Warning: Could not find enough matches for {team_name}. Found {home_count} home and {away_count} away.")

        team_histories[team_id] = selected_matches
        return selected_matches

    processed_upcoming = []

    # Process all upcoming matches
    for m in upcoming_matches:
        home_team = m.get('homeTeam') or {}
        away_team = m.get('awayTeam') or {}
        home_team_id = home_team.get('id')
        home_team_name = home_team.get('name')
        away_team_id = away_team.get('id')
        away_team_name = away_team.get('name')

        match_date = m['utcDate'].split('T')[0]

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
