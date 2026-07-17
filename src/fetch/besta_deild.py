import os
import requests
from datetime import datetime

API_URL = "https://v3.football.api-sports.io/fixtures"
LEAGUE_ID = 164

def get_besta_deild_data(season="2026", total_matches=4):
    api_key = os.environ.get('API_FOOTBALL_KEY')
    if not api_key:
        raise ValueError("API_FOOTBALL_KEY environment variable is required")

    headers = {
        'x-apisports-key': api_key
    }

    params = {
        'league': LEAGUE_ID,
        'season': season
    }

    print(f"Fetching Besta deild karla data for season {season}...")
    response = requests.get(API_URL, headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"API Request failed with status {response.status_code}: {response.text}")

    data = response.json()
    if 'response' not in data:
        raise Exception(f"Unexpected API response format: {data}")

    fixtures = data['response']

    played_matches = []
    upcoming_matches = []

    for item in fixtures:
        status = item.get('fixture', {}).get('status', {}).get('short')

        # Determine if played based on status FT (Full Time), AET (After Extra Time), PEN (Penalties)
        if status in ['FT', 'AET', 'PEN']:
            played_matches.append(item)
        else: # Treat all non-finished as upcoming (NS, TBD, PST, etc.)
            upcoming_matches.append(item)

    # MOCK_UPCOMING FOR TESTING
    if not upcoming_matches and os.environ.get('MOCK_UPCOMING') == '1':
        print("MOCK_UPCOMING is set. Using last 5 matches as upcoming for Besta deild karla.")
        # Reverse chronological
        played_matches.sort(key=lambda x: x['fixture']['timestamp'], reverse=True)
        upcoming_matches = played_matches[:5]
        played_matches = played_matches[5:]
        # Reverse upcoming back to chronological
        upcoming_matches.sort(key=lambda x: x['fixture']['timestamp'])

    # Sort played matches by timestamp descending
    played_matches.sort(key=lambda x: x['fixture']['timestamp'], reverse=True)

    # Sort upcoming matches by timestamp ascending
    upcoming_matches.sort(key=lambda x: x['fixture']['timestamp'])

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

            is_home = m['teams']['home']['id'] == team_id
            is_away = m['teams']['away']['id'] == team_id

            if not is_home and not is_away:
                continue

            match_date = m['fixture']['date'].split('T')[0]

            if is_home and home_count < home_matches_needed:
                selected_matches.append({
                    'opponent': m['teams']['away']['name'],
                    'date': match_date,
                    'venue': 'home',
                    'goals_for': m['goals']['home'],
                    'goals_against': m['goals']['away']
                })
                home_count += 1
            elif is_away and away_count < away_matches_needed:
                selected_matches.append({
                    'opponent': m['teams']['home']['name'],
                    'date': match_date,
                    'venue': 'away',
                    'goals_for': m['goals']['away'],
                    'goals_against': m['goals']['home']
                })
                away_count += 1

        if home_count < home_matches_needed or away_count < away_matches_needed:
            print(f"Warning: Could not find enough matches for {team_name}. Found {home_count} home and {away_count} away.")

        team_histories[team_id] = selected_matches
        return selected_matches

    processed_upcoming = []

    # Process all upcoming matches
    for m in upcoming_matches:
        home_team_id = m['teams']['home']['id']
        home_team_name = m['teams']['home']['name']
        away_team_id = m['teams']['away']['id']
        away_team_name = m['teams']['away']['name']

        match_date = m['fixture']['date'].split('T')[0]

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
