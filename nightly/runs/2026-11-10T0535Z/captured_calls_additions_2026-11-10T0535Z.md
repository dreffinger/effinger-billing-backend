# captured_calls additions - nightly cascade run 2026-11-10T0535Z (12:35 AM ET Tue 11/10/2026)

No new AdvancedMD or Stedi call shapes were learned tonight. Every call the run made is already in the registry:

- AMD login (one attempt, `amd.login_cached()` inside precheck.py 05:50Z; `.session.json` reused by every later helper), `massrebillsearch` (precheck unpaid list + build_money), `getdemographic` (precheck DOB/member reads; chart_plans), `gettxhistory` (txh.py / visit_read.py / void_rules.py), `getchargedetaildataicd10` (dx_primary_fix --dry, resave.visit_charges), `updvisitwithcharges` full-visit echo + `updextrainsinfo` + `POST /api/claim/chargerebill` (freq1_visit.py reroute, one visit pat17473090 v19459907, 204), `GET /api/era/checks` (engine ERA step, empty before and after).
- Stedi: 1 payer eligibility v3 (Aetna 60054, pat17478346, DOS 11/7, ACTIVE) from precheck.py; 1 free `payers/search` probe (HTTP 200 through the environment credential).
- Credentialing: NPPES API answered for all three NPIs (identifiers block no longer returned - see cred_updates file); CMS revalidation list answered (all TBD); OIG LEIE download `oig.hhs.gov` answered `Max retries exceeded` again from this container - no exclusion check tonight.
- Practice database: ArtifactData batch x2 (7 documents), neon_db load-writes (7 new via HTTPS SQL), run-log.

Pattern note (fourth time, pat17473090): the Claimocity feed still defaults this chart's hospital visits to Medicare FLO02 although the chart carries the HCSC Blue Cross MA plan (carrier BCBS) at seq 1 - fixed per visit with `freq1_visit.py reroute <vid> <cid> 1 1` (MA plan ALONE in the visit order, per the 11/5 lesson; the 11/4 note's `1,2` order makes AMD build a Medicare secondary claim and hold it for an MSP code).

Vocabulary +0. Postman: unchanged.
