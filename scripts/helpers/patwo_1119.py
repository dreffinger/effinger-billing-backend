# PLAIN ENGLISH (Patient-balance write-off on William's word, 11/19/2026) - command line for patient_writeoff.post.
# Decides: Nothing. William on the board card of chart 17477639 (10/11/2026): "write off the ccm claim not paid post the one
#          paid as paid". Writes off ONE charge's PATIENT balance with the code given (patient_writeoff.post re-reads the
#          charge live and refuses more than the live patient balance).
# Never touches: insurance balances, payments, other charges. Usage: python3 patwo_1119.py <chargeid> <amount> <code> [--live]
import amd, patient_writeoff, sys
a = [x for x in sys.argv[1:] if not x.startswith("--")]; amd.login_cached()
print(patient_writeoff.post(a[0], float(a[1]), a[2], "BOARD1119", "William board 10/11/2026: write off the CCM not paid", dry="--live" not in sys.argv))
