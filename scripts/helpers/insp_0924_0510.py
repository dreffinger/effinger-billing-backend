# PLAIN ENGLISH (Claim Inspector pass, 1am ET 9/24/2026 run 2026-09-24T0510Z): the Unbilled/cascade resaves re-ran the inspector on the
#   September CCM visits and it raised 15 advisories - Pattern 35790 (99489 add-on with 99487) on 10 visits and Pattern 11256 (unspecified
#   laterality) on 5. Rule: modifier 25 = mcode7 on the 99489 (never on 99487) when missing, then bypass 35790; 11256 -> bypass + log to
#   laterality_flag_log.md. Error ids change on every re-inspection, so every bypass uses ids from a fresh batch listing.
# Never touches: the standing holds (pat17472874 April stay, v19430630 Pattern 15775, v19455625/v19455691 deceased guard, v19455936 CCI,
#   v19455940 duplicate CCM lines), payments, plans.
"""Usage: python3 insp_0924_0510.py [--dry]"""
import amd, resave, re, time, json, sys, datetime
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv
S = "2026-09-24T0510Z"
amd.login_cached()
HOLD_VIDS = {"19430630", "19455625", "19455691", "19455936", "19455940"}
HOLD_PIDS = {"17472874"}
ADV = ("Pattern 35790", "Pattern 11256", "Pattern 4426", "Pattern 4310", "Pattern 4311", "Pattern 3429", "Pattern 7011", "Pattern 35777", "Pattern 33799", "Pattern 20657", "Pattern 27261", "Pattern 23400", "The Source of Payment you have chosen is not typical")
out = {"stamp": S, "dry": DRY, "mod25": [], "bypassed": [], "left": [], "faults": []}
def L(m): print(m, flush=True)
def list_batches():
    r = amd.post(amd.msg("getclaiminspectorbatches", "chargeentry", {"nocookie": "1"}), timeout=120)
    return re.findall(r'<batch id="(\d+)"', r) or re.findall(r'batchid="(\d+)"', r) or re.findall(r'<claimbatch [^>]*id="(\d+)"', r)
def list_batch(bid):
    r = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
    root = ET.fromstring(r); rows = []
    for v in root.iter("visit"):
        errs = [(e.get("id"), re.sub(r"\s+", " ", (e.get("name") or "") + " " + (e.text or "") + "".join((c.text or "") for c in e.iter()))[:220]) for e in v.iter("error")]
        rows.append({"vid": v.get("id"), "pid": v.get("patientid"), "status": v.get("claimstatus"), "errs": errs, "chgs": [(c.get("id"), c.get("chgcode") or c.get("proccode"), c.get("modifiers")) for c in v.iter("charge")]})
    return rows
def add_mod25_on_99489(cid):
    vis, pat, allc = resave.visit_charges(cid); chg = ""; hit = None; has87 = False
    codes = {}
    for c in allc:
        d = resave.detail(c.get("id").replace("charge", "")); codes[c.get("id")] = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', d)).get(c.get("proccode"), "?")
        if codes[c.get("id")] == "99487": has87 = True
    if not has87: return "no 99487 on the visit", None
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        if codes[c.get("id")] == "99489" and "mcode7" not in (a.get("modcodes") or ""):
            a["modcodes"] = "mcode7" if not (a.get("modcodes") or "").strip() else a["modcodes"] + ",mcode7"; hit = c.get("id")
        if codes[c.get("id")] == "99487" and "mcode7" in (a.get("modcodes") or ""):
            a["modcodes"] = ",".join(m for m in a["modcodes"].split(",") if m != "mcode7"); hit = hit or c.get("id")
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    if not hit: return "99489 already carries mcode7", None
    va = dict(vis.attrib); va["force"] = "1"; va["onhcfa"] = "1"
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:200]), None
    time.sleep(0.6); d2 = resave.detail(hit.replace("charge", ""))
    return "mcode7 on %s -> readback mods %s" % (hit, re.findall(r'<modcode [^>]*code="([^"]*)"', d2)), hit
# pass 1: modifier 25 on the 99489 of every 35790 visit not on hold
scan = json.load(open("scan_0912/summary_after.json"))
targets = []
for bid, rows in scan["inspector"].items():
    for v in rows:
        if v["vid"] in HOLD_VIDS or v["pid"] in HOLD_PIDS or not v["errs"]: continue
        targets.append((bid, v))
for bid, v in targets:
    if any("35790" in e[1] for e in v["errs"]):
        cid = None
        for c in v.get("chgs", []):
            cc = c.get("id") if isinstance(c, dict) else (c[0] if isinstance(c, (list, tuple)) and c else c)
            cid = re.sub(r"\D", "", str(cc or "")) or cid
        if not cid:
            sb = json.load(open("scan_0912/summary_before.json"))
            cid = next((r["_chgs"][0]["id"] for r in sb["unbilled"] if r["id"] == v["vid"] and r["_chgs"]), None)
        if DRY: L("DRY v%s pat%s would put mcode7 on 99489 (cid %s)" % (v["vid"], v["pid"], cid)); continue
        try:
            msg, hit = add_mod25_on_99489(cid); L("v%s pat%s %s" % (v["vid"], v["pid"], msg)); out["mod25"].append({"vid": v["vid"], "pid": v["pid"], "result": msg})
        except Exception as e:
            out["faults"].append({"vid": v["vid"], "step": "mod25", "err": str(e)[:160]}); L("v%s mod25 EXC %s" % (v["vid"], str(e)[:160]))
        time.sleep(0.4)
if DRY: sys.exit()
time.sleep(3)
# pass 2: fresh listing, bypass advisories on the target visits only
tvids = {v["vid"] for _, v in targets}
lat = []
for bid in list_batches():
    try: rows = list_batch(bid)
    except Exception as e: out["faults"].append({"batch": bid, "err": str(e)[:120]}); continue
    for r in rows:
        if r["vid"] not in tvids: continue
        adv = [(eid, txt) for eid, txt in r["errs"] if any(p in txt for p in ADV)]
        other = [(eid, txt) for eid, txt in r["errs"] if not any(p in txt for p in ADV)]
        if other: out["left"].append({"vid": r["vid"], "pid": r["pid"], "errs": other}); L("LEFT v%s %s" % (r["vid"], other))
        if not adv: continue
        x = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (r["vid"], "".join('<claimedit id="%s"/>' % eid for eid, _ in adv))))
        ok = "Fault" not in x; L("bypass v%s pat%s %s -> %s" % (r["vid"], r["pid"], [t[:40] for _, t in adv], ok))
        out["bypassed"].append({"vid": r["vid"], "pid": r["pid"], "batch": bid, "errs": [t[:80] for _, t in adv], "ok": ok})
        for _, t in adv:
            if "11256" in t: lat.append("- %s run %s: v%s pat%s %s bypassed" % (datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ"), S, r["vid"], r["pid"], re.sub(r"\s+", " ", t)[:120]))
        time.sleep(0.4)
if lat: open("laterality_flag_log.md", "a").write("\n".join(lat) + "\n")
json.dump(out, open("registers/insp_%s.json" % S, "w"), indent=1)
L("SUMMARY mod25 %d bypassed %d left %d faults %d laterality-logged %d" % (len(out["mod25"]), len(out["bypassed"]), len(out["left"]), len(out["faults"]), len(lat)))
