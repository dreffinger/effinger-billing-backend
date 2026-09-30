# PLAIN ENGLISH (AMD writes from the 2026-09-30T0630Z nightly cascade - APPLIED 9/30 12:15-12:28Z with William's approval; kept as the record)
# Decides: Nothing new. Applies the three chart fixes the cascade settled on 9/30 (rules a/c of the nightly prompt) once a session
#          with AMD-write permission runs it: cd /home/claude/unbilled && python3 amd_writes_pending.py
# Why it was not run: the auto-mode permission classifier refused the batch ("Modify Shared Resources") - third refusal of this kind
#          (9/28 2310Z plan add, 9/30 0510Z void/hide batch, 9/30 0630Z this batch). See docs/ROUTINE_PERMISSIONS.md.
# Evidence (all in the run digest + board inbox file board_updates_2026-09-30T0630Z.json):
#   pat17477638: Stedi MBI lookup ERR 72, CMS direct ERR 72, AMD 271 ERR 72 on Medicare AND Medicaid ids; Stedi discovery -> UHC 87726
#                member <UHC member id - see board file> "LPPO-UHC NURSING HOME PLAN FL-F001 (PPO I-SNP)" ACTIVE; Stedi elig 87726 on DOS 9/2 ACTIVE.
#   pat17473748: Medicare 271 names UNITEDHEALTHCARE OF FLORIDA H2509 (HN) COB 20260701; Stedi 87726 by MBI on DOS 9/24 ACTIVE
#                "FL UNITEDHEALTHCARE DUAL COMPLETE HMOPOS HIDE FULL" plan 20260701-20261231, member <UHCMA member id - see board file> group FLDSNP;
#                chart UNI20 <old UNI20 number on chart> (ins9518020) INACTIVE on Stedi and AMD.
#   pat17476681: AMD Medicare 271 ACTIVE (QMB, WellCare PDP only = original Medicare); FL Medicaid 271 "SMMC MMA Capitated HUMANA";
#                Stedi 61101 with the Medicaid id on DOS 9/24 ACTIVE "MEDICAID GATE CAP DIR" planBegin 20260623; the 9/20 + 9/24
#                visits were billed Medicaid-primary (MCAD) - Medicare-first rule.
# IDS REDACTED in this repo copy (PHI gate): the runnable copy with the member ids is in Drive "workspace mirror" as amd_writes_pending_2026-09-30T0630Z.py and in /home/claude/unbilled/amd_writes_pending.py.
# Never touches: paid visits (rebill_patient_year skips them), any other chart.
import add_ins, ins_update, rebill_patient_year as R, re
out = []
def seq_of(s): return s[1] if isinstance(s, tuple) else re.sub(r"\D", "", str(s))   # add_ins.add returns (insid, seq) - the 9/30 first pass concatenated both and AMD faulted
# pat17477638: add UNI20 (car6404) <UHC member id - see board file> from 09/01/2026; rebill the 4 open visits (9/2, 9/20, 9/23, 9/24; $976) freq-1 to it
s = add_ins.add("17477638", "car6404", "<UHC member id - see board file>", "09/01/2026"); out.append(("17477638 add UNI20", s))
out += [("17477638", l) for l in R.run("17477638", seq_of(s), 40)]
# pat17473748: add UHCMA (car302853) <UHCMA member id - see board file> from 07/01/2026; end the dead UNI20 ins9518020 on 06/30/2026; rebill 9/24 ($141) UHCMA then Medicaid (seq 3)
s = add_ins.add("17473748", "car302853", "<UHCMA member id - see board file>", "07/01/2026"); out.append(("17473748 add UHCMA", s))
out.append(("17473748 end UNI20 ins9518020", ins_update.update("17473748", "ins9518020", enddate="06/30/2026")))
out += [("17473748", l) for l in R.run("17473748", seq_of(s) + ",3", 92)]
# pat17476681: add HUM01 (car6285) <Medicaid id on chart> from 06/23/2026 (Humana Medicaid MMA); rebill 9/20 ($206) + 9/24 ($141) Medicare (seq 2) first, Humana Medicaid second
s = add_ins.add("17476681", "car6285", "<Medicaid id on chart>", "06/23/2026"); out.append(("17476681 add HUM01", s))
out += [("17476681", l) for l in R.run("17476681", "2," + seq_of(s), 15)]
for o in out: print(o)
