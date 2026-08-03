import json
import os
import sys

# Add the project root to sys.path so we can import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from src.supabase_client import supabase_request

def load_match_database():
    """
    Loads and returns the unified match database from Supabase.
    """
    data, error = supabase_request("/matches?select=*", method="GET")
    if error:
        print(f"Error loading match database from Supabase: {error}")
        return []
    return data or []

def get_team_matches(database, team_name, league_id, venue=None, limit=None):
    """
    Filters database by league_id and team_name, optionally by venue (home/away).
    Returns list sorted chronologically (newest first).
    """
    filtered = []
    team_lower = team_name.strip().lower()
    league_lower = league_id.strip().lower()

    for entry in database:
        if entry.get("league", "").strip().lower() != league_lower:
            continue
        if entry.get("team", "").strip().lower() != team_lower:
            continue
        if venue and entry.get("venue", "").strip().lower() != venue.strip().lower():
            continue
        filtered.append(entry)

    # Sort chronologically, newest first
    filtered.sort(key=lambda x: x.get("date", ""), reverse=True)

    if limit is not None:
        filtered = filtered[:limit]
    return filtered

def fetch_balanced_matches(database, team_name, league_id, methodology_id):
    """
    Fetches balanced matches for a team according to the methodology.
    Methodology 1: Last 2 home + 2 away.
    Methodology 2: Last 4 home + 4 away.
    Returns combined matches sorted chronologically (newest first).
    """
    if methodology_id == 1:
        home_limit, away_limit = 2, 2
    elif methodology_id == 2:
        home_limit, away_limit = 4, 4
    else:
        raise ValueError(f"Unknown methodology ID: {methodology_id}")

    home_matches = get_team_matches(database, team_name, league_id, venue='home', limit=home_limit)
    away_matches = get_team_matches(database, team_name, league_id, venue='away', limit=away_limit)

    combined = home_matches + away_matches
    # Sort combined chronologically, newest first
    combined.sort(key=lambda x: x.get("date", ""), reverse=True)
    return combined

def get_default_weights(methodology_id, num_matches):
    """
    Generates default weights for a list of matches of length num_matches (ordered newest first).
    Methodology 1: Equal weight (1.0 / num_matches).
    Methodology 2: 70% collectively for most recent 4 matches, 30% collectively for older matches.
                   If num_matches <= 4, all are treated as Tier 1 and equal weight is assigned summing to 1.0.
    """
    if num_matches == 0:
        return []

    if methodology_id == 1:
        return [1.0 / num_matches] * num_matches

    elif methodology_id == 2:
        if num_matches <= 4:
            return [1.0 / num_matches] * num_matches
        else:
            tier1_count = 4
            tier2_count = num_matches - 4
            weights = []
            for i in range(num_matches):
                if i < 4:
                    weights.append(0.70 / tier1_count)
                else:
                    weights.append(0.30 / tier2_count)
            return weights
    else:
        raise ValueError(f"Unknown methodology ID: {methodology_id}")

def get_tiers(methodology_id, num_matches):
    """
    Returns the tiers (indices and target weights) for a methodology and list length.
    """
    if num_matches == 0:
        return []

    if methodology_id == 1:
        return [
            {
                "indices": list(range(num_matches)),
                "target_weight": 1.0
            }
        ]
    elif methodology_id == 2:
        if num_matches <= 4:
            return [
                {
                    "indices": list(range(num_matches)),
                    "target_weight": 1.0
                }
            ]
        else:
            return [
                {
                    "indices": [0, 1, 2, 3],
                    "target_weight": 0.70
                },
                {
                    "indices": list(range(4, num_matches)),
                    "target_weight": 0.30
                }
            ]
    else:
        raise ValueError(f"Unknown methodology ID: {methodology_id}")

