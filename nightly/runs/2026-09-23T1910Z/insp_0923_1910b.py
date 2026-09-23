# PLAIN ENGLISH (Claim Inspector pass, 3pm ET 9/22/2026 run 2026-09-22T1910Z): one new batch (127765) of 19 HCA hospital visits on 17
#   charts, every one held 'Hospitalization From Date in the Extra Info tab is empty'; three pat20729 visits also raise Pattern 11256
#   (S72.90XD unspecified laterality - bypass + log); one UMR visit raises the Source-of-Payment advisory. Adapted from insp_0921_1910.py.
#   DECEASED GUARD (William [DOB]): before any visit is resaved (which releases it to the claim run) deceased_guard.check(pid, dos,
#   carrier, cpt) runs - a DOS after a known date of death HOLDS the visit (listed for William to void); a failed lookup is reported as
#   'unverified' and does not block.
# Decides, per visit: (1) PRIMARY-DX GATE - read every live charge's diagnosis list; Winslow Jr (pat17472546) with S81.801S leading gets
#   M86.9 (dcode1034545415) put IN FRONT (William 9/6/2026 rule, S81.801S kept second); any other never-primary first code goes through
#   dx_primary_fix.plan/fix_visit (delete / move / add I10). (2) ADMISSION DATE = the most recent 99223 on/before the visit DOS within
#   45 days from gettxhistory; a visit that IS the 99223 uses its own DOS; no anchor -> HOLD and report, never guess.
#   updextrainsinfo hospitalizationfrom only (never hospitalizationto) per CPT on the visit. (3) 99497 next to a 99223/99306 carries
#   modifier 25 = mcode7 (never the literal 25). (4) full-visit resave (every live charge echoed - the void trap) with onhcfa=1 so the
#   inspector re-runs. (5) after all visits: re-list every batch and bypass ONLY advisory patterns with FRESH error ids
#   (Pattern 20389 only on a Winslow Jr visit that now leads with M86.9); Pattern 11256 bypassed + logged to laterality_flag_log.md.
# Never touches: payments, write-offs, visits outside the inspector list, hospitalizationto, insurance plans.
"""Usage: python3 insp_0918_1910.py [--dry] [--only vid,vid]"""
import amd, resave, era_post, dx_primary_fix, deceased_guard, re, time, json, sys, datetime, collections
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
STAMP = "2026-09-23T1910Z"
HOLD_PIDS = {"17472874", "17474541"}
import os
BLOCKED = set(json.load(open("registers/insp_%s_blocked.json" % STAMP))) if os.path.exists("registers/insp_%s_blocked.json" % STAMP) else set()
BLOCKED |= {"19455940"}  # duplicated CCM charge lines on one visit - held, not bypassed
WINSLOW = "17472546"; M869 = "dcode1034545415"
ADV = ("The Source of Payment you have chosen is not typical", "Pattern 23400", "Pattern 4426", "Pattern 4310", "Pattern 4311", "Pattern 35790", "Pattern 7011", "Pattern 3429", "Pattern 35777", "Pattern 33799", "Pattern 20657", "Pattern 27261")
amd.login_cached(); batch = era_post.batch()
scan = json.load(open("scan_0912/summary_before.json"))
import glob
CARR = {}
for _f in glob.glob("scan_0912/insp_*_before.xml"):
    for _m in re.finditer(r'<visit [^>]*>', open(_f).read()):
        _a = dict(re.findall(r'(\w+)="([^"]*)"', _m.group(0)))
        if _a.get("id"): CARR[_a["id"]] = _a.get("carriername") or ""
visits = [v for b in scan["inspector"].values() for v in b if v["pid"] not in HOLD_PIDS and v["vid"] not in BLOCKED]
if ONLY: visits = [v for v in visits if v["vid"] in ONLY]
out = {"stamp": STAMP, "dry": DRY, "visits": [], "held": [], "left": []}
def L(m): print(m, flush=True)
def d(s): return datetime.datetime.strptime(s.strip()[:10], "%m/%d/%Y").date()
hist = {}
def history(pid):
    if pid not in hist:
        t = amd.post(amd.msg("gettxhistory", "demographics", {"patientid": pid, "filterhistory": "0", "pagenumber": "1", "typefilter": "1", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "getmemo": "false", "nocookie": "1"}), timeout=120)
        rows = []
        for m in re.finditer(r'<charge [^>]*/?>', t):
            a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
            if a.get("void") == "1" or (a.get("fee") or "").startswith("-") or not a.get("dos"): continue
            rows.append((d(a["dos"]), a.get("proccode"), a.get("visit"), a.get("id")))
        hist[pid] = rows; time.sleep(0.3)
    return hist[pid]
