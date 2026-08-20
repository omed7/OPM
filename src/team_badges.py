"""Current-roster team badge bootstrap and non-blocking coverage helpers.

The one-time bootstrap retrieves current league rosters from ESPN's public team
feed and writes a static checked-in manifest. The scheduled data refresh does
not call ESPN: it only validates the manifest and warns when a newly published
fixture needs the existing initials fallback.
"""

from __future__ import annotations

import json
import os
import subprocess
import unicodedata
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ESPN_TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/{league_slug}/teams"
ESPN_SOURCE_URL = "https://www.espn.com/soccer/"
ESPN_LEAGUE_URL = "https://www.espn.com/soccer/teams/_/league/{league_slug}"
ESPN_BADGE_URL_PREFIX = "https://a.espncdn.com/"
ESPN_SOURCE_NAME = "ESPN"
ESPN_ATTRIBUTION = "Team badges: ESPN"

# These are ESPN's current competition slugs. The static manifest produced from
# them is the only asset used by OPM at runtime.
PROVIDER_LEAGUES = {
    "2-bundesliga": {"espn_slug": "ger.2"},
    "admiral-bundesliga": {"espn_slug": "aut.1"},
    "bundesliga": {"espn_slug": "ger.1"},
    "eerste-divisie": {"espn_slug": "ned.2"},
    "eliteserien": {"espn_slug": "nor.1"},
    "eredivisie": {"espn_slug": "ned.1"},
    "la_liga": {"espn_slug": "esp.1"},
    "liga-mx": {"espn_slug": "mex.1"},
    "liga-portugal": {"espn_slug": "por.1"},
    "ligue_1": {"espn_slug": "fra.1"},
    "mls": {"espn_slug": "usa.1"},
    "premier_league": {"espn_slug": "eng.1"},
    "premiership": {"espn_slug": "sco.1"},
    "pro-league-belgium": {"espn_slug": "bel.1"},
    "pro-league-saudi": {"espn_slug": "ksa.1"},
    "serie-a-brazil": {"espn_slug": "bra.1"},
    "serie_a": {"espn_slug": "ita.1"},
    "super-lig": {"espn_slug": "tur.1"},
    "superliga-denmark": {"espn_slug": "den.1"},
}


PayloadFetcher = Callable[[str], tuple[dict[str, Any] | None, str | None]]
RosterFetcher = Callable[[dict[str, str]], tuple[list[dict[str, Any]], str | None]]


def normalize_team_name(value: object) -> str:
    """Return a conservative, accent-insensitive canonical team name."""
    decomposed = unicodedata.normalize("NFKD", str(value))
    ascii_value = decomposed.encode("ascii", "ignore").decode("ascii")
    return "".join(character for character in ascii_value.casefold() if character.isalnum())


def fixture_teams(leagues: list[dict[str, Any]]) -> dict[str, set[str]]:
    """Return distinct published fixture team names grouped by OPM league ID."""
    teams_by_league: dict[str, set[str]] = {}
    for league in leagues:
        league_id = league.get("id")
        if not isinstance(league_id, str) or not league_id:
            continue
        teams = {
            team
            for fixture in league.get("fixtures", [])
            if isinstance(fixture, dict)
            for team in (fixture.get("home_team"), fixture.get("away_team"))
            if isinstance(team, str) and team
        }
        if teams:
            teams_by_league[league_id] = teams
    return teams_by_league


