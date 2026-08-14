# RLS Migration Verification Checklist

This checklist applies to `migrations/20260814204852_enable_opm_table_rls.sql`. The migration has been prepared locally only and must **not** be applied to production without explicit approval.

## Intended access model

| Actor | Expected access after migration |
|---|---|
| Browser visitor / `anon` | No direct access to `public.matches` or `public.predictions`. |
| Signed-in user / `authenticated` | No direct access to `public.matches` or `public.predictions`. |
| GitHub Actions pipeline | Trusted read/write access through the server-side Supabase Secret/service-role key. |
| Static frontend | Continues to read `public/data.json`; it never needs direct Supabase access. |

The migration enables RLS, revokes all table privileges from `anon` and `authenticated`, and grants only the operations the server-side pipeline needs to `service_role`. It creates no permissive public policies.

## Pre-application checks

Before any production application, record the current state and retain it with the change review.

```sql
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('matches', 'predictions')
ORDER BY tablename;

SELECT grantee, table_name, privilege_type
FROM information_schema.role_table_grants
WHERE table_schema = 'public'
  AND table_name IN ('matches', 'predictions')
  AND grantee IN ('anon', 'authenticated', 'service_role')
ORDER BY table_name, grantee, privilege_type;

SELECT schemaname, tablename, policyname, roles, cmd
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN ('matches', 'predictions')
ORDER BY tablename, policyname;
```

The reviewer must also confirm that the GitHub Actions `SUPABASE_KEY` secret is a server-side Secret/service-role key. An anon or publishable key is not acceptable for the scheduled pipeline.

## Safe-environment verification

Apply the migration to a Supabase database branch or isolated non-production project first. Never use test secrets or test data in production.

| Test | Method | Expected result |
|---|---|---|
| RLS enabled | Query `pg_tables.rowsecurity` for both tables. | `true` for `matches` and `predictions`. |
| No direct public policies | Query `pg_policies` for both tables. | No policy grants access to `anon` or `authenticated`. |
| Public-role privileges removed | Query `information_schema.role_table_grants`. | No privileges remain for `anon` or `authenticated`. |
| Anonymous read denied | Make a `GET` request with a publishable/anon key only. | The Data API denies access; it must not return table rows. |
| Anonymous write denied | Attempt an insert only in the isolated test database. | The Data API denies the request; no row is created. |
| Trusted read succeeds | Run a limited `GET` using the server-side Secret/service-role identity. | HTTP success and limited data returned. |
| Trusted match upsert succeeds | Run an idempotent test match upsert using the server-side identity. | HTTP success; repeated request does not create a duplicate. |
| Trusted prediction upsert succeeds | Run a test prediction upsert using the server-side identity. | HTTP success; a repeated logical prediction merges as intended. |

Do not print or paste server-side credentials in a terminal transcript, commit, issue, pull request, or chat.

## Production application gate

Production application requires all of the following:

1. The local migration diff, schema reference, and this checklist are reviewed and approved.
2. Safe-environment verification is complete and recorded.
3. The user explicitly approves the production database migration.
4. The user separately approves a controlled GitHub Actions verification run, because it writes production data.

After approval, apply **only** the reviewed migration. Do not bundle unrelated schema changes, RLS policies, data changes, or source refactors.

## Post-application verification

After a successful production migration, rerun the pre-application SQL queries. The expected end state is RLS enabled on both tables, no `anon` or `authenticated` grants, and service-role privileges limited to `SELECT, INSERT` for `matches` and `SELECT, INSERT, UPDATE` for `predictions`.

Then rerun the Supabase security advisors. The `rls_disabled_in_public` findings for `public.matches` and `public.predictions` must be absent. Only after that check passes should the user approve a controlled `Update Data` workflow run. The run must show the existing successful Supabase credential preflight and successful upsert messages.

## Rollback

Do not disable RLS merely because a test fails. First confirm whether the scheduled pipeline was configured with the required server-side Secret/service-role key and whether the failure is a missing table privilege, a request issue, or an unrelated Data API error.

If an emergency rollback is explicitly approved, restore the pre-application state captured above. A conceptual rollback disables RLS on the two tables and restores only the prior grants that were intentionally required. Because that reopens public exposure, it is an incident response action, not the normal remediation path.

## References

[1]: https://supabase.com/docs/guides/database/postgres/row-level-security "Supabase Row Level Security documentation"
[2]: https://supabase.com/docs/guides/database/secure-data "Supabase secure-data guidance"
