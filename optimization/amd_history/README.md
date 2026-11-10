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
| 3. Chart facts: insurance plans (payer, dates, order), sex, birth year, ZIP, deceased and inactive flags, ageing buckets | `getdemographic` | `chartfacts` | chart | `amd_pull2.py demog` |

Typed tables: `amd_history.sql` creates schema `amd` (views `amd.v_*` read the documents live; the materialized views `amd.charts`,
`amd.charges`, `amd.payments`, `amd.payment_reasons`, `amd.writeoffs` are indexed copies), `amd_refresh.sql` refreshes them after a
load, `amd_analysis.sql` adds `amd.facility_settings`, `amd.charge_outcomes` and `amd.paid_lines_monthly`.

## Rules these scripts keep
- ONE AdvancedMD login per session, made with `amd.login_cached()` before a pull. The pull scripts never log in: when the session dies
  they stop (exit 3) so a person decides when to log in again. HTTP 429 or 5xx means wait and retry the same call, then stop (exit 4).
- Calls are paced (two workers, half a second apart, about two calls a second).
- Copied by allow-list. No patient or responsible-party name, no Social Security number, no full birth date, no street address, phone,
  e-mail, member id, group number or free-text note is written to a document. Chart ids, dates of service, codes, payer codes,
  buildings and dollars are.
- The database must carry the HIPAA marker (`ops.settings` hipaa_enabled = true); `neon_db.py load-docs` refuses otherwise.

## How to run (paths)
The copies here were written for a chat session's scratch folder: the constant `S` near the top of each script is that folder, and
`HELPERS` points at `scripts/helpers` of a checkout. Set `S` (or the `AMDPULL_HOME` / `AMDPULL_HELPERS` environment variables where a
script reads them) to a private working folder outside the repository before running. Pulled documents and progress files live in
that folder; they are chart-level billing data and are never committed.

1. `python3 amd_pull.py enumerate` - lists every chart id (ids only).
2. `python3 amd_pull.py pull` - layer 1; resumable; `python3 verify_local.py` checks it (item counts, fee = payments + write-offs +
   balance on every live charge, allow-list only).
3. `python3 load_buckets.py prod --watch` - loads finished folders; then `neon_exec.py prod --file amd_history.sql`, `--file
   amd_refresh.sql`, `--file amd_analysis.sql`.
4. `python3 amd_pull2.py demog` and `python3 amd_pull2.py detail` - layers 3 and 2; `python3 load_layer.py prod chartfacts --watch`
   and `load_layer.py prod chargedetail --watch`.

A file named `STOP` in the working folder's `state/` ends a pull cleanly after the chart in hand.
