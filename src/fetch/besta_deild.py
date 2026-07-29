from fetch.api_football_common import fetch_api_football_league

LEAGUE_ID = 164

def get_besta_deild_data(season="2026", total_matches=4):
    return fetch_api_football_league(
        league_id=LEAGUE_ID,
        league_name="Besta deild karla",
        season=season,
        total_matches=total_matches
    )
