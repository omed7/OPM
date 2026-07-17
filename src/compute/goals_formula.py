SAMPLE_SIZE = 4

def calculate_expected_goals(team_a_matches, team_b_matches):
    if not team_a_matches or not team_b_matches:
        raise ValueError("Match data for both teams is required.")

    def avg(lst):
        return sum(lst) / len(lst) if lst else 0

    team_a_goals_for = avg([m['goals_for'] for m in team_a_matches])
    team_a_goals_against = avg([m['goals_against'] for m in team_a_matches])

    team_b_goals_for = avg([m['goals_for'] for m in team_b_matches])
    team_b_goals_against = avg([m['goals_against'] for m in team_b_matches])

    team_a_expected = (team_a_goals_for + team_b_goals_against) / 2
    team_b_expected = (team_b_goals_for + team_a_goals_against) / 2

    return {
        'team_a_expected_goals': team_a_expected,
        'team_b_expected_goals': team_b_expected
    }
