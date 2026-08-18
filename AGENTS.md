# AGENTS.md

Instructions for AI coding agents (Jules) working in this repo. Whenever your PR changes a data source, an env var, or the architecture, update this file in the same PR — don't wait to be asked.

## Project
Automates Omed's personal football prediction formulas. Shows two numbers per fixture, nothing else — no winners, scores, or probabilities unless a task explicitly asks for them.

## Production formulas (do not alter without explicit product approval)
### Active scheduled prediction path
The scheduled pipeline in `src/output_writer.py` uses `src/compute/venue_weighted_methodology.py` through version-controlled settings in `src/compute/methodology_config.py`.

- **Default active methodology**: `main_last_4`. Each team must supply two newest same-league home matches and two newest same-league away matches. Every selected match has equal weight.
- **Strict history rule**: If either team lacks the full required home/away sample, the writer omits the fixture prediction rather than publishing a partial-sample result.
- **Main calculation**: Team X's AVG FOR/AGAINST is the equal average of its two home and two away records. Team A's expected metric is `(Team A AVG FOR + Team B AVG AGAINST) / 2`; Team B's value is symmetric.
- **Available Last-8 methodology**: `last_8` selects four home and four away records per team. Within each venue group, the two newest records receive `LAST_8_RECENT_SHARE` (default 70%) and the older two receive `LAST_8_OLDER_SHARE` (default 30%); home and away group estimates then contribute equally.
- **Configuration boundary**: `ACTIVE_METHODOLOGY`, `LAST_8_RECENT_SHARE`, and `LAST_8_OLDER_SHARE` are version-controlled product settings. Shares must be between 0 and 1 and total 1. Changing the active methodology or shares requires a reviewed PR and before/after numerical evidence.
- **Active output**: The scheduled artifact and prediction records contain expected xG and expected-goals values. They contain no methodology identifier, override weights, or `comparisons` field. Expected goals remains `null` when source goal data is unavailable.

### Legacy weighted methodology engine
`src/compute/methodology.py` retains the earlier combined-history Methodology 1/2 engine, tier override normalization, and comparison projections. The scheduled writer does not use it. Do not route production through it or expose its comparison data without a separate product decision.

## Data sources

- **Fully automated (5 leagues)**: Understat.com, scraped using the `understatapi` package. Supported leagues: Premier League (`EPL`), La Liga (`La_Liga`), Serie A (`Serie_A`), Bundesliga (`Bundesliga`), and Ligue 1 (`Ligue_1`). RFPL (Russia) is deliberately excluded. Be a polite scraper (use rate limiting).
- **OddAlerts Automated Data**: OddAlerts.com. Free pages only — robots.txt blocks `/UpdateLiveFeed`, `/UpdateLiveStats`, `/app/`; everything else public is fair game. "Recent Results with xG" on `/xg/<league>` pages is server-rendered and scrapeable. "Upcoming Fixtures" on `/leagues/<country>/<league>/fixtures` pages are server-rendered and scrapeable. 15 valid leagues (including MLS, Eliteserien, Premiership, and Superliga) are fully automated. Note: Iceland and Canada do not have scrapeable server-rendered fixtures.
- **Season-aware prediction history**: `src/compute/season_policy.py` defines each active league's current-season boundary. Before Main/Last-4 or Last-8 history selection, retain only same-league records on or after that boundary and before the upcoming fixture. Never fall back to a prior completed season when the current season has no played matches. Incomplete current-season samples are intentionally omitted and reported in source health.

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

- **Automated pipeline**: Python fetch/compute → `public/data.json` (the default Main/Last-4 path includes four underlying matches per team) → static HTML/CSS/JS frontend → Vercel. Daily cron plus manual `workflow_dispatch`. Also consolidates all Understat played matches and OddAlerts leagues and upserts them directly into Supabase.
- **Upcoming-fixture metrics**: Every upcoming fixture exposes the expected-xG and expected-goals triplets. `league.metric` remains `xg`, so the current frontend displays xG; expected-goals values are additive public data and may be `null` when source goal inputs are unavailable. The optional `kickoff_time` field preserves the source clock as `HH:MM`; the Home UI presents that source time as UTC+03:00 by user decision, not as a verified offset-aware timestamp.
- **League standings artifact**: The writer also emits `public/league_standings.json`, an additive static artifact derived from retained `matches` and `predictions` rows. It groups results by existing league-season policy and exposes team `matches_played` plus signed `actual − predicted` xG, Goals, and `(xG + Goals) / 2` PA aggregates for Overall, For, and Against views. Stored pre-match forecasts take priority. If none exists, historical PA may use an explicitly labeled `reconstructed_historical` replay of the active formula, using only earlier same-season **calendar-date** results; same-day results are excluded to prevent leakage. The live prediction path is unchanged. Never label a reconstructed figure as an original forecast.
- Note: The Semi-Automatic manual prediction UI and its `/api` backend have been completely removed, as fixture detection is now fully automated.
- **Deployment Configuration**: Vercel deployment relies on `.vercelignore` to deploy only the essential directories (`public`, `api`, `src`) and files (`requirements.txt`).

## Environment Variables

- `SEASON` (Optional): Override the league-specific Understat current-season label for controlled testing only; it must not be used to make production fall back to a prior season.
- `MOCK_UPCOMING` (Optional): Enable fallback mock fixture generation in `src/fetch/understat_common.py` when no live future fixtures exist.
- `SUPERBASE_URL` or `SUPABASE_URL`: URL for the Supabase REST API (Required for both serverless and cron).
- `SUPERBASE_KEY` or `SUPABASE_KEY`: Server-side Supabase Secret/service-role key only; never use an anon or publishable key. Required for trusted cron and server-side maintenance only.
- No API keys are currently required for scrapers — every active data source is scraped.

## Frontend
- **Fixture card**: Compact Home cards show team badges/names and source kickoff time; their xG/goals results, predictions, bars, and underlying history are revealed only when the card is expanded. Missing numeric values must remain safe fallbacks rather than zeroes.
- **Layout & Navigation**: A horizontal scrolling date strip (7 days: today ± 3) remains Home navigation. A fixed bottom navigation selects Home, League, or Favorite. Fixtures are grouped by league within the selected date. The League view selects the current season by default, offers retained historical seasons, and provides Overall/For/Against PA modes. Favorites are local-browser preferences only. Footer shows an auto-incrementing version.
- **Theme**: Supports a persistent Dark Mode mapped via `[data-theme="dark"]` in `public/style.css` and saved in `localStorage`.

## Conventions

- Tests live under `tests/` — run them before opening a PR.
- Before opening a PR: run `git status` and `git diff --stat`, paste the actual output in the write-up alongside the plain-language summary.
- Stay scoped to exactly what the task asks. Bigger ideas belong in the Claude Project's roadmap, not here.
- Run sanity check: `python3 src/verify.py`
