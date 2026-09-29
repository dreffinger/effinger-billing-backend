# PLAIN ENGLISH (Unbilled 'Insurance order is missing' - eight new HCA charts + pat21489 exclusions, 7pm ET 9/28/2026 run 2026-09-28T2310Z)
# Decides, per William's lookup order (patient_db -> AMD 271 -> Stedi -> facesheet -> William) run this slot (inv_2310.json + cascade2_2310.json;
#   the plan/member config lives in secrets/newcharts_0928_2310_cfg.json - member ids never leave the workspace):
#   straight Medicare (MBI, no MA entity) -> FLO02; Medicare's 271 names an MA plan -> that plan alone (Humana PPO x2 via Stedi 61101 with
#   the MBI, AARP MA from UHC via discovery + 87726); CMS 'OT' UHC entity with no MA type = AARP Medigap -> FLO02 first + AAR01 second.
#   Per chart: add_ins.add (NO group number) -> AMD free 271 on the new plan -> address line 1 moved up from line 2 (Claimocity feed
#   leaves it blank) -> admission date = the stay's own 99223 DOS via updextrainsinfo hospitalizationfrom ONLY -> PRIMARY-DX GATE
#   (dx_primary_fix.plan on the first code; the cascade helper resaves + freq-1 rebills) -> full-visit resave insorder + onhcfa=1 (every
#   live charge echoed) -> patient default order (ins_update sequence=) -> release from Unbilled (hideunbillablevisits).
#   pat21489: SUN01 INACTIVE on AMD's 271, Medicaid 271 names SMMC MMA Capitated FLORIDA COMMUNITY CARE (FCC seq 4 on the chart) ->
#   SUN01 end-dated 04/13/2026, the two 99309 visits set to insorder 4, freq-1 rebilled to FCC, exclusions on run 1700243 completed.
#   HOLDS: pat17477892 (MBI 72 + discovery 0 -> William, facesheet), pat17477898 + pat17477850 (CHP MA - CHP wants its own member id -> William).
# Never touches: group numbers, hospitalizationto, payments, write-offs, any other chart.
"""Usage: python3 apply_0928_2310.py [--dry] [--only pid,pid]"""
import amd, resave, add_ins, elig_amd, addr_line1_fix, dx_primary_fix, ins_update, freq1_visit, json, re, sys, time, datetime
S = "2026-09-28T2310Z"; DRY = "--dry" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
amd.login_cached()
inv = json.load(open("inv_2310.json")); CFG = json.load(open("secrets/newcharts_0928_2310_cfg.json"))
REG = {"stamp": S, "dry": DRY, "charts": {}, "released": [], "held": []}
def L(m): print(m, flush=True)
def set_admit(vid, code, admit):
    r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"}, '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)))
    return "ok" if "Fault" not in r else "FAULT " + re.sub(r"\s+", " ", r[:160])
def resave_full(cid, insorder, chg_over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        if chg_over and c.get("id") in chg_over: a.update(chg_over[c.get("id")])
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = insorder; va["onhcfa"] = "1"
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    if "Fault" in r: return False, "FAULT " + re.sub(r"\s+", " ", r[:200])
    time.sleep(0.6); v2, p2, c2 = resave.visit_charges(cid); ex = v2.find("extins")
    return True, "saved live=%d/%d insorder=%s onhcfa=%s hospfrom=%s charges=%s" % (len(c2), len(allc), v2.get("insorder"), v2.get("onhcfa"), ex.get("hospitalizationfrom") if ex is not None else None, [(x.get("id"), x.get("modcodes")) for x in c2])
def release(vids):
    vids = [re.sub(r"\D", "", v) for v in vids]
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in vids)))
    return ('success="1"' in r and "<Fault" not in r), re.sub(r"\s+", " ", r)[:160]
