# PLAIN ENGLISH (Claim Inspector pass, 3pm ET 10/8/2026 run 2026-10-08T1910Z): stamp copy of insp_1003_2310.py for HCA batch 127900 (52 admission-date holds, 7 laterality advisories, 1 sequela primary) - same rules; the original note: the admission
#   anchor history is read with gettxhistory typefilter=0 (ALL charges) instead of typefilter=1, because the 5 PM pass missed pat17472703's
#   9/5/2026 99223 (the anchor already written on his 9/6-9/24 visits) and held his 9/29-10/2 99233s as "no anchor". Same standing holds,
#   same deceased guard, same primary-dx gate, same hospitalizationfrom-only write + full-visit resave onhcfa=1 + fresh-id advisory bypass.
# Decides per visit: deceased guard -> primary-dx gate -> admission date = own 99223 DOS or the most recent 99223 within 45 days
#   (gettxhistory) -> updextrainsinfo hospitalizationfrom ONLY -> full-visit resave (every live charge echoed) with onhcfa=1 ->
#   re-list every batch and bypass ONLY advisory patterns with FRESH error ids. No anchor -> HOLD (never guessed).
# Never touches: payments, write-offs, hospitalizationto, insurance plans, the standing holds.
"""Usage: python3 insp_1003_2310.py [--dry] [--only vid,vid] [--bypass-only]"""
import amd, resave, era_post, dx_primary_fix, deceased_guard, re, time, json, sys, datetime, collections, glob
DRY = "--dry" in sys.argv
BYPASS_ONLY = "--bypass-only" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
STAMP = "2026-10-08T1910Z"
HOLD_PIDS = {"17472874"}
HOLD_VIDS = {"19430630","19455625","19455691","19455936","19455940","19456171"}
WORK = ("Hospitalization From Date", "Pattern 20389")
WINSLOW = "17472546"; M869 = "dcode1034545415"
ADV = ("The Source of Payment you have chosen is not typical", "Pattern 23400", "Pattern 4426", "Pattern 4310", "Pattern 4311", "Pattern 35790", "Pattern 7011", "Pattern 3429", "Pattern 35777", "Pattern 33799", "Pattern 20657", "Pattern 27261")
amd.login_cached(); batch = era_post.batch()
scan = json.load(open("scan_2026-10-08/summary_before.json"))
CARR = {}
for _f in glob.glob("scan_2026-10-08/insp_*_before.xml"):
    for _m in re.finditer(r'<visit [^>]*>', open(_f).read()):
        _a = dict(re.findall(r'(\w+)="([^"]*)"', _m.group(0)))
        if _a.get("id"): CARR[_a["id"]] = (_a.get("carriercode") or "", _a.get("carriername") or "")
visits = [v for b, rows in scan["inspector"].items() for v in rows if v["pid"] not in HOLD_PIDS and v["vid"] not in HOLD_VIDS and (any(e[1].startswith(WORK) for e in v["errs"]) or (v["status"] == "PENDING" and not v["errs"]))]
if ONLY: visits = [v for v in visits if v["vid"] in ONLY]
out = {"stamp": STAMP, "dry": DRY, "visits": [], "held": [], "left": [], "bypassed": []}
def L(m): print(m, flush=True)
def d(s): return datetime.datetime.strptime(s.strip()[:10], "%m/%d/%Y").date()
hist = {}
def history(pid):
    if pid not in hist:
        t = amd.post(amd.msg("gettxhistory", "demographics", {"patientid": pid, "filterhistory": "0", "pagenumber": "1", "typefilter": "0", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "getmemo": "false", "nocookie": "1"}), timeout=120)
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
    return None, "no 99223 anchor within 45 days"
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
    return ok, ("FAULT " + re.sub(r"\s+", " ", r[:200])) if not ok else "saved live=%d/%d onhcfa=%s hospfrom=%s charges=%s" % (len(c2), len(allc), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None, [(x.get("id"), x.get("modcodes"), x.get("diagcodes", "")[:30]) for x in c2])