def admit_for(pid, dos, own_cpts):
    if "99223" in own_cpts: return dos, "own 99223"
    adm = [x for x, p, v, c in history(pid) if p == "99223" and x <= dos and (dos - x).days <= 45]
    if adm: return max(adm), "most recent 99223 within 45d"
    # fallback: the same stay's earlier hospital visit already carries the admission date (written by an earlier run)
    HOSP = ("99221", "99222", "99223", "99231", "99232", "99233", "99238", "99239", "99291")
    prev = sorted([(x, v, c) for x, p, v, c in history(pid) if p in HOSP and x < dos and (dos - x).days <= 45], reverse=True)
    for x, v, c in prev[:3]:
        try: vv, pp, cc = resave.visit_charges(c.replace("charge", ""))
        except Exception: continue
        ex = vv.find("extins"); hf = ex.get("hospitalizationfrom") if ex is not None else None
        if hf and (dos - d(hf)).days <= 60: return d(hf), "same stay: admission %s already on visit %s (%s)" % (hf, v, x)
    return None, "no 99223 anchor within 45 days and no earlier visit of the stay carries an admission date"
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
    ok = "Fault" not in r
    return ok, ("FAULT " + re.sub(r"\s+", " ", r[:200])) if not ok else "saved live=%d/%d onhcfa=%s hospfrom=%s charges=%s" % (len(c2), len(allc), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None, [(x.get("id"), x.get("modcodes"), x.get("diagcodes")) for x in c2])
