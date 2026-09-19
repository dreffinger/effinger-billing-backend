# PLAIN ENGLISH (3pm ET 9/19/2026 run 2026-09-19T1910Z): pat17474446 v19455133 99344 (new-patient home visit) was held by Pattern 4310
#   (established patient: the practice saw the patient 12/20/2025, within three years). Standing rule: a second new-patient code on an
#   established patient -> 99349 (pcode65142). Uses recode.swap_proc (full-visit resave + freq-1, precedent inspector_0906.py), then
#   re-lists the inspector batches and bypasses only advisory edits with fresh ids. Result register: registers/whitlock_recode_<stamp>.json
# Never touches: payments, write-offs, other visits.
import amd, resave, recode, re, time, json
amd.login_cached()
cid="23366273"; vid="19455133"; pid="17474446"
vis,pat,allc=resave.visit_charges(cid); pc=allc[0].get("proccode"); res={"vid":vid,"pid":pid,"cid":cid,"from":pc}
if pc=="pcode601053":
    res["swap"]=recode.swap_proc(cid, {"pcode601053":"pcode65142"}, (vis.get("insorder") or "1").split(",")[0]); time.sleep(1)
    res["after"]=[(c.get("id"),c.get("proccode"),c.get("fee")) for c in resave.visit_charges(cid)[2]]
print(res); json.dump(res,open("registers/whitlock_recode_2026-09-19T1910Z.json","w"),indent=1)
