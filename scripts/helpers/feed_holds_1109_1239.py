#!/usr/bin/env python3
# PLAIN ENGLISH (feed holds of the 2026-11-09T1239Z columns run)
# Decides: nothing new - applies the standing cascade to the two charts the feed verify step held:
#   chart 17478349 (new chart F261109-03): Stedi discovery found UMR member [member id] ACTIVE from 7/1/2026 (the verify helper
#     has no STEDI_NAME_MAP entry for UMR, so it held) -> add the UMR plan (car303242, no group number), chart order to it,
#     AMD 271 on the new plan, visit insorder on both feed visits.
#   chart 17477946 (TRICARE East, paid on every SNF visit since 9/28/2026): the 271 answered EB*I under the Direct Care plan,
#     which the verify step read as 'no active plan'; TRI00 is the paying carrier -> visit insorder 1 on the 11/4 99316.
# Rules it uses: add_ins.add (no group), ins_update._set_order, claimocity_verify.fast_set_insorder (full-visit echo), ONE login.
# Never touches: balances, rebills (nothing is billed yet), other visits.
import sys, json, re, os
os.environ.setdefault("FEED_STAMP", "20261109T1239Z")
sys.path.insert(0, "/home/claude/unbilled")
import amd, add_ins, ins_update, elig_amd, claimocity_verify as cv
amd.login_cached()
reg = json.load(open("/home/claude/unbilled/registers/feed_import_20261109T1239Z.json"))
def _flat(x):
    if isinstance(x, dict): return [x]
    out = []
    for y in (x if isinstance(x, list) else []): out += _flat(y)
    return out
rows = _flat(reg.get("created") if isinstance(reg, dict) else reg)
byvisit = {r["visit"]: r for r in rows if isinstance(r, dict) and "visit" in r}
out = {}
if "--umr" in sys.argv:
    pid = "17478349"
    insid, seq = add_ins.add(pid, "car303242", "50242529", "07/01/2026")
    out["add"] = [insid, seq]
    if insid and str(insid).startswith("ins"):
        plans = {p["id"]: p for p in elig_amd.plans(pid)[1]}
        out["order"] = ins_update._set_order(pid, plans, insid, str(seq))
        try:
            out["271"] = (amd.check_eligibility(re.sub(r"\D", "", insid)) or "")[:600]
        except Exception as e:
            out["271"] = "error %s" % str(e)[:200]
        for v in ("vst19460539", "vst19460546"):
            out[v] = cv.fast_set_insorder(byvisit[v], str(seq))
if "--tri" in sys.argv:
    out["vst19460541"] = cv.fast_set_insorder(byvisit["vst19460541"], "1")
print(json.dumps(out, default=str, indent=1))
