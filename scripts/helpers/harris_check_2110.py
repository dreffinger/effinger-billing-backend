# PLAIN ENGLISH (5pm ET 9/19 run): re-reads chart pat17477798 (Unbilled 'Insurance order is missing') - counts live insurance plans. Never writes.
import amd, re
amd.login_cached()
t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "17477798", "nocookie": "1"}), timeout=120)
plans = re.findall(r'<insplan [^>]*/?>', t)
print("pat17477798 insplans:", len(plans), [dict(re.findall(r'(carrier|sequence|enddate)="([^"]*)"', p)) for p in plans])
