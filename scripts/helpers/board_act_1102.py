# PLAIN ENGLISH (Insurance Refresh Board answers of 11/2/2026 - William's words on 16 rows, chat run 2026-11-02T0855Z)
# Decides: nothing new - it carries out what William wrote on each board row this morning, one lettered section per chart:
#   A HUNTER 25558 'restore'   - void the twelve 2025 Medicare-$0 write-offs (3/3-8/1/2025), move the balances back to insurance,
#                                re-send every one plus the three still-open 9/8-10/25/2025 visits to UHC Dual Complete (seq 4) as originals.
#   B PAVLO 17475837 'restore' - void the seven 2026 WOINS write-offs ($1,986) and send the visits to AARP MA (seq 2) as originals.
#   C GOMER 17472519           - add the Florida Blue Medicare Advantage plan William pasted (BCBS1 car303217, 8/1/2024), end the dead
#                                Humana plan 7/31/2024, patient order = the new plan, re-route the 10/27 CCM to it.
#   D JACOBSEN 17477039         - add Humana Medicare Advantage (HUM01, 1/1/2026), end WellCare 12/31/2025, re-route the six July visits.
#   E MONROE 47979             - chart DOB [DOB] -> [DOB] (REST PATCH with familyupdate, placeholder address HCA), add UHC Dual
#                                Complete (UHCMA car302853, member from the HCA facesheet), end the dead UNI20 plan, re-route 11 hospital visits
#                                (UHC Dual first, FCC second).
#   F PRIMROSE 17478213            - chart DOB [DOB] -> [DOB] (facesheet), then re-send the eleven SUN01 hospital claims as originals.
#   G TOLLIVER 17471204           - the Aetna subscriber (spouse) gets his DOB [DOB] (updaterespparty), the four AET07 claims go again.
#   H ROWANTREE 17475392        - Stedi says TRICARE East is ACTIVE on the DBN the chart carries: re-send the seven TRI00 claims as originals.
#   I BROWN 17478229           - add TRICARE For Life (TRI05 car6559) as the Medicare secondary, order Medicare first.
#   J LAMPRON RISCH 12183299   - 'write-off': the seven AET07 cost-share residuals (Aetna ended 1/31/2025) -> WOCLTREQ.
#   K LANGE 21593              - 'written off': the eight August-2026 WellCare residuals (deceased [DOB], no live secondary) -> WOCLTREQ.
#   L MAPLIN 17469446         - 'Humana Medicaid': every 2025 residual still billed to the dead WellCare plan goes to the Humana Medicaid
#                                plan (seq 2) behind Medicare (seq 3) - one re-route per visit.
#   M OSGOOD 45011             - 'write off': the 1/9/2025 CHP charge $61.34 -> WOINS (CHP $0 answers, patient deceased [DOB]).
#   N THACKERAY 17472874         - 'OK': end WellCare 12/4/2025, re-send the two December-2025 visits Medicare first, Sunshine second.
#   O NESBIT 17471793           - 'move 10/22 CCM to 10/21': re-date the CCM visit (full-visit echo, same charge ids), then re-route the
#                                CCM and the 10/22 99309 to Medicare first (2,4) as originals.
# Rules it uses: one frequency-1 rebill per visit (freq1_visit.reroute / run; amd.rebill_charge's per-run guard + deceased guard);
#   void_tx.void_writeoff + move_to_ins.move(no rebill) for a restore; add_ins.add (no group number); ins_update.update verifies the
#   patient order; manual_post.post for write-offs (never over-apply); patient_patch.get/flatten + the familyupdate PATCH for a DOB.
# Never touches: charts not named above; payments; the ERA Center. --dry (default) reads and prints the plan; --live writes.
# Usage: python3 board_act_1102.py [--live] [--only A,B,...]   register: registers/board_act_2026-11-02T0855Z.json
# LOCAL ONLY: the data table (member ids, dates of birth) lives in the workspace copy /home/claude/unbilled/board_act_1102.py and the Drive workspace mirror; this stub carries the header only.
