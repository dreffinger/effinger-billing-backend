# captured_calls additions - 2026-10-15 1310 UTC (9 AM ET) backend billing run, ehpa cloud (repo attached)

No new AdvancedMD or Stedi call shapes this run (0 vocabulary entries).

## Run notes
- Columns (list calls) 0/5/28/141 -> 0/5/28/141; ERA Center 2 checks $153.95 unposted -> 2 checks $71.00.
- Charge Review 0. Claim Inspector 5 standing holds unchanged. Unbilled 28 unchanged (cards H/J/K/L/M/N waiting; pat17478059 / pat17478064 CHP ids and pat17478063 facesheet on William's turn; 4 inspector-hold visits). Exclusions 141 unchanged: 99 Humana / VA CCN rows on cards A-2026-10-15T1110Z-A..M, 28 BCBS PREF0283 (card O), 8 AET07 (card P), 5 AET07 pat17472859 held, 1 AET12 pat24750 held. No new claim run since 1700302. No AMD column write this slot.
- ERA: NEW WellCare / American Progressive 1003843664 (1053182, $82.95): pat23083 v19443859 99309 05/28/2026 posted ERA-linked (pay 82.95 + WOINS 58.05, balance 0.00; era_new_1015_1310.py); v19443011 99306+99497 05/22/2026 $0 CO-252/M127 documentation required ($389) -> denial-only, board row on William's turn (records), check held in the Center by era_clear ('denial with write-off (cascade handles)'). 1053116 UHC W0020208 ($71) held for William's takeback decision. Availity: nothing new. No new 835 to upload.
- UNI20/BCBS pre-5/1 sweep pass 104: 17 asked - 16 PENDING (pat17472874 $2,563), 1 UNKNOWN (pat17475632 v19433791); 0 candidates, 0 sent.
- Boards: drops 0, Working Denials queue 0, Mandatory Approvals 0 approved / 29 waiting. board_updates_2026-10-15T1310Z.json (2 ops) -> board inbox; registry 'applied' map unchanged since 9/20 - nothing trashed.
- Permission classifier: no refusal this run (era_new_1015_1310.py --live allowed; no other AMD write attempted).
- Calls: no new call shape (login, columns scan, gettxhistory, getdemographic, GET /api/era/checks + checkdetails, addpayments postingmethod=era, 276/277 via Stedi). Helper added: era_new_1015_1310.py (stamp copy of era_new_1015_1110.py).
