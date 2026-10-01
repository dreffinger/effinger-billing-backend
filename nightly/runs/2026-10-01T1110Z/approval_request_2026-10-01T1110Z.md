APPROVAL NEEDED - backend billing run 2026-10-01T1110Z (ehpa cloud)

The run's permission classifier refused 3 AdvancedMD write(s). Each was planned, dry-run verified and NOT retried. Nothing was changed in AMD for these items.

HOW TO APPROVE (pick one):
  1. Reply to this email with the line:  APPROVED <id>   (one per line; add 'NO <id>' to decline). The next run reads the reply and re-attempts that helper once.
  2. Or paste the same text as a command on the Working Denials board (command = 'approve <id>').
  3. Or do it yourself now: the exact command and the AMD UI steps are under each item.
NOTE: an approval lets the next run RE-ATTEMPT the helper; the refusal comes from the routine environment's auto-mode classifier, which does not read approvals.
      The durable fix is on the routine itself (web UI > Edit routine > permission mode not classified for unattended runs, or the allow rules in .claude/settings.json on main - docs/ROUTINE_PERMISSIONS.md).

==============================================================================
ID: A-2026-10-01T1110Z-A1
WHAT: UHC ERA check 1052921 (W0616257, 10/02/2026) answered CO-B9 'enrolled in hospice' on 9 visits that are still at UHC with the money open. William's 9/20 rule: straight Medicare + GV, frequency-1 rebill. pat22023 v19420906 (10/25/2025 99487 $206), v19427600 (12/28/2025 99487 $206), v19430695 (1/27/2026 99487 $206), v19432008 (2/2/2026 99307 $68) -> Medicare seq 1, GV added; pat21263 v19442472 (5/17/2026 99487+99489 $315, GV on the 99487 only), v19446290 (6/25/2026 99487+99489 $315), v19421096 (10/25/2025 99487+99489 $105.76 open after UHC paid then recouped) -> Medicare seq 1; pat17473477 v19442357 (5/17/2026 99487 $206) and v19448745 (7/17/2026 99487 $206, both before the 9/15/2026 date of death, GV already present) -> Medicare seq 2. Dry run clean: registers/hospice_reroute_2026-10-01T1110Z_dry.json.
DOLLARS: $1,924.52 open insurance balance (9 visits)
COMMAND (cd /home/claude/unbilled): cd /home/claude/unbilled && python3 hospice_reroute_1110.py --live
REFUSED AS: Permission for this action was denied by the Claude Code auto mode classifier. Reason: Blocked by classifier.
UI STEPS (same result by hand): AdvancedMD > Patient > Charges: open each visit, add modifier GV to every charge (Charge Edit > Modifiers), save; Claims > Rebill: frequency 1 (original), bill the Medicare plan (sequence 1 on charts 22023 and 21263, sequence 2 on chart 17473477).
EVIDENCE: registers/hospice_reroute_2026-10-01T1110Z_dry.json
--- dry-run register (first lines) ---
[
 {
  "stamp": "2026-10-01T1110Z",
  "live": false,
  "pid": "22023",
  "anchor": "23326012",
  "seq": "1",
  "why": "UHCMA CO-B9 10/25/2025 99487",
  "vid": "19420906",
  "charges": [
   {
    "id": "charge23326012",
    "proc": "pcode492676",
    "mods": "",
    "insbalance": "206.00"
   }
  ],
  "payments": [],
  "net_paid": 0,
  "gv_missing_before": [
   "charge23326012"
  ],
  "result": "dry: would add GV to 1 charge(s) ['charge23326012'] then frequency-1 rebill seq 1"
 },
 {
  "stamp": "2026-10-01T1110Z",
  "live": false,
  "pid": "22023",
  "anchor": "23334147",
  "seq": "1",
  "why": "UHCMA CO-B9 12/28/2025 99487",
  "vid": "19427600",
  "charges": [
   {
    "id": "charge23334147",
    "proc": "pcode492676",
    "mods": "",
    "insbalance": "206.00"
   }
  ],
  "payments": [],
  "net_paid": 0,
  "gv_missing_before": [
   "charge23334147"
  ],
  "result": "dry: would add GV to 1 charge(s) ['charge23334147'] then frequency-1 rebill seq 1"
 },
 {
  "stamp": "2026-10-01T1110Z",
  "live": false,
  "pid": "22023",
  "anchor": "23337128",
  "seq": "1",
  "why": "UHCMA CO-B9 01/27/2026 99487",
  "vid": "19430695",
  "charges": [
   {
    "id": "charge23337128",
    "proc": "pcode492676",
    "mods": "",
    "insbalance": "206.00"
   }
  ],
  "payments": [],
  "net_paid": 0,
  "gv_missing_before": [
   "charge23337128"
  ],
  "result": "dry: would add GV to 1 charge(s) ['charge23337128'] then frequency-1 rebill seq 1"
 },
 {
  "stamp": "2026-10-01T1110Z",
  "live": false,
  "pid": "22023",
  "anchor": "23338626",
  "seq": "1",
  "why": "UHCMA CO-B9 02/02/2026 99307",
  "vid": "19432008",
  "charges": [
   {
    "id": "charge23338626",
    "proc": "pcode65117",
    "mods": "",
    "insbalance": "68.00"
   }
  ],
  "payments": [],
  "net_paid": 0,
  "gv_missing_before": [
   "charge23338626"
  ],
  "result": "dry: would add GV to 1 charge(s) ['charge23338626'] then frequency-1 rebill seq 1"
 },
 {
  "stamp": "2026-10-01T1110Z",
  "live": false,
  "pid": "21263",
  "anchor": "23350599",
  "seq": "1",
  "why": "UNI20 OA-18/CO-B9 05/17/2026 99487+99489 (GV on 99487 only)",
  "vid": "19442472",
  "charges": [
   {
    "id": "charge23350599",
    "proc": "pcode492676",
    "mods": "mcode713",
    "insbalance": "206.00"
   },
   {
    "id": "charge23364539",
    "proc": "pcode492677",
    "mods": "",
    "insbalance": "109.00"
   }
  ],
  "payments": [],
  "net_paid": 0,
  "gv_missing_before": [
   "charge23364539"
  ],
  "result": "dry: would add GV to 1 charge
---

==============================================================================
ID: A-2026-10-01T1110Z-A2
WHAT: UHC ERA check 1052921 (W0616257) CO-29 'time limit for filing has expired' on pat17475602 (DOD 4/16/2026) 2/20/2026 99306+99497 (v19433580, $389) and 2/26/2026 99309 (v19434260, $141) - first filed to UHC 9/4/2026 after Medicare answered $0 in May; and on pat21263 8/17/2025 99487+99489 (v19413646, $105.76 open after UHC paid then recouped; 13 months from DOS = the 12-month rule). Standing rule: CO-29 -> WOLATE, pay 0 + write-off = live balance, check number W0616257, deposit 10/02/2026, dated note. Dry run clean: registers/era_denials_1052921_2026-10-01T1110Z_dry.json.
DOLLARS: $635.76 WOLATE write-offs
COMMAND (cd /home/claude/unbilled): cd /home/claude/unbilled && python3 era_denials_1052921_1110.py --live
REFUSED AS: Permission for this action was denied by the Claude Code auto mode classifier. Reason: Blocked by classifier.
UI STEPS (same result by hand): AdvancedMD > Payment Entry: patient 17475602 (then 21263), carrier UNI20, check W0616257 dated 10/02/2026, payment 0.00, write-off code WOLATE for the full open balance on each listed charge, note 'ERA 1052921 CO-29 untimely'.
EVIDENCE: registers/era_denials_1052921_2026-10-01T1110Z_dry.json
--- dry-run register (first lines) ---
[
 {
  "pid": "17475602",
  "vid": "19433580",
  "cid": "23340303",
  "cpt": "99306",
  "dos": "02/20/2026",
  "amount": 256.0,
  "why": "CO-29 untimely (UHC W0616257)",
  "code": "WOLATE",
  "ok": true,
  "msg": "DRY bal 256.00 prof prof13 pid 17475602 -> pay 0.00 wo 256.00",
  "insbalance_after": null,
  "when": "2026-10-01T11:30:34Z",
  "dry": true
 },
 {
  "pid": "17475602",
  "vid": "19433580",
  "cid": "23340304",
  "cpt": "99497",
  "dos": "02/20/2026",
  "amount": 133.0,
  "why": "CO-29 untimely (UHC W0616257)",
  "code": "WOLATE",
  "ok": true,
  "msg": "DRY bal 133.00 prof prof13 pid 17475602 -> pay 0.00 wo 133.00",
  "insbalance_after": null,
  "when": "2026-10-01T11:30:34Z",
  "dry": true
 },
 {
  "pid": "17475602",
  "vid": "19434260",
  "cid": "23341236",
  "cpt": "99309",
  "dos": "02/26/2026",
  "amount": 141.0,
  "why": "CO-29 untimely (UHC W0616257)",
  "code": "WOLATE",
  "ok": true,
  "msg": "DRY bal 141.00 prof prof15 pid 17475602 -> pay 0.00 wo 141.00",
  "insbalance_after": null,
  "when": "2026-10-01T11:30:34Z",
  "dry": true
 },
 {
  "pid": "21263",
  "vid": "19413646",
  "cid": "23316734",
  "cpt": "99487",
  "dos": "08/17/2025",
  "amount": 68.62,
  "why": "CO-29 untimely + 12-month rule (UHC W0616257, paid 9/4/2026 then recouped)",
  "code": "WOLATE",
  "ok": true,
  "msg": "DRY bal 68.62 prof prof13 pid 21263 -> pay 0.00 wo 68.62",
  "insbalance_after": null,
  "when": "2026-10-01T11:30:34Z",
  "dry": true
 },
 {
  "pid": "21263",
  "vid": "19413646",
  "cid": "23316735",
  "cpt": "99489",
  "dos": "08/17/2025",
  "amount": 37.14,
  "why": "CO-29 untimely + 12-month rule (UHC W0616257, paid 9/4/2026 then recouped)",
  "code": "WOLATE",
  "ok": true,
  "msg": "DRY bal 37.14 prof prof13 pid 21263 -> pay 0.00 wo 37.14",
  "insbalance_after": null,
  "when": "2026-10-01T11:30:34Z",
  "dry": true
 }
]
---

==============================================================================
ID: A-2026-10-01T1110Z-A3
WHAT: UHC ERA check 1052921 answered PR-27 'coverage terminated' on pat20379 9/7/2025 99487 (v19416099, $206, still at UNI20). CMS MBI lookup at DOS 9/7/2025: Medicare A/B since 2014 with a Humana Health Insurance Company of Florida PPO (Medicare Advantage) in force 8/1-9/30/2025 - the chart's Humana plan HUM01 (seq 4, member H74410073, AMD 271 ACTIVE) is the payer for that date. Action: frequency-1 rebill of the visit to sequence 4 (HUM01).
DOLLARS: $206.00
COMMAND (cd /home/claude/unbilled): cd /home/claude/unbilled && python3 freq1_visit.py 19416099 23319630 4
REFUSED AS: Permission for this action was denied by the Claude Code auto mode classifier. Reason: Blocked by classifier.
UI STEPS (same result by hand): AdvancedMD > chart 20379 > visit 9/7/2025 (99487): Claims > Rebill as original (frequency 1) to the Humana plan (sequence 4).
EVIDENCE: registers/era_1052921_live2_2026-10-01T1110Z.txt
--- dry-run register (first lines) ---
== pat17471977
  v19424211 c23329979 99233 11/20/2025 ERA[PRPR27] fee 160.00 paid 0.00 insbal 160.00 patbal 0.00 mods '' carrier UNI20 billdate 09/06/2026
  v19424212 c23329980 99223 11/19/2025 ERA[PRPR27] fee 310.00 paid 0.00 insbal 310.00 patbal 0.00 mods '' carrier UNI20 billdate 09/06/2026
== pat17471762
  v19427055 c23333253 99233 12/23/2025 ERA[PRPR26] fee 160.00 paid 89.83 insbal 70.17 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19427059 c23333257 99223 12/18/2025 ERA[PRPR26] fee 310.00 paid 132.31 insbal 177.69 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19429273 c23335828 99233 01/15/2026 ERA[PRPR27] fee 160.00 paid 85.46 insbal 74.54 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19429274 c23335829 99233 01/14/2026 ERA[PRPR27] fee 160.00 paid 85.46 insbal 74.54 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19429275 c23335830 99223 01/13/2026 ERA[PRPR27] fee 310.00 paid 125.20 insbal 184.80 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19429389 c23335883 99233 01/16/2026 ERA[PRPR27] fee 160.00 paid 85.46 insbal 74.54 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19429529 c23336055 99233 01/18/2026 ERA[PRPR27] fee 160.00 paid 85.46 insbal 74.54 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19429530 c23336056 99233 01/17/2026 ERA[PRPR27] fee 160.00 paid 85.46 insbal 74.54 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19429531 c23336057 99233 01/19/2026 ERA[PRPR27] fee 160.00 paid 85.46 insbal 74.54 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19430121 c23336539 99233 01/24/2026 ERA[PRPR27] fee 160.00 paid 85.46 insbal 74.54 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19430121 c23336597 99223 01/23/2026 ERA[PRPR27] fee 310.00 paid 125.20 insbal 184.80 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19430403 c23336712 99233 01/26/2026 ERA[PRPR27] fee 160.00 paid 85.46 insbal 74.54 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19430411 c23336720 99233 01/25/2026 ERA[PRPR27] fee 160.00 paid 85.46 insbal 74.54 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
  v19430871 c23337460 99233 01/27/2026 ERA[PRPR27] fee 160.00 paid 85.46 insbal 74.54 patbal 0.00 mods '' carrier FLO99 billdate 09/23/2026
== pat21263
  v19413646 c23316734 99487 08/17/2025 ERA[COCO29] fee 206.00 paid 137.38 insbal 68.62 patbal 0.00 mods '' carrier UNI20 billdate 09/04/2026
  v19413646 c23316735 99489 08/17/2025 ERA[COCO29] fee 109.00 paid 71.8
---
