# PLAIN ENGLISH (Unbilled pass, 1am ET 9/23/2026 run 2026-09-23T0510Z): 36 rows on the snapshot - 11 pat17472874 'Unresolved Claim
#   Inspector errors' (standing hold), 17 'A payment from the prior payor is required' (primary claims sent 9/5-9/21 and unanswered -> release
#   per rule (b); pat17470743 v19441047 = the known MCAD crossover hold, kept), 8 'Insurance order is missing' and 1 'DOS outside coverage'.
# Decides, per insurance row (cascade already run: no facesheet / Pam email / drop; AMD 271 only on charts with a plan; Stedi MBI lookup,
#   payer eligibility, insurance discovery):
#   pat17477830 -> straight Medicare (Stedi MBI, Part A/B since 10/2005, WellCare stand-alone PDP) -> FLO02 plan added, insorder 1;
#   pat17477828 -> UHC MA 'LPPO-UHC COMPLETE CARE GA-3 (PPO C-SNP)' 3/1/2026-12/31/2026 (discovery) -> UNI20 plan added, insorder 1,
#       three HCA visits get the admission date (own 99223 9/18/2026);
#   pat17477827 -> Ambetter 'Clarity Silver' 7/1-12/31/2026 (discovery) -> AMB03 plan added, insorder 1;
#   pat17477829 -> Florida Medicaid Full Medicaid (discovery) -> MCAD plan added; AMD's 271 read after the add (an SMMC plan named there
#       means the MMA plan must be added first - reported, visit released only when the order is right);
#   pat17477183 -> cascade exhausted (Sunshine ended 8/31/2026, not Medicare, Medicaid FFS inactive, discovery 0) -> board row, visit held;
#   pat24039 -> chart order 1,3 (Medicare + FCC) -> visit insorder 1,3;  pat17473669 -> UNI20 ended 5/31/2026, AMB03 live -> visit insorder 2.
#   Every plan added with NO group number; AMD's free 271 run on each new plan; full-visit resave (every live charge echoed) with onhcfa=1;
#   released with hideunbillablevisits only once the order is right. Address line 1 filled (street moved up from line 2) where AMD accepts it.
# Never touches: payments, write-offs, the pat17472874 holds, v19441047.
# ---
# LOCAL ONLY: the body of this script carries the member numbers / MBI the run entered on the four new charts, so only the
# header is mirrored. The full file lives in the workspace (/home/claude/unbilled/local/unbilled_0923_0510.py) and in the
# practice's Drive project folder ('workspace mirror'). Shape: add_ins.add (no group) -> elig_amd 271 -> updextrainsinfo
# hospitalizationfrom (hospital visits) -> full-visit resave insorder + onhcfa=1 -> addr_line1_fix -> hideunbillablevisits.
