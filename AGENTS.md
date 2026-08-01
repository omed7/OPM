# AGENTS.md

Instructions for AI coding agents (Jules) working in this repo. Whenever your PR changes a data source, an env var, or the architecture, update this file in the same PR — don't wait to be asked.

## Project
Automates Omed's personal football prediction formulas. Shows two numbers per fixture, nothing else — no winners, scores, or probabilities unless a task explicitly asks for them.

## The formulas (do not alter without being told to)
### Methodology System
The prediction engine supports multiple methodologies and metrics (xG and Goals) running on balanced historical matches pulled directly from the unified match database. Both teams in a fixture must share the same methodology and the same metric.

- **Methodology 1**: Equal weight, last 4 matches (2 home + 2 away). Default weight: 25.0% per match.
- **Methodology 2**: Last 8 matches (4 home + 4 away), chronologically ordered. Default weight: 70% collectively across the most recent 4 matches (17.5% each) / 30% collectively across the older 4 matches (7.5% each).

### Weight Normalization and Redistribution
Weights are normalized per tier to sum to 100% of that tier's target total (Methodology 1 has one tier with total 1.0; Methodology 2 has two tiers: recent with total 0.70 and older with total 0.30).
- If a match is deleted (weight set to 0.0) or manually overridden, the difference is redistributed **proportionally** across all other unoverridden matches within the same tier to maintain the tier's target total.

### Formula Calculations (xG & Goals)
For a fixture between Team A (home) and Team B (away) with computed weighted averages for each team:
- Team X's AVG FOR = weighted sum of X's scored goals/xG across matches
- Team X's AVG AGAINST = weighted sum of X's conceded goals/xG across matches
- Team A's expected metric = (Team A's AVG FOR + Team B's AVG AGAINST) / 2
- Team B's expected metric = (Team B's AVG FOR + Team A's AVG AGAINST) / 2

When computing a prediction, the engine also silently computes comparison projections for all default methodologies/metrics and stores them inside the `comparisons` field.

## Data sources

- **Fully automated (5 leagues)**: Understat.com, scraped using the `understatapi` package. Supported leagues: Premier League (`EPL`), La Liga (`La_Liga`), Serie A (`Serie_A`), Bundesliga (`Bundesliga`), and Ligue 1 (`Ligue_1`). RFPL (Russia) is deliberately excluded. Be a polite scraper (use rate limiting).
- **Semi-automatic / Unified database**: OddAlerts.com. Free pages only — robots.txt blocks `/UpdateLiveFeed`, `/UpdateLiveStats`, `/app/`; everything else public is fair game. "Recent Results with xG" on `/xg/<league>` pages is server-rendered and scrapeable. "Upcoming Fixtures" on those same pages is Vue-rendered client-side and invisible to a plain fetch — don't build against it. Active semi-automatic leagues include MLS, Eliteserien, Premiership, and Superliga.

## Unified Match Database
- `public/match_database.json`: Consolidates played team-matches from both Understat and OddAlerts.
- Structure per entry:
  ```json
  {
    "team": "Team Name",
    "opponent": "Opponent Name",
    "date": "Date of match",
    "venue": "home" or "away",
    "goals_for": integer or null,
    "goals_against": integer or null,
    "xg_for": float or null,
    "xg_against": float or null,
    "source": "understat" or "oddalerts",
    "league": "league_id",
    "weight": 1.0
  }
  ```

## Stack

- **Automated pipeline**: Python fetch/compute → `public/data.json` (includes the 4 underlying matches per team) → static HTML/CSS/JS frontend → Vercel. Daily cron plus manual `workflow_dispatch`. Also consolidates all Understat played matches and OddAlerts leagues into `public/match_database.json`.
- **Semi-automatic**: On-demand Python serverless functions under `/api` (Vercel), called live from the frontend — separate from the daily pipeline. Uses a direct team-picker UI. Supports direct scraping of OddAlerts or manual HTML copy-paste input to bypass Cloudflare protection.

## Environment Variables

- `SEASON` (Optional): Override automatic season detection for testing.
- `MOCK_UPCOMING` (Optional): Enable fallback mock fixture generation in `src/fetch/understat_common.py` when no live future fixtures exist.
- No API keys are currently required — every active data source is scraped.

## Frontend
- **Fixture card**: Team badges on either side (CSS-based initials in colored shapes, no external images), combined value between them, a bar under each team on a shared scale, and the 4 underlying matches listed below.
- **Layout & Navigation**: Tab bar scrolls horizontally on mobile. Fixture lists are capped at a maximum of 10 matches (enforced via `FIXTURE_LIMIT` in JS). Footer shows an auto-incrementing version.
- **Theme**: Supports a persistent Dark Mode mapped via `[data-theme="dark"]` in `public/style.css` and saved in `localStorage`.

## Conventions

- Tests live under `tests/` — run them before opening a PR.
- Before opening a PR: run `git status` and `git diff --stat`, paste the actual output in the write-up alongside the plain-language summary.
- Stay scoped to exactly what the task asks. Bigger ideas belong in the Claude Project's roadmap, not here.
- Run sanity check: `python3 src/verify.py`