def d(s): return datetime.datetime.strptime(s.strip()[:10], "%m/%d/%Y").date()
for pid, c in CFG.items():
    if ONLY and pid not in ONLY: continue
    rec = {"code": c["code"], "why": c["why"], "steps": []}; REG["charts"][pid] = rec
    def S_(m): L("pat%s %s" % (pid, m)); rec["steps"].append(m)
    S_("plan %s %s begin %s - %s" % (c["code"], c["car"], c["begin"], c["why"]))
    vs = inv[pid]["visits"]; adm = min(d(v["chgs"][0][1]) for v in vs).strftime("%m/%d/%Y")
    own223 = [v for v in vs if v.get("cpt") == "99223"]
    if own223: adm = own223[0]["chgs"][0][1]
    S_("visits %s admission %s (own 99223=%s)" % ([(v["vid"], v.get("cpt"), v["chgs"][0][1], v.get("dx")) for v in vs], adm, bool(own223)))
    if DRY: S_("DRY: would add plan, 271, addr fix, admit, resave insorder, dx gate, patient order, release"); continue
    insid, seq = add_ins.add(pid, c["car"], c["num"], c["begin"], "1", c["fin"]); S_("add_ins -> %s seq %s" % (insid, seq))
    if not insid: REG["held"].append({"pid": pid, "why": "addinsurance failed: %s" % seq}); continue
    try: s = elig_amd.run_plan(pid, insid.replace("ins", ""), force=True); S_("AMD 271 -> %s" % elig_amd.one_line(s)[:300]); rec["elig"] = elig_amd.one_line(s)[:300]
    except Exception as e: S_("AMD 271 ERR %s" % str(e)[:120])
    order = seq
    if c.get("secondary"):
        sc = c["secondary"]; ins2, seq2 = add_ins.add(pid, sc["car"], sc["num"], sc["begin"], "1", sc["fin"]); S_("add_ins secondary %s -> %s seq %s" % (sc["code"], ins2, seq2))
        if ins2:
            try: s2 = elig_amd.run_plan(pid, ins2.replace("ins", ""), force=True); S_("AMD 271 secondary -> %s" % elig_amd.one_line(s2)[:300]); rec["elig2"] = elig_amd.one_line(s2)[:300]
            except Exception as e: S_("AMD 271 secondary ERR %s" % str(e)[:120])
            order = "%s,%s" % (seq, seq2)
    ad = inv[pid].get("address") or {}
    if isinstance(ad, dict) and not (ad.get("address1") or "").strip() and (ad.get("address2") or "").strip():
        try: msg, det = addr_line1_fix.fix(pid, ad["address2"], ad.get("city") or "TALLAHASSEE", ad.get("state") or "FL", ad.get("zipcode") or "32308-4486"); S_("addr line1 fix -> %s %s" % (msg, det))
        except Exception as e: S_("addr fix ERR %s" % str(e)[:160])
    elif isinstance(ad, dict) and (ad.get("address1") or "").strip().upper().startswith(("APT", "UNIT", "SUITE", "STE")) and (ad.get("address2") or "").strip():
        S_("address line 1 holds the apartment (%s), street in line 2 - left as is (deliverable)" % ad.get("address1"))
    for v in vs:
        vid = v["vid"]; cid = v["cid"]; vis, pat, allc = resave.visit_charges(cid)
        codes = []
        for ch in allc:
            det = resave.detail(ch.get("id").replace("charge", "")); pm = re.search(r'<proccode id="%s"[^>]*?\bcode="([^"]*)"' % ch.get("proccode"), det); codes.append(pm.group(1) if pm else ch.get("proccode"))
        for code in codes: S_("v%s updextrainsinfo %s hospitalizationfrom %s -> %s" % (vid, code, adm, set_admit(vid, code, adm)))
        chg_over = {}
        for ch in allc:
            if "99497" in codes and (ch.get("proccode") and re.search(r'99497', str(codes))):
                pass
        ok, msg = resave_full(cid, order, chg_over); S_("v%s resave insorder %s -> %s %s" % (vid, order, ok, msg))
        if not ok: REG["held"].append({"pid": pid, "vid": vid, "why": msg}); continue
        dx = v.get("dx") or []
        if dx and dx_primary_fix.never_primary(dx[0]):
            pl = dx_primary_fix.plan(dx, v.get("cpt")); S_("v%s PRIMARY-DX GATE %s -> plan %s" % (vid, dx, pl))
            try: r = dx_primary_fix.fix_visit(pid, vid, cid, seq=str(seq), dry=False, bad=dx[0]); S_("v%s fix_visit -> %s" % (vid, str(r)[:300]))
            except Exception as e: S_("v%s fix_visit FAILED %s" % (vid, str(e)[:160])); REG["held"].append({"pid": pid, "vid": vid, "why": "dx gate failed"}); continue
        REG["released"].append(vid); time.sleep(0.4)
    try: ok2, r2 = ins_update.update(pid, insid, sequence=order); S_("patient default order %s -> %s %s" % (order, ok2, str(r2)[:120]))
    except Exception as e: S_("patient order ERR %s" % str(e)[:120])
    vids = [v["vid"] for v in vs if v["vid"] in REG["released"]]
    if vids: ok3, r3 = release(vids); S_("release %s -> %s %s" % (vids, ok3, r3))
    time.sleep(0.5)
# ---- pat21489 PELLAM: SUN01 inactive, Medicaid 271 names FCC (seq 4)
if not ONLY or "21489" in ONLY:
    pid = "21489"; rec = {"steps": []}; REG["charts"][pid] = rec
    def S_(m): L("pat%s %s" % (pid, m)); rec["steps"].append(m)
    vs = inv[pid]["visits"]
    if DRY: S_("DRY: would end-date SUN01 ins7696 04/13/2026, resave v19455358/v19455359 insorder 4, freq-1 rebill seq 4, hideexclusions 1700243")
    else:
        ok, r = ins_update.update(pid, "7696", enddate="04/13/2026"); S_("SUN01 ins7696 enddate 04/13/2026 -> %s %s" % (ok, str(r)[:120]))
        done = []
        for v in vs:
            vid, cid = v["vid"], v["cid"]
            ok, msg = resave_full(cid, "4"); S_("v%s resave insorder 4 -> %s %s" % (vid, ok, msg))
            if not ok: continue
            r = freq1_visit.run(vid, cid, "4"); S_("v%s freq1 seq 4 -> %s" % (vid, str(r)[:160])); done.append(vid); time.sleep(0.4)
        if done:
            lst = "".join('<visit id="%s" claimid="%sB"/>' % (v, v) for v in done)
            x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": "1700243", "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % lst), timeout=120); S_("hideexclusions 1700243 %s -> %s" % (done, re.sub(r"\s+", " ", x)[:120]))
json.dump(REG, open("registers/unbilled_apply_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
L("DONE released %d held %d" % (len(REG["released"]), len(REG["held"])))
