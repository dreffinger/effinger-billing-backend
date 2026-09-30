# PLAIN ENGLISH (board-requested rebills, 11 PM ET 9/13/2026 slot - ehpa cloud run 9/14 0420UTC)
# Decides, from William's board rows / chat notes gathered this run:
#   DALLOWAY pat17469541: SUN01 member on file matches the facesheet -> freq-1 rebill the one open charge on seq 1.
#   DOVEDALE pat17477059: BCBS member matches the facesheet -> Stedi BCBSF eligibility at the July 2026 DOS; ACTIVE -> freq-1
#     rebill the 5 July visits on the BCBS seq; INACTIVE -> reported for William's patient-responsibility rule (no write-off here).
#   WHITBY ROOKWOOD pat17474496: Dec 2025 visits (12/2-12/5) resaved with preauth 251203513351 (full charge echo) + freq-1 rebill
#     on the AET07 seq; Oct/Nov 2025 visits -> Stedi 60054 eligibility at 10/27/2025; ACTIVE -> freq-1 rebill, else reported.
#   BEXLEY pat17475817: facesheet says SUNSHINE AMBETTER HIX (AMB03) U9896931601 eff 3/14/2026, auth IP5065597859 -> add AMB03
#     (no group number), end-date SUN01 3/13/2026, set the two open visits' insorder to the AMB03 seq with the preauth, freq-1 rebill.
# Never touches: paid lines, UNI20/BCBS balances older than 5/1/2026 rule (Dovedale is July 2026), group numbers.
"""Usage: python3 board_rebills_0914.py [--dry] [--only dalloway,dovedale,white,bexley]"""
import amd, txh, resave, freq1_visit, add_ins, ins_update, stedi, json, re, sys, time, datetime
import xml.etree.ElementTree as ET
dry = "--dry" in sys.argv
only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else ["dalloway", "dovedale", "whitby", "bexley"]
amd.login_cached()
LOG = open("board_rebills_0914.log", "a"); OUT = {}
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
L("=== board rebills %s dry=%s only=%s ===" % (datetime.datetime.utcnow().isoformat(), dry, only))

def demo(pid):
    root = ET.fromstring(amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}), timeout=60))
    p = root.find(".//patient"); return dict(p.attrib), [dict(i.attrib) for i in root.iter("insplan")]
def open_lines(pid, carrier=None):
    vs = {}
    for c in txh.fetch(pid).iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or float(a.get("insbal") or 0) <= 0: continue
        if carrier and a.get("carrier") != carrier: continue
        paid = any(p.get("void") != "1" and float(p.get("amount") or 0) != 0 for p in c.iter("payment"))
        vs.setdefault(a.get("visit"), []).append({"cid": a.get("id"), "dos": a.get("dos", "").strip(), "proc": a.get("proccode"), "bal": float(a.get("insbal")), "billdate": a.get("billdate") or "", "carrier": a.get("carrier"), "paid": paid})
    return vs
def resave_full(cid, insorder=None, preauth=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    if insorder: va["insorder"] = str(insorder)
    if preauth: va["preauth"] = preauth
    if dry: return "DRY resave %d charges insorder %s->%s preauth %s" % (len(allc), vis.get("insorder"), va.get("insorder"), preauth)
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                         "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.6)
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:200])
    v2, p2, c2 = resave.visit_charges(cid)
    x = resave.detail(re.sub(r"\D", "", cid)); pa = re.findall(r'preauth="([^"]*)"', x)
    return "ok insorder=%s live %d (was %d) preauth on detail %s" % (v2.get("insorder"), len(c2), len(allc), sorted(set(pa)))
def rebill(vid, cid, seq, tag):
    if dry: L("  DRY v%s chg %s freq1 rebill seq %s" % (vid, cid, seq)); return
    r = freq1_visit.run(vid, re.sub(r"\D", "", cid), seq); L("  v%s chg %s -> %s" % (vid, cid, r)); OUT.setdefault(tag, []).append((vid, r)); time.sleep(0.4)
def stedi_elig(payer, first, last, dob, member, dos, pid, tag):
    try:
        import os; os.makedirs("patient_db/%s" % pid, exist_ok=True)
        j = stedi.elig(payer, first, last, dob, member, dos)
        json.dump(j, open("patient_db/%s/stedi_elig_%s_%s.json" % (pid, payer, dos), "w"), indent=1)
        s = stedi.med_summ(j); L("  Stedi %s @%s: %s" % (payer, dos, s[:400])); OUT[tag + "_elig"] = s[:400]
        act = any((b.get("code") == "1") for b in j.get("benefitsInformation", []))
        inact = any((b.get("code") == "6") for b in j.get("benefitsInformation", []))
        return "ACTIVE" if act else ("INACTIVE" if inact else "UNKNOWN " + str(j.get("errors", ""))[:150])
    except Exception as e:
        L("  Stedi ERR %s" % str(e)[:200]); return "ERR"

if "dalloway" in only:
    pid = "17469541"; L("--- DALLOWAY pat%s ---" % pid)
    pa, pl = demo(pid); seq = [p["sequence"] for p in pl if p.get("carrier") == "car6194" and not p.get("enddate")]
    vs = open_lines(pid, "SUN01"); L("  open SUN01 visits %s seq %s" % ({v: [(x["cid"], x["dos"], x["bal"]) for x in l] for v, l in vs.items()}, seq))
    for vid, lines in vs.items():
        if any(x["paid"] for x in lines): L("  skip v%s paid" % vid); continue
        rebill(vid, lines[0]["cid"], seq[0], "dalloway")

