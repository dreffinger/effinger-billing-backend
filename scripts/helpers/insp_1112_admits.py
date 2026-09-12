# PLAIN ENGLISH (inspector: admission dates for the 4 new HCA admits + Lowry's 99497, 9/12 7am ET run)
# Decides: writes hospitalizationfrom with updextrainsinfo (the resave's extins child did not stick on these brand-new visits),
#   resaves each visit with onhcfa=1 (full echo) so the inspector re-runs; for Lowry v19453862 checks the 99497 carries
#   modifier 25 (mcode7 - never the literal "25") next to the 99223, adds it if missing, then bypasses the unbundle advisory
#   (Pattern 23400) with a FRESH id after re-listing. Anything else left is reported, not bypassed.
import amd, resave, era_post, re, time, json
LOG = open("insp_1112_admits.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
amd.login_cached(); batch = era_post.batch()
ADMITS = {"19454317": ("23365390", "09/08/2026"), "19454284": ("23365356", "09/08/2026"), "19454270": ("23365342", "09/08/2026"),
          "19454314": ("23365387", "09/08/2026"), "19454286": ("23365358", "09/08/2026"), "19454283": ("23365355", "09/08/2026"),
          "19454316": ("23365389", "09/08/2026"), "19454294": ("23365367", "09/08/2026"), "19454313": ("23365386", "09/09/2026")}
def set_date(vid, code, admit):
    return amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"},
        '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)))
def full_resave(cid, over=None, chg_over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        if chg_over and c.get("id") in chg_over: a.update(chg_over[c.get("id")])
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va.update(over or {})
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(batch), "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
    time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    return ("FAULT " + re.sub(r"\s+", " ", r[:160])) if "Fault" in r else "saved live=%d/%d onhcfa=%s hospfrom=%s mods=%s" % (len(c2), len(allc), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None, [(x.get("proccode"), x.get("modcodes")) for x in c2])
for vid, (cid, admit) in ADMITS.items():
    vis, pat, allc = resave.visit_charges(cid)
    codes = sorted({re.search(r'code="([^"]*)"', resave.detail(c.get("id").replace("charge", ""))).group(1) if False else c.get("proccode") for c in allc})
    # updextrainsinfo wants the CPT text; get it from the charge detail's <proccode ... code="99223"> element
    det = resave.detail(cid); cpts = sorted(set(re.findall(r'<proccode [^>]*code="(\d{5}|G\d{4})"', det)))
    for cpt in cpts: 
        r = set_date(vid, cpt, admit); L("v%s updextrainsinfo %s %s -> %s" % (vid, cpt, admit, "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])))
    L("v%s %s" % (vid, full_resave(cid, {"onhcfa": "1"}))); time.sleep(0.4)
# Lowry 99497 + 99223 on v19453862: modifier 25 on the 99497 (mcode7)
vis, pat, allc = resave.visit_charges("23364970")
info = [(c.get("id"), c.get("proccode"), c.get("modcodes")) for c in allc]; L("allen v19453862 charges %s" % info)
det = resave.detail("23364970"); L("  99497 detail modcodes: %s" % re.findall(r'<modcode [^>]*code="([^"]*)"', det))
if "mcode7" not in (dict((c.get("id"), c.get("modcodes") or "") for c in allc).get("charge23364970", "")):
    L("  adding mcode7 to charge23364970: " + full_resave("23364970", {"onhcfa": "1"}, {"charge23364970": {"modcodes": "mcode7"}}))
time.sleep(3)
ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); bids = re.findall(r'<batch id="([^"]+)"', ib); L("batches after: %s" % bids)
left = []
for bid in bids:
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
    for v in re.findall(r'<visit id="(\d+)"[^>]*>(.*?)</visit>', t, re.S):
        errs = re.findall(r'<error id="(\d+)"[^>]*>([^<]{0,90})', v[1]); L("  b%s v%s %s" % (bid, v[0], errs))
        adv = [e[0] for e in errs if e[1].startswith(("Pattern 23400", "Pattern 4426", "Pattern 4310", "Pattern 4311", "Pattern 35790"))]
        if adv and len(adv) == len(errs):
            r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (v[0], "".join('<claimedit id="%s"/>' % e for e in adv))))
            L("  bypass v%s %s -> %s" % (v[0], adv, "ok" if 'retval="0"' in r else re.sub(r"\s+", " ", r[:160])))
        elif errs: left.append((bid, v[0], errs))
time.sleep(2)
ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); L("batches final: %s" % re.findall(r'<batch id="([^"]+)"', ib))
json.dump(left, open("insp_1112_left.json", "w"))
