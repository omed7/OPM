"""Generate a read-only TheStatsAPI coverage report for OPM's approved backfill boundary."""

import argparse
import json
from pathlib import Path

from src.fetch.thestatsapi import TheStatsAPIClient, TheStatsAPIError, build_coverage_report


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate a read-only TheStatsAPI coverage report; does not write OPM data."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Path for the dry-run JSON report. Public artifacts are not valid outputs.",
    )
    parser.add_argument(
        "--leagues",
        help="Optional comma-separated retained league IDs for an incremental dry run.",
    )
    args = parser.parse_args(argv)
    output_path = Path(args.output)
    if output_path.parts and output_path.parts[0] == "public":
        raise ValueError("Dry-run output must not be written inside public/.")

    selected_leagues = None
    if args.leagues:
        selected_leagues = tuple(
            league_id.strip() for league_id in args.leagues.split(",") if league_id.strip()
        )
    report = build_coverage_report(
        TheStatsAPIClient(),
        league_ids=selected_leagues,
        progress=lambda league_id: print(f"Dry-running {league_id}...", flush=True),
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote read-only TheStatsAPI coverage report to {output_path}")


if __name__ == "__main__":
    try:
        main()
    except TheStatsAPIError as exc:
        raise SystemExit(f"TheStatsAPI dry run failed: {exc}") from exc
