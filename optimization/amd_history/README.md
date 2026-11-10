# AdvancedMD history pull (started 11/10/2026)

William, 11/10/2026: "pull all the data going back from advanced md back two years and upload it all to the data base", then
"pull all data from advanced md not just back 2 years and update it all to the database".

These are the scripts that did it, kept here so the work can be resumed or repeated. They only READ AdvancedMD, with call shapes
that are already in `docs/captured_calls.md`, and they write to the practice database through its one door, `tools/db/neon_db.py`
(`raw.documents`, source `amd_history`).

| Layer | AdvancedMD call | Collection | One document per | Script |
|---|---|---|---|---|
| 1. Transaction history: every charge, payment with its adjustment codes, write-off and unapplied credit, every page | `gettxhistory` | `txhistory` | chart | `amd_pull.py enumerate`, `amd_pull.py pull` |
| 2. Charge detail: place of service as billed, units, diagnoses, modifiers, allowed and expected, claim numbers, billing history | `getchargedetaildataicd10` | `chargedetail` | chart | `amd_pull2.py detail` |
| 3. Chart facts: insurance plans (payer, dates, order), sex, birth year (1936 and earlier stored as 1936), state, deceased and inactive flags, ageing buckets | `getdemographic` | `chartfacts` | chart | `amd_pull2.py demog` |

Typed tables: `amd_history.sql` creates schema `amd` (views `amd.v_*` read the documents live; the materialized views `amd.charts`,
`amd.charges`, `amd.payments`, `amd.payment_reasons`, `amd.writeoffs` and `amd.unapplied_payments` are indexed copies),
`amd_history2.sql` adds the chart-facts and charge-detail views, `amd_refresh.sql` / `amd_refresh2.sql` refresh them after a load,
`amd_analysis.sql` adds `amd.facility_settings`, `amd.charge_outcomes` and `amd.paid_lines_monthly`.

### Corrections of November 10, 2026 (`migrations/migrate_1110.sql`, applied to the practice database at 13:33 UTC)
An independent check of the pull found the copy exact but four definitions wrong or missing. They were corrected without dropping
anything, reviewed, rehearsed on the preview database and proved on the full data before they were applied:
- `amd.charges.paid` was AdvancedMD's fee minus balance, that is payments PLUS write-offs ($10,042,860.47 on live lines against
  $3,757,541.84 really paid). The column is now called `settled`. Money paid comes from `amd.payments` (not void) only.
- Adjustment codes whose code part starts with a letter (B9, B7, A1 ...) were split wrongly into group and code (1,415 rows). The group
  is now the first two characters and the code the rest.
- Empty charts carried AdvancedMD's placeholder date 1900-01-01 (5,534 charts); it is now no date.
- Unapplied payments (310 lines, $9,266.19 with money) are now `amd.unapplied_payments`; with them every chart ties to AdvancedMD's
  own totals.
- `amd.chart_facts` no longer has ZIP or city columns; `facility_settings` counts only the five nursing buildings as nursing facility.
- Payment and write-off dates are the day of ENTRY in AdvancedMD, not the day money arrived: read money by year of service.
The old objects are kept, renamed `..._before_1110` (16 of them). They are removed only on the owner's word, in this order:
`paid_lines_monthly_before_1110`, `charge_outcomes_before_1110`, `facility_settings_before_1110`, then the four materialized views
`..._before_1110` (their indexes go with them), then the four views `v_..._before_1110`. Do not run `migrate_1110.sql` again once any
of them has been removed. `migrations/verify_1110.sql` (31 read-only checks) and `migrations/postcheck_1110.sql` (14) re-check it.
Never run an OLDER copy of the definition files against the database: it would quietly put the old definitions back.

## Rules these scripts keep
- ONE AdvancedMD login per session, made with `amd.login_cached()` before a pull. The pull scripts never log in: when the session dies
  they stop (exit 3) so a person decides when to log in again. HTTP 429 or 5xx means wait and retry the same call, then stop (exit 4).
- Calls are paced (two workers, half a second apart, about two calls a second).
- Copied by allow-list. No patient or responsible-party name, no Social Security number, no full birth date, no street address, phone,
  e-mail, member id, group number or free-text note is written to a document. Chart ids, dates of service, codes, payer codes,
  buildings and dollars are.
- Since November 10, 2026 the chart-facts layer also leaves out ZIP code, city, marital status and the raw deceased value (it keeps
  a yes/no flag), and stores birth years of 1936 or earlier as 1936. `coarsen_chartfacts.py` rewrote the documents pulled before that.
- The result is pseudonymous, not anonymous: a chart id can be tied to a name through other data the practice holds. Treat every
  table built from these documents as patient data.
- The database must carry the HIPAA marker (`ops.settings` hipaa_enabled = true); `neon_db.py load-docs` refuses otherwise.

## How to run (paths)
The copies here were written for a chat session's scratch folder: the constant `S` near the top of each script is that folder, and
`HELPERS` points at `scripts/helpers` of a checkout. Set `S` (or the `AMDPULL_HOME` / `AMDPULL_HELPERS` environment variables where a
script reads them) to a private working folder outside the repository before running. Pulled documents and progress files live in
that folder; they are chart-level billing data and are never committed.

1. `python3 amd_pull.py enumerate` - lists every chart id (ids only).
2. `python3 amd_pull.py pull` - layer 1; resumable; `python3 verify_local.py` checks it (item counts, fee = payments + write-offs +
   balance on every live charge, allow-list only).
3. `python3 load_buckets.py prod --watch` - loads finished folders; then `neon_exec.py prod --file amd_refresh.sql` (a NEW database:
   first `--file amd_history.sql`, `--file amd_history2.sql`, `--file amd_analysis.sql`).
4. `python3 amd_pull2.py demog` and `python3 amd_pull2.py detail` - layers 3 and 2; `python3 load_layer.py prod chartfacts --watch`
   and `load_layer.py prod chargedetail --watch`.

A file named `STOP` in the working folder's `state/` ends a pull cleanly after the chart in hand.
