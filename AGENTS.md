# AGENTS.md

Instructions for AI coding agents (Jules) working in this repo. Whenever your PR changes a data source, an env var, or the architecture, update this file in the same PR — don't wait to be asked.

## Project
Automates Omed's personal football prediction formulas. Shows two numbers per fixture, nothing else — no winners, scores, or probabilities unless a task explicitly asks for them.

## The formulas (do not alter without being told to)
### xG Formula
For a fixture between Team A (home) and Team B (away), using each team's last 4 matches (2 home + 2 away):

- Team X's AVG xG FOR = average of X's xG scored across those 4 matches
- Team X's AVG xG AGAINST = average of X's xG conceded across those 4 matches
- Team A's expected xG = (Team A's AVG xG FOR + Team B's AVG xG AGAINST) / 2
- Team B's expected xG = (Team B's AVG xG FOR + Team A's AVG xG AGAINST) / 2

### Goals Formula
Same as above, using actual goals scored/conceded instead of xG. A Python compute module for this formula (`src/compute/goals_formula.py`) exists in the codebase but is not currently used by the active automated or semi-automatic modes (both modes predict using xG).

Sample size (4 matches) must be a configurable variable (`SAMPLE_SIZE` in `xg_formula.py` / `goals_formula.py`), never hardcoded on the frontend or fetch scripts.

## Data sources

- **Fully automated (5 leagues)**: Understat.com, scraped using the `understatapi` package. Supported leagues: Premier League (`EPL`), La Liga (`La_Liga`), Serie A (`Serie_A`), Bundesliga (`Bundesliga`), and Ligue 1 (`Ligue_1`). RFPL (Russia) is deliberately excluded. Be a polite scraper (use rate limiting).
- **Semi-automatic / Proof of Concept**: OddAlerts.com. Free pages only — robots.txt blocks `/UpdateLiveFeed`, `/UpdateLiveStats`, `/app/`; everything else public is fair game. "Recent Results with xG" on `/xg/<league>` pages is server-rendered and scrapeable. "Upcoming Fixtures" on those same pages is Vue-rendered client-side and invisible to a plain fetch — don't build against it. Active semi-automatic leagues include MLS, Eliteserien, Premiership, and Superliga. A scheduled daily fetch is implemented as a proof-of-concept for MLS, scraping `/xg/mls` and storing the results as structured data.

## Stack

- **Automated pipeline**: Python fetch/compute → `public/data.json` (includes the 4 underlying matches per team) → static HTML/CSS/JS frontend → Vercel. Daily cron plus manual `workflow_dispatch`. Also runs a daily OddAlerts scheduled fetch for MLS, writing results to `public/oddalerts_mls.json`.
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
