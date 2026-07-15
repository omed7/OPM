# AGENTS.md

Instructions for AI coding agents (Jules) working in this repo. Keep this in sync with reality as the codebase grows — update it, don't let it drift.

## Project
A website that automates Omed's personal football xG prediction formula. It shows two numbers per fixture and nothing else. It does **not** predict match winners, scores, or probabilities. Do not add those unless the task prompt explicitly asks for them.

## The formula (do not alter without being told to)
For a fixture between Team A (home) and Team B (away), using each team's last 4 matches (2 home + 2 away):

- Team X's AVG xG FOR = average of X's xG scored across those 4 matches
- Team X's AVG xG AGAINST = average of X's xG conceded across those 4 matches
- Team A's expected xG = (Team A's AVG xG FOR + Team B's AVG xG AGAINST) / 2
- Team B's expected xG = (Team B's AVG xG FOR + Team A's AVG xG AGAINST) / 2

Sample size (4 matches) must be a configurable variable, never hardcoded.

## Data source
Understat.com, scraped (no official API) — use the `understatapi` package on PyPI. Rate-limit requests (a few seconds apart, be a polite scraper). Premier League only for now.

## Stack
Python fetch/compute script → single output JSON (include the 4 underlying matches per team, not just the averages — the frontend displays them) → static HTML/CSS/JS frontend → Vercel. A scheduled GitHub Actions workflow runs fetch + compute automatically; no manual trigger.

## Frontend
Fixture card: team badges either side, combined xG shown between them, a horizontal bar under each team sized to its xG on a shared scale (not each normalized to its own max), the 4 underlying match values listed below each bar. Footer shows an auto-generated version tag (git commit hash/date or GitHub Actions run number) — no manual version bumping.

## Conventions
- Build/test commands: none yet — add here once the codebase exists.
- Stay scoped to exactly what the task prompt asks. Bigger feature ideas live in the Claude Project's roadmap doc, not here — don't build them speculatively just because they're mentioned somewhere.
To run sanity check: python3 src/verify.py
