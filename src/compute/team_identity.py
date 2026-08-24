"""Canonical team identities for reviewed provider-name differences.

The mapping is deliberately league-scoped and explicit. Unknown names are preserved exactly
rather than guessed, so the system remains safe for future provider changes.
"""

from copy import copy

from src.compute.source_boundary import provider_for_historical_date


TEAM_ALIASES = {
    "serie-a-brazil": {
        "Athletico": "Athletico PR",
        "Red Bull Bragantino": "Bragantino",
    },
}


def canonical_team_name(league_id, team_name):
    """Return the reviewed display identity for a league/team input."""
    if not isinstance(team_name, str):
        return team_name
    return TEAM_ALIASES.get(league_id, {}).get(team_name, team_name)


def canonicalize_match_record(record):
    """Return a shallow canonicalized copy of a team-perspective match record."""
    canonical = copy(record)
    league_id = canonical.get("league")
    canonical["team"] = canonical_team_name(league_id, canonical.get("team"))
    canonical["opponent"] = canonical_team_name(league_id, canonical.get("opponent"))
    return canonical


def canonicalize_prediction_record(record):
    """Return a shallow canonicalized copy of a public/stored prediction record."""
    canonical = copy(record)
    league_id = canonical.get("league")
    canonical["home_team"] = canonical_team_name(league_id, canonical.get("home_team"))
    canonical["away_team"] = canonical_team_name(league_id, canonical.get("away_team"))
    return canonical


def canonical_fixture_key(record):
    """Return a stable fixture key after a match record has been canonicalized."""
    return (
        record.get("league"),
        record.get("team"),
        record.get("opponent"),
        str(record.get("date", ""))[:10],
        record.get("venue"),
    )


def record_uses_approved_source(record):
    """Keep unbounded leagues and enforce the retained OddAlerts source boundary."""
    league_id = record.get("league")
    fixture_date = record.get("date")
    try:
        expected_provider = provider_for_historical_date(league_id, fixture_date)
    except (TypeError, ValueError):
        return False
    if expected_provider is None:
        return True
    source = str(record.get("source") or "")
    if not source:
        return True
    if source == "thestatsapi_goals_only":
        source = "thestatsapi"
    return source == expected_provider


def _record_quality(record):
    return sum(
        value is not None
        for value in (
            record.get("goals_for"),
            record.get("goals_against"),
            record.get("xg_for"),
            record.get("xg_against"),
        )
    )


def canonical_boundary_valid_records(records):
    """Return canonical, boundary-valid, deterministically deduplicated match rows."""
    selected = {}
    for record in records:
        if not record_uses_approved_source(record):
            continue
        canonical = canonicalize_match_record(record)
        key = canonical_fixture_key(canonical)
        rank = (_record_quality(canonical), str(canonical.get("source") or ""))
        prior = selected.get(key)
        prior_rank = (
            _record_quality(prior), str(prior.get("source") or "")
        ) if prior is not None else None
        if prior is None or rank > prior_rank:
            selected[key] = canonical
    return [selected[key] for key in sorted(selected)]
