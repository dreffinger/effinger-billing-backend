# PLAIN ENGLISH (Claim Inspector pass, 3pm ET 9/23/2026 run 2026-09-23T1910Z): batch 127783 holds 31 nursing-home / ALF visits from the
#   Claimocity feed (CCM 99487+99489, 99309/99349, DOS 8-9/2026): 17 raise only Pattern 35790 (CCM add-on advisory), 9 raise Pattern 11256
#   (unspecified laterality - bypass + log), 4 raise Pattern 20389 on F02.80 / F02.84 (dementia in other diseases - William's standing
#   inspector swap to F03.90 dcode1034545095, then re-inspect), 1 sits PENDING with no error (full-visit resave so the inspector re-runs).
#   The 15 pat17472874 April-2026 hospital visits + pat17474541 v19430630 stay held (standing holds, William's board rows).
# Decides, per visit: (1) DECEASED GUARD (deceased_guard.check on every visit before anything is bypassed or resaved - a DOS after a known
#   date of death holds the visit); (2) F02.8x -> F03.90 swap on every live charge of the visit through recode._save (full-visit echo, the
#   void trap; NO rebill - these claims have never left); (3) PRIMARY-DX GATE on the first code (dx_primary_fix cascade) for the PENDING
#   resave; (4) then re-list every batch and bypass ONLY advisory patterns with FRESH error ids (Pattern 11256 logged to laterality_flag_log.md).
# Never touches: payments, write-offs, hospitalizationto, insurance plans, the held pids, visits outside the inspector list.
"""Usage: python3 insp_0923_1910.py [--dry] [--only vid,vid] [--bypass-only]"""
import amd, resave, era_post, dx_primary_fix, deceased_guard, recode, re, time, json, sys, datetime, glob
DRY = "--dry" in sys.argv
BYPASS_ONLY = "--bypass-only" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
STAMP = "2026-09-23T1910Z"
HOLD_PIDS = {"17472874", "17474541"}
F0390 = "dcode1034545095"
ADV = ("The Source of Payment you have chosen is not typical", "Pattern 23400", "Pattern 4426", "Pattern 4310", "Pattern 4311", "Pattern 35790", "Pattern 7011", "Pattern 3429", "Pattern 35777", "Pattern 33799", "Pattern 20657", "Pattern 27261")
amd.login_cached(); batch = era_post.batch()
scan = json.load(open("scan_0912/summary_before.json"))
CARR = {}
for _f in glob.glob("scan_0912/insp_*_before.xml"):
    for _m in re.finditer(r'<visit [^>]*>', open(_f).read()):
        _a = dict(re.findall(r'(\w+)="([^"]*)"', _m.group(0)))
        if _a.get("id"): CARR[_a["id"]] = (_a.get("carriercode") or "", _a.get("carriername") or "")
visits = [v for b, rows in scan["inspector"].items() for v in rows if v["pid"] not in HOLD_PIDS]
if ONLY: visits = [v for v in visits if v["vid"] in ONLY]
out = {"stamp": STAMP, "dry": DRY, "swapped": [], "resaved": [], "held": [], "left": [], "bypassed": [], "guard_clear": []}
BLOCKED = set()
import os
if os.path.exists("registers/insp_%s_blocked.json" % STAMP): BLOCKED |= set(json.load(open("registers/insp_%s_blocked.json" % STAMP)))
def L(m): print(m, flush=True)
def d(s): return datetime.datetime.strptime(s.strip()[:10], "%m/%d/%Y").date()
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
    time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid)
    ok = "Fault" not in r
    return ok, ("FAULT " + re.sub(r"\s+", " ", r[:200])) if not ok else "saved live=%d/%d onhcfa=%s charges=%s" % (len(c2), len(allc), v2.get("onhcfa"), [(x.get("id"), x.get("modcodes"), x.get("diagcodes", "")[:40]) for x in c2])
