import time
from understatapi import UnderstatClient

def get_current_season():
    # Simplistic season logic: Understat uses the starting year of the season.
    # In August 2024, the season is 2024. In May 2025, the season is still 2024.
    import datetime
    now = datetime.datetime.now()
    if now.month >= 7:
        return str(now.year)
    else:
        return str(now.year - 1)

def get_team_matches(team_name, total_matches=4, season=None):
    if season is None:
        season = get_current_season()

    client = UnderstatClient()

    # Be a polite scraper
    time.sleep(2)

    # Fetch team data to find the team ID
    league_data = client.league(league='EPL').get_team_data(season)

    team_id = None
    for t_id, t_data in league_data.items():
        if t_data['title'].lower() == team_name.lower():
            team_id = t_id
            break

    if not team_id:
        raise ValueError(f"Team {team_name} not found in EPL for season {season}")

    time.sleep(2)

    # Get match data for the league to filter by team
    # (The alternative is getting all match data and parsing, or using get_match_data for the league)
    # Actually, we can get team match data directly if there's an endpoint, but the library
    # doesn't easily expose team match data directly by ID in a straightforward single call without parsing league matches.
    # Let's get the league matches and filter them for the team.

    league_matches = client.league(league='EPL').get_match_data(season)

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
        print(f"Warning: Could not find enough matches for {team_name}. Found {home_count} home and {away_count} away.")

    return selected_matches
