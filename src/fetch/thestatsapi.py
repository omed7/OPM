"""Read-only TheStatsAPI support for the approved OPM historical-backfill dry run."""

import json
import math
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date

from src.compute.source_boundary import THESTATSAPI_CUTOFF, accepts_provider_record

BASE_URL = "https://api.thestatsapi.com/api"

# Each entry is explicit so resolution failures are reported rather than guessed.
THESTATSAPI_COMPETITIONS = {
    "superliga-argentina": (("Liga Profesional de Fútbol", "Argentina"),),
    "admiral-bundesliga": (("Austrian Bundesliga", "Austria"),),
    "pro-league-belgium": (("Pro League", "Belgium"),),
    "serie-a-brazil": (("Brasileirão Série A", "Brazil"),),
    "superliga-denmark": (("Danish Superliga", "Denmark"),),
    "2-bundesliga": (("2. Bundesliga", "Germany"),),
    "liga-mx": (
        ("Liga MX, Apertura", "Mexico"),
        ("Liga MX, Clausura", "Mexico"),
    ),
    "eredivisie": (("Eredivisie", "Netherlands"),),
    "eerste-divisie": (("Eerste Divisie", "Netherlands"),),
    "eliteserien": (("Eliteserien", "Norway"),),
    "liga-portugal": (("Liga Portugal Betclic", "Portugal"),),
    "pro-league-saudi": (("Saudi Pro League", "Saudi Arabia"),),
    "premiership": (("Scottish Premiership", "Scotland"),),
    "super-lig": (("Trendyol Süper Lig", "Turkey"),),
    "mls": (("MLS", "USA"),),
}


class TheStatsAPIError(RuntimeError):
    """Raised when the provider returns an unusable response."""


class TheStatsAPIClient:
    """Small REST client with no persistence side effects."""

    def __init__(
        self,
        api_key=None,
        opener=None,
        timeout=30,
        sleep=time.sleep,
        retries=4,
        request_interval_seconds=0.55,
    ):
        self.api_key = api_key or os.environ.get("THESTATSAPI_KEY")
        self.opener = opener or urllib.request.urlopen
        self.timeout = timeout
        self.sleep = sleep
        self.retries = retries
        self.request_interval_seconds = request_interval_seconds
        if not self.api_key:
            raise TheStatsAPIError("THESTATSAPI_KEY is required for the dry run.")

    def get(self, path, params=None):
        query = urllib.parse.urlencode(params or {})
        url = f"{BASE_URL}{path}"
        if query:
            url = f"{url}?{query}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "User-Agent": "OPM historical dry-run/1.0",
            },
        )
        for attempt in range(self.retries):
            try:
                with self.opener(request, timeout=self.timeout) as response:
                    payload = json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code != 429 or attempt == self.retries - 1:
                    raise TheStatsAPIError(
                        f"TheStatsAPI request failed for {path}: {exc}"
                    ) from exc
                self.sleep(min(15 * (attempt + 1), 60))
                continue
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise TheStatsAPIError(f"TheStatsAPI request failed for {path}: {exc}") from exc
            if not isinstance(payload, dict) or "data" not in payload:
                raise TheStatsAPIError(f"Unexpected TheStatsAPI response for {path}.")
            self.sleep(self.request_interval_seconds)
            return payload
        raise TheStatsAPIError(f"Rate limited after {self.retries} attempts for {path}.")

    def resolve_competition(self, name, country):
        payload = self.get("/football/competitions", {"search": name, "per_page": 20})
        matches = [
            item
            for item in payload["data"]
            if item.get("name") == name and item.get("country") == country
        ]
        if len(matches) != 1:
            raise TheStatsAPIError(
                f"Expected one competition for {name} ({country}); found {len(matches)}."
            )
        return matches[0]

    def get_seasons(self, competition_id):
        payload = self.get(f"/football/competitions/{competition_id}/seasons", {"per_page": 100})
        if not isinstance(payload["data"], list):
            raise TheStatsAPIError(f"Unexpected season data for {competition_id}.")
        return payload["data"]

    def get_finished_matches(self, competition_id, season_id):
        matches = []
        page = 1
        while True:
            payload = self.get(
                "/football/matches",
                {
                    "competition_id": competition_id,
                    "season_id": season_id,
                    "status": "finished",
                    "per_page": 100,
                    "page": page,
                },
            )
            page_rows = payload["data"]
            if not isinstance(page_rows, list):
                raise TheStatsAPIError(
                    f"Unexpected finished-match data for {competition_id}/{season_id}."
                )
            matches.extend(page_rows)
            meta = payload.get("meta") or {}
            total_pages = meta.get("total_pages")
            if not isinstance(total_pages, int) or page >= total_pages:
                return matches
            page += 1

    def get_match_stats(self, match_id):
        return self.get(f"/football/matches/{match_id}/stats")["data"]


