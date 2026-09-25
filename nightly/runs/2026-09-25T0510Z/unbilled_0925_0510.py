# PLAIN ENGLISH (Unbilled pass, 1am ET 9/25/2026 run 2026-09-25T0510Z): 40 rows on the snapshot - 16 pat17472874 + pat17474541 behind
#   the standing Claim Inspector holds, 8 standing 'Insurance order is missing' rows on William's turn, 1 'Payment reason codes' row
#   (pat46673 v19420915 = the standing ERA check 1052828 - repaired by payreasons.py --live --unbilled, run separately),
#   14 'A payment from the prior payor is required' rows and 2 NEW 'Insurance order is missing' rows (9/22/2026 SNF 99306+99497).
# Decides:
#   prior payor (13 visits): the primary claim is at Medicare (charge carrier FLO02, billdate 9/5-9/13/2026, $0 paid, only a $0 BCBS/UHC
#     wrong-payer denial on the charge) -> nothing to fix, release (William's 9/8 rule b; they re-queue on their own). pat17470743 v19441047
#     = the standing MCAD crossover hold, NOT released. Any visit with a payment older than 60 days and the secondary still unbilled is held.
#   pat17476042 v19456057: UNI20 plan ended 08/19/2026, Medicare FLO02 seq 2 ACTIVE on AMD's 271 (straight Medicare, WellCare PDP only)
#     -> visit insorder 2 (full-visit resave, both charges echoed), patient default order 2, address line 1 = ALF placeholder, release.
#   pat17477870 v19456058: a NEW chart the Claimocity feed created for a patient who already has chart pat17470849 (same DOB,
#     name spelled differently) -> the existing chart's three plans copied onto the new chart (UHC MA primary, Medicaid, Humana Medicaid;
#     NO group numbers), AMD 271 on each, patient order 1,3 like the original, visit insorder 1,3, SNF address placeholder, release;
#     board row on William's turn to MERGE the duplicate chart.
# Never touches: payments, write-offs, the pat17472874 / pat17474541 inspector holds, v19441047, the 8 standing insurance rows.
# ---------------- 1. prior payor rows
# ---------------- 2. HOLLIS pat17476042 v19456057 -> Medicare seq 2
# ---------------- 3. OSGOOD duplicate chart pat17477870 v19456058 -> copy the plans of pat17470849
# ---
# LOCAL ONLY: the body of this script carries the member numbers the run copied onto the duplicate chart, so only the
# header is mirrored. The full file lives in the workspace (/home/claude/unbilled/local/unbilled_0925_0510.py) and in the
# practice's Drive project folder ('workspace mirror'). Shape: txh.fetch_visit -> hideunbillablevisits (prior payor, rule b);
# elig_amd.run_plan -> amdw.resave_visit insorder -> ins_update.update(sequence) -> addr_line1_fix -> hideunbillablevisits;
# add_ins.add x3 (no group) -> elig_amd.run_plan -> ins_update.update(sequence "1,3") -> patient_patch.family_address (500) -> HELD.
