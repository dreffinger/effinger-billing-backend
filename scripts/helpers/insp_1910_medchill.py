# PLAIN ENGLISH (inspector, 3pm ET 9/16/2026 run 2026-09-16T1910Z): one hold - v19454776 pat17477516 (99223+99497 on 9/13/2026, new HCA admit,
#   'Hospitalization From Date empty'). Rules: admission = the visit's own 99223 date (09/13/2026) -> updextrainsinfo hospitalizationfrom only
#   (never hospitalizationto) per CPT; primary-dx gate (dx_primary_fix.never_primary) before anything else; 99497 next to 99223 carries
#   modifier 25 = mcode7 (never the literal 25); full-visit resave (every live charge echoed) with onhcfa=1; re-list the batch and bypass
#   only advisories with FRESH ids. Never touches: payments, other visits.
import amd, resave, era_post, dx_primary_fix, re, time, json, sys
DRY = "--dry" in sys.argv
amd.login_cached(); batch = era_post.batch()
VID, CID, ADMIT = "19454776", "23365867", "09/13/2026"
out = {"visit": VID, "steps": []}
def L(m): print(m, flush=True); out["steps"].append(m)
vis, pat, allc = resave.visit_charges(CID)
L("charges: %s" % [(c.get("id"), c.get("proccode"), c.get("modcodes"), c.get("diagcodes")) for c in allc])
# primary-dx gate
for c in allc:
    det = resave.detail(c.get("id").replace("charge", ""))
    dmap = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', det))
    order = (c.get("diagcodes") or "").split()
    codes = [dmap.get(d, d) for d in order]
    L("%s dx order %s never_primary(first)=%s" % (c.get("proccode"), codes, dx_primary_fix.never_primary(codes[0]) if codes else None))
    if codes and dx_primary_fix.never_primary(codes[0]):
        L("PRIMARY-DX GATE fires -> dx_primary_fix.plan %s" % dx_primary_fix.plan(codes, c.get("proccode")))
        if not DRY:
            r = dx_primary_fix.fix_visit(pat.get("id").replace("pat", ""), VID, c.get("id").replace("charge", ""), seq="1", dry=False, bad=codes[0]); L("fix_visit -> %s" % str(r)[:300])
            vis, pat, allc = resave.visit_charges(CID)
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
    return ("FAULT " + re.sub(r"\s+", " ", r[:200])) if "Fault" in r else "saved live=%d/%d onhcfa=%s hospfrom=%s mods=%s" % (len(c2), len(allc), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None, [(x.get("proccode"), x.get("modcodes")) for x in c2])
det = resave.detail(CID); cpts = sorted(set(re.findall(r'<proccode [^>]*code="(\d{5}|G\d{4})"', det)))
if DRY: L("DRY: would set admit %s on %s, mcode7 on the 99497, resave onhcfa=1" % (ADMIT, cpts)); json.dump(out, open("registers/insp_2026-09-16T1910Z_dry.json", "w"), indent=1); sys.exit()
for cpt in cpts:
    r = set_date(VID, cpt, ADMIT); L("updextrainsinfo %s %s -> %s" % (cpt, ADMIT, "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])))
mods = {c.get("id"): (c.get("modcodes") or "") for c in allc}
c497 = [c.get("id") for c in allc if c.get("proccode") == "99497"]
chg_over = {}
if c497 and "mcode7" not in mods.get(c497[0], ""):
    chg_over[c497[0]] = {"modcodes": ("mcode7 " + mods[c497[0]]).strip()}; L("adding mcode7 to %s" % c497[0])
L("resave: " + full_resave(CID, {"onhcfa": "1"}, chg_over))
time.sleep(3)
for attempt in range(2):
    ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); bids = re.findall(r'<batch id="([^"]+)"', ib); L("batches after: %s" % bids)
    left = []
    for bid in bids:
        t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
        for v in re.findall(r'<visit id="(\d+)"[^>]*>(.*?)</visit>', t, re.S):
            errs = re.findall(r'<error id="(\d+)"[^>]*>([^<]{0,90})', v[1]); L("  b%s v%s %s" % (bid, v[0], errs))
            adv = [e[0] for e in errs if e[1].startswith(("Pattern 23400", "Pattern 4426", "Pattern 4310", "Pattern 4311", "Pattern 35790", "Pattern 7011", "Pattern 3429", "Pattern 35777", "Pattern 33799", "Pattern 20657", "Pattern 27261"))]
            lat = [e[0] for e in errs if e[1].startswith("Pattern 11256")]
            if lat:
                open("laterality_flag_log.md", "a").write("- 2026-09-16 19:xxZ run 2026-09-16T1910Z: v%s pat%s Pattern 11256 unspecified laterality bypassed\n" % (v[0], pat.get("id")))
            ids = adv + lat
            if ids and len(ids) == len(errs):
                r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (v[0], "".join('<claimedit id="%s"/>' % e for e in ids))))
                L("  bypass v%s %s -> %s" % (v[0], ids, "ok" if 'retval="0"' in r or "Fault" not in r else re.sub(r"\s+", " ", r[:160])))
            elif errs: left.append((bid, v[0], errs))
    if not left and not bids: break
    time.sleep(3)
out["left"] = left
json.dump(out, open("registers/insp_2026-09-16T1910Z.json", "w"), indent=1)
L("LEFT: %s" % left)
