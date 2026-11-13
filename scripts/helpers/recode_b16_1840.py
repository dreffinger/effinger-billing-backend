# PLAIN ENGLISH (run 2026-11-13T1840Z): RRB Medicare check 321478300 (ERA 1053519) denied v19457097 99344 10/01/2026 CO-B16
#   'New Patient qualifications were not met' - the chart has 2026 99349s, so the standing rule (act_1910_1004.py part C):
#   99344 (pcode601053) -> 99349 (pcode65142) via recode.swap_proc (full-visit resave + freq-1 rebill on the visit's seq).
#   --dry prints only. Never touches payments.
import amd, resave, recode, sys, time
DRY = "--dry" in sys.argv
amd.login_cached()
cid = "23368919"
vis, pat, allc = resave.visit_charges(cid)
seq = (vis.get("insorder") or "1").split(",")[0]
print("visit", vis.get("id"), "insorder", vis.get("insorder"), "charges", [(c.get("id"), c.get("proccode")) for c in allc])
if any(c.get("proccode") != "pcode601053" for c in allc):
    print("not a lone 99344 visit - skipped"); sys.exit(0)
if DRY:
    print("DRY swap_proc pcode601053 -> pcode65142 freq-1 seq", seq); sys.exit(0)
print(recode.swap_proc(cid, {"pcode601053": "pcode65142"}, seq)); time.sleep(1)
print("after", [(c.get("id"), c.get("proccode")) for c in resave.visit_charges(cid)[2]])