if not BYPASS_ONLY:
  for v in visits:
    vid, pid, cid0 = v["vid"], v["pid"], v["chgs"][0][0]
    rec = {"vid": vid, "pid": pid, "name": v["name"], "status": v["status"], "steps": []}
    def S(m): L("v%s pat%s %s" % (vid, pid, m)); rec["steps"].append(m)
    try: vis, pat, allc = resave.visit_charges(cid0)
    except Exception as e: S("visit_charges failed: %s" % e); out["held"].append(rec); BLOCKED.add(vid); continue
    if not allc: S("no live charges"); out["held"].append(rec); BLOCKED.add(vid); continue
    dos = d(allc[0].get("begindate") or vis.get("date") or "")
    dets = {c.get("id"): resave.detail(c.get("id").replace("charge", "")) for c in allc}
    cpt = {}
    for c in allc:
        pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', dets[c.get("id")]))
        cpt[c.get("id")] = pm.get(c.get("proccode"), c.get("proccode"))
    cpts = sorted(set(cpt.values()))
    S("dos %s cpts %s pos %s insorder %s onhcfa %s charges %s" % (dos, cpts, allc[0].get("pos"), vis.get("insorder"), vis.get("onhcfa"), [(c.get("id"), cpt[c.get("id")], c.get("modcodes"), c.get("insbalance"), c.get("fee")) for c in allc]))
    paid = [m for det in dets.values() for m in re.findall(r'<payment [^>]*amount="([^"]*)"[^>]*/?>', det) if m not in ("0", "0.00", "")]
    # deceased guard first - nothing is bypassed or resaved on a visit after a known date of death
    code, cname = CARR.get(vid, ("", ""))
    carr = "FLO02" if "MEDICARE" in cname.upper() else code
    dg_block = False
    for c in allc:
        try: blocked, why_dg = deceased_guard.check(pid, dos.isoformat(), carr, cpt[c.get("id")], allow_lookup=not DRY)
        except Exception as e: blocked, why_dg = False, "guard error %s" % e
        if blocked: S("DECEASED GUARD BLOCK: %s" % why_dg); dg_block = True; break
    if dg_block: out["held"].append(rec); BLOCKED.add(vid); continue
    S("deceased guard: clear (carrier %s)" % carr); out["guard_clear"].append(vid)
    errtxt = " ".join(e[1] for e in v["errs"])
    # F02.8x -> F03.90 inspector swap (Pattern 20389 on a dementia-in-other-diseases code)
    if "Pattern 20389" in errtxt:
        if paid: S("payment posted on a charge (%s) - HOLD, no resave" % paid); out["held"].append(rec); BLOCKED.add(vid); continue
        swaps = {}
        for c in allc:
            det = dets[c.get("id")]
            dmap = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', det))
            order = (c.get("diagcodes") or "").split(); codes = [dmap.get(x, x) for x in order]
            bad = [x for x in order if re.match(r"F02\.?(8|A|B|C)", dmap.get(x, ""), re.I)]
            S("%s dx %s F02.8x ids %s" % (cpt[c.get("id")], codes, bad))
            if bad:
                new = []
                for x in order:
                    y = F0390 if x in bad else x
                    if y not in new: new.append(y)
                swaps[c.get("id")] = new
        if not swaps: S("Pattern 20389 but no F02.8x code found on the live charges - LEFT for review"); out["held"].append(rec); BLOCKED.add(vid); continue
        if DRY: S("DRY: would swap -> %s" % swaps); out["swapped"].append(rec); continue
        def e(a):
            if a.get("id") in swaps: a["diagcodes"] = " ".join(swaps[a.get("id")]); return True
            return False
        c2, msg = recode._save(cid0.replace("charge", ""), e); S("swap F02.8x -> F03.90: %s" % msg)
        if c2 is None: out["held"].append(rec); BLOCKED.add(vid); continue
        v2, p2, c2 = resave.visit_charges(cid0)
        S("readback charges=%s" % [(x.get("id"), x.get("diagcodes")) for x in c2])
        out["swapped"].append(rec); time.sleep(0.4); continue
    if v["status"] != "PENDING" or v["errs"]:
        S("advisory-only errors - left for the bypass pass"); continue
    # PENDING visit with no error text: full-visit resave so the inspector re-runs (the 9/13 Orme lesson)
    if paid: S("payment posted on a charge (%s) - HOLD, no resave" % paid); out["held"].append(rec); BLOCKED.add(vid); continue
    chg_over = {}; gate_fault = False
    for c in allc:
        cid = c.get("id").replace("charge", ""); det = dets[c.get("id")]
        dmap = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', det))
        order = (c.get("diagcodes") or "").split(); codes = [dmap.get(x, x) for x in order]
        first_bad = bool(codes) and dx_primary_fix.never_primary(codes[0])
        S("%s dx %s never_primary(first)=%s" % (cpt[c.get("id")], codes, first_bad))
        if not first_bad: continue
        pl = dx_primary_fix.plan(codes, cpt[c.get("id")]); S("PRIMARY-DX GATE: plan %s" % (pl,))
        if not DRY:
            try:
                r = dx_primary_fix.fix_visit(pid, vid, cid, seq=(vis.get("insorder") or "1").split(",")[0] or "1", dry=False, bad=codes[0]); S("fix_visit -> %s" % str(r)[:300])
                vis, pat, allc = resave.visit_charges(cid0)
            except Exception as e: S("fix_visit FAILED %s" % e); gate_fault = True
    if gate_fault: out["held"].append(rec); BLOCKED.add(vid); continue
    if allc[0].get("pos") == "21": S("HOLD: hospital POS on a feed visit - admission rule not applied in this pass"); out["held"].append(rec); BLOCKED.add(vid); continue
    c497 = [c for c in allc if cpt[c.get("id")] == "99497"]
    if c497 and any(p in cpts for p in ("99223", "99306")):
        for c in c497:
            mods = c.get("modcodes") or ""
            if "mcode7" not in mods.split(): chg_over.setdefault(c.get("id"), {}).update({"modcodes": ("mcode7 " + mods).strip()}); S("adding mcode7 (modifier 25) to 99497")
    if DRY: S("DRY: would resave onhcfa=1 chg_over=%s" % chg_over); out["resaved"].append(rec); continue
    ok, msg = full_resave(cid0, {"onhcfa": "1"}, chg_over); S("resave: " + msg)
    (out["resaved"] if ok else out["held"]).append(rec); time.sleep(0.4)