def match_date(match):
    value = match.get("utc_date")
    if not value:
        raise TheStatsAPIError("Finished match is missing utc_date.")
    return date.fromisoformat(str(value)[:10])


def match_xg(stats):
    try:
        home_xg = stats["overview"]["expected_goals"]["all"]["home"]
        away_xg = stats["overview"]["expected_goals"]["all"]["away"]
    except (KeyError, TypeError) as exc:
        raise TheStatsAPIError("Match statistics are missing expected goals.") from exc
    if not all(
        isinstance(value, (int, float)) and math.isfinite(value)
        for value in (home_xg, away_xg)
    ):
        raise TheStatsAPIError("Match expected goals must be finite numeric values.")
    return float(home_xg), float(away_xg)


def coverage_for_season(client, league_id, competition, season):
    """Return counts only; never fetches match stats or writes any OPM data."""
    matches = client.get_finished_matches(competition["id"], season["id"])
    counts = {
        "finished_matches": len(matches),
        "before_cutoff": 0,
        "post_cutoff_excluded": 0,
        "xg_candidates": 0,
        "xg_unavailable": 0,
        "invalid_date": 0,
    }
    for fixture in matches:
        try:
            fixture_date = match_date(fixture)
        except (TheStatsAPIError, ValueError):
            counts["invalid_date"] += 1
            continue
        if not accepts_provider_record("thestatsapi", league_id, fixture_date):
            counts["post_cutoff_excluded"] += 1
            continue
        counts["before_cutoff"] += 1
        if fixture.get("xg_available"):
            counts["xg_candidates"] += 1
        else:
            counts["xg_unavailable"] += 1
    return {
        "provider_competition_id": competition["id"],
        "provider_competition_name": competition["name"],
        "provider_season_id": season["id"],
        "provider_season_name": season.get("name"),
        **counts,
    }


def build_coverage_report(client, league_ids=None, progress=None):
    """Build a complete in-memory dry-run report for selected retained leagues."""
    selected_leagues = tuple(league_ids or THESTATSAPI_COMPETITIONS)
    unknown_leagues = set(selected_leagues) - set(THESTATSAPI_COMPETITIONS)
    if unknown_leagues:
        raise TheStatsAPIError(
            f"Unknown TheStatsAPI dry-run leagues: {', '.join(sorted(unknown_leagues))}."
        )
    report = {
        "schema_version": 1,
        "mode": "dry_run",
        "provider": "thestatsapi",
        "cutoff": THESTATSAPI_CUTOFF.isoformat(),
        "requested_leagues": list(selected_leagues),
        "leagues": [],
    }
    for league_id in selected_leagues:
        identities = THESTATSAPI_COMPETITIONS[league_id]
        if progress:
            progress(league_id)
        league_report = {"league": league_id, "competitions": [], "resolution_errors": []}
        for name, country in identities:
            try:
                competition = client.resolve_competition(name, country)
                seasons = client.get_seasons(competition["id"])
                competition_report = {
                    "provider_competition_id": competition["id"],
                    "provider_competition_name": competition["name"],
                    "provider_country": competition["country"],
                    "seasons": [],
                }
                for season in seasons:
                    competition_report["seasons"].append(
                        coverage_for_season(client, league_id, competition, season)
                    )
                league_report["competitions"].append(competition_report)
            except TheStatsAPIError as exc:
                league_report["resolution_errors"].append(str(exc))
        report["leagues"].append(league_report)
    return report
