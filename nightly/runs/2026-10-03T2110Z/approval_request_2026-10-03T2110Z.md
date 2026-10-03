APPROVAL NEEDED - backend billing run 2026-10-03T2110Z (ehpa cloud)

The run's permission classifier refused 1 AdvancedMD write(s). Each was planned, dry-run verified and NOT retried. Nothing was changed in AMD for these items.

HOW TO APPROVE (pick one):
  1. Reply to this email with the line:  APPROVED <id>   (one per line; add 'NO <id>' to decline). The next run reads the reply and re-attempts that helper once.
  2. Or paste the same text as a command on the Working Denials board (command = 'approve <id>').
  3. Or do it yourself now: the exact command and the AMD UI steps are under each item.
NOTE: an approval lets the next run RE-ATTEMPT the helper; the refusal comes from the routine environment's auto-mode classifier, which does not read approvals.
      The durable fix is on the routine itself (web UI > Edit routine > permission mode not classified for unattended runs, or the allow rules in .claude/settings.json on main - docs/ROUTINE_PERMISSIONS.md).

==============================================================================
ID: A-2026-10-03T2110Z-A1
WHAT: DISMISS three settled ERA Center checks (POST /api/era/checks/dismiss, the captured shape, one call per check) so they leave the unposted list: 1052948 TRICARE East R36061002014230 $0.00 (5 CO-29 lines on pat17473493 v19409106/v19409114 and pat17473856 v19414701/v19414702/v19414820, 7-8/2025 DOS - every charge already at $0 insurance balance); 1052949 UHC 00148049016 $68.12 (3 OA-23 secondary lines on pat17477350 v19452226/v19452057/v19452225 - all posted ERA-linked this run, balances $0); 1052954 Humana 201994566261003 $121.57 (pat17471384 v19456305 99223 posted ERA-linked $121.57 + WOINS 188.43; its 99497 CO-147 and the three CCM PI-252 lines are denial-only and on the board; the CO-185 line was already $0). The dry run (act_2110_1003.py --dry) verified every line settled. Result once done: ERA Center unposted list = 1052906 (held, William's takeback decision) only.
DOLLARS: $0 (housekeeping - the money is already posted)
COMMAND (cd /home/claude/unbilled): cd /home/claude/unbilled && python3 act_2110_1003.py 1052948 1052949 1052954
REFUSED AS: Permission for this action was denied by the Claude Code auto mode classifier. Reason: Blocked by classifier.
UI STEPS (same result by hand): AdvancedMD > Billing > ERA Center > Unposted: select check 1052948, click Dismiss; repeat for 1052949 and 1052954. (Do NOT touch 1052906.)
EVIDENCE: registers/act_2026-10-03T2110Z.dry.json
--- dry-run register (first lines) ---
{
 "stamp": "2026-10-03T2110Z",
 "dry": true,
 "checks": {
  "1052948": {
   "trn": "R36061002014230",
   "carrier": "TRI00",
   "amount": 0.0,
   "open_lines": 0,
   "lines": [
    {
     "visitid": "19409106",
     "pid": "17473493",
     "chargedetailid": "22484525",
     "cpt": "99233",
     "dos": "2025-07-09",
     "paid": 0.0,
     "claimamount": 160.0,
     "carcs": [
      "CO29"
     ],
     "state": "settled - insurance balance already 0 (CO29)"
    },
    {
     "visitid": "19409114",
     "pid": "17473493",
     "chargedetailid": "22484534",
     "cpt": "99223",
     "dos": "2025-07-08",
     "paid": 0.0,
     "claimamount": 310.0,
     "carcs": [
      "CO29"
     ],
     "state": "settled - insurance balance already 0 (CO29)"
    },
    {
     "visitid": "19414701",
     "pid": "17473856",
     "chargedetailid": "23317914",
     "cpt": "99232",
     "dos": "2025-08-26",
     "paid": 0.0,
     "claimamount": 111.0,
     "carcs": [
      "CO29"
     ],
     "state": "settled - insurance balance already 0 (CO29)"
    },
    {
     "visitid": "19414702",
     "pid": "17473856",
     "chargedetailid": "23317915",
     "cpt": "99223",
     "dos": "2025-08-25",
     "paid": 0.0,
     "claimamount": 310.0,
     "carcs": [
      "CO29"
     ],
     "state": "settled - insurance balance already 0 (CO29)"
    },
    {
     "visitid": "19414820",
     "pid": "17473856",
     "chargedetailid": "23318060",
     "cpt": "99232",
     "dos": "2025-08-27",
     "paid": 0.0,
     "claimamount": 111.0,
     "carcs": [
      "CO29"
     ],
     "state": "settled - insurance balance already 0 (CO29)"
    }
   ],
   "dismiss": "dry"
  },
  "1052949": {
   "trn": "00148049016",
   "carrier": "UNI20",
   "amount": 68.12,
   "open_lines": 0,
   "lines": [
    {
     "visitid": "19452226",
     "pid": "17477350",
     "chargedetailid": "23362347",
     "cpt": "99233",
     "dos": "2026-08-21",
     "paid": 21.8,
     "claimamount": 160.0,
     "carcs": [
      "OA23"
     ],
     "state": "posted (00148049016 on the charge), insbal 0.00"
    },
    {
     "visitid": "19452057",
     "pid": "17477350",
     "chargedetailid": "23362170",
     "cpt": "99232",
     "dos": "2026-08-18",
     "paid": 14.38,
     "claimamount": 111.0,
     "carcs": [
      "OA23"
     ],
     "state": "posted (00148049016 on the charge), insbal 0.00"
    },
    {
     "visitid": "19452225",
     "pid": "17477350",
     "chargedetailid": "23362346",
     "cpt": "99223",
     "dos": "2026-08-2
---
