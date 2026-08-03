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
