"""Explicit historical TheStatsAPI import command.

The default mode is local-only: it validates a reviewed manifest and writes a
non-public summary. Production persistence requires both --write and the exact
--confirm-production-write acknowledgement.
"""

import argparse
import json
import math
from datetime import date
from pathlib import Path

from src.compute.source_boundary import accepts_provider_record
from src.fetch.thestatsapi import TheStatsAPIClient, TheStatsAPIError, match_xg
from src.output_writer import save_matches_to_supabase
from src.supabase_client import supabase_request


class HistoricalImportError(RuntimeError):
    """Raised when an approved historical manifest is unsafe or incomplete."""


CONFIRMATION = "I_APPROVE_HISTORICAL_PRODUCTION_WRITE"


def _non_public_path(value):
    path = Path(value)
    if "public" in path.parts:
        raise ValueError("Historical import outputs must not be written under public/.")
    return path


def _finite_xg(value, field):
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise HistoricalImportError(f"{field} must be a finite non-negative number.")
    return float(value)


def _required_fixture_value(fixture, field):
    value = fixture.get(field)
    if value in (None, ""):
        raise HistoricalImportError(f"Historical fixture is missing {field}.")
    return value


def _fixture_date(fixture):
    raw_date = str(_required_fixture_value(fixture, "date"))[:10]
    try:
        parsed = date.fromisoformat(raw_date)
    except ValueError as exc:
        raise HistoricalImportError(f"Historical fixture has invalid date: {raw_date}.") from exc
    league = _required_fixture_value(fixture, "league")
    if not accepts_provider_record("thestatsapi", league, parsed):
        raise HistoricalImportError(
            f"Historical fixture violates source boundary: {league} on {raw_date}."
        )
    return raw_date


def _fixture_score(fixture):
    home_goals = _required_fixture_value(fixture, "home_goals")
    away_goals = _required_fixture_value(fixture, "away_goals")
    if not all(isinstance(value, int) and value >= 0 for value in (home_goals, away_goals)):
        raise HistoricalImportError("Historical fixture goals must be non-negative integers.")
    return home_goals, away_goals


def _fixture_xg(fixture, client=None):
    manual = fixture.get("manual_xg")
    if manual is not None:
        if not isinstance(manual, dict):
            raise HistoricalImportError("manual_xg must be an object when supplied.")
        return (
            _finite_xg(manual.get("home"), "manual home xG"),
            _finite_xg(manual.get("away"), "manual away xG"),
            "thestatsapi_manual_override",
        )

    if fixture.get("provider_xg_available") is False:
        return None, None, "thestatsapi_goals_only"
    if fixture.get("provider_xg_available") is not True:
        raise HistoricalImportError("Historical fixture has unresolved xG.")
    if client is None:
        raise HistoricalImportError("A TheStatsAPI client is required to retrieve provider xG.")
    match_id = _required_fixture_value(fixture, "provider_match_id")
    home_xg, away_xg = match_xg(client.get_match_stats(match_id))
    return home_xg, away_xg, "thestatsapi"


def fixture_to_match_records(fixture, client=None):
    """Convert one reviewed fixture to two OPM team-perspective records."""
    fixture_date = _fixture_date(fixture)
    league = _required_fixture_value(fixture, "league")
    home_team = _required_fixture_value(fixture, "home_team")
    away_team = _required_fixture_value(fixture, "away_team")
    home_goals, away_goals = _fixture_score(fixture)
    home_xg, away_xg, source = _fixture_xg(fixture, client=client)
    common = {"date": fixture_date, "league": league, "source": source, "weight": 1.0}
    return [
        {
            **common,
            "team": home_team,
            "opponent": away_team,
            "venue": "home",
            "goals_for": home_goals,
            "goals_against": away_goals,
            "xg_for": home_xg,
            "xg_against": away_xg,
        },
        {
            **common,
            "team": away_team,
            "opponent": home_team,
            "venue": "away",
            "goals_for": away_goals,
            "goals_against": home_goals,
            "xg_for": away_xg,
            "xg_against": home_xg,
        },
    ]


def load_manifest(path):
    try:
        fixture_list = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HistoricalImportError(f"Could not read historical manifest: {exc}") from exc
    if not isinstance(fixture_list, list):
        raise HistoricalImportError("Historical manifest must be a JSON array.")
    return fixture_list


def summarize_manifest(fixtures):
    keys = set()
    manual_count = 0
    provider_count = 0
    goals_only_count = 0
    score_override_count = 0
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            raise HistoricalImportError("Historical manifest entries must be objects.")
        fixture_date = _fixture_date(fixture)
        league = _required_fixture_value(fixture, "league")
        home = _required_fixture_value(fixture, "home_team")
        away = _required_fixture_value(fixture, "away_team")
        _fixture_score(fixture)
        key = (league, fixture_date, home, away)
        if key in keys:
            raise HistoricalImportError(f"Duplicate historical fixture key: {key}.")
        keys.add(key)
        if fixture.get("manual_xg") is not None:
            _fixture_xg(fixture)
            manual_count += 1
            if fixture.get("score_source") == "user_supplied":
                score_override_count += 1
        elif fixture.get("provider_xg_available") is True:
            provider_count += 1
        elif fixture.get("provider_xg_available") is False:
            goals_only_count += 1
        else:
            raise HistoricalImportError(f"Historical fixture has unresolved xG: {key}.")
    return {
        "mode": "dry_run",
        "fixture_count": len(fixtures),
        "team_perspective_row_count": len(fixtures) * 2,
        "manual_xg_pair_count": manual_count,
        "provider_xg_fixture_count": provider_count,
        "goals_only_fixture_count": goals_only_count,
        "user_score_override_count": score_override_count,
    }


