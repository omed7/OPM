"""Validate the public league standings artifact."""

import json
import math
import re
import sys


SENSITIVE_PATTERN = re.compile(r"(supabase|service_role|api[_-]?key|authorization|bearer)", re.I)
VIEWS = {"overall", "for", "against"}
METRICS = {"xg", "goals", "xg_goals"}
PREDICTION_PROVENANCE = {"stored_pre_match", "reconstructed_historical", "mixed", "unavailable"}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _finite_number(value, field):
    _require(isinstance(value, (int, float)) and not isinstance(value, bool), f"{field} must be numeric.")
    _require(math.isfinite(value), f"{field} must be finite.")


def _validate_metric(metric, value, field):
    if value is None:
        return
    _require(isinstance(value, dict), f"{field} must be null or an object.")
    expected = {"total", "average"}
    if metric != "xg_goals":
        expected.add("eligible_matches")
    _require(set(value) == expected, f"{field} has unexpected keys.")
    _finite_number(value["total"], f"{field}.total")
    _finite_number(value["average"], f"{field}.average")
    if metric != "xg_goals":
        _require(
            isinstance(value["eligible_matches"], int) and value["eligible_matches"] > 0,
            f"{field}.eligible_matches must be a positive integer.",
        )


def validate(payload):
    _require(isinstance(payload, dict), "Artifact root must be an object.")
    _require(set(payload) == {"schema_version", "meta", "leagues"}, "Artifact root has unexpected keys.")
    _require(payload["schema_version"] == 2, "Unsupported schema version.")
    _require(isinstance(payload["meta"], dict), "meta must be an object.")
    _require(set(payload["meta"]) == {"version", "generated_at"}, "meta has unexpected keys.")
    _require(all(isinstance(payload["meta"][key], str) for key in payload["meta"]), "meta values must be strings.")
    _require(isinstance(payload["leagues"], list), "leagues must be an array.")

    league_ids = set()
    for league in payload["leagues"]:
        _require(isinstance(league, dict), "Each league must be an object.")
        _require(set(league) == {"id", "name", "seasons"}, "League has unexpected keys.")
        _require(isinstance(league["id"], str) and league["id"], "League id must be a non-empty string.")
        _require(league["id"] not in league_ids, "League ids must be unique.")
        league_ids.add(league["id"])
        _require(isinstance(league["name"], str) and league["name"], "League name must be a non-empty string.")
        _require(isinstance(league["seasons"], list), "League seasons must be an array.")

        season_ids = set()
        for season in league["seasons"]:
            _require(
                set(season) == {"id", "label", "prediction_provenance", "teams"},
                "Season has unexpected keys.",
            )
            _require(isinstance(season["id"], str) and season["id"], "Season id must be a non-empty string.")
            _require(season["id"] not in season_ids, "Season ids must be unique per league.")
            season_ids.add(season["id"])
            _require(isinstance(season["label"], str) and season["label"], "Season label must be a non-empty string.")
            _require(
                season["prediction_provenance"] in PREDICTION_PROVENANCE,
                "Season prediction provenance is invalid.",
            )
            _require(isinstance(season["teams"], list), "Season teams must be an array.")

            team_names = set()
            for team in season["teams"]:
                _require(set(team) == {"name", "matches_played", "views"}, "Team has unexpected keys.")
                _require(isinstance(team["name"], str) and team["name"], "Team name must be a non-empty string.")
                _require(team["name"] not in team_names, "Team names must be unique per season.")
                team_names.add(team["name"])
                _require(
                    isinstance(team["matches_played"], int) and team["matches_played"] > 0,
                    "matches_played must be a positive integer.",
                )
                _require(set(team["views"]) == VIEWS, "Team views have unexpected keys.")
                for view, metrics in team["views"].items():
                    _require(isinstance(metrics, dict) and set(metrics) == METRICS, f"{view} has unexpected metrics.")
                    for metric, value in metrics.items():
                        _validate_metric(metric, value, f"{team['name']}.{view}.{metric}")

    serialised = json.dumps(payload, ensure_ascii=False)
    _require(not SENSITIVE_PATTERN.search(serialised), "Artifact appears to contain sensitive content.")


def main(path):
    with open(path, encoding="utf-8") as artifact_file:
        payload = json.load(artifact_file)
    validate(payload)
    print(f"Validated {path}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "public/league_standings.json")
