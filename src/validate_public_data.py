import json
import math
import re
import sys
from pathlib import Path


TOP_LEVEL_KEYS = {"meta", "leagues"}
LEAGUE_REQUIRED_FIELDS = {"id", "name", "metric", "fixtures"}
FIXTURE_IDENTITY_FIELDS = {"home_team", "away_team", "date"}
UNDERLYING_MATCH_REQUIRED_FIELDS = {
    "opponent",
    "date",
    "venue",
    "xg_for",
    "xg_against",
}
EXPECTED_METRIC_FIELDS = {
    "home_expected_xg",
    "away_expected_xg",
    "combined_expected_xg",
    "home_expected_goals",
    "away_expected_goals",
    "combined_expected_goals",
}
DATE_PREFIX_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")
KICKOFF_TIME_PATTERN = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
KICKOFF_AT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\dZ$")
SENSITIVE_CONTENT_PATTERN = re.compile(
    r"SUP(?:ER)?BASE_(?:URL|KEY)|service_role|Authorization:\s*Bearer|"
    r"Bearer\s+[A-Za-z0-9._-]{20,}|Traceback \(most recent call last\)|"
    r"postgres(?:ql)?://[^\s]+@",
    re.IGNORECASE,
)


def validation_error(message):
    raise ValueError(message)


def is_finite_number_or_null(value):
    if value is None:
        return True
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def validate_date(value, location):
    if not isinstance(value, str) or not DATE_PREFIX_PATTERN.match(value):
        validation_error(f"{location} must begin with YYYY-MM-DD")


def validate_underlying_matches(matches, location):
    if not isinstance(matches, list):
        validation_error(f"{location} must be an array")

    for index, match in enumerate(matches):
        match_location = f"{location}[{index}]"
        if not isinstance(match, dict):
            validation_error(f"{match_location} must be an object")
        missing_fields = UNDERLYING_MATCH_REQUIRED_FIELDS - set(match)
        if missing_fields:
            validation_error(
                f"{match_location} is missing required fields: {sorted(missing_fields)}"
            )
        if not isinstance(match["opponent"], str):
            validation_error(f"{match_location}.opponent must be a string")
        validate_date(match["date"], f"{match_location}.date")
        if match["venue"] not in {"home", "away"}:
            validation_error(f"{match_location}.venue must be home or away")
        for field in ("xg_for", "xg_against"):
            if not is_finite_number_or_null(match[field]):
                validation_error(f"{match_location}.{field} must be a finite number or null")


def validate_fixture(fixture, location):
    if not isinstance(fixture, dict):
        validation_error(f"{location} must be an object")
    missing_fields = FIXTURE_IDENTITY_FIELDS - set(fixture)
    if missing_fields:
        validation_error(f"{location} is missing required fields: {sorted(missing_fields)}")

    for field in ("home_team", "away_team"):
        if not isinstance(fixture[field], str):
            validation_error(f"{location}.{field} must be a string")
    validate_date(fixture["date"], f"{location}.date")
    if "kickoff_time" in fixture and fixture["kickoff_time"] is not None:
        if not isinstance(fixture["kickoff_time"], str) or not KICKOFF_TIME_PATTERN.match(fixture["kickoff_time"]):
            validation_error(f"{location}.kickoff_time must be null or HH:MM")
    if "kickoff_at" in fixture:
        kickoff_at = fixture["kickoff_at"]
        if fixture.get("status") != "FINISHED":
            validation_error(f"{location}.kickoff_at requires status FINISHED")
        if not isinstance(kickoff_at, str) or not KICKOFF_AT_PATTERN.match(kickoff_at):
            validation_error(f"{location}.kickoff_at must be canonical UTC RFC3339")

    for field in EXPECTED_METRIC_FIELDS & set(fixture):
        if not is_finite_number_or_null(fixture[field]):
            validation_error(f"{location}.{field} must be a finite number or null")

    for field, value in fixture.items():
        if field.startswith(("home_last_", "away_last_")) and field.endswith("_matches"):
            validate_underlying_matches(value, f"{location}.{field}")


def validate_payload(payload, raw_text):
    if SENSITIVE_CONTENT_PATTERN.search(raw_text):
        validation_error("public artifact contains sensitive or internal error content")

    if not isinstance(payload, dict):
        validation_error("top-level JSON value must be an object")
    if set(payload) != TOP_LEVEL_KEYS:
        validation_error(
            f"top-level keys must be {sorted(TOP_LEVEL_KEYS)}, got {sorted(payload)}"
        )

    meta = payload["meta"]
    if not isinstance(meta, dict):
        validation_error("meta must be an object")
    for field in ("version", "generated_at"):
        if not isinstance(meta.get(field), str):
            validation_error(f"meta.{field} must be a string")

    leagues = payload["leagues"]
    if not isinstance(leagues, list):
        validation_error("leagues must be an array")

    league_ids = set()
    fixture_count = 0
    for index, league in enumerate(leagues):
        location = f"leagues[{index}]"
        if not isinstance(league, dict):
            validation_error(f"{location} must be an object")
        missing_fields = LEAGUE_REQUIRED_FIELDS - set(league)
        if missing_fields:
            validation_error(f"{location} is missing required fields: {sorted(missing_fields)}")
        for field in ("id", "name", "metric"):
            if not isinstance(league[field], str) or not league[field]:
                validation_error(f"{location}.{field} must be a non-empty string")
        if league["id"] in league_ids:
            validation_error(f"duplicate league id: {league['id']}")
        league_ids.add(league["id"])
        if not isinstance(league["fixtures"], list):
            validation_error(f"{location}.fixtures must be an array")

        for fixture_index, fixture in enumerate(league["fixtures"]):
            validate_fixture(fixture, f"{location}.fixtures[{fixture_index}]")
            fixture_count += 1

    return len(leagues), fixture_count


def main():
    if len(sys.argv) != 2:
        print("Usage: python validate_public_data.py <data.json>", file=sys.stderr)
        return 1

    path = Path(sys.argv[1])
    try:
        raw_text = path.read_text(encoding="utf-8")
        payload = json.loads(raw_text)
        league_count, fixture_count = validate_payload(payload, raw_text)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"Public data validation failed: {error}", file=sys.stderr)
        return 1

    print(
        f"Public data validation passed: leagues={league_count} fixtures={fixture_count}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
