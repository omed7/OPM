def calculate_expected_xg(team_a_matches, team_b_matches):
    if not team_a_matches or not team_b_matches:
        raise ValueError("Match data for both teams is required.")

    def avg(lst):
        return sum(lst) / len(lst) if lst else 0

    team_a_xg_for = avg([m['xg_for'] for m in team_a_matches])
    team_a_xg_against = avg([m['xg_against'] for m in team_a_matches])

    team_b_xg_for = avg([m['xg_for'] for m in team_b_matches])
    team_b_xg_against = avg([m['xg_against'] for m in team_b_matches])

    team_a_expected = (team_a_xg_for + team_b_xg_against) / 2
    team_b_expected = (team_b_xg_for + team_a_xg_against) / 2

    return {
        'team_a_expected_xg': team_a_expected,
        'team_b_expected_xg': team_b_expected
    }
