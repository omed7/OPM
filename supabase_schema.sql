-- Create the matches table
CREATE TABLE public.matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team TEXT NOT NULL,
    opponent TEXT NOT NULL,
    date TEXT NOT NULL,
    venue TEXT NOT NULL,
    goals_for INTEGER,
    goals_against INTEGER,
    xg_for NUMERIC,
    xg_against NUMERIC,
    source TEXT,
    league TEXT NOT NULL,
    weight NUMERIC DEFAULT 1.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Add a unique constraint to avoid duplicate matches during bulk upserts from the cron script
ALTER TABLE public.matches ADD CONSTRAINT matches_unique_constraint UNIQUE (team, opponent, date, venue, league);

-- Create the predictions table
CREATE TABLE public.predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    date TEXT NOT NULL,
    league TEXT NOT NULL,
    home_expected_xg NUMERIC,
    away_expected_xg NUMERIC,
    combined_expected_xg NUMERIC,
    home_expected_goals NUMERIC,
    away_expected_goals NUMERIC,
    combined_expected_goals NUMERIC,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

-- Add a unique constraint to avoid duplicate predictions and support continuous upserts
ALTER TABLE public.predictions ADD CONSTRAINT predictions_unique_constraint UNIQUE (home_team, away_team, date, league);

-- Restrict tables in the exposed public schema to trusted server-side access.
ALTER TABLE public.matches ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.predictions ENABLE ROW LEVEL SECURITY;

REVOKE ALL PRIVILEGES ON TABLE public.matches FROM anon, authenticated;
REVOKE ALL PRIVILEGES ON TABLE public.predictions FROM anon, authenticated;

GRANT SELECT, INSERT ON TABLE public.matches TO service_role;
GRANT SELECT, INSERT, UPDATE ON TABLE public.predictions TO service_role;
