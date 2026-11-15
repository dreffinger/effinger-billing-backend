#!/usr/bin/env python3
# PLAIN ENGLISH (Exclusions column by hand, 1:39 PM ET 11/15 columns run, fired 18:39Z)
# Decides: nothing new - the 11/11 precedent (excl_1111_1839.py B) for chart 12232512: Humana 'ENTITY NOT FOUND: PATIENT' on William's
#   claim run 1700379, v19461101 (11/05/2026 99309, $141). Humana is only the SMMC long-term-care plan; the medical payer is UHC Dual
#   Complete (UNI20 seq 4, chart default order 4,3). Visit order -> 4,3 by a no-rebill full-visit echo, then the standing outpatient-stroke
#   swap I63.9 -> I69.30 (recode.swap_dx: full echo, freq-1, ONE rebill to seq 4), then complete the exclusion. Never rebill a paid visit.
# Usage: python3 excl_1115_1840.py [--live]
import sys, re, json, time, amd, recode, resave, txh
LIVE = "--live" in sys.argv; STAMP = "2026-11-15T1840Z"; RID, VID, CID, PID = "1700379", "19461101", "23373930", "12232512"
out = {"stamp": STAMP, "live": LIVE, "steps": []}
def step(k, v): out["steps"].append({k: v}); print(k, "->", str(v)[:300])
amd.login_cached()
x = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": RID, "clearinghouse": "1", "payer": "1", "nocookie": "1"}))
l = {m.group(1): m.group(2) for m in re.finditer(r'<visit [^>]*\bid="(\d+)" claimid="([^"]+)"', x)}; step("listed", l)
paid = any(c.attrib.get("visit") == VID and [p for p in c.iter("payment") if p.get("void") not in ("1", "true")] for c in txh.fetch(PID).iter("charge"))
step("paid", paid)
if VID in l and not paid:
    ok, msg = resave.set_insorder(CID, "4,3", dry=not LIVE, allow_billed=True); step("insorder", (ok, msg))
    if ok and LIVE:
        time.sleep(0.5); r = recode.swap_dx(CID, "dcode1034545006", "dcode1034545425", 4); step("swap_dx_rebill_seq4", r)
        if "FAULT" not in str(r).upper():
            time.sleep(0.5)
            h = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RID, "hide": "-1", "nocookie": "1"}, '<visitlist><visit id="%s" claimid="%s"/></visitlist>' % (VID, l[VID])))
            step("complete", "ok" if "Fault" not in h else h[:200])
    elif ok: step("swap", "DRY swap_dx I63.9->I69.30 + freq1 rebill seq 4; complete")
r = amd.post(amd.msg("getclaimexclusionclaimruns", "claimsreports", {"nocookie": "1"})); m = re.search(r'<Results[^>]*>', r); step("after", m.group(0) if m else r[:200])
json.dump(out, open("registers/excl_hand_%s_actions%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1)
