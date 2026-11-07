# ehpa Practice Database app (Neon Function `ehpadb`)

PLAIN ENGLISH: William's own page over the practice's permanent store. It runs **inside the Neon project** (ehpa-database,
`steep-rain-79347575`) as a Neon Function, next to the Postgres that holds every board, run, register and report
(`tools/db/neon_db.py`, `tools/db/neon_schema.sql`). Nothing is hosted anywhere else, so the Neon BAA covers it.

- **Sign-in:** Neon Auth (Managed Better Auth) on the branch, email + password. The browser gets a 15-minute JWT and sends it
  as `Authorization: Bearer` on every `/api` call; the function verifies it against the branch's JWKS and then checks the email
  against `ALLOWED_EMAILS` in `neon.ts`. Any other account gets 403 and no data. Idle sessions end after `SESSION_IDLE_MINUTES`.
- **Pages:** `/` (the shell, no data), `/app.js` (the bundled client), `/health`. **Data:** `/api/views`, `/api/view/<name>`;
  the views are defined in `src/views.ts` as read-only SQL over `ehpa.*` and `ops.*` (chart ids, dates, codes and dollars only).
- **Audit:** every allowed `/api` request is written to `ops.app_access_log` (email, route, status, milliseconds).

## Work on it

```bash
cd apps/ehpadb
npm install
neon link --project-id steep-rain-79347575 --org-id org-sparkling-silence-16346164 -y --no-env-pull   # once; writes .neon (git-ignored)
npm run build:client        # src/client.ts -> src/generated/client-bundle.ts (served as /app.js)
neon dev                    # local loop with DATABASE_URL and the Auth URLs injected
npm run deploy              # build the client, then `neon deploy` (applies neon.ts: Auth + the function)
neon functions get ehpadb   # the invocation_url
neon neon-auth domain add https://<that url>     # the Auth server only redirects to trusted origins
neon logs query --source function --since 1h     # the function's logs
```

Custom domain: `neon functions domains register app.ehpa.dev --slug ehpadb --output json` prints the CNAME target; create
the CNAME (DNS only, no proxy), then `neon functions domains list` until `active`, and add `https://app.ehpa.dev` as a trusted
Auth domain. The apex `ehpa.dev` works only with a DNS provider that flattens CNAMEs at the apex.

Secrets: none in this folder. `DATABASE_URL`, `NEON_AUTH_BASE_URL` and `NEON_AUTH_JWKS_URL` are injected by Neon at runtime;
`.neon`, `.env` and `.env.local` are git-ignored.
