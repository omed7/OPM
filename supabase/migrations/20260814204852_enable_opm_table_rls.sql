-- Restrict OPM match and prediction data to trusted server-side access.
-- The scheduled GitHub Actions pipeline uses the Supabase Secret/service-role key.

alter table public.matches enable row level security;
alter table public.predictions enable row level security;

revoke all privileges on table public.matches from anon, authenticated;
revoke all privileges on table public.predictions from anon, authenticated;

grant select, insert on table public.matches to service_role;
grant select, insert, update on table public.predictions to service_role;
