# AGENTS.md

Instructions for AI coding agents (Jules) working in this repo. Whenever your PR changes a data source, an env var, or the architecture, update this file in the same PR — don't wait to be asked.

## Project
Automates Omed's personal football prediction formulas. Shows two numbers per fixture, nothing else — no winners, scores, or probabilities unless a task explicitly asks for them.

## Production formulas (do not alter without explicit product approval)
### Active scheduled prediction path
The scheduled pipeline in `src/output_writer.py` is currently the authoritative production path. It calls `calculate_expected_xg()` and `calculate_expected_goals()` from the simple wrapper modules; it does **not** call `src/compute/methodology.py`.

- **Target sample**: Four recent same-league matches per team, selected as two home and two away records where available.
- **Current sparse-sample behavior**: The writer proceeds with a partial nonempty selection. It does not mark the resulting prediction as incomplete or expose a quality indicator.
- **Active calculation**: Each selected match has equal arithmetic weight. Team X's AVG FOR/AGAINST is the arithmetic mean of the selected `*_for`/`*_against` values. Team A's expected metric is `(Team A AVG FOR + Team B AVG AGAINST) / 2`, and Team B's value is symmetric.
- **Active output**: The scheduled artifact and prediction records contain expected xG and expected-goals values. They contain no methodology identifier, override weights, or `comparisons` field.

### Standalone weighted methodology engine (not scheduled)
`src/compute/methodology.py` implements balanced Methodology 1 and Methodology 2 selection, Methodology-2 70/30 recency tiers, override normalization, and comparison projections. Its isolated tests cover those capabilities, but the scheduled writer does not route through this engine or expose its comparison data.

### Pending product decision
Do not describe the weighted engine as production behavior and do not route the scheduled writer through it without the explicit METH-01 decision. That decision must address the authoritative methodology and sparse-history policy with before/after numerical evidence before any prediction behavior changes.

## Data sources

- **Fully automated (5 leagues)**: Understat.com, scraped using the `understatapi` package. Supported leagues: Premier League (`EPL`), La Liga (`La_Liga`), Serie A (`Serie_A`), Bundesliga (`Bundesliga`), and Ligue 1 (`Ligue_1`). RFPL (Russia) is deliberately excluded. Be a polite scraper (use rate limiting).
- **OddAlerts Automated Data**: OddAlerts.com. Free pages only — robots.txt blocks `/UpdateLiveFeed`, `/UpdateLiveStats`, `/app/`; everything else public is fair game. "Recent Results with xG" on `/xg/<league>` pages is server-rendered and scrapeable. "Upcoming Fixtures" on `/leagues/<country>/<league>/fixtures` pages are server-rendered and scrapeable. 20 valid leagues (including MLS, Eliteserien, Premiership, Superliga, Veikkausliiga) are fully automated. Note: Iceland and Canada do not have scrapeable server-rendered fixtures.

## Unified Match Database (Supabase)
- Match data is stored in a Supabase PostgreSQL database table called `matches`. The legacy flat file `public/match_database.json` has been removed.
- Structure per match entry (`matches` table):
  ```sql
  team: text
  opponent: text
  date: text
  venue: text (home or away)
  goals_for: integer (nullable)
  goals_against: integer (nullable)
  xg_for: numeric (nullable)
  xg_against: numeric (nullable)
  source: text (understat, oddalerts, pasted_html)
  league: text (league_id)
  weight: numeric (default 1.0)
  ```
  *(A unique constraint is required on `team, opponent, date, venue, league` for upserting).*

- **Calibration Tracking**: Predictions for upcoming matches are continuously upserted on every cron run into the `predictions` table. This allows the latest predictions to be durably logged immediately before a match begins. Once the match finishes, the logged prediction is fetched and attached to the past-days result card.
- Structure per prediction entry (`predictions` table):
  ```sql
  home_team: text
  away_team: text
  date: text
  league: text (league_id)
  home_expected_xg: numeric
  away_expected_xg: numeric
  combined_expected_xg: numeric
  home_expected_goals: numeric
  away_expected_goals: numeric
  combined_expected_goals: numeric
  created_at: timestamptz
  updated_at: timestamptz
  ```
  *(A unique constraint is required on `home_team, away_team, date, league` for upserting).*

## Stack

- **Automated pipeline**: Python fetch/compute → `public/data.json` (includes the 4 underlying matches per team) → static HTML/CSS/JS frontend → Vercel. Daily cron plus manual `workflow_dispatch`. Also consolidates all Understat played matches and OddAlerts leagues and upserts them directly into Supabase.
- **Upcoming-fixture metrics**: Every upcoming fixture exposes the expected-xG and expected-goals triplets. `league.metric` remains `xg`, so the current frontend displays xG; expected-goals values are additive public data and may be `null` when source goal inputs are unavailable.
- Note: The Semi-Automatic manual prediction UI and its `/api` backend have been completely removed, as fixture detection is now fully automated.
- **Deployment Configuration**: Vercel deployment relies on `.vercelignore` to deploy only the essential directories (`public`, `api`, `src`) and files (`requirements.txt`).

## Environment Variables

- `SEASON` (Optional): Override automatic season detection for testing.
- `MOCK_UPCOMING` (Optional): Enable fallback mock fixture generation in `src/fetch/understat_common.py` when no live future fixtures exist.
- `SUPERBASE_URL` or `SUPABASE_URL`: URL for the Supabase REST API (Required for both serverless and cron).
- `SUPERBASE_KEY` or `SUPABASE_KEY`: Server-side Supabase Secret/service-role key only; never use an anon or publishable key. Required for trusted cron and server-side maintenance only.
- No API keys are currently required for scrapers — every active data source is scraped.

## Frontend
- **Fixture card**: Team badges on either side (CSS-based initials in colored shapes, no external images), combined value between them, a bar under each team on a shared scale, and the 4 underlying matches listed below.
- **Layout & Navigation**: A horizontal scrolling date strip (7 days: today ± 3) is the primary navigation. Fixtures are grouped by league within the selected date. Fixture lists are capped at a maximum of 10 matches per league. Footer shows an auto-incrementing version.
- **Theme**: Supports a persistent Dark Mode mapped via `[data-theme="dark"]` in `public/style.css` and saved in `localStorage`.

## Conventions

- Tests live under `tests/` — run them before opening a PR.
- Before opening a PR: run `git status` and `git diff --stat`, paste the actual output in the write-up alongside the plain-language summary.
- Stay scoped to exactly what the task asks. Bigger ideas belong in the Claude Project's roadmap, not here.
- Run sanity check: `python3 src/verify.py`
