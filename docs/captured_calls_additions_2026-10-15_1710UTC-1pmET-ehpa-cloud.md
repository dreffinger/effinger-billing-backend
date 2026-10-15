# captured_calls additions - 2026-10-15 1710 UTC (1 PM ET) backend billing run, ehpa cloud (repo attached)

No new AdvancedMD or Stedi call shapes this run (0 vocabulary entries).

## Run notes
- Columns (list calls) 0/5/28/141 -> 0/5/28/141; ERA Center 1 check $71.00 unposted before and after (1053116 UHC W0020208 held for William's takeback decision).
- Charge Review 0. Claim Inspector 5 standing holds unchanged. Unbilled 28 unchanged (cards H/J/K/L/M/N waiting; pat17478059 / pat17478064 CHP ids and pat17478063 facesheet on William's turn; 4 inspector-hold visits). Exclusions 141 unchanged: 99 Humana / VA CCN rows on cards A-2026-10-15T1110Z-A..M, 28 BCBS PREF0283 (card O), 8 AET07 (card P), 5 AET07 pat17472859 held, 1 AET12 pat24750 held. No new claim run since 1700302. No AMD write this slot.
- ERA: era_post --dry 0 postable / 3 skipped (OA-18 pair settled; CO-29 reversal 'does not match any payments' x2); era_clear --dry HELD. Nothing to upload; Availity: nothing new.
- UNI20/BCBS pre-5/1 sweep pass 106: 17 asked - 16 PENDING (pat17472874 $2,563), 1 UNKNOWN (pat17475632 v19433791); 0 candidates, 0 sent.
- Pam Gmail: two new Brynwood admit emails 17:01-17:02Z; lookuppatient (name wildcard, read-only) finds no AMD chart for either - listed, not turned into charts.
- Boards: drops 0, Working Denials queue 0, Mandatory Approvals 0 approved / 29 waiting. board_updates_2026-10-15T1710Z.json (1 op) -> board inbox; registry 'applied' map unchanged since 9/20 - nothing trashed.
- Permission classifier: no refusal this run (no AMD write attempted).
- Calls: no new call shape (login, columns scan, lookuppatient, GET /api/era/checks + checkdetails, posterapayments dry, 276/277 via Stedi). Helpers added: report_1015_1710.py, admit_lookup_1015_1710.py (stamp copies).
