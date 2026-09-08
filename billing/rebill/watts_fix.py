# PLAIN ENGLISH (Watts Feb-May 2026 to Medicare)
# Decides: UHC was inactive Feb-May 2026 (Stedi), so those visits go Medicare first, FCC second; UHC start set to 6/1/26.
# Rules it uses: Medicare before Medicaid/LTC.
# Never touches: June 2026 onward, which is UHC's.
# ---
import amd, ins_update, rebill_patient_year
amd.login_cached(); pid='17471645'
print('UHC begin 6/1/26', ins_update.update(pid,'ins9510928', begindate='06/01/2026')[0], flush=True)
print('Medicare begin 1/1/26', ins_update.update(pid,'ins9519226', begindate='01/01/2026')[0], flush=True)
import datetime
def order(d): return '3,2' if d < datetime.date(2026,6,1) else '1'
for l in rebill_patient_year.run('pat'+pid, order, 365):
    if 'skip' not in l: print(' ', l, flush=True)
print('DONE')
