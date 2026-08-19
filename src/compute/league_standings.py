"""Build static, season-specific team prediction-accuracy standings."""

from collections import defaultdict
from math import isfinite

from src.compute.methodology_config import (
    ACTIVE_METHODOLOGY,
    LAST_8_OLDER_SHARE,
    LAST_8_RECENT_SHARE,
    validate_methodology_configuration,
)
from src.compute.season_policy import (
    LEAGUE_SEASON_POLICIES,
    SeasonConfigurationError,
    filter_history_for_fixture,
    season_start_date,
)
from src.compute.venue_weighted_methodology import (
    IncompleteHistoryError,
    MissingMetricDataError,
    calculate_fixture_expectation,
)


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
            view: {**{metric: _empty_metric() for metric in METRICS}, "xg_goals": _empty_metric()}
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
    combined = _metric_output(metrics["xg_goals"])
    xg_goals = (
        None
        if combined is None
        else {"total": combined["total"], "average": combined["average"]}
    )
    return {"xg": xg, "goals": goals, "xg_goals": xg_goals}


def _team_record(fixture, side):
    if side == "home":
        return {
            "date": fixture["date"],
            "venue": "home",
            "xg_for": fixture["xg_for"],
            "xg_against": fixture["xg_against"],
            "goals_for": fixture["goals_for"],
            "goals_against": fixture["goals_against"],
        }
    return {
        "date": fixture["date"],
        "venue": "away",
        "xg_for": fixture["xg_against"],
        "xg_against": fixture["xg_for"],
        "goals_for": fixture["goals_against"],
        "goals_against": fixture["goals_for"],
    }


def _has_usable_metric(record, metric):
    fields = ("xg_for", "xg_against") if metric == "xg" else ("goals_for", "goals_against")
    try:
        return all(isfinite(float(record.get(field))) for field in fields)
    except (TypeError, ValueError):
        return False


def _metric_history(history, metric):
    """Keep only prior records with both values for the requested metric."""
    return {
        venue: [record for record in records if _has_usable_metric(record, metric)]
        for venue, records in history.items()
    }


def _reconstruct_prediction(history_by_team, fixture):
    """Replay each available metric without allowing any same-day or later result."""
    configuration = validate_methodology_configuration(
        ACTIVE_METHODOLOGY,
        LAST_8_RECENT_SHARE,
        LAST_8_OLDER_SHARE,
    )
    league = fixture["league"]
    fixture_date = fixture["date"]
    home_history = {
        venue: filter_history_for_fixture(records, league, fixture_date)
        for venue, records in history_by_team[fixture["team"]].items()
    }
    away_history = {
        venue: filter_history_for_fixture(records, league, fixture_date)
        for venue, records in history_by_team[fixture["opponent"]].items()
    }

    prediction = {}
    for metric, home_key, away_key in (
        ("xg", "home_expected_xg", "away_expected_xg"),
        ("goals", "home_expected_goals", "away_expected_goals"),
    ):
        try:
            expectation = calculate_fixture_expectation(
                _metric_history(home_history, metric),
                _metric_history(away_history, metric),
                methodology=configuration["active_methodology"],
                metric=metric,
                recent_share=configuration["recent_share"],
                older_share=configuration["older_share"],
            )
        except (IncompleteHistoryError, MissingMetricDataError):
            continue
        prediction[home_key] = expectation["home_expected"]
        prediction[away_key] = expectation["away_expected"]
    return prediction or None


def _apply_prediction(season, fixture, prediction):
    home = season["teams"][fixture["team"]]
    away = season["teams"][fixture["opponent"]]
    used_metric = False
    differences = {}
    for metric, actual_home_key, actual_away_key, prediction_home_key, prediction_away_key in (
        ("xg", "xg_for", "xg_against", "home_expected_xg", "away_expected_xg"),
        ("goals", "goals_for", "goals_against", "home_expected_goals", "away_expected_goals"),
    ):
        actual_home = fixture.get(actual_home_key)
        actual_away = fixture.get(actual_away_key)
        predicted_home = prediction.get(prediction_home_key)
        predicted_away = prediction.get(prediction_away_key)
        if any(value is None for value in (actual_home, actual_away, predicted_home, predicted_away)):
            continue

        home_for = float(actual_home) - float(predicted_home)
        home_against = float(actual_away) - float(predicted_away)
        away_for = home_against
        away_against = home_for
        differences[metric] = {
            "home": {"for": home_for, "against": home_against, "overall": home_for + home_against},
            "away": {"for": away_for, "against": away_against, "overall": away_for + away_against},
        }
        for view, difference in differences[metric]["home"].items():
            _add_metric(home, view, metric, difference)
        for view, difference in differences[metric]["away"].items():
            _add_metric(away, view, metric, difference)
        used_metric = True

    if set(differences) == set(METRICS):
        for view in VIEWS:
            _add_metric(
                home,
                view,
                "xg_goals",
                (differences["xg"]["home"][view] + differences["goals"]["home"][view]) / 2,
            )
            _add_metric(
                away,
                view,
                "xg_goals",
                (differences["xg"]["away"][view] + differences["goals"]["away"][view]) / 2,
            )
    return used_metric