def build_match_records(fixtures, client):
    records = []
    for fixture in fixtures:
        records.extend(fixture_to_match_records(fixture, client=client))
    return records


def match_natural_key(record):
    return (
        record["team"],
        record["opponent"],
        record["date"],
        record["venue"],
        record["league"],
    )


def fixture_natural_keys(fixture):
    fixture_date = _fixture_date(fixture)
    league = _required_fixture_value(fixture, "league")
    home = _required_fixture_value(fixture, "home_team")
    away = _required_fixture_value(fixture, "away_team")
    _fixture_score(fixture)
    return {
        (home, away, fixture_date, "home", league),
        (away, home, fixture_date, "away", league),
    }


def load_existing_match_key_snapshot(path):
    snapshot_path = _non_public_path(path)
    try:
        rows = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HistoricalImportError(f"Could not read existing-key snapshot: {exc}") from exc
    if not isinstance(rows, list):
        raise HistoricalImportError("Existing-key snapshot must be a JSON array.")
    try:
        return {match_natural_key(row) for row in rows}
    except (KeyError, TypeError) as exc:
        raise HistoricalImportError("Existing-key snapshot contains an invalid record.") from exc


def fetch_existing_match_keys(league_ids, page_size=1000):
    """Read existing pre-cutoff match keys through the project Supabase seam."""
    if not league_ids:
        return set()
    league_filter = ",".join(sorted(league_ids))
    fields = "team,opponent,date,venue,league"
    offset = 0
    keys = set()
    while True:
        endpoint = (
            "/matches?select=" + fields
            + "&league=in.(" + league_filter + ")"
            + "&date=lt.2026-08-10"
            + "&order=league.asc,date.asc,team.asc,opponent.asc,venue.asc"
            + f"&limit={page_size}&offset={offset}"
        )
        page, error = supabase_request(endpoint)
        if error is not None:
            raise HistoricalImportError(f"Could not preflight existing match keys: {error}")
        if not isinstance(page, list):
            raise HistoricalImportError("Unexpected existing match-key response shape.")
        keys.update(match_natural_key(record) for record in page)
        if len(page) < page_size:
            return keys
        offset += page_size


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Explicit historical TheStatsAPI import.")
    parser.add_argument("--manifest", required=True, help="Reviewed non-public fixture manifest JSON.")
    parser.add_argument("--output", required=True, help="Non-public dry-run summary JSON path.")
    parser.add_argument("--write", action="store_true", help="Perform the separately approved production match write.")
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Read existing match keys and report conflict-filtered rows without writing.",
    )
    parser.add_argument(
        "--existing-keys",
        help="Optional non-public JSON snapshot of existing match natural keys for preflight only.",
    )
    parser.add_argument(
        "--confirm-production-write",
        help="Required exact acknowledgement when --write is used.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    output_path = _non_public_path(args.output)
    fixtures = load_manifest(args.manifest)
    summary = summarize_manifest(fixtures)
    if args.preflight and args.write:
        raise HistoricalImportError("--preflight and --write cannot be used together.")
    if args.existing_keys and not args.preflight:
        raise HistoricalImportError("--existing-keys is valid only with --preflight.")

    if args.preflight:
        manifest_keys = {
            natural_key
            for fixture in fixtures
            for natural_key in fixture_natural_keys(fixture)
        }
        existing_keys = (
            load_existing_match_key_snapshot(args.existing_keys)
            if args.existing_keys
            else fetch_existing_match_keys({fixture["league"] for fixture in fixtures})
        )
        summary["mode"] = "preflight"
        summary["existing_natural_key_count"] = len(manifest_keys & existing_keys)
        summary["new_team_perspective_row_count"] = len(manifest_keys - existing_keys)

    if args.write:
        if args.confirm_production_write != CONFIRMATION:
            raise HistoricalImportError(
                "--write requires --confirm-production-write " + CONFIRMATION
            )
        existing_keys = fetch_existing_match_keys(
            {fixture["league"] for fixture in fixtures}
        )
        client = TheStatsAPIClient()
        records = build_match_records(fixtures, client)
        new_records = [
            record for record in records if match_natural_key(record) not in existing_keys
        ]
        save_matches_to_supabase(new_records)
        summary["mode"] = "production_write"
        summary["existing_natural_key_count"] = len(
            {match_natural_key(record) for record in records} & existing_keys
        )
        summary["written_team_perspective_row_count"] = len(new_records)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(
        f"Historical import {summary['mode']} complete: "
        f"{summary['fixture_count']} fixtures, "
        f"{summary['team_perspective_row_count']} team-perspective rows."
    )
    return summary


if __name__ == "__main__":
    try:
        main()
    except (HistoricalImportError, TheStatsAPIError, ValueError) as exc:
        raise SystemExit(str(exc))
