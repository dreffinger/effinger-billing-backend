# nightly cascade 2026-11-17T0536Z (Tuesday)
- precheck --days 3 --max 120: 26 pairs, 1 new Stedi lookup (payer eligibility, 0.30 dollars), 2 flagged - both Medicare Advantage on DOS.
- chart 17474611: v19461282 11/15 (99233, 160 dollars) insorder 2,4 -> 1 (UNI20 UHC MA), freq 1, rebill seq 1 -> 204; read back insbilled 0, insorder 1; primary dx acceptable (dx_primary_fix plan).
- chart 17472491: RET01 (C and O retiree plan) = the payer Medicare names; already billed RET01 first - no change.
- chart 17478395: still waiting on a CHP member number (William's turn).
- Step 2 skipped (Tuesday). void_rules: 1 open rule, no VOID lines. ERA step: 0 checks before/after.
- cred_check: NPPES 0 changed, revalidation TBD x3, LEIE 84,224 rows 0 matches; reminders = standing past-due cards already on William's turn - no cred file.
- board: 1 append op on the chart 17474611 MA card (Drive board inbox); no drops; no inbox file in either applied map.
- practice_db: 6 + 2 swept documents committed; Neon 8 new, run logged ok.
- Fix: /home/claude/effinger-billing-backend did not exist in this container (cascade_record wrote a stray copy there) - replaced by a symlink to the attached clone and re-recorded.
