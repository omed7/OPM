import time
import os
from datetime import datetime, timedelta
from understatapi import UnderstatClient

_cached_active_season = None

def get_current_season():
    global _cached_active_season
    if _cached_active_season is not None:
        return _cached_active_season

    # Simplistic season logic: Understat uses the starting year of the season.
    now = datetime.now()
    if now.month >= 7:
        season = str(now.year)
    else:
        season = str(now.year - 1)

    # Verify if the season has any played matches on Understat yet
    try:
        client = UnderstatClient()
        time.sleep(1)
        matches = client.league(league='EPL').get_match_data(season)
        played_matches = [m for m in matches if m.get('isResult')]
        if not played_matches:
            fallback = str(int(season) - 1)
            print(f"Season {season} has no played matches on Understat yet. Falling back to most recently completed season {fallback}.")
            season = fallback
    except Exception as e:
        print(f"Error checking season {season} matches: {e}. Falling back to default simplistic calculation.")

    _cached_active_season = season
    return season

def get_team_matches(league_code, team_name, total_matches=4, season=None):
    if season is None:
        season = os.environ.get('SEASON', get_current_season())

    client = UnderstatClient()

    # Be a polite scraper
    time.sleep(2)

    # Fetch team data to find the team ID
    league_data = client.league(league=league_code).get_team_data(season)

    team_id = None
    for t_id, t_data in league_data.items():
        if t_data['title'].lower() == team_name.lower():
            team_id = t_id
            break

    if not team_id:
        raise ValueError(f"Team {team_name} not found in {league_code} for season {season}")

    time.sleep(2)

    league_matches = client.league(league=league_code).get_match_data(season)

    # Filter matches involving the team and where isResult is True (meaning it has been played)
    team_matches = [m for m in league_matches if m.get('isResult') and
                   (m['h']['id'] == team_id or m['a']['id'] == team_id)]

    # Sort by datetime descending
    team_matches.sort(key=lambda x: x['datetime'], reverse=True)

    home_matches_needed = total_matches // 2
    away_matches_needed = total_matches // 2

    selected_matches = []

    home_count = 0
    away_count = 0

    for m in team_matches:
        if home_count == home_matches_needed and away_count == away_matches_needed:
            break

        is_home = m['h']['id'] == team_id

        if is_home and home_count < home_matches_needed:
            selected_matches.append({
                'opponent': m['a']['title'],
                'date': m['datetime'],
                'venue': 'home',
                'xg_for': float(m['xG']['h']),
                'xg_against': float(m['xG']['a'])
            })
            home_count += 1
        elif not is_home and away_count < away_matches_needed:
            selected_matches.append({
                'opponent': m['h']['title'],
                'date': m['datetime'],
                'venue': 'away',
                'xg_for': float(m['xG']['a']),
                'xg_against': float(m['xG']['h'])
            })
            away_count += 1

    if home_count < home_matches_needed or away_count < away_matches_needed:
        print(f"Warning: Could not find enough matches for {team_name} in {league_code}. Found {home_count} home and {away_count} away.")

    return selected_matches

def get_played_matches(league_code, season=None):
    if season is None:
        season = os.environ.get('SEASON', get_current_season())

    client = UnderstatClient()
    # Be a polite scraper
    time.sleep(2)

    try:
        league_matches = client.league(league=league_code).get_match_data(season)
    except Exception as e:
        print(f"Error fetching league matches for {league_code}: {e}")
        return []

    return [m for m in league_matches if m.get('isResult')]

def get_upcoming_fixtures(league_code, season=None):
    if season is None:
        season = os.environ.get('SEASON', get_current_season())

    client = UnderstatClient()
    # Be a polite scraper
    time.sleep(2)

    try:
        league_matches = client.league(league=league_code).get_match_data(season)
    except Exception as e:
        print(f"Error fetching league matches for {league_code}: {e}")
        return []

    upcoming = [m for m in league_matches if not m.get('isResult')]

    if not upcoming:
        # For testing purposes in environments where no upcoming matches exist
        if os.environ.get('MOCK_UPCOMING') == '1':
            print(f"MOCK_UPCOMING is set. Returning mock upcoming fixtures for {league_code}.")
            # Use the last few matches as "upcoming" for demonstration if none are actually upcoming
            played = [m for m in league_matches if m.get('isResult')]
            if played:
                played.sort(key=lambda x: x['datetime'], reverse=True)
                mock_matches = played[:5]
                return [{
                    'home_team': m['h']['title'],
                    'away_team': m['a']['title'],
                    'date': m['datetime']
                } for m in mock_matches]

        return []

    # Sort by datetime
    upcoming.sort(key=lambda x: x['datetime'])

    # Get the datetime of the first upcoming match
    try:
        first_match_dt = datetime.strptime(upcoming[0]['datetime'], '%Y-%m-%d %H:%M:%S')
    except ValueError:
        # Fallback if format is different
        first_match_dt = datetime.strptime(upcoming[0]['datetime'].split(' ')[0], '%Y-%m-%d')

    # Define "next gameweek" as all matches within 7 days of the first one
    end_date = first_match_dt + timedelta(days=7)

    next_gameweek_matches = []
    for m in upcoming:
        try:
            match_dt = datetime.strptime(m['datetime'], '%Y-%m-%d %H:%M:%S')
        except ValueError:
            match_dt = datetime.strptime(m['datetime'].split(' ')[0], '%Y-%m-%d')

        if match_dt <= end_date:
            next_gameweek_matches.append({
                'home_team': m['h']['title'],
                'away_team': m['a']['title'],
                'date': m['datetime']
            })
        else:
            break

    return next_gameweek_matches