def fetch_espn_payload(url: str) -> tuple[dict[str, Any] | None, str | None]:
    """Fetch one ESPN public-feed JSON response without adding runtime dependencies."""
    request = urllib.request.Request(url, headers={"User-Agent": "OPM badge bootstrap"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError, json.JSONDecodeError) as error:
        # ESPN may reject Python's default HTTP client while accepting its own
        # browser-facing JSON feed through curl. This fallback is one read-only
        # request to the same fixed endpoint and is never used at OPM runtime.
        try:
            result = subprocess.run(
                ["curl", "--fail", "--silent", "--show-error", "--location", "--max-time", "20", url],
                check=False,
                capture_output=True,
                text=True,
                timeout=25,
            )
        except (OSError, subprocess.TimeoutExpired) as curl_error:
            return None, f"{error}; curl fallback failed: {curl_error}"
        if result.returncode != 0:
            return None, f"{error}; curl fallback failed: {result.stderr.strip()}"
        try:
            payload = json.loads(result.stdout)
        except (ValueError, json.JSONDecodeError) as json_error:
            return None, f"curl fallback returned invalid JSON: {json_error}"
    if not isinstance(payload, dict):
        return None, "ESPN response was not a JSON object."
    return payload, None


def fetch_provider_league_teams(
    provider_league: dict[str, str],
    payload_fetcher: PayloadFetcher = fetch_espn_payload,
) -> tuple[list[dict[str, Any]], str | None]:
    """Fetch one current ESPN league roster, returning provider failures as data."""
    league_slug = provider_league["espn_slug"]
    payload, error = payload_fetcher(ESPN_TEAMS_URL.format(league_slug=league_slug))
    if error is not None:
        return [], error
    assert payload is not None

    sports = payload.get("sports")
    if not isinstance(sports, list) or not sports or not isinstance(sports[0], dict):
        return [], "ESPN response did not contain a sport payload."
    leagues = sports[0].get("leagues")
    if not isinstance(leagues, list) or not leagues or not isinstance(leagues[0], dict):
        return [], "ESPN response did not contain a league roster."
    entries = leagues[0].get("teams")
    if not isinstance(entries, list):
        return [], "ESPN response did not contain team entries."

    records = [entry.get("team") for entry in entries if isinstance(entry, dict)]
    return [record for record in records if isinstance(record, dict)], None


def _primary_logo_url(team: dict[str, Any]) -> str | None:
    logos = team.get("logos")
    if not isinstance(logos, list):
        return None
    for logo in logos:
        if not isinstance(logo, dict):
            continue
        href = logo.get("href")
        rel = logo.get("rel")
        if isinstance(href, str) and href.startswith(ESPN_BADGE_URL_PREFIX):
            if not isinstance(rel, list) or "default" in rel:
                return href
    return None


def badge_record(provider_record: dict[str, Any], provider_league: dict[str, str]) -> dict[str, Any] | None:
    """Convert one validated ESPN team record to the public manifest shape."""
    team_id = provider_record.get("id")
    team_name = provider_record.get("displayName") or provider_record.get("name")
    badge_url = _primary_logo_url(provider_record)
    if not isinstance(team_id, str) or not team_id.isdigit():
        return None
    if not isinstance(team_name, str) or not team_name or badge_url is None:
        return None
    return {
        "provider_id": team_id,
        "provider_name": team_name,
        "provider_league": provider_league["espn_slug"],
        "badge_url": badge_url,
        "source_url": ESPN_LEAGUE_URL.format(league_slug=provider_league["espn_slug"]),
        "mapping_method": "espn_current_roster",
    }


def _badge_key_index(league_badges: dict[str, dict[str, Any]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for team_name in league_badges:
        normalized = normalize_team_name(team_name)
        if normalized:
            index.setdefault(normalized, []).append(team_name)
    return index


def resolve_manifest_badge(
    league_badges: dict[str, dict[str, Any]], team_name: str
) -> dict[str, Any] | None:
    """Resolve an exact or unique normalized public-name match without fuzzy matching."""
    direct = league_badges.get(team_name)
    if isinstance(direct, dict):
        return direct
    matches = _badge_key_index(league_badges).get(normalize_team_name(team_name), [])
    if len(matches) == 1:
        candidate = league_badges.get(matches[0])
        return candidate if isinstance(candidate, dict) else None
    return None


def build_bootstrap_manifest(
    existing_manifest: dict[str, Any],
    leagues: list[dict[str, Any]],
    roster_fetcher: RosterFetcher = fetch_provider_league_teams,
    generated_at: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build an all-current-roster manifest and a non-blocking resolution report."""
    del existing_manifest  # The generated manifest is intentionally current-roster only.
    badges: dict[str, dict[str, dict[str, Any]]] = {}
    pending: list[dict[str, str]] = []

    for league_id, provider_league in PROVIDER_LEAGUES.items():
        records, error = roster_fetcher(provider_league)
        if error is not None:
            pending.append(
                {
                    "league": league_id,
                    "team": "*",
                    "reason": "provider_lookup_failed",
                    "detail": error,
                }
            )
            continue

        league_badges: dict[str, dict[str, Any]] = {}
        records_by_normalized_name: dict[str, list[tuple[str, dict[str, Any]]]] = {}
        for record in records:
            converted = badge_record(record, provider_league)
            if converted is None:
                continue
            provider_name = converted["provider_name"]
            normalized_name = normalize_team_name(provider_name)
            if normalized_name:
                records_by_normalized_name.setdefault(normalized_name, []).append(
                    (provider_name, converted)
                )

        for candidates in records_by_normalized_name.values():
            if len(candidates) != 1:
                pending.extend(
                    {
                        "league": league_id,
                        "team": provider_name,
                        "reason": "ambiguous_provider_roster_name",
                    }
                    for provider_name, _record in candidates
                )
                continue
            provider_name, converted = candidates[0]
            league_badges[provider_name] = converted
        if not league_badges:
            pending.append(
                {
                    "league": league_id,
                    "team": "*",
                    "reason": "empty_provider_roster",
                }
            )
            continue
        badges[league_id] = dict(sorted(league_badges.items()))

    fixture_teams_by_league = fixture_teams(leagues)
    unmapped: dict[str, list[str]] = {}
    for league_id, teams in fixture_teams_by_league.items():
        league_badges = badges.get(league_id, {})
        unresolved = sorted(
            team for team in teams if resolve_manifest_badge(league_badges, team) is None
        )
        if unresolved:
            unmapped[league_id] = unresolved
            pending.extend(
                {
                    "league": league_id,
                    "team": team,
                    "reason": "no_current_roster_match",
                }
                for team in unresolved
            )

    manifest = {
        "schema_version": 1,
        "source": {
            "name": ESPN_SOURCE_NAME,
            "url": ESPN_SOURCE_URL,
            "attribution": ESPN_ATTRIBUTION,
            "reviewed_at": (generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        },
        "badges": dict(sorted(badges.items())),
        "unmapped": dict(sorted(unmapped.items())),
    }
    return manifest, {"resolved": badges, "pending": pending}


def validate_badge_manifest(manifest: dict[str, Any]) -> None:
    """Raise ValueError only for an invalid public manifest, never for missing coverage."""
    if manifest.get("schema_version") != 1:
        raise ValueError("team badge manifest schema_version must be 1")
    source = manifest.get("source")
    if not isinstance(source, dict):
        raise ValueError("team badge manifest source must be an object")
    if source.get("name") != ESPN_SOURCE_NAME:
        raise ValueError("team badge manifest must identify ESPN as its source")
    if source.get("url") != ESPN_SOURCE_URL:
        raise ValueError("team badge manifest source URL is invalid")
    if source.get("attribution") != ESPN_ATTRIBUTION:
        raise ValueError("team badge manifest attribution is invalid")

    badges = manifest.get("badges")
    unmapped = manifest.get("unmapped")
    if not isinstance(badges, dict) or not isinstance(unmapped, dict):
        raise ValueError("team badge manifest badges and unmapped must be objects")

    for league_id, league_badges in badges.items():
        if not isinstance(league_id, str) or not isinstance(league_badges, dict):
            raise ValueError("team badge manifest has an invalid league badge mapping")
        provider_league = PROVIDER_LEAGUES.get(league_id)
        if provider_league is None:
            raise ValueError(f"team badge manifest has an unsupported league: {league_id}")
        seen_normalized_names: set[str] = set()
        for team_name, record in league_badges.items():
            if not isinstance(team_name, str) or not isinstance(record, dict):
                raise ValueError("team badge manifest has an invalid badge record")
            provider_id = record.get("provider_id")
            if not isinstance(provider_id, str) or not provider_id.isdigit():
                raise ValueError(f"team badge provider ID is invalid for {league_id}:{team_name}")
            if not isinstance(record.get("badge_url"), str) or not record["badge_url"].startswith(
                ESPN_BADGE_URL_PREFIX
            ):
                raise ValueError(f"team badge URL is invalid for {league_id}:{team_name}")
            expected_source_url = ESPN_LEAGUE_URL.format(
                league_slug=provider_league["espn_slug"]
            )
            if record.get("source_url") != expected_source_url:
                raise ValueError(f"team badge source URL is invalid for {league_id}:{team_name}")
            if record.get("mapping_method") != "espn_current_roster":
                raise ValueError(f"team badge mapping method is invalid for {league_id}:{team_name}")
            if record.get("provider_league") != provider_league["espn_slug"]:
                raise ValueError(f"team badge provider league is invalid for {league_id}:{team_name}")
            normalized_name = normalize_team_name(team_name)
            if not normalized_name or normalized_name in seen_normalized_names:
                raise ValueError(f"team badge names are ambiguous for league {league_id}")
            seen_normalized_names.add(normalized_name)

    for league_id, teams in unmapped.items():
        if not isinstance(league_id, str) or not isinstance(teams, list):
            raise ValueError("team badge manifest has an invalid unmapped list")
        league_badges = badges.get(league_id, {})
        for team_name in teams:
            if not isinstance(team_name, str) or not team_name:
                raise ValueError("team badge manifest has an invalid unmapped team")
            if resolve_manifest_badge(league_badges, team_name) is not None:
                raise ValueError(
                    f"team badge manifest marks an already-resolved team unmapped: {league_id}:{team_name}"
                )


def badge_coverage(leagues: list[dict[str, Any]], manifest: dict[str, Any]) -> list[dict[str, str]]:
    """Return unresolved fixture teams; callers treat them as initials-fallback warnings."""
    badges = manifest.get("badges")
    if not isinstance(badges, dict):
        raise ValueError("team badge manifest badges must be an object")
    unresolved: list[dict[str, str]] = []
    for league_id, teams in fixture_teams(leagues).items():
        league_badges = badges.get(league_id, {})
        if not isinstance(league_badges, dict):
            league_badges = {}
        for team_name in sorted(teams):
            if resolve_manifest_badge(league_badges, team_name) is None:
                unresolved.append({"league": league_id, "team": team_name})
    return unresolved


def print_coverage_summary(unresolved: list[dict[str, str]]) -> None:
    """Emit CI-friendly fallback warnings and always allow the refresh to continue."""
    if not unresolved:
        print("Badge coverage: all published fixture teams have a crest mapping.")
        return
    labels = ", ".join(f"{item['league']}:{item['team']}" for item in unresolved)
    print(f"::warning title=Badge initials fallback::{labels}")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as summary:
            summary.write("## Teams using initials fallback\n\n")
            summary.write("| League | Team |\n| --- | --- |\n")
            for item in unresolved:
                summary.write(f"| {item['league']} | {item['team']} |\n")


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from disk with a concise contract error."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Validate then publish the manifest in a stable, reviewable JSON format."""
    validate_badge_manifest(manifest)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
