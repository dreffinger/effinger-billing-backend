# nightly cascade 2026-11-15T0535Z (Sunday)
- precheck --days 3 --max 120: 24 pairs, 5 new Stedi lookups, 2 flagged (both Medicare Advantage on DOS).
- chart 17473090: v19460675 / v19461075 / v19461183 (99233 x3, 480 dollars) rerouted insorder 2,1 -> 1 (BCBS HCSC MA), freq 1, rebill seq 1 -> 204 x3 (freq1_visit reroute).
- chart 17478395: still needs a CHP member number (William's turn since 11/14).
- Sunday claim-status sweep: 83 checks 24.90 dollars, run cap hit (46 due not asked; 3 more stopped after 68069 gave 5 unusable answers); 7 PAID-not-posted; 1 finalized 0 (chart 17476912, CARC 252 known); 1 duplicate denial (chart 17477375 v19455316 = duplicate of paid v19451040 -> William: void?); 30 hand-offs; 19 TRI05 payer-switched-off lines.
- void_rules: 1 open rule, no VOID lines. ERA step: 0 checks before/after.
- cred_check: NPPES 0 changed, revalidation TBD x3, LEIE 0 matches; reminder windows all already on William's turn - no cred file.
- pay_scan.py failed: FileNotFoundError patient_universe_0907.json (not in the workspace); money ledger rebuilt without payments_by_carrier.json and republished.
- practice_db: first build ran with the default --repo /home/claude/effinger-billing-backend (absent in this container) -> empty repo snapshot; rebuilt with --repo <clone>, repo + neon snapshots resent with if_version, 3 engine reports swept. Lesson: pass --repo when the bootstrap path is missing.