HOSP = ("99221", "99222", "99223", "99231", "99232", "99233", "99238", "99239", "99291")
if not BYPASS_ONLY:
  for v in visits:
    vid, pid, cid0 = v["vid"], v["pid"], v["chgs"][0][0]
    rec = {"vid": vid, "pid": pid, "name": v["name"], "steps": []}
    def S(m): L("v%s pat%s %s" % (vid, pid, m)); rec["steps"].append(m)
    if pid in HOLD_PIDS or vid in HOLD_VIDS: S("standing hold"); out["held"].append(rec); continue
    try: vis, pat, allc = resave.visit_charges(cid0)
    except Exception as e: S("visit_charges failed: %s" % e); out["held"].append(rec); continue
    if not allc: S("no live charges"); out["held"].append(rec); continue
    dos = d(allc[0].get("begindate") or vis.get("date") or "")
    dets = {c.get("id"): resave.detail(c.get("id").replace("charge", "")) for c in allc}
    cpt = {}
    for c in allc:
        pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', dets[c.get("id")]))
        cpt[c.get("id")] = pm.get(c.get("proccode"), c.get("proccode"))
    cpts = sorted(set(cpt.values()))
    S("dos %s cpts %s pos %s insorder %s onhcfa %s charges %s" % (dos, cpts, allc[0].get("pos"), vis.get("insorder"), vis.get("onhcfa"), [(c.get("id"), cpt[c.get("id")], c.get("modcodes"), c.get("insbalance"), c.get("fee")) for c in allc]))
    paid = [m for det in dets.values() for m in re.findall(r'<payment [^>]*amount="([^"]*)"[^>]*/?>', det) if m not in ("0", "0.00", "")]
    if paid: S("payment posted on a charge (%s) - HOLD, no resave" % paid); out["held"].append(rec); continue
    chg_over = {}; gate_fault = False
    for c in allc:
        cid = c.get("id").replace("charge", ""); det = dets[c.get("id")]
        dmap = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', det))
        order = (c.get("diagcodes") or "").split(); codes = [dmap.get(x, x) for x in order]
        first_bad = bool(codes) and dx_primary_fix.never_primary(codes[0])
        S("%s dx %s never_primary(first)=%s" % (cpt[c.get("id")], codes, first_bad))
        if not first_bad: continue
        if pid == WINSLOW and codes[0].replace(".", "").upper().startswith("S81801S"):
            neworder = [M869] + [x for x in order if x != M869]; chg_over[c.get("id")] = {"diagcodes": " ".join(neworder)}; S("Winslow Jr rule: M86.9 in front")
        else:
            pl = dx_primary_fix.plan(codes, cpt[c.get("id")]); S("PRIMARY-DX GATE: plan %s" % (pl,))
            if not DRY:
                try:
                    r = dx_primary_fix.fix_visit(pid, vid, cid, seq=(vis.get("insorder") or "1").split(",")[0] or "1", dry=False, bad=codes[0]); S("fix_visit -> %s" % str(r)[:300])
                    vis, pat, allc = resave.visit_charges(cid0)
                except Exception as e: S("fix_visit FAILED %s" % e); gate_fault = True
    if gate_fault: out["held"].append(rec); continue
    code, cname = CARR.get(vid, ("", ""))
    carr = "FLO02" if "MEDICARE" in cname.upper() else code
    dg_block = False
    for c in allc:
        try: blocked, why_dg = deceased_guard.check(pid, dos.isoformat(), carr, cpt[c.get("id")], allow_lookup=not DRY)
        except Exception as e: blocked, why_dg = False, "guard error %s" % e
        if blocked: S("DECEASED GUARD BLOCK: %s" % why_dg); dg_block = True; break
    if dg_block: out["held"].append(rec); continue
    S("deceased guard: clear (carrier %s)" % carr)
    over = {"onhcfa": "1"}
    if allc[0].get("pos") == "21" or any(p in cpts for p in HOSP):
        admit, why = admit_for(pid, dos, cpts)
        if not admit: S("HOLD: %s" % why); out["held"].append(rec); continue
        adm = admit.strftime("%m/%d/%Y"); S("admission %s (%s)" % (adm, why)); rec["admission"] = adm
    else: adm = None
    c497 = [c for c in allc if cpt[c.get("id")] == "99497"]
    if c497 and any(p in cpts for p in ("99223", "99306")):
        for c in c497:
            mods = c.get("modcodes") or ""
            if "mcode7" not in mods.split(): chg_over.setdefault(c.get("id"), {}).update({"modcodes": ("mcode7 " + mods).strip()}); S("adding mcode7 (modifier 25) to 99497")
    if DRY: S("DRY: would resave onhcfa=1 admission=%s chg_over=%s" % (adm, chg_over)); out["visits"].append(rec); continue
    if adm:
        for p in cpts: r = set_date(vid, p, adm); S("updextrainsinfo %s %s -> %s" % (p, adm, "ok" if "Fault" not in r else re.sub(r"\s+", " ", r[:160])))
    ok, msg = full_resave(cid0, over, chg_over); S("resave: " + msg)
    (out["visits"] if ok else out["held"]).append(rec); time.sleep(0.4)
json.dump(out, open("registers/insp_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
if DRY: L("DRY done: %d would resave, %d held" % (len(out["visits"]), len(out["held"]))); sys.exit()
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
            if pid in HOLD_PIDS or vid in HOLD_VIDS: left.append((bid, vid, pid, errs)); continue
            adv = [e[0] for e in errs if e[1].startswith(ADV)]
            lat = [e[0] for e in errs if e[1].startswith("Pattern 11256")]
            if lat: open("laterality_flag_log.md", "a").write("- %s run %s: v%s pat%s Pattern 11256 unspecified laterality bypassed\n" % (datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ"), STAMP, vid, pid))
            ids = adv + lat
            if ids and len(ids) == len(errs):
                r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in ids))))
                ok = "Fault" not in r; L("  bypass b%s v%s pat%s %s -> %s" % (bid, vid, pid, [e[1][:40] for e in errs], "ok" if ok else re.sub(r"\s+", " ", r[:160]))); did += 1
                out["bypassed"].append({"batch": bid, "vid": vid, "pid": pid, "errs": [e[1][:60] for e in errs], "ok": ok})
            else: left.append((bid, vid, pid, errs)); L("  LEFT b%s v%s pat%s %s" % (bid, vid, pid, [e[1][:60] for e in errs]))
    L("  pending-no-error rows still listed: %d" % pending)
    if not did: break
    time.sleep(4)
out["left"] = left; out["pending_left"] = pending
json.dump(out, open("registers/insp_%s.json" % STAMP, "w"), indent=1)
L("DONE: resaved %d, held %d, bypassed %d, left after bypass %d, pending %d" % (len(out["visits"]), len(out["held"]), len(out["bypassed"]), len(left), pending))
