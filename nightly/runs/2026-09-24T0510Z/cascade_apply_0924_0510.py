# PLAIN ENGLISH (insurance cascade - APPLY, 1am ET 9/24/2026 run 2026-09-24T0510Z), from cascade_0510.json (Stedi MBI lookup /
#   discovery / payer eligibility with the MBI): per chart add the plan the payers named (NO group number), read AMD's free 271 on it,
#   fill a blank address line 1 from line 2 (addr_line1_fix), write the admission date on hospital visits (own 99223 = 9/21/2026),
#   modifier 25 (mcode7) on a 99497 billed with 99223/99306, full-visit resave with insorder + onhcfa=1, release from Unbilled.
#   Straight Medicare (MBI, no MA entity) -> FLO02; Medicare's 271 / discovery names an MA plan -> that plan alone (facesheet Medicare-label
#   rule); UHC Dual Complete -> UHCMA; wrong MBI on the chart (271 AAA 72) -> corrected in place, original claim to Medicare.
# Holds (never touched): pat17477639 (MBI 72 + discovery 0 -> William), pat17477842 (placeholder-DOB duplicate chart -> William),
#   pat17477850 unless discovery names the CHP member id (Medicare's 271 names Capital Health Plan MA; CHP wants its own member id).
# Never touches: payments, write-offs, other charts' plans.
# ---
# LOCAL ONLY: the body of this script carries the member numbers / MBIs the run entered on the ten charts, so only this header is
# mirrored. The full file lives in the workspace (/home/claude/unbilled/local/cascade_apply_0924_0510.py) and in Drive 'workspace mirror'.
# Shape: add_ins.add(pid, carrier, member, begin, "1", finclass) (no group) -> elig_amd.run_plan (free 271) -> addr_line1_fix.fix ->
# updextrainsinfo hospitalizationfrom=09/21/2026 per CPT on the HCA visits -> full-visit updvisitwithcharges echo with insorder + onhcfa=1
# (+ mcode7 on a 99497 billed with 99223/99306, pos 21 on hospital charges) -> hideunbillablevisits. Bissell: ins_update subscribernum
# then freq1_visit.run seq 1. Tillman K: add FLO02 from discovery, 271, begindate = Part B date, three September visits -> new seq, freq-1, release.