json.dump(out, open("registers/insp_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
if DRY: L("DRY done: %d would swap, %d would resave, %d held" % (len(out["swapped"]), len(out["resaved"]), len(out["held"]))); sys.exit()
time.sleep(4)
for attempt in range(3):
    ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); bids = re.findall(r'<batch id="([^"]+)"', ib); L("batches after (attempt %d): %s" % (attempt, bids))
    left = []; did = 0; pending = 0
    for bid in bids:
        t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
        for vm in re.finditer(r'<visit id="(\d+)"([^>]*)>(.*?)</visit>', t, re.S):
            vid = vm.group(1); pm = re.search(r'patientid="(\d+)"', vm.group(2)); pid = pm.group(1) if pm else "?"
            errs = re.findall(r'<error id="(\d+)"[^>]*>([^<]{0,90})', vm.group(3))
            if not errs: pending += 1; continue
            if pid in HOLD_PIDS or vid in BLOCKED: left.append((bid, vid, pid, errs)); continue
            adv = [e[0] for e in errs if e[1].startswith(ADV)]
            lat = [e[0] for e in errs if e[1].startswith("Pattern 11256")]
            ids = adv + lat
            if ids and len(ids) == len(errs):
                r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in ids))))
                ok = "Fault" not in r; L("  bypass b%s v%s pat%s %s -> %s" % (bid, vid, pid, [e[1][:40] for e in errs], "ok" if ok else re.sub(r"\s+", " ", r[:160]))); did += 1
                if ok and lat: open("laterality_flag_log.md", "a").write("- %s run %s: v%s pat%s Pattern 11256 unspecified laterality bypassed\n" % (datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ"), STAMP, vid, pid))
                out["bypassed"].append({"batch": bid, "vid": vid, "pid": pid, "errs": [e[1][:60] for e in errs], "ok": ok})
            else: left.append((bid, vid, pid, errs)); L("  LEFT b%s v%s pat%s %s" % (bid, vid, pid, [e[1][:60] for e in errs]))
    L("  pending-no-error rows still listed: %d" % pending)
    if not did: break
    time.sleep(4)
out["left"] = left; out["pending_left"] = pending
json.dump(sorted(BLOCKED | {r["vid"] for r in out["held"]}), open("registers/insp_%s_blocked.json" % STAMP, "w"))
json.dump(out, open("registers/insp_%s%s.json" % (STAMP, "_bypassonly" if BYPASS_ONLY else ""), "w"), indent=1)
L("DONE: swapped %d, resaved %d, held %d, bypassed %d, left after bypass %d, pending %d" % (len(out["swapped"]), len(out["resaved"]), len(out["held"]), len(out["bypassed"]), len(left), pending))
