#!/usr/bin/env python3
"""Bootstrap ESPN crest mappings for OPM's current league rosters.

Usage:
    python3 scripts/bootstrap_team_badges.py --dry-run
    python3 scripts/bootstrap_team_badges.py --write

The script never retrieves historical rosters. Provider failures and name
mismatches are reported as initials fallbacks; they do not make the command
fail unless its input or output manifest is structurally invalid.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src import team_badges  # noqa: E402


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Preview without changing the manifest.")
    mode.add_argument("--write", action="store_true", help="Validate and write the generated manifest.")
    parser.add_argument(
        "--data-path",
        type=Path,
        default=ROOT / "public" / "data.json",
        help="Published fixture artifact used only to identify initials-fallback warnings.",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=ROOT / "public" / "team_badges.json",
        help="Badge manifest to validate and optionally replace.",
    )
    return parser.parse_args()


def print_report(manifest: dict, report: dict, write: bool) -> None:
    badge_count = sum(len(league_badges) for league_badges in manifest["badges"].values())
    print(
        f"Current-roster crest mappings: {badge_count} across "
        f"{len(manifest['badges'])}/{len(team_badges.PROVIDER_LEAGUES)} leagues."
    )
    fallback_count = sum(len(teams) for teams in manifest["unmapped"].values())
    print(f"Published-fixture initials fallbacks: {fallback_count} teams.")
    for pending in report["pending"]:
        detail = f" — {pending['detail']}" if pending.get("detail") else ""
        print(
            f"WARNING: {pending['league']}:{pending['team']} "
            f"({pending['reason']}){detail}"
        )
    print("Manifest written." if write else "Dry run complete; manifest was not changed.")


def main() -> None:
    arguments = parse_arguments()
    data = team_badges.load_json(arguments.data_path)
    leagues = data.get("leagues")
    if not isinstance(leagues, list):
        raise ValueError("Published fixture artifact must contain a leagues list.")

    manifest, report = team_badges.build_bootstrap_manifest({}, leagues)
    team_badges.validate_badge_manifest(manifest)
    if arguments.write:
        team_badges.write_manifest(arguments.manifest_path, manifest)
    print_report(manifest, report, arguments.write)


if __name__ == "__main__":
    main()