def _prediction_provenance(sources):
    if not sources:
        return "unavailable"
    if len(sources) == 1:
        return next(iter(sources))
    return "mixed"


def _normalise_completed_home_fixture(match):
    if match.get("venue") != "home":
        return None
    if match.get("goals_for") is None or match.get("goals_against") is None:
        return None
    fixture = {
        "team": match.get("team"),
        "opponent": match.get("opponent"),
        "date": str(match.get("date", ""))[:10],
        "league": match.get("league"),
        "goals_for": match.get("goals_for"),
        "goals_against": match.get("goals_against"),
        "xg_for": match.get("xg_for"),
        "xg_against": match.get("xg_against"),
    }
    if not all((fixture["team"], fixture["opponent"], fixture["date"], fixture["league"])):
        return None
    try:
        season_id, season_label = _season_label(fixture["league"], fixture["date"])
    except (KeyError, SeasonConfigurationError):
        return None
    fixture["season_id"] = season_id
    fixture["season_label"] = season_label
    return fixture


def build_standings_artifact(matches, predictions, league_names, version, generated_at):
    """Build standings from completed rows and stored or reconstructed predictions.

    Completed fixtures are evaluated by calendar date. Every prediction for a date is
    computed before that date's results enter history, preventing same-day leakage.
    Stored pre-match predictions retain priority; otherwise the active OPM formula is
    reconstructed only from earlier same-season team records.
    """
    predictions_by_key = {}
    for prediction in predictions:
        league = prediction.get("league")
        home_team = prediction.get("home_team")
        away_team = prediction.get("away_team")
        fixture_date = prediction.get("date")
        if all((league, home_team, away_team, fixture_date)):
            predictions_by_key[_fixture_key(league, home_team, away_team, fixture_date)] = prediction

    seasons = {}
    for match in matches:
        fixture = _normalise_completed_home_fixture(match)
        if fixture is None:
            continue
        season = seasons.setdefault(
            (fixture["league"], fixture["season_id"]),
            {
                "id": fixture["season_id"],
                "label": fixture["season_label"],
                "teams": defaultdict(_empty_team),
                "fixtures": [],
                "prediction_sources": set(),
            },
        )
        season["teams"][fixture["team"]]["matches_played"] += 1
        season["teams"][fixture["opponent"]]["matches_played"] += 1
        season["fixtures"].append(fixture)

    leagues = []
    grouped_seasons = defaultdict(list)
    for (league_id, _season_id), season in seasons.items():
        history_by_team = defaultdict(lambda: {"home": [], "away": []})
        fixtures_by_date = defaultdict(list)
        for fixture in season["fixtures"]:
            fixtures_by_date[fixture["date"]].append(fixture)

        for fixture_date in sorted(fixtures_by_date):
            fixtures_for_date = sorted(
                fixtures_by_date[fixture_date],
                key=lambda fixture: (fixture["team"].casefold(), fixture["opponent"].casefold()),
            )
            for fixture in fixtures_for_date:
                stored_prediction = predictions_by_key.get(
                    _fixture_key(
                        fixture["league"], fixture["team"], fixture["opponent"], fixture["date"]
                    )
                )
                source = "stored_pre_match"
                prediction = stored_prediction
                if prediction is None:
                    prediction = _reconstruct_prediction(history_by_team, fixture)
                    source = "reconstructed_historical"
                if prediction is not None and _apply_prediction(season, fixture, prediction):
                    season["prediction_sources"].add(source)

            for fixture in fixtures_for_date:
                history_by_team[fixture["team"]]["home"].append(_team_record(fixture, "home"))
                history_by_team[fixture["opponent"]]["away"].append(_team_record(fixture, "away"))

        teams = []
        for team_name, team in season["teams"].items():
            teams.append(
                {
                    "name": team_name,
                    "matches_played": team["matches_played"],
                    "views": {view: _view_output(team["metrics"][view]) for view in VIEWS},
                }
            )
        teams.sort(key=lambda team: team["name"].casefold())
        grouped_seasons[league_id].append(
            {
                "id": season["id"],
                "label": season["label"],
                "prediction_provenance": _prediction_provenance(season["prediction_sources"]),
                "teams": teams,
            }
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
        "schema_version": 2,
        "meta": {"version": version, "generated_at": generated_at},
        "leagues": leagues,
    }
