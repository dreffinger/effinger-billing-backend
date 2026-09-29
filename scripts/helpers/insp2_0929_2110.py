# PLAIN ENGLISH (second inspector pass, run 2026-09-29T2110Z): the Ambetter CO-45 correction resaved two PAID CCM visits (v19455800 pat17475198,
#   v19455735 pat17473669) and the re-inspection raised Pattern 35790 (99489 add-on advisory) on each. Ambetter already paid both claims as
#   coded, so the coding is left alone and the advisory is bypassed with the FRESH error ids (the standing rule: a resave of an old CCM
#   visit re-raises 35790 - just bypass again). Never touches: charges, modifiers, payments, any other row.
import amd, re, json, time, sys
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv; S = "2026-09-29T2110Z"; TARGET = {"19455800", "19455735"}
amd.login_cached(); out = []
ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"')
for bid in re.findall(r'<batch id="([^"]+)"', ib):
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
    for v in ET.fromstring(t).iter("visit"):
        if v.get("id") not in TARGET: continue
        errs = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))[:120]) for e in v.iter("error")]
        rec = {"batch": bid, "vid": v.get("id"), "pid": v.get("patientid"), "errs": errs}
        if errs and all("Pattern 35790" in e[1] for e in errs):
            if DRY: rec["bypassed"] = "dry"
            else:
                r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (v.get("id"), "".join('<claimedit id="%s"/>' % e[0] for e in errs))))
                rec["bypassed"] = "Fault" not in r; rec["resp"] = re.sub(r"\s+", " ", r)[:160]
        else: rec["bypassed"] = "not advisory-only - left"
        out.append(rec); print(rec, flush=True); time.sleep(0.3)
    time.sleep(0.3)
json.dump(out, open("registers/insp2_%s.json" % S, "w"), indent=1)
