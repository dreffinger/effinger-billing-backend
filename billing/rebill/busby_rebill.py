# PLAIN ENGLISH (Busby hospice-period rebill)
# Decides: Busby's 5/31-8/4/26 visits to FCC with GV.
# Rules it uses: Hospice period from the census.
# Never touches: Visits outside the hospice window.
# ---
import amd, rebill_patient_year
amd.login_cached()
for line in rebill_patient_year.run('pat23161', '2', 365): print(line, flush=True)
print("=== done", flush=True)
