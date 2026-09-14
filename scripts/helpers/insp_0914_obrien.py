# PLAIN ENGLISH (Claim Inspector pass, 11 PM ET 9/13/2026 slot - ehpa cloud run 9/14; William's 9/14 primary-dx rule)
# Decides: for every inspector visit of pat44953 (CCM 99487+99489, Humana denied ZY3 'diagnosis cannot be billed in the
#   primary position' with F31.9 first): move F31.9 out of the primary slot (G30.9 Alzheimer's leads, F31.9 last) per
#   William 9/14 ('delete the bad code if that works, or move it to not primary, or add I10 in its place'); keep modifier 25
#   on the 99489 add-on only (mcode7); full-visit resave (charge echo); re-list the batch and bypass Pattern 35790 with the
#   FRESH error ids; then reset freq 1 + chargerebill on the Humana sequence so the corrected claim leaves as an original.
# Never touches: missing-data errors, voided/paid charges, other patients.
"""Usage: python3 insp_0914_obrien.py [--dry]"""
import amd, resave, freq1_visit, json, re, sys, time
import xml.etree.ElementTree as ET
dry = "--dry" in sys.argv
amd.login_cached()
LOG = open("insp_0914_obrien.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
S = json.load(open("scan_0912/summary_before.json"))
BAD = "dcode1034545237"   # F31.9
targets = []
for bid, vs in S["inspector"].items():
    for v in vs:
        if v["pid"] == "44953": targets.append((bid, v))
L("=== O'Brien inspector visits: %d (dry=%s) ===" % (len(targets), dry))
# Humana sequence on the chart
x = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat44953", "nocookie": "1"}), timeout=60)
plans = [dict(i.attrib) for i in ET.fromstring(x).iter("insplan")]
hum = [p for p in plans if p.get("carrier") == "car6285" and not p.get("enddate")]
seq = hum[0]["sequence"] if hum else None
L("chart plans: %s -> HUM01 seq %s" % ([(p.get("carrier"), p.get("sequence"), p.get("begindate"), p.get("enddate")) for p in plans], seq))
if not seq: L("no open HUM01 plan - stop"); sys.exit(1)

def list_batch(bid):
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
    out = []
    for v in ET.fromstring(t).iter("visit"):
        errs = []
        for e in v.iter("error"):
            name = e.get("name") or ""; m = re.search(r"Pattern (\d+)", name)
            errs.append({"id": e.get("id"), "pat": m.group(1) if m else "OTHER", "name": name})
        out.append({"vid": v.get("id"), "errs": errs})
    return out

def resave_dx(cid):
    vis, pat, allc = resave.visit_charges(cid); chg = ""; changed = 0
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        d = (a.get("diagcodes") or "").split()
        if BAD in d and d[0] == BAD:
            a["diagcodes"] = " ".join([z for z in d if z != BAD] + [BAD]); changed += 1
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, val) for k, val in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    body = "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, val) for k, val in va.items()), chg)
    if dry: return "DRY %d charges, %d dx edits, insorder=%s" % (len(allc), changed, va.get("insorder"))
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, body))
    time.sleep(0.8)
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:250])
    v2, p2, c2 = resave.visit_charges(cid)
    dx = [(c.get("proccode"), c.get("diagcodes"), c.get("modcodes")) for c in c2]
    return "ok (%d edited; %d live, was %d) now %s" % (changed, len(c2), len(allc), dx)

def bypass(vid, errids):
    r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in errids))))
    return "Fault" not in r

done = []
for bid, v in targets:
    cid = v["chgs"][0][0]
    L("DX    v%s batch %s chg %s -> %s" % (v["vid"], bid, cid, resave_dx(cid)))
    time.sleep(0.5)
if dry: sys.exit()
time.sleep(2)
for bid, v in targets:
    V2 = list_batch(bid); me = [z for z in V2 if z["vid"] == v["vid"]]
    if not me: L("CLEAR v%s batch %s: no longer listed" % (v["vid"], bid))
    else:
        adv = [e["id"] for e in me[0]["errs"] if e["pat"] in ("35790", "3429", "7011", "35777", "33799", "20657", "4310", "4311", "4426")]
        other = [e for e in me[0]["errs"] if e["id"] not in adv]
        L("BYPASS v%s %s -> %s; left %s" % (v["vid"], [e["pat"] for e in me[0]["errs"] if e["id"] in adv], bypass(v["vid"], adv) if adv else "none", [(e["pat"], e["name"][:80]) for e in other]))
    time.sleep(0.4)
time.sleep(2)
for bid, v in targets:
    cid = v["chgs"][0][0]
    try: L("REBILL v%s -> %s" % (v["vid"], freq1_visit.run(v["vid"], cid, seq)))
    except Exception as e: L("REBILL ERR v%s %s" % (v["vid"], str(e)[:150]))
    time.sleep(0.5)
b = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); L("BATCHES after: %s" % re.findall(r'<batch id="([^"]+)"', b))