if "dovedale" in only:
    pid = "17477059"; L("--- DOVEDALE pat%s ---" % pid)
    pa, pl = demo(pid); bc = [p for p in pl if p.get("carrier") == "car6062" and not p.get("enddate")]
    last, first = (pa.get("name") or ",").split(",")[0].strip(), (pa.get("name") or ",").split(",")[1].strip().split()[0]
    dob = datetime.datetime.strptime(pa.get("dob"), "%m/%d/%Y").strftime("%Y%m%d")
    vs = open_lines(pid, "BCBS"); L("  open BCBS visits %s" % {v: [(x["cid"], x["dos"], x["bal"]) for x in l] for v, l in vs.items()})
    st = stedi_elig("BCBSF", first, last, dob, bc[0]["subscribernum"], "20260709", pid, "dovedale") if bc else "no plan"
    L("  BCBS status at 7/9/2026: %s" % st); OUT["dovedale_status"] = st
    if st == "ACTIVE":
        for vid, lines in vs.items():
            if any(x["paid"] for x in lines): L("  skip v%s paid" % vid); continue
            rebill(vid, lines[0]["cid"], bc[0]["sequence"], "dovedale")
    else: L("  NOT rebilled -> report for William (patient-responsibility rule)")

if "whitby" in only:
    pid = "17474496"; L("--- WHITBY ROOKWOOD pat%s ---" % pid)
    pa, pl = demo(pid); ae = [p for p in pl if p.get("carrier") == "car6047" and not p.get("enddate")]
    last, first = (pa.get("name") or ",").split(",")[0].strip(), (pa.get("name") or ",").split(",")[1].strip().split()[0]
    dob = datetime.datetime.strptime(pa.get("dob"), "%m/%d/%Y").strftime("%Y%m%d")
    vs = open_lines(pid, "AET07"); L("  open AET07 visits %s seq %s" % ({v: [(x["cid"], x["dos"], x["bal"]) for x in l] for v, l in vs.items()}, ae[0]["sequence"] if ae else None))
    dec = {v: l for v, l in vs.items() if l[0]["dos"].startswith("12/")}
    oct_ = {v: l for v, l in vs.items() if v not in dec}
    for vid, lines in dec.items():
        if any(x["paid"] for x in lines): L("  skip v%s paid" % vid); continue
        L("  v%s %s preauth resave -> %s" % (vid, lines[0]["dos"], resave_full(lines[0]["cid"], preauth="251203513351")))
        rebill(vid, lines[0]["cid"], ae[0]["sequence"], "whitby_dec")
    st = stedi_elig("60054", first, last, dob, ae[0]["subscribernum"], "20251027", pid, "whitby_oct") if ae else "no plan"
    L("  AET07 status at 10/27/2025: %s" % st); OUT["whitby_oct_status"] = st
    if st == "ACTIVE":
        for vid, lines in oct_.items():
            if any(x["paid"] for x in lines): L("  skip v%s paid" % vid); continue
            rebill(vid, lines[0]["cid"], ae[0]["sequence"], "whitby_oct")
    else: L("  Oct/Nov visits NOT rebilled (%s) -> report" % st)

if "bexley" in only:
    pid = "17475817"; L("--- BEXLEY pat%s ---" % pid)
    pa, pl = demo(pid); L("  plans %s" % [(p["id"], p["carrier"], p["subscribernum"], p["sequence"], p["begindate"], p["enddate"]) for p in pl])
    amb = [p for p in pl if p.get("carrier") == "car6802" and not p.get("enddate")]
    if not amb and not dry:
        insid, seq = add_ins.add(pid, "car6802", "U9896931601", "03/14/2026"); L("  add AMB03 U9896931601 -> %s seq %s" % (insid, seq)); time.sleep(0.5)
        pa, pl = demo(pid); amb = [p for p in pl if p.get("carrier") == "car6802" and not p.get("enddate")]
    elif not amb: L("  DRY add AMB03")
    sun = [p for p in pl if p.get("carrier") == "car6194" and not p.get("enddate")]
    for p in sun:
        if dry: L("  DRY end-date SUN01 %s 03/13/2026" % p["id"]); continue
        L("  end-date SUN01 %s -> %s" % (p["id"], ins_update.update(pid, p["id"], enddate="03/13/2026")))
    vs = open_lines(pid); L("  open visits %s" % {v: [(x["cid"], x["dos"], x["proc"], x["carrier"], x["bal"]) for x in l] for v, l in vs.items()})
    if amb:
        seq = amb[0]["sequence"]
        for vid, lines in vs.items():
            if any(x["paid"] for x in lines): L("  skip v%s paid" % vid); continue
            if not lines[0]["dos"].startswith("03/"): L("  skip v%s dos %s not the 3/2026 stay" % (vid, lines[0]["dos"])); continue
            L("  v%s resave insorder %s + preauth -> %s" % (vid, seq, resave_full(lines[0]["cid"], insorder=seq, preauth="IP5065597859")))
            rebill(vid, lines[0]["cid"], seq, "bexley")
    else: L("  no AMB03 plan -> HOLD")
json.dump(OUT, open("registers/board_rebills_2026-09-14_0420UTC.json", "w"), indent=1)
