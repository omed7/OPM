"""Provider boundary for the approved one-time TheStatsAPI historical backfill."""

from datetime import date

THESTATSAPI_CUTOFF = date(2026, 8, 10)

RETAINED_ODDALERTS_LEAGUES = frozenset(
    {
        "admiral-bundesliga",
        "pro-league-belgium",
        "serie-a-brazil",
        "superliga-denmark",
        "2-bundesliga",
        "liga-mx",
        "eredivisie",
        "eerste-divisie",
        "eliteserien",
        "liga-portugal",
        "pro-league-saudi",
        "premiership",
        "super-lig",
        "mls",
    }
)


def parse_match_date(value):
    """Return the calendar-date identity used by OPM's existing match contract."""
    return date.fromisoformat(str(value)[:10])


def provider_for_historical_date(league_id, value):
    """Return the approved provider for a retained league/date, or None when unbounded."""
    if league_id not in RETAINED_ODDALERTS_LEAGUES:
        return None
    return "thestatsapi" if parse_match_date(value) < THESTATSAPI_CUTOFF else "oddalerts"


def accepts_provider_record(provider, league_id, value):
    """Whether a record is inside the approved provider boundary for its date."""
    return provider_for_historical_date(league_id, value) == provider
