# ehpa Practice Database app (Neon Function `ehpadb`)

PLAIN ENGLISH: William's own page over the practice's permanent store, live at https://app.ehpa.dev. It runs **inside the Neon
project** (ehpa-database, `steep-rain-79347575`) as a Neon Function, next to the Postgres that holds every board, run, register
and report (`tools/db/neon_db.py`, `tools/db/neon_schema.sql`, `tools/db/ccm_schema.sql`). Nothing is hosted anywhere else, so the
Neon BAA covers it. One sign-in opens the hub: Universal Practice Optimization, My practice, the **ehpa Practice Database** (the
billing dashboard and the Practice Database page's views), the **CCM notes** and Learn.

- **Sign-in:** Neon Auth (Managed Better Auth) on the branch, Google or email + password. The browser gets a 15-minute JWT and sends
  it as `Authorization: Bearer` on every `/api` call; the function verifies it against the branch's JWKS, then checks that the
  account's email is on `ALLOWED_EMAILS` in `neon.ts` AND that its owner confirmed it (`neon_auth."user"."emailVerified"`). Anything
  else gets 401/403 before a query runs. Idle sessions end after `SESSION_IDLE_MINUTES`.
- **Signing out** (the button, the idle limit, or another tab signing out) empties the page first and tells the sign-in
  service second, so nothing stays on screen while a request hangs. The idle limit is counted on the wall clock too (a sleeping
  laptop cannot outlast it). A sign-out the service did not confirm is said so, remembered in `localStorage` as a flag with no
  data in it, and finished on the next load, the next sign-in or when the connection returns. An answer from the server that
  arrives after the page moved on or the session ended is dropped, never drawn - on the dashboard and the Insurance Refresh Board,
  the Practice Database page's views and the CCM notes alike (and the header buttons are not put back on the sign-in page).
- **Public answers (no data):** `/` (the shell), `/theme.js` (applies the remembered color scheme before the first paint), `/app.js`
  (the bundled client), `/health`. None of them names a claude.ai page or carries a patient's data.
- **Data - every route below is behind that gate, and every request is written to `ops.app_access_log`:**
  - `/api/views`, `/api/view/<name>`: the generic views (`src/views.ts`) over `ehpa.*` and `ops.*`; one of them,
    `insurance_refresh`, is the Insurance Refresh Board (below).
  - `POST /api/board/item`: one Insurance Refresh Board card's notes, lookup trail and API results (`src/board.ts`).
  - `/api/pdb/overview | feed?from&to | runs | run/<stamp> | era | era/<stamp> | approvals | mirror | data | data/<collection> |
    doc/<collection>/<id>` (`src/pdb.ts`): the Practice Database page's views - Overview (tiles and "Is it working?"), Census
    inputs (the Claimocity feed, its charts, the nightly cascade, the runs of the last 14 days, every feed charge with its
    AdvancedMD outcome), Billing runs, ERA, Approvals, Raw data (the practice database's own documents; the copies of other boards
    are left out because they can carry names) and Mirror & sources - from the same documents the page reads, in Neon. Chart ids,
    dates of service, codes and dollars only.
  - `/api/ccm/summary | month/<YYYY-MM> | note/<chart>_<YYYY-MM> | patients | patient/<chart> | signed` (`src/ccm.ts`): the CCM
    Documentation Hub's notes from `ccm.notes`, `ccm.signed_notes`, `ccm.patients`, `ccm.months`. **Read-only, and it shows patient
    names and birth dates** - only behind the gate. Signing stays on the hub page on claude.ai.
    **Where the `ccm.*` views come from:** `tools/db/ccm_schema.sql` on the branch `claude/ccm-documentation-hub`, which is not
    merged yet, so the file is not in this tree. The views were already applied to the practice database on 11/11/2026, so these
    routes need no schema change. Merge that branch (and draft PR #28, whose copy of this folder this branch starts from) before
    this one; once the file is here, `tools/selftest/test_ehpadb_app.py` checks that it builds every view `src/ccm.ts` reads.
  - `/api/upo/...` (`src/upo.ts`): Universal Practice Optimization; its work-list POST is the app's one write.
  - `/api/links`: the header buttons - Practice Database page, Insurance Refresh Board, CCM Documentation Hub, CCM Hub Build
    (`src/links.ts`). The Insurance Refresh Board button opens this site's own board page (`#db/insurance_refresh`); the others
    open the claude.ai page in a new tab.
- **The Insurance Refresh Board** (`#db/insurance_refresh`) is the one dashboard page that shows patients: the board's cards
  from `ehpa.insurance_refresh_cards` (names, dates of birth, insurance ids), read-only, as fresh as the last nightly copy
  (`nightly/practice_db_sync_prompt_v1.txt`). `src/board.ts` reads it, `src/boardview.ts` draws the cards with the board's own
  rules (ported from `boards/templates/tracker.html`; `npm test` runs both side by side and fails when they differ) and
  `src/client/board.ts` keeps the filters and the search. The list comes with the view; one card's notes and lookup trail
  come from `POST /api/board/item` with the card id in the body, so an id never sits in an address. Nothing of it is written
  to the browser's storage, and signing out empties the page. Posting a note or handing a patient to Claude stays on the board
  on claude.ai, which the page links to. It is drawn with the palette tokens, so it follows the five color schemes.
- **Audit:** every allowed `/api` request is written to `ops.app_access_log` (email, route, status, milliseconds); opening a
  card's notes records the chart number with the route (for a card without a chart number, a short one-way tag of its id).
- **Color schemes:** the five ehpa schemes of the Practice Database page (Lapis, Midnight, Navy, Plum, Light), its tokens word for
  word (`src/palettes.ts`), **Light by default**; the switcher in the header remembers the pick in that browser (localStorage
  `ehpa-palette`).
- **Tests:** `npm test` runs `scripts/selftest.mjs` (the real Function built with stand-ins, every `/api` route asked with no
  session, a forged token, a not-allowed email, an unconfirmed email and as the owner; the real browser code with a stand-in
  document) and `scripts/test-boardview.mjs` (the board's rules: the port in `src/boardview.ts` against
  `boards/templates/tracker.html`, made-up cards only); `python3 tools/selftest/test_ehpadb_app.py` runs the first, plus the
  palette and header-button checks against the source.

## Work on it

```bash
cd apps/ehpadb
npm ci
neon link --project-id steep-rain-79347575 --org-id org-sparkling-silence-16346164 -y --no-env-pull   # once; writes .neon (git-ignored)
npm run build:client        # src/client.ts -> src/generated/client-bundle.ts (served as /app.js)
npx tsc --noEmit && npm test    # scripts/selftest.mjs, then scripts/test-boardview.mjs (the board's rules, made-up cards only)
neon dev                    # local loop with DATABASE_URL and the Auth URLs injected
npm run deploy              # build the client, then `neon deploy` (applies neon.ts: Auth + the function)
#   or, from a container with no neon CLI session: scripts/deploy-api.sh prod   (Neon API; keeps the deployed environment)
neon functions get ehpadb   # the invocation_url
neon neon-auth domain add https://<that url>     # the Auth server only redirects to trusted origins
neon logs query --source function --since 1h     # the function's logs
```

After a deploy, check: `curl -s https://app.ehpa.dev/health` says ok; `/` has `data-ehpa="light"` and loads `/theme.js`;
`curl -s -o /dev/null -w '%{http_code}' https://app.ehpa.dev/api/ccm/summary` (and `/api/pdb/overview`, `/api/links`) answers
401 without a session; `/app.js` contains no `claude.ai/artifact`; signed in, the four header buttons show (Insurance Refresh
Board opens `#db/insurance_refresh` on the site), a picked scheme survives a reload, every Practice Database view, the board and
the CCM notes open, and the requests appear in `ops.app_access_log`.

Custom domain: `neon functions domains register app.ehpa.dev --slug ehpadb --output json` prints the CNAME target; create
the CNAME (DNS only, no proxy), then `neon functions domains list` until `active`, and add `https://app.ehpa.dev` as a trusted
Auth domain. The apex `ehpa.dev` works only with a DNS provider that flattens CNAMEs at the apex.

Secrets: none in this folder. `DATABASE_URL`, `NEON_AUTH_BASE_URL` and `NEON_AUTH_JWKS_URL` are injected by Neon at runtime;
`.neon`, `.env` and `.env.local` are git-ignored.
