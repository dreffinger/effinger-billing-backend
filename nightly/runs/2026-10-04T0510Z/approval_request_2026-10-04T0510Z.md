APPROVAL NEEDED - backend billing run 2026-10-04T0510Z (ehpa cloud)

The run's permission classifier refused 2 AdvancedMD write(s). Each was planned, dry-run verified and NOT retried. Nothing was changed in AMD for these items.

HOW TO APPROVE (pick one):
  1. Reply to this email with the line:  APPROVED <id>   (one per line; add 'NO <id>' to decline). The next run reads the reply and re-attempts that helper once.
  2. Or paste the same text as a command on the Working Denials board (command = 'approve <id>').
  3. Or do it yourself now: the exact command and the AMD UI steps are under each item.
NOTE: an approval lets the next run RE-ATTEMPT the helper; the refusal comes from the routine environment's auto-mode classifier, which does not read approvals.
      The durable fix is on the routine itself (web UI > Edit routine > permission mode not classified for unattended runs, or the allow rules in .claude/settings.json on main - docs/ROUTINE_PERMISSIONS.md).

==============================================================================
ID: A-2026-10-04T0510Z-A1
WHAT: Your nine Insurance Refresh Board answers of 10/4 02:28-03:19Z (dry-run clean again this run, register registers/act_2026-10-04T0310Z_dry.json): pat17476868 admission 09/30/2026 on v19456834/35/36; pat17477850 admission 09/21/2026 on 4 HCA visits + release (CHP plan is already on the chart); pat17477549 Medicare member id -> the TMH id (3E77W70DR59) + freq-1 x2; pat17471977 2 HCA visits moved off the patient balance to the BCBS seq 2 + freq-1; write-offs WONCS G0439 pat23617/pat21885, WOLATE pat17474613 v19422927, WONCS pat17468923 v19442292, WOCAID2ND pat24039 (the dry run shows these charges already at insurance balance 0 - possibly done by you in the UI; the live run skips them if so); voids pat23159 v19456297 + pat45668 v19455691; pat17474611 six Nov-2025 visits freq-1 to UNI20; pat17477183 three visits to the patient balance + release. PLUS the approved A-2026-10-03T2110Z-A1 dismiss of ERA checks 1052948 / 1052949 / 1052954 (your APPROVED reply 03:08Z) - refused again in the same command.
DOLLARS: about 4,900 (admission dates 480 + 763; freq-1 rebills 748 + 470 + 1,243; write-offs 204x2 + 389 + 315 + 21.80; voids 443 + 315; patient-balance moves 597) + ERA dismiss of 3 settled checks (0 dollars)
COMMAND (cd /home/claude/unbilled): cd /home/claude/unbilled && python3 act_0310_1004.py  (then: python3 approval_request.py approved A-2026-10-03T2110Z-A1 ...; python3 act_2110_1003.py 1052948 1052949 1052954)
REFUSED AS: auto-mode classifier: Real-World Transactions (refused 05:33Z 10/4; the same batch was refused 'Modify Shared Resources' by the 0310Z run)
UI STEPS (same result by hand): Each row's UI steps are in the 0310Z email; the ERA dismiss = ERA Center > select the three checks > Dismiss.
EVIDENCE: registers/act_2026-10-04T0310Z_dry.json
--- dry-run register (first lines) ---
{
 "stamp": "2026-10-04T0310Z",
 "dry": true,
 "steps": [
  "pat17476868 v19456834 cpts ['99233'] insorder 2,1 onhcfa 1",
  "  updextrainsinfo 99233 09/30/2026 -> DRY",
  "  resave: DRY resave visit vst19456834 over={'onhcfa': '1', 'insorder': '2,1'} charges=1",
  "pat17476868 v19456835 cpts ['99233'] insorder 2,1 onhcfa 1",
  "  updextrainsinfo 99233 09/30/2026 -> DRY",
  "  resave: DRY resave visit vst19456835 over={'onhcfa': '1', 'insorder': '2,1'} charges=1",
  "pat17476868 v19456836 cpts ['99233'] insorder 2,1 onhcfa 1",
  "  updextrainsinfo 99233 09/30/2026 -> DRY",
  "  resave: DRY resave visit vst19456836 over={'onhcfa': '1', 'insorder': '2,1'} charges=1",
  "pat17477850 CAP07 already on chart ins9520708 seq 1",
  "  AMD 271 CAP07: ACTIVE | plan  | A  B  | others HN  ; HN  ; HN  ; HN   | death - | addr 24 OLD COURTHOUSE WAY UNIT A CRAWFORDVILLE FL 32327 | aaa []",
  "  Stedi CHP 95112 @9/21/2026: ['Active Coverage', 'Active Coverage', 'Out of Pocket (Stop Loss)'] errors [] plan {'planBegin': '20260201'}",
  "  v19455898 updextrainsinfo 99223 09/21/2026 -> DRY",
  "  v19455898 updextrainsinfo 99497 09/21/2026 -> DRY",
  "  v19455898 resave: DRY resave visit vst19455898 over={'onhcfa': '1', 'insorder': '1'} charges=2",
  "  v19455868 updextrainsinfo 99233 09/21/2026 -> DRY",
  "  v19455868 resave: DRY resave visit vst19455868 over={'onhcfa': '1', 'insorder': '1'} charges=1",
  "  v19456282 updextrainsinfo 99233 09/21/2026 -> DRY",
  "  v19456282 resave: DRY resave visit vst19456282 over={'onhcfa': '1', 'insorder': '1'} charges=1",
  "  v19456281 updextrainsinfo 99233 09/21/2026 -> DRY",
  "  v19456281 resave: DRY resave visit vst19456281 over={'onhcfa': '1', 'insorder': '1'} charges=1",
  "  release ['19455898', '19455868', '19456282', '19456281'] -> DRY release ['19455898', '19455868', '19456282', '19456281']",
  "pat17471977 BCBS already on chart ins9520709 seq 2",
  "  AMD 271 BCBS: REJECTED   | plan  | A  B  | others  | death - | addr  | aaa [{'ConditionOrResponseCode': 'Y', 'RejectReasonCode': '42', 'FollowUpActionCode': 'R'}]",
  "  v19424212 DRY move_to_ins seq 2 + freq1",
  "  v19424211 DRY move_to_ins seq 2 + freq1",
  "awv pat23617 c23357819 WONCS 204.00: FAIL over-apply: pay 0.00 + wo 204.00 > insbalance 0.00",
  "awv pat21885 c23357813 DRY move_to_ins then WONCS 204.00",
  "pat17474613 c23328277 WOLATE 256.00: FAIL over-apply: pay 0.00 + wo 256.00 > insbalance 0.00",
  "pat17474613 c23328278 WOLATE 133.00: FAIL over-apply: pay 0.00 + wo 1
---

==============================================================================
ID: A-2026-10-04T0510Z-A2
WHAT: Your board answers of 10/4 03:20-03:47Z plus the inspector holds the 05:13Z scan found, each from a live chart read (registers/reads_2026-10-04T0510Z.json): A pat17474541 'restore' - the 99487 is ALREADY restored on the chart (unbilled charge beside the 99489): resave the visit Medicare-first and freq-1 rebill (315). B pat17477375 'bill Medicare with GV' - the Medicare plan (seq 3) and GV are ALREADY on the chart/charges but the three 8/11-8/13/2026 visits went back to WellCare on 9/27: set insorder 3 + freq-1 seq 3 (630). C pat17477892 - the CAP07 plan CIO50078852 is ALREADY on the chart (AMD 271 ACTIVE): admission 09/23/2026 on the 3 HCA visits (9/23 99223, 9/24 + 9/29 99232), insorder 1, release (532). D pat17477842 'fix the charts and send the claim' - the chart already carries the real DOB and the Medicare plan: visit 19455665 insorder 1 + release (315). E pat17477975 inspector hold: admission 09/28/2026 (its own 99223) on 3 visits (532). F pat17477933 v19456467 Pattern 20389: F02.80 -> F03.90, resave, bypass the fresh advisory id (141). G pat12180329: chart last name 'SCOTT III' -> SCOTT + suffix III (Medicare 271 rejects AAA 73 on the name; TMH reads SCOTT,ROBERT N III), re-run the 271, freq-1 the 5 open Medicare visits only if ACTIVE (751). I pat17477777: addreferralplan ismain=0/status=stat1 for a blank plan; repoint the 2 open visits with preauth='' if a new plan id comes back. J pat17476534 'write off WONCS' - the dry run found NO open 5/11-5/13/2026 insurance balance on the chart (nothing to write off; please check the chart). K pat17477640 admission 09/02/2026 (your HCA arrival list: ADM IN 9/2, discharged 9/27) on v19456252/v19456267, extins only.
DOLLARS: about 3,900 (Rodriguez 315; Screws 630; Pignataro 532; Joiner 315; Singleton 532; Smith 141; Scott 751 if Medicare's 271 turns ACTIVE after the name fix; Bellamy write-off 731 at most; Reeves/Lazarchik 0)
COMMAND (cd /home/claude/unbilled): cd /home/claude/unbilled && python3 act_0510_1004.py
REFUSED AS: auto-mode classifier: Real-World Transactions (refused 05:52Z 10/4; dry run clean, registers/act_2026-10-04T0510Z_dry.json)
UI STEPS (same result by hand): Per item: Charge Entry > visit > Extra Info tab > Hospitalization From (C/E/K); Visit insurance order + Rebill (A/B/D); Claim Inspector > Smith 9/21 visit > diagnosis F02.80 -> F03.90 > Bypass (F); Patient demographics > Last name SCOTT, suffix III (G); Referral Plans > add a blank plan, point the two HCA visits at it (I).
EVIDENCE: registers/act_2026-10-04T0510Z_dry.json
--- dry-run register (first lines) ---
{
 "stamp": "2026-10-04T0510Z",
 "dry": true,
 "steps": [
  "A pat17474541 v19430630 charges [('23336998', '99489', '109.00', '09/04/2026'), ('23368589', '99487', '206.00', None)]",
  "  resave: DRY resave visit vst19430630 over={'insorder': '2,1'} charges=2",
  "  DRY freq1 v19430630 seq 2",
  "B pat17477375 v19451378 [('23361422', '99223', 'GV', 'WEL04', '09/27/2026')]",
  "  resave: DRY resave visit vst19451378 over={'insorder': '3'} charges=1",
  "  DRY freq1 v19451378 seq 3",
  "B pat17477375 v19451386 [('23361430', '99233', 'GV', 'WEL04', '09/27/2026')]",
  "  resave: DRY resave visit vst19451386 over={'insorder': '3'} charges=1",
  "  DRY freq1 v19451386 seq 3",
  "B pat17477375 v19451481 [('23361529', '99233', 'GV', 'WEL04', '09/27/2026')]",
  "  resave: DRY resave visit vst19451481 over={'insorder': '3'} charges=1",
  "  DRY freq1 v19451481 seq 3",
  "C pat17477892 v19456293 cpts ['99223'] insorder '1' onhcfa 1",
  "  updextrainsinfo 99223 09/23/2026 -> DRY",
  "  resave: DRY resave visit vst19456293 over={'onhcfa': '1', 'insorder': '1'} charges=1",
  "C pat17477892 v19456228 cpts ['99232'] insorder '1' onhcfa 1",
  "  updextrainsinfo 99232 09/23/2026 -> DRY",
  "  resave: DRY resave visit vst19456228 over={'onhcfa': '1', 'insorder': '1'} charges=1",
  "C pat17477892 v19456888 cpts ['99232'] insorder '1' onhcfa 1",
  "  updextrainsinfo 99232 09/23/2026 -> DRY",
  "  resave: DRY resave visit vst19456888 over={'onhcfa': '1', 'insorder': '1'} charges=1",
  "  release -> DRY release ['19456293', '19456228', '19456888']",
  "  271 CAP07: ACTIVE | plan  | A  B  | others HN  ; HN  ; HN  ; HN   | death - | addr 4760 PIMLICO DR TALLAHASSEE FL 32309 | aaa []",
  "D pat17477842 v19455665 resave: DRY resave visit vst19455665 over={'onhcfa': '1', 'insorder': '1'} charges=2",
  "  release -> DRY release ['19455665']",
  "E pat17477975 v19456900 cpts ['99223'] insorder '1' onhcfa 1",
  "  updextrainsinfo 99223 09/28/2026 -> DRY",
  "  resave: DRY resave visit vst19456900 over={'onhcfa': '1', 'insorder': '1'} charges=1",
  "E pat17477975 v19456869 cpts ['99232'] insorder '1' onhcfa 1",
  "  updextrainsinfo 99232 09/28/2026 -> DRY",
  "  resave: DRY resave visit vst19456869 over={'onhcfa': '1', 'insorder': '1'} charges=1",
  "E pat17477975 v19456870 cpts ['99232'] insorder '1' onhcfa 1",
  "  updextrainsinfo 99232 09/28/2026 -> DRY",
  "  resave: DRY resave visit vst19456870 over={'onhcfa': '1', 'insorder': '1'} charges=1",
  "F pat17477933 v19456467 dx {'dcode103
---
