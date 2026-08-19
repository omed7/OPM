"""League-aware season boundaries for OPM prediction history."""

from datetime import date


class SeasonConfigurationError(ValueError):
    """Raised when a league season policy is missing or invalid."""


# Each policy defines the first month of the competition stage used for predictions.
# July marks European-style and Apertura/Clausura transition leagues; January marks
# calendar-year competitions. This mapping is reviewed alongside league registry changes.
LEAGUE_SEASON_POLICIES = {
    # Understat: European cross-year leagues.
    "premier_league": {"season_start_month": 7, "provider": "understat"},
    "la_liga": {"season_start_month": 7, "provider": "understat"},
    "serie_a": {"season_start_month": 7, "provider": "understat"},
    "bundesliga": {"season_start_month": 7, "provider": "understat"},
    "ligue_1": {"season_start_month": 7, "provider": "understat"},
    # OddAlerts: summer/autumn-to-spring competitions and split-year stages.
    "admiral-bundesliga": {"season_start_month": 7, "provider": "oddalerts"},
    "pro-league-belgium": {"season_start_month": 7, "provider": "oddalerts"},
    "superliga-denmark": {"season_start_month": 7, "provider": "oddalerts"},
    "2-bundesliga": {"season_start_month": 7, "provider": "oddalerts"},
    "liga-mx": {"season_start_month": 7, "provider": "oddalerts"},
    "eredivisie": {"season_start_month": 7, "provider": "oddalerts"},
    "eerste-divisie": {"season_start_month": 7, "provider": "oddalerts"},
    "liga-portugal": {"season_start_month": 7, "provider": "oddalerts"},
    "pro-league-saudi": {"season_start_month": 7, "provider": "oddalerts"},
    "premiership": {"season_start_month": 7, "provider": "oddalerts"},
    "super-lig": {"season_start_month": 7, "provider": "oddalerts"},
    # OddAlerts: calendar-year competitions.
    "serie-a-brazil": {"season_start_month": 1, "provider": "oddalerts"},
    "eliteserien": {"season_start_month": 1, "provider": "oddalerts"},
    "mls": {"season_start_month": 1, "provider": "oddalerts"},
}


def _as_date(value):
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError) as error:
        raise SeasonConfigurationError(f"Invalid ISO-like date: {value}") from error


def validate_season_configuration(policies=LEAGUE_SEASON_POLICIES):
    for league_id, policy in policies.items():
        try:
            month = int(policy["season_start_month"])
        except (KeyError, TypeError, ValueError) as error:
            raise SeasonConfigurationError(
                f"League {league_id} has no valid season_start_month."
            ) from error
        if not 1 <= month <= 12:
            raise SeasonConfigurationError(
                f"League {league_id} season_start_month must be between 1 and 12."
            )
        if policy.get("provider") not in {"understat", "oddalerts"}:
            raise SeasonConfigurationError(
                f"League {league_id} has an unsupported provider."
            )
    return policies


def season_start_date(league_id, fixture_date):
    policies = validate_season_configuration()
    try:
        start_month = policies[league_id]["season_start_month"]
    except KeyError as error:
        raise SeasonConfigurationError(
            f"No season policy configured for league {league_id}."
        ) from error

    fixture_day = _as_date(fixture_date)
    start_year = fixture_day.year if fixture_day.month >= start_month else fixture_day.year - 1
    return date(start_year, start_month, 1).isoformat()


def provider_season_label(league_id, fixture_date):
    """Return the provider season label, currently the derived start year."""
    return season_start_date(league_id, fixture_date)[:4]


def filter_history_for_fixture(history, league_id, fixture_date):
    """Return records inside the fixture's season and strictly before kickoff date."""
    season_start = _as_date(season_start_date(league_id, fixture_date))
    fixture_day = _as_date(fixture_date)
    eligible = []

    for record in history:
        try:
            record_day = _as_date(record.get("date"))
        except SeasonConfigurationError:
            continue
        if season_start <= record_day < fixture_day:
            eligible.append(record)

    return eligible


def summarize_history_filter(history, league_id, fixture_date):
    """Return eligible history and non-sensitive filter counts for source health logs."""
    season_start = _as_date(season_start_date(league_id, fixture_date))
    fixture_day = _as_date(fixture_date)
    eligible = []
    counts = {
        "accepted": 0,
        "prior_season_filtered": 0,
        "future_filtered": 0,
        "invalid_date_filtered": 0,
    }

    for record in history:
        try:
            record_day = _as_date(record.get("date"))
        except SeasonConfigurationError:
            counts["invalid_date_filtered"] += 1
            continue
        if record_day < season_start:
            counts["prior_season_filtered"] += 1
        elif record_day >= fixture_day:
            counts["future_filtered"] += 1
        else:
            eligible.append(record)
            counts["accepted"] += 1

    return eligible, counts