def normalize_weights(num_matches, default_weights, overrides, methodology_id):
    """
    Applies overrides (as dict {index: weight}) and normalizes weights per tier.
    A weight of 0 is how a match gets "deleted."
    Changing one match's weight redistributes the difference proportionally across
    the rest of its tier.
    """
    if num_matches == 0:
        return []

    # Initialize weights list as a copy of default weights
    weights = list(default_weights)

    # Get tiers configuration
    tiers = get_tiers(methodology_id, num_matches)

    # Process each tier
    for tier in tiers:
        tier_indices = tier["indices"]
        target_total = tier["target_weight"]

        # Classify indices in this tier into overridden and unoverridden
        overridden_indices = []
        unoverridden_indices = []

        for idx in tier_indices:
            has_override = False
            override_val = None
            if overrides is not None:
                if idx in overrides:
                    has_override = True
                    override_val = overrides[idx]
                elif str(idx) in overrides:
                    has_override = True
                    override_val = overrides[str(idx)]

            if has_override:
                # Force float
                try:
                    override_val = float(override_val)
                except (ValueError, TypeError):
                    override_val = 0.0
                overridden_indices.append((idx, override_val))
            else:
                unoverridden_indices.append(idx)

        # If there are overrides in this tier
        if overridden_indices:
            total_override = sum(val for _, val in overridden_indices)

            # If all indices in the tier are overridden:
            if not unoverridden_indices:
                if total_override > 0:
                    for idx, val in overridden_indices:
                        weights[idx] = (val / total_override) * target_total
                else:
                    for idx, _ in overridden_indices:
                        weights[idx] = target_total / len(overridden_indices)
            else:
                # If overrides exceed or equal target_total:
                if total_override >= target_total:
                    for idx in unoverridden_indices:
                        weights[idx] = 0.0
                    if total_override > 0:
                        for idx, val in overridden_indices:
                            weights[idx] = (val / total_override) * target_total
                    else:
                        for idx, _ in overridden_indices:
                            weights[idx] = target_total / len(overridden_indices)
                else:
                    # Apply overrides
                    for idx, val in overridden_indices:
                        weights[idx] = val
                    # Proportional redistribution for unoverridden matches
                    remaining_target = target_total - total_override
                    total_default = sum(default_weights[idx] for idx in unoverridden_indices)

                    if total_default > 0:
                        for idx in unoverridden_indices:
                            weights[idx] = (default_weights[idx] / total_default) * remaining_target
                    else:
                        for idx in unoverridden_indices:
                            weights[idx] = remaining_target / len(unoverridden_indices)
        else:
            # No overrides in this tier, keep default weights
            pass

    return weights

def calculate_weighted_average_for_field(matches, weights, field_name):
    """
    Computes weighted average for a given field across matches using weights.
    """
    total = 0.0
    for match, weight in zip(matches, weights):
        val = match.get(field_name)
        if val is None:
            val = 0.0
        try:
            total += float(val) * weight
        except (ValueError, TypeError):
            pass
    return total

def predict_fixture(database, home_team, away_team, league_id, methodology_id=1, metric="xg", home_overrides=None, away_overrides=None):
    """
    Predicts a fixture using a specific methodology, metric, and overrides.
    Returns expected home/away goals/xG and full match/weight details.
    """
    # 1. Fetch balanced matches
    home_matches = fetch_balanced_matches(database, home_team, league_id, methodology_id)
    away_matches = fetch_balanced_matches(database, away_team, league_id, methodology_id)

    if not home_matches or not away_matches:
        raise ValueError("Match database contains no games for one or both of the teams in this league.")

    # 2. Get default weights
    home_defaults = get_default_weights(methodology_id, len(home_matches))
    away_defaults = get_default_weights(methodology_id, len(away_matches))

    # 3. Apply overrides and normalize
    home_weights = normalize_weights(len(home_matches), home_defaults, home_overrides, methodology_id)
    away_weights = normalize_weights(len(away_matches), away_defaults, away_overrides, methodology_id)

    # 4. Map metric to field names
    metric_lower = metric.strip().lower()
    if metric_lower == "xg":
        for_field = "xg_for"
        against_field = "xg_against"
    elif metric_lower == "goals":
        for_field = "goals_for"
        against_field = "goals_against"
    else:
        raise ValueError(f"Unknown metric: {metric}")

    home_avg_for = calculate_weighted_average_for_field(home_matches, home_weights, for_field)
    home_avg_against = calculate_weighted_average_for_field(home_matches, home_weights, against_field)

    away_avg_for = calculate_weighted_average_for_field(away_matches, away_weights, for_field)
    away_avg_against = calculate_weighted_average_for_field(away_matches, away_weights, against_field)

    # 5. Compute expectation
    expected_home = (home_avg_for + away_avg_against) / 2.0
    expected_away = (away_avg_for + home_avg_against) / 2.0

    return {
        "home_expected": expected_home,
        "away_expected": expected_away,
        "home_matches_count": len(home_matches),
        "away_matches_count": len(away_matches),
        "home_weights": home_weights,
        "away_weights": away_weights,
        "home_avg_for": home_avg_for,
        "home_avg_against": home_avg_against,
        "away_avg_for": away_avg_for,
        "away_avg_against": away_avg_against,
        "home_matches": home_matches,
        "away_matches": away_matches
    }

def compute_all_comparisons(database, home_team, away_team, league_id):
    """
    Computes and returns default predictions for all methodologies under both metrics.
    """
    comparisons = {}
    for m_id in [1, 2]:
        comparisons[f"methodology_{m_id}"] = {}
        for m_metric in ["xg", "goals"]:
            try:
                pred = predict_fixture(
                    database, home_team, away_team, league_id,
                    methodology_id=m_id, metric=m_metric,
                    home_overrides=None, away_overrides=None
                )
                comparisons[f"methodology_{m_id}"][m_metric] = {
                    "home_expected": pred["home_expected"],
                    "away_expected": pred["away_expected"],
                    "combined_expected": pred["home_expected"] + pred["away_expected"]
                }
            except Exception:
                comparisons[f"methodology_{m_id}"][m_metric] = None
    return comparisons
