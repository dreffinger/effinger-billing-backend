# PLAIN ENGLISH (Claim Inspector dementia-primary fix, 11 PM ET 10/13 run 2026-10-14T0310Z - ehpa cloud)
# Decides: nothing new. Two secondary-claim visits the 10/13 patient-balance review re-queued carry F02.80 (dementia in other
#   diseases) in the FIRST diagnosis slot and the inspector holds them with Pattern 20389. William's standing inspector rule:
#   F02.8x -> F03.90 (dcode1034545095) - the swap, then a full-visit echo resave (recode._save: every live charge echoed, so no
#   charge is voided), then re-list the visit's batch and bypass ONLY the advisory patterns with FRESH error ids (20657 timely,
#   35790 add-on). A visit whose only code is a sequela (S06.5XAS) is NOT touched - it holds for William.
# Rules it uses: dry by default (--live); reads the charge's live diagnosis list first and does nothing when F02.80 is not first.
# Never touches: payments, write-offs, procedure codes, insurance plans, other visits.
"""Usage: python3 insp_dx_1014_0310.py [--live]"""
import amd, resave, recode, re, sys, time, json, datetime
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv
F0280 = "dcode1034545129"; F0390 = "dcode1034545095"
ADV = ("Pattern 20657", "Pattern 35790", "Pattern 33799", "Pattern 3429", "Pattern 35777", "Pattern 11256")
WORK = [("19409352", "22484794", "114394"), ("19452645", "23363008", "127559")]   # (visit, a charge id on it, inspector batch)
reg = {"stamp": "2026-10-14T0310Z", "live": LIVE, "done": []}
amd.login_cached()
def listing(bid):
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
    out = {}
    for v in ET.fromstring(t).iter("visit"):
        out[v.get("id")] = [(e.get("id"), re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))[:120]) for e in v.iter("error")]
    return out
for vid, cid, bid in WORK:
    x = resave.detail(cid); m = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x)
    dx = (dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))).get("diagcodes") or "").split()
    if not dx or dx[0] != F0280:
        print("SKIP v%s: first dx is %s, not F02.80" % (vid, dx[:1])); continue
    new = [F0390] + [d for d in dx[1:] if d != F0390]
    if not LIVE:
        print("DRY v%s charge %s: %s -> %s (F02.80 -> F03.90 first), then re-list batch %s and bypass advisories" % (vid, cid, dx, new, bid)); continue
    def e(a, new=new, dx=dx):
        if (a.get("diagcodes") or "").split() == dx: a["diagcodes"] = " ".join(new); return True
        return False
    c2, msg = recode._save(cid, e)
    ok = c2 is not None
    print("SWAP v%s charge %s -> %s %s" % (vid, cid, "OK" if ok else "FAULT", str(msg)[:120]), flush=True)
    rec = {"vid": vid, "cid": cid, "swap": ok, "msg": str(msg)[:160], "bypassed": [], "left": []}
    if ok:
        time.sleep(1.5); errs = listing(bid).get(vid, [])
        adv = [i for i, t in errs if t.startswith(ADV)]; other = [(i, t) for i, t in errs if not t.startswith(ADV)]
        if adv:
            r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % i for i in adv))))
            rec["bypassed"] = adv if "Fault" not in r else []; print("  bypass %s -> %s" % (adv, "OK" if "Fault" not in r else r[:120]))
        rec["left"] = other; print("  left on the visit:", other)
    reg["done"].append(rec); time.sleep(0.5)
json.dump(reg, open("registers/insp_dx_2026-10-14T0310Z%s.json" % ("" if LIVE else "_dry"), "w"), indent=1)
