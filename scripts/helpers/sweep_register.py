# PLAIN ENGLISH (UNI20/BCBS pre-5/1/2026 sweep register writer, 7 AM ET 10/7/2026 run)
# Decides: nothing. Copies this run's claim_status_sweep.py output (claimstatus_<date>.json, a list of
#   {visitid, patientid, carrier, dos, balance, icn, status, errors, action} rows - chart and visit ids only, no names)
#   into registers/uni20_bcbs_pre0501_sweep_<stamp>.json in the shape the earlier passes used ({about, stamp, rows}),
#   so the next pass can feed it to --skip-answered.
# Never touches: AdvancedMD, Stedi, any other file.
# Usage: python3 sweep_register.py <claimstatus json> <run stamp> <pass number>
import json, sys
src, stamp, npass = sys.argv[1], sys.argv[2], sys.argv[3]
rows = json.load(open(src))
rows = [{k: v for k, v in r.items() if k.lower() not in ("name", "patientname", "patient")} for r in rows]
reg = {"about": "UNI20/BCBS pre-5/1/2026 claim-status sweep pass %s (claim_status_sweep.py --min-age 159 --max 60 --carriers UNI20,BCBS --skip-answered <passes 1-%d>)" % (npass, int(npass) - 1),
       "stamp": stamp, "rows": rows}
out = "registers/uni20_bcbs_pre0501_sweep_%s.json" % stamp
json.dump(reg, open(out, "w"), indent=1)
from collections import Counter
print("wrote", out, len(rows), "rows", dict(Counter(r.get("action") for r in rows)))
