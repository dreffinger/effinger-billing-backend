# captured_calls additions - 2026-10-15 2110 UTC (5 PM ET) backend billing run, ehpa cloud (repo attached)

No new AdvancedMD or Stedi call shapes this run (0 vocabulary entries).

## Run notes
- Columns (list calls) 0/5/28/141 -> 0/5/28/141; ERA Center 1 check $71.00 unposted before and after (1053116 UHC W0020208 held for William's takeback decision).
- Charge Review 0. Claim Inspector 5 standing holds unchanged (pat23177 v19451190 CCI 24078/15775; pat44983 v13979435/v13984519 duplicate 99239 2023; pat22845 v19364378 TRI05; pat17472519 v19395738). Unbilled 28 unchanged (8 visits pat17478013 card H; 12 visits on the 10/12-10/13 HCA charts pat17478058/59/60/62/63/64 cards J-N; pat17477183 x2 and pat17471019 x2; 4 inspector-hold visits) - the seven zero-plan charts re-read live at 21:22Z (zeroplan_1015_2110.py, read-only): still 0 plans. Exclusions 141 unchanged: 99 Humana / VA CCN rows on cards A-2026-10-15T1110Z-A..M, 28 BCBS PREF0283 (card O), 8 AET07 (card P), 5 AET07 pat17472859 held, 1 AET12 pat24750 held. No new claim run since 1700302. No AMD write this slot.
- ERA: era_post --dry 0 postable / 3 skipped (OA-18 pair v19421789 settled; CO-29 reversal 'does not match any payments' x2 on v19395670); era_clear --dry HELD (denial-with-writeoff 1, unvalidated money 1, unvalidated $0 1). Nothing to upload; Availity / Treasury: nothing new.
- UNI20/BCBS pre-5/1 sweep pass 108 (--min-age 167 --max 60 --carriers UNI20,BCBS --skip-answered 98 registers, 585 skipped): 17 asked - 16 PENDING (pat17472874 $2,563), 1 UNKNOWN (pat17475632 v19433791 $310); 0 candidates, 0 sent.
- Pam Gmail: a third admit email 19:19Z (NA Tapestry, two photo facesheets) joins the two 17:0xZ Brynwood admits; lookuppatient (name wildcard, read-only, admit_lookup_1015_2110.py) finds no AMD chart for any of the three - listed, not turned into charts.
- Boards: drops 0, Working Denials queue 0, Mandatory Approvals 0 approved / 29 waiting; 0 items rows changed since 19:00Z. board_updates_2026-10-15T2110Z.json (1 op) -> board inbox; both registries' 'applied' maps unchanged since 9/20 - nothing trashed.
- Permission classifier: no refusal this run (no AMD write attempted).
- Calls: no new call shape (login, columns scan, lookuppatient, getdemographic, GET /api/era/checks + checkdetails, posterapayments dry, 276/277 via Stedi). Helpers added: report_1015_2110.py, admit_lookup_1015_2110.py, zeroplan_1015_2110.py, sweep_eval_1015_2110.py, board_updates_1015_2110_build.py (stamp copies).
