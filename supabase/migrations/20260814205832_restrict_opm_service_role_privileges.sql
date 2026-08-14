-- Restrict service_role to the operations required by the OPM pipeline.
-- matches: read historical data and insert new records.
-- predictions: read, insert, and merge current records.

revoke all privileges on table public.matches from service_role;
revoke all privileges on table public.predictions from service_role;

grant select, insert on table public.matches to service_role;
grant select, insert, update on table public.predictions to service_role;
