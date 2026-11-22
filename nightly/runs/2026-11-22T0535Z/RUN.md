# nightly cascade 2026-11-22T0535Z (Sunday)
- precheck --days 3 --max 120: 32 pairs, 2 new Stedi lookups, 5 flagged (4 Medicare Advantage on DOS, 1 FLO99 no Stedi route).
- chart 17472826: v19462054 11/20 (99233, 160 dollars) insorder 2,1 -> 1 (BCBS / BCBS-MI MA), freq 1, rebill seq 1 -> 204.
- chart 17473090: v19462051 11/20 (99233, 160 dollars) insorder 2 -> 1 (BCBS / HCSC MA), freq 1, rebill seq 1 -> 204.
- chart 17478471: v19462041 11/18 (late entry) + v19462065 11/20 (99233, 160 each) insorder 1,2 -> 2 (UNI20 / UHC AARP MA), freq 1, rebill seq 2 -> 204 x2.
- read back: all four insbilled 0 at the new order; primary dx acceptable (dx_primary_fix plan L03.90 / R55 / M48.02). 640 dollars re-sent.
- chart 17478455: one more visit (11/20) at Medicare; CHP member number still needed (950 dollars, 5 visits). chart 17469549 FLO99 known.
- Sunday claim-status sweep: aging_refresh 2793 visits / 502 charts; 83 checks 24.90 dollars (month 166 / 49.80); run cap hit (20 not asked) + 8 not asked after 62308 gave 5 unusable answers.
  PAID not posted 5 (438.77 dollars; Paid_but_unposted_2026-11-22.csv); FINALIZED 0 / DENIED 17 on 10 charts (no remit detail on file - left for the denial work);
  NOT ELIGIBLE 3 = chart 17477648 UMR (630 dollars): AMD 271 ACTIVE but the subscriber is the spouse -> new board card on William's turn;
  HAND OFF tonight 11, still on list 28, payer switched off 21 (TRI05 19, AAR01 2), final answers not acted on 8.
- Medicare number scan --fix: 73 asked; invalid 10 / mismatch 6 / no plan 2 / after death 0 / to the fixer 0 (all 10 invalid were 'no other number found' within 30 days); all 18 already carded by the 11/20 session (inbox).
- void_rules: 1 open rule, no VOID lines. ERA step: 0 checks before/after.
- cred_check: NPPES 0 changed, revalidation TBD x3, LEIE 84,224 rows 0 matches; reminder hits all past-due cards already on William's turn -> no cred file.
- board: 5 ops (4 appends + 1 new card) -> Drive board inbox; no drops; 0 inbox files in the applied map (21 files since 11/19 still unapplied - board not opened).
- pay_scan.py failed: FileNotFoundError patient_universe_0907.json (same as 11/15); money ledger rebuilt and republished.
- cascade_record.py wrote to its default --repo (/home/claude/effinger-billing-backend, absent) - file moved into the clone and practice_db rebuilt before any send. Lesson: pass --repo to cascade_record.py too.
- Stedi: 85 calls 25.50 dollars (claim status 83, eligibility 2).
- practice_db: 6 documents committed (billing_runs 1, cascade_runs 1, snapshots 4), 0 swept; Neon 6 new, run logged ok.