winslow_fixed = set()
for v in visits:
    vid, pid, cid0 = v["vid"], v["pid"], v["chgs"][0][0]
    rec = {"vid": vid, "pid": pid, "name": v["name"], "steps": []}
    def S(m): L("v%s pat%s %s" % (vid, pid, m)); rec["steps"].append(m)
    try:
        vis, pat, allc = resave.visit_charges(cid0)
    except Exception as e:
        S("visit_charges failed: %s" % e); out["held"].append(rec); continue
    if not allc: S("no live charges"); out["held"].append(rec); continue
    dos = d(allc[0].get("begindate") or vis.get("date") or "")
    dets = {c.get("id"): resave.detail(c.get("id").replace("charge", "")) for c in allc}
    cpt = {}
    for c in allc:
        pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', dets[c.get("id")]))
        cpt[c.get("id")] = pm.get(c.get("proccode"), c.get("proccode"))
    cpts = sorted(set(cpt.values()))
    S("dos %s cpts %s charges %s" % (dos, cpts, [(c.get("id"), cpt[c.get("id")], c.get("modcodes"), c.get("diagcodes"), c.get("insbalance"), c.get("fee")) for c in allc]))
    if v["status"] != "PENDING" and not any("Hospitalization From Date" in e[1] for e in v["errs"]): S("advisory-only errors - left for the bypass pass"); continue
    paid = [m for det in dets.values() for m in re.findall(r'<payment [^>]*amount="([^"]*)"[^>]*/?>', det) if m not in ("0", "0.00", "")]
    if paid:
        S("payment posted on a charge (%s) - HOLD, no resave" % paid); out["held"].append(rec); continue
    # (1) primary-dx gate
    chg_over = {}; gate_fault = False
    for c in allc:
        cid = c.get("id").replace("charge", "")
        det = dets[c.get("id")]
        dmap = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', det))
        order = (c.get("diagcodes") or "").split()
        codes = [dmap.get(x, x) for x in order]
        first_bad = bool(codes) and dx_primary_fix.never_primary(codes[0])
        S("%s dx %s never_primary(first)=%s" % (cpt[c.get("id")], codes, first_bad))
        if not first_bad: continue
        if pid == WINSLOW and codes[0].replace(".", "").upper().startswith("S81801S"):
            if M869 in order: S("M86.9 already present but not first -> reorder M86.9 first"); neworder = [M869] + [x for x in order if x != M869]
            else: neworder = [M869] + order
            chg_over[c.get("id")] = {"diagcodes": " ".join(neworder)}; winslow_fixed.add(vid)
            S("Winslow Jr rule (William 9/6): M86.9 %s in front of S81.801S -> diagcodes %s" % (M869, neworder))
        else:
            pl = dx_primary_fix.plan(codes, cpt[c.get("id")]); S("PRIMARY-DX GATE: plan %s" % (pl,))
            if not DRY:
                try:
                    r = dx_primary_fix.fix_visit(pid, vid, cid, seq=vis.get("insorder", "1").split(",")[0] or "1", dry=False, bad=codes[0]); S("fix_visit -> %s" % str(r)[:300])
                    vis, pat, allc = resave.visit_charges(cid0)
                except Exception as e:
                    S("fix_visit FAILED %s" % e); gate_fault = True
    if gate_fault: out["held"].append(rec); continue
    # (1b) deceased guard (William [DOB])
    carr = "FLO02" if "MEDICARE" in CARR.get(vid, "").upper() else CARR.get(vid, "")
    dg_block = False
    for c in allc:
        try: blocked, why_dg = deceased_guard.check(pid, dos.isoformat(), carr, cpt[c.get("id")], allow_lookup=not DRY)
        except Exception as e: blocked, why_dg = False, "guard error %s" % e
        if blocked: S("DECEASED GUARD BLOCK: %s" % why_dg); dg_block = True; break
    if dg_block: out["held"].append(rec); BLOCKED.add(vid); continue
    S("deceased guard: clear (carrier %s)%s" % (carr, (" | " + "; ".join(deceased_guard.LOG[-1:])) if deceased_guard.LOG and pid in deceased_guard.LOG[-1] else ""))
    # (2) admission date
    admit, why = admit_for(pid, dos, cpts)
    if not admit: S("HOLD: %s" % why); out["held"].append(rec); continue
    adm = admit.strftime("%m/%d/%Y"); S("admission %s (%s)" % (adm, why))
    # (3) modifier 25 on 99497 next to 99223/99306
    c497 = [c for c in allc if cpt[c.get("id")] == "99497"]
    if c497 and any(p in cpts for p in ("99223", "99306")):
        for c in c497:
            mods = c.get("modcodes") or ""
            if "mcode7" not in mods.split():
                chg_over.setdefault(c.get("id"), {}).update({"modcodes": ("mcode7 " + mods).strip()}); S("adding mcode7 (modifier 25) to %s 99497" % c.get("id"))
    if DRY:
        S("DRY: would set hospitalizationfrom %s on %s, resave onhcfa=1 chg_over=%s" % (adm, cpts, chg_over)); out["visits"].append(rec); continue
    for cpt in cpts:
        r = set_date(vid, cpt, adm); S("updextrainsinfo %s %s -> %s" % (cpt, adm, "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])))
    ok, msg = full_resave(cid0, {"onhcfa": "1"}, chg_over); S("resave: " + msg)
    if not ok: out["held"].append(rec)
    else: out["visits"].append(rec)
    time.sleep(0.4)
json.dump(out, open("registers/insp_%sb%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
if DRY: L("DRY done: %d would fix, %d held" % (len(out["visits"]), len(out["held"]))); sys.exit()
# (5) re-list and bypass advisories with fresh ids
time.sleep(4)
for attempt in range(3):
    ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); bids = re.findall(r'<batch id="([^"]+)"', ib); L("batches after (attempt %d): %s" % (attempt, bids))
    left = []; did = 0
    for bid in bids:
        t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
        for vm in re.finditer(r'<visit id="(\d+)"([^>]*)>(.*?)</visit>', t, re.S):
            vid = vm.group(1); pid = (re.search(r'patientid="(\d+)"', vm.group(2)) or re.search(r'patient="pat(\d+)"', vm.group(2)))
            pid = pid.group(1) if pid else "?"
            errs = re.findall(r'<error id="(\d+)"[^>]*>([^<]{0,90})', vm.group(3))
            if not errs: continue
            if pid in HOLD_PIDS or vid in BLOCKED: left.append((bid, vid, pid, errs)); continue
            adv = [e[0] for e in errs if e[1].startswith(ADV)]
            if vid in winslow_fixed: adv += [e[0] for e in errs if e[1].startswith("Pattern 20389")]
            lat = [e[0] for e in errs if e[1].startswith("Pattern 11256")]
            if lat: open("laterality_flag_log.md", "a").write("- %s run %s: v%s pat%s Pattern 11256 unspecified laterality bypassed\n" % (datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ"), STAMP, vid, pid))
            ids = adv + lat
            if ids and len(ids) == len(errs):
                r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in ids))))
                L("  bypass b%s v%s pat%s %s -> %s" % (bid, vid, pid, [e[1][:40] for e in errs], "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160]))); did += 1
            else: left.append((bid, vid, pid, errs)); L("  LEFT b%s v%s pat%s %s" % (bid, vid, pid, errs))
    if not did: break
    time.sleep(4)
out["left"] = left
json.dump(sorted(BLOCKED), open("registers/insp_%s_blocked.json" % STAMP, "w")); json.dump(out, open("registers/insp_%sb.json" % STAMP, "w"), indent=1)
L("DONE: fixed %d, held %d, left after bypass %d" % (len(out["visits"]), len(out["held"]), len(left)))
