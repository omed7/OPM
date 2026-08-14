# OPM

Automated football xG and expected-goals prediction pipeline.

## Local setup

OPM is tested in continuous integration with **Python 3.12**. Create an isolated environment and install the pinned direct dependency before running local validation.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The active Understat and OddAlerts scrapers do not require an API-Football key. The repository pins `understatapi` in `requirements.txt` so local and continuous-integration installs resolve the same direct scraper dependency.

## Validate the repository

These checks use mocked source and Supabase seams where applicable. They do not require production credentials or write production data.

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src tests
find public -name '*.js' -type f -print0 | xargs -0 -r -n1 node --check
python3 src/validate_public_data.py public/data.json
```

## Run the data pipeline locally

A full pipeline run fetches live public source data and writes matches and predictions to Supabase. Use server-side credentials only; never place these values in browser code or commit them to the repository.

```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-server-side-service-role-key"
python3 src/output_writer.py
```

The scheduled GitHub Actions workflow receives the same server-side variables from repository secrets. Full pipeline runs are separate from local validation and pull-request checks.
