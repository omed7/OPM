"""Venue-balanced OPM prediction methodology calculations."""

from math import isfinite

from src.compute.methodology_config import MethodologyConfigurationError


class IncompleteHistoryError(ValueError):
    """Raised when a team cannot supply the complete approved venue-balanced sample."""


class MissingMetricDataError(ValueError):
    """Raised when a selected record lacks a usable requested metric."""


_METHOD_REQUIREMENTS = {
    "main_last_4": 2,
    "last_8": 4,
}

_METRIC_FIELDS = {
    "xg": ("xg_for", "xg_against"),
    "goals": ("goals_for", "goals_against"),
}


def validate_last_8_shares(recent_share, older_share):
    """Validate and normalize the configurable Last-8 venue-group shares."""
    try:
        recent_share = float(recent_share)
        older_share = float(older_share)
    except (TypeError, ValueError) as error:
        raise MethodologyConfigurationError(
            "Last-8 weight shares must be numeric."
        ) from error

    if not 0 <= recent_share <= 1 or not 0 <= older_share <= 1:
        raise MethodologyConfigurationError(
            "Last-8 weight shares must be between 0 and 1."
        )
    if abs((recent_share + older_share) - 1.0) > 1e-9:
        raise MethodologyConfigurationError(
            "Last-8 recent and older shares must sum to 1."
        )

    return recent_share, older_share


def _selected_group(history, venue, required_count):
    try:
        candidates = history[venue]
    except (KeyError, TypeError) as error:
        raise IncompleteHistoryError(
            f"Missing {venue} history required for the selected methodology."
        ) from error

    ordered = sorted(candidates, key=lambda match: match.get("date", ""), reverse=True)
    selected = ordered[:required_count]
    if len(selected) != required_count:
        raise IncompleteHistoryError(
            f"Expected {required_count} {venue} matches, found {len(selected)}."
        )
    return selected


def _metric_value(match, field_name):
    value = match.get(field_name)
    try:
        numeric = float(value)
    except (TypeError, ValueError) as error:
        raise MissingMetricDataError(
            f"Selected match is missing usable {field_name}."
        ) from error
    if not isfinite(numeric):
        raise MissingMetricDataError(
            f"Selected match contains non-finite {field_name}."
        )
    return numeric


def _equal_average(matches, field_name):
    return sum(_metric_value(match, field_name) for match in matches) / len(matches)


def _last_8_group_average(matches, field_name, recent_share, older_share):
    recent_average = _equal_average(matches[:2], field_name)
    older_average = _equal_average(matches[2:], field_name)
    return (recent_average * recent_share) + (older_average * older_share)


def _team_averages(history, methodology, metric, recent_share, older_share):
    if methodology not in _METHOD_REQUIREMENTS:
        raise MethodologyConfigurationError(f"Unsupported methodology: {methodology}")
    if metric not in _METRIC_FIELDS:
        raise MethodologyConfigurationError(f"Unsupported metric: {metric}")

    required_count = _METHOD_REQUIREMENTS[methodology]
    home_matches = _selected_group(history, "home", required_count)
    away_matches = _selected_group(history, "away", required_count)
    for_field, against_field = _METRIC_FIELDS[metric]

    if methodology == "main_last_4":
        average = _equal_average
        home_for = average(home_matches, for_field)
        home_against = average(home_matches, against_field)
        away_for = average(away_matches, for_field)
        away_against = average(away_matches, against_field)
    else:
        recent_share, older_share = validate_last_8_shares(recent_share, older_share)
        home_for = _last_8_group_average(home_matches, for_field, recent_share, older_share)
        home_against = _last_8_group_average(home_matches, against_field, recent_share, older_share)
        away_for = _last_8_group_average(away_matches, for_field, recent_share, older_share)
        away_against = _last_8_group_average(away_matches, against_field, recent_share, older_share)

    return {
        "for_average": (home_for + away_for) / 2.0,
        "against_average": (home_against + away_against) / 2.0,
        "home_matches": home_matches,
        "away_matches": away_matches,
    }


def calculate_fixture_expectation(
    home_history,
    away_history,
    methodology="main_last_4",
    metric="xg",
    recent_share=0.70,
    older_share=0.30,
):
    """Calculate home, away, and combined expectations from venue-grouped histories."""
    home_averages = _team_averages(
        home_history, methodology, metric, recent_share, older_share
    )
    away_averages = _team_averages(
        away_history, methodology, metric, recent_share, older_share
    )

    home_expected = (
        home_averages["for_average"] + away_averages["against_average"]
    ) / 2.0
    away_expected = (
        away_averages["for_average"] + home_averages["against_average"]
    ) / 2.0

    return {
        "home_expected": home_expected,
        "away_expected": away_expected,
        "combined_expected": home_expected + away_expected,
        "home_history": home_averages,
        "away_history": away_averages,
    }
