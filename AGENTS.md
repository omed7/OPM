# AGENTS.md

Instructions for AI coding agents (Jules) working in this repo. Keep this in sync with reality as the codebase grows — update it, don't let it drift.

## Project
A website that automates Omed's personal football xG prediction formula. It shows two numbers per fixture and nothing else. It does **not** predict match winners, scores, or probabilities. Do not add those unless the task prompt explicitly asks for them.

## The formulas (do not alter without being told to)
### xG Formula
For a fixture between Team A (home) and Team B (away), using each team's last 4 matches (2 home + 2 away):

- Team X's AVG xG FOR = average of X's xG scored across those 4 matches
- Team X's AVG xG AGAINST = average of X's xG conceded across those 4 matches
- Team A's expected xG = (Team A's AVG xG FOR + Team B's AVG xG AGAINST) / 2
- Team B's expected xG = (Team B's AVG xG FOR + Team A's AVG xG AGAINST) / 2

### Goals Formula
Same as above, but uses actual goals scored and conceded rather than expected goals (xG). Used for Besta deild karla.

Sample size (4 matches) must be a configurable variable, never hardcoded.

## Data source
- **Premier League**: Understat.com, scraped (no official API) — use the `understatapi` package on PyPI. Rate-limit requests (a few seconds apart, be a polite scraper).
- **Besta deild karla**: API-Football REST API (`https://v3.football.api-sports.io`). **Requires the `API_FOOTBALL_KEY` environment variable** to be set.

## Stack
Python fetch/compute script → single output JSON (include the 4 underlying matches per team, not just the averages — the frontend displays them) → static HTML/CSS/JS frontend → Vercel. A scheduled GitHub Actions workflow runs fetch + compute automatically; no manual trigger.

## Environment Variables
- `API_FOOTBALL_KEY` (Required): Used to authenticate with the API-Football service. Do not hardcode this anywhere.
- `SEASON` (Optional): Can be set to override automatic season detection for testing.
- `MOCK_UPCOMING` (Optional): Used in tests or when there are no live future fixtures (e.g., `MOCK_UPCOMING=1`).

## Frontend
Fixture card: team badges either side, combined xG shown between them, a horizontal bar under each team sized to its xG on a shared scale (not each normalized to its own max), the 4 underlying match values listed below each bar. Footer shows an auto-incrementing app version (e.g. v1.0.0) — no manual version bumping.

## Conventions
- Build/test commands: none yet — add here once the codebase exists.
- Stay scoped to exactly what the task prompt asks. Bigger feature ideas live in the Claude Project's roadmap doc, not here — don't build them speculatively just because they're mentioned somewhere.
To run sanity check: python3 src/verify.py
