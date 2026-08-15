"""Build static, season-specific team prediction-accuracy standings."""

from collections import defaultdict

from src.compute.season_policy import LEAGUE_SEASON_POLICIES, SeasonConfigurationError, season_start_date


VIEWS = ("overall", "for", "against")
METRICS = ("xg", "goals")


def _fixture_key(league, home_team, away_team, fixture_date):
    return (league, home_team, away_team, str(fixture_date)[:10])


def _season_label(league_id, fixture_date):
    season_start = season_start_date(league_id, fixture_date)
    start_year = int(season_start[:4])
    if LEAGUE_SEASON_POLICIES[league_id]["season_start_month"] == 1:
        return season_start, str(start_year)
    return season_start, f"{start_year}/{str(start_year + 1)[-2:]}"


def _empty_metric():
    return {"total": 0.0, "eligible_matches": 0}


def _empty_team():
    return {
        "matches_played": 0,
        "metrics": {
            view: {metric: _empty_metric() for metric in METRICS}
            for view in VIEWS
        },
    }


def _add_metric(team, view, metric, difference):
    metric_data = team["metrics"][view][metric]
    metric_data["total"] += difference
    metric_data["eligible_matches"] += 1


def _normalise_number(value):
    return round(float(value), 12)


def _metric_output(metric_data):
    if metric_data["eligible_matches"] == 0:
        return None
    total = _normalise_number(metric_data["total"])
    return {
        "total": total,
        "average": _normalise_number(total / metric_data["eligible_matches"]),
        "eligible_matches": metric_data["eligible_matches"],
    }


def _view_output(metrics):
    xg = _metric_output(metrics["xg"])
    goals = _metric_output(metrics["goals"])
    if xg is None or goals is None:
        xg_goals = None
    else:
        xg_goals = {
            "total": _normalise_number((xg["total"] + goals["total"]) / 2),
            "average": _normalise_number((xg["average"] + goals["average"]) / 2),
        }
    return {"xg": xg, "goals": goals, "xg_goals": xg_goals}


def build_standings_artifact(matches, predictions, league_names, version, generated_at):
    """Return a static standings artifact from home match rows and stored predictions.

    `matches` follows the existing team-perspective storage model. Only home-venue,
    completed rows are used so every completed fixture is represented exactly once.
    Prediction accuracy remains null when an original pre-match value is unavailable.
    """
    predictions_by_key = {}
    for prediction in predictions:
        league = prediction.get("league")
        home_team = prediction.get("home_team")
        away_team = prediction.get("away_team")
        fixture_date = prediction.get("date")
        if not all((league, home_team, away_team, fixture_date)):
            continue
        predictions_by_key[_fixture_key(league, home_team, away_team, fixture_date)] = prediction

    seasons = {}
    for match in matches:
        if match.get("venue") != "home":
            continue
        if match.get("goals_for") is None or match.get("goals_against") is None:
            continue

        league = match.get("league")
        home_team = match.get("team")
        away_team = match.get("opponent")
        fixture_date = match.get("date")
        if not all((league, home_team, away_team, fixture_date)):
            continue

        try:
            season_id, season_label = _season_label(league, fixture_date)
        except (KeyError, SeasonConfigurationError):
            continue

        season = seasons.setdefault(
            (league, season_id),
            {"id": season_id, "label": season_label, "teams": defaultdict(_empty_team)},
        )
        home = season["teams"][home_team]
        away = season["teams"][away_team]
        home["matches_played"] += 1
        away["matches_played"] += 1

        prediction = predictions_by_key.get(
            _fixture_key(league, home_team, away_team, fixture_date)
        )
        if prediction is None:
            continue

        for metric, actual_home_key, actual_away_key, prediction_home_key, prediction_away_key in (
            ("xg", "xg_for", "xg_against", "home_expected_xg", "away_expected_xg"),
            ("goals", "goals_for", "goals_against", "home_expected_goals", "away_expected_goals"),
        ):
            actual_home = match.get(actual_home_key)
            actual_away = match.get(actual_away_key)
            predicted_home = prediction.get(prediction_home_key)
            predicted_away = prediction.get(prediction_away_key)
            if any(value is None for value in (actual_home, actual_away, predicted_home, predicted_away)):
                continue

            home_for = float(actual_home) - float(predicted_home)
            home_against = float(actual_away) - float(predicted_away)
            away_for = home_against
            away_against = home_for

            _add_metric(home, "for", metric, home_for)
            _add_metric(home, "against", metric, home_against)
            _add_metric(home, "overall", metric, home_for + home_against)
            _add_metric(away, "for", metric, away_for)
            _add_metric(away, "against", metric, away_against)
            _add_metric(away, "overall", metric, away_for + away_against)

    leagues = []
    grouped_seasons = defaultdict(list)
    for (league_id, _season_id), season in seasons.items():
        teams = []
        for team_name, team in season["teams"].items():
            teams.append(
                {
                    "name": team_name,
                    "matches_played": team["matches_played"],
                    "views": {
                        view: _view_output(team["metrics"][view]) for view in VIEWS
                    },
                }
            )
        teams.sort(key=lambda team: team["name"].casefold())
        grouped_seasons[league_id].append(
            {"id": season["id"], "label": season["label"], "teams": teams}
        )

    for league_id in sorted(grouped_seasons, key=lambda value: league_names.get(value, value).casefold()):
        league_seasons = sorted(
            grouped_seasons[league_id], key=lambda season: season["id"], reverse=True
        )
        leagues.append(
            {
                "id": league_id,
                "name": league_names.get(league_id, league_id),
                "seasons": league_seasons,
            }
        )

    return {
        "schema_version": 1,
        "meta": {"version": version, "generated_at": generated_at},
        "leagues": leagues,
    }
