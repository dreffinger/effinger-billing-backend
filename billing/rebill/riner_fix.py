# PLAIN ENGLISH (Riner to UHC Advantage)
# Decides: End Humana 6/30/25, add UHC MA <member number> from 7/1/25, undo the two Medicare CO24 postings, re-send the three visits.
# Rules it uses: CO24 = an Advantage plan is responsible; discovery said which one.
# Never touches: Riner's paid 2025 visits.
# ---
import os, sys, amd, add_ins, ins_update, co24_restore, rebill_patient_year
# REDACTED: the UHC member number is patient data and stays out of git (rules.md).
# Pass it in: MEMBER_NUM=<number> python riner_fix.py   (the value is in the workspace copy)
MEMBER_NUM = os.environ.get('MEMBER_NUM') or (sys.argv[1] if len(sys.argv) > 1 else None)
if not MEMBER_NUM: sys.exit('set MEMBER_NUM (UHC MA member number) or pass it as argv[1]')
amd.login_cached(); pid='17473032'
print('end Humana', ins_update.update(pid,'ins9512579', enddate='06/30/2025')[0], flush=True)
r=add_ins.add(pid,'car6404',MEMBER_NUM,'07/01/2025'); print('add UNI20', r, flush=True); seq=r[1]
for l in co24_restore.run(pid, seq, '09/01/2025', '12/31/2025'): print(' ', l, flush=True)
for l in rebill_patient_year.run('pat'+pid, seq, 365):
    if 'skip' not in l: print(' ', l, flush=True)
print('DONE')
