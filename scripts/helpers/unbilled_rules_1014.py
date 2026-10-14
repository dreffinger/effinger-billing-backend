# PLAIN ENGLISH (Unbilled column - William's three 10/14/2026 rules + the cascade verdicts of the 10/14 chat pass)
# Decides, per Unbilled row, by the error text:
#  (A) 'Date of service is outside insurance coverage effective dates' -> William 10/14: when the active plan's begin date is
#      AFTER the date of service, move that plan's begin date back ONE YEAR (updateinsurance begindate) and resubmit (freq-1).
#      Refinement from the cascade (same night): when another plan already on the chart covered that date of service (Stedi
#      Medicare record / payer 271), point the visit at THAT plan instead of rolling a date (reroute = visit order + ONE freq-1
#      rebill); a Medicare claim over 12 months old is written off untimely (WOINS, dated note) per the standing rule.
#  (B) 'Bill Insurance = "No" at charge level and charge has insurance balance' -> William 10/14: set the charge-level
#      Bill Insurance flag to Yes (billins="1" on the full-visit echo, fin class = the plan's) and resubmit (freq-1).
#      CCM (99487/99489) on a Medicaid/FCC-only chart is never payable (William 10/13) -> WONCS write-off instead of a claim.
#  (C) 'Insurance order is missing on visit' -> William 10/14: run Stedi, add the correct insurance, submit. The plan found by
#      the cascade is added (add_ins, no group number), the visit order set, ONE freq-1 rebill sent. No plan found -> board row.
#  Every fixed visit is released from the column (hideunbillablevisits); nothing is released while its data is still broken.
# Never touches: payments, write-offs on paid lines, voided charges; never bypasses the deceased guard (inside amd.rebill_charge).
#   python3 unbilled_rules_1014.py            # dry: prints the plan, writes nothing
#   python3 unbilled_rules_1014.py --live     # acts; register -> registers/unbilled_rules_<stamp>.json
import amd, resave, freq1_visit, ins_update, add_ins, manual_post, payreasons, json, re, sys, time, datetime
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv
ONLY = [a for a in sys.argv[1:] if a.startswith("--only=")]
ONLY = set(ONLY[0][7:].split(",")) if ONLY else None
amd.login_cached()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
REG = {"run": stamp, "live": LIVE, "charts": {}, "visits": [], "writeoffs": [], "left": []}
def num(s): return re.sub(r"\D", "", str(s or ""))
def log(*a):
    print(*a, flush=True)
    open("unbilled_rules_1014.log", "a").write(time.strftime("%Y-%m-%dT%H:%M:%SZ ", time.gmtime()) + " ".join(str(x) for x in a) + "\n")

def plans(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    pl = [dict(re.findall(r'(\w+)="([^"]*)"', t)) for t in re.findall(r'<insplan [^>]*>', r)]
    pl = [p for p in pl if p.get("id")]
    m = re.search(r'<patient [^>]*?insorder="([^"]*)"', r)
    return pl, (m.group(1) if m else "")

def year_back(mdy):
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", mdy); return "%s/%s/%d" % (m.group(1), m.group(2), int(m.group(3)) - 1)

def visit_resave(cid, charge_over=None, visit_over=None):
    """Full-visit echo (every live charge, CHG_FIELDS) with attribute overrides - the only safe way to change a charge flag.
    Returns (ok, message); verifies the re-read shows the overrides and the same live-charge count."""
    vis, pat, allc = resave.visit_charges(num(cid))
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        a.update(charge_over or {})
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va.update(visit_over or {})
    if not LIVE: return True, "DRY resave %s charges=%d over=%s visit=%s" % (vis.get("id"), len(allc), charge_over, visit_over)
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
                 "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                 "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    if "Fault" in r: return False, "resave FAULT %s: %s" % (vis.get("id"), re.sub(r"\s+", " ", r[:300]))
    time.sleep(0.8)
    v2, p2, c2 = resave.visit_charges(num(cid))
    ok = len(c2) == len(allc) and all((v2.get(k) or "").replace(" ", "") == str(v).replace(" ", "") for k, v in (visit_over or {}).items()) \
         and all(all(c.get(k) == str(v) for k, v in (charge_over or {}).items() if k != "finclasscode") for c in c2)
    return ok, "resave %s -> charges %d/%d, visit %s, charge flags %s" % (vis.get("id"), len(c2), len(allc), {k: v2.get(k) for k in (visit_over or {})}, {k: sorted({c.get(k) for c in c2}) for k in (charge_over or {})})

def rebill(vid, cid, seq):
    if not LIVE: return "DRY freq1 + rebill seq %s" % seq
    return freq1_visit.run(vid, cid, seq)

def release(vid):
    if not LIVE: return "DRY release"
    ok, msg = payreasons.release_visit(vid); return "released" if ok else "release failed: " + msg

def visit_charges_from_row(row):
    return [(num(ch["id"]), ch["chgcode"], ch["dos"].strip(), float(ch["fee"]), ch.get("billinsurance")) for ch in row["_chgs"]]

def writeoff(pid, vid, cid, carrier, amount, code, note):
    ok, msg = manual_post.post(cid, carrier, 0.0, round(amount, 2), code, "UNTIMELY1014", None, note, dry=not LIVE)
    REG["writeoffs"].append({"pid": pid, "vid": vid, "cid": cid, "carrier": carrier, "amount": round(amount, 2), "code": code, "note": note, "ok": ok, "msg": msg[:160]})
    return ok, msg

scan = json.load(open("scan_2026-10-14_chat/summary_before.json"))
# visits finished by an earlier (interrupted) live run of this same pass: a 'released' step in the log = done
DONE = set()
import os
if os.path.exists("unbilled_rules_1014.log"):
    for line in open("unbilled_rules_1014.log"):
        if '"vid"' in line and '"released"' in line:
            try: DONE.add(json.loads(line.split(" ", 1)[1])["vid"])
            except Exception: pass
rows = {r["id"]: r for r in scan["unbilled"]}
by_pid = {}
for r in scan["unbilled"]: by_pid.setdefault(r["patientid"], []).append(r)

# ------------------------------------------------------------------ the per-chart plan (facts from the 10/14 cascade lookups)
PLAN = {
 # rule A + C, chart with CHP only, begin 02/23/2026 > every DOS; CMS: CHP HMO Medicare Risk 10/1/2010-2/28/2026, date of death [DOB]
 "48008":    {"rollback": [("ins9518597", "02/23/2026")], "order": "1", "seq": 1, "flip": False, "note": "CHP MA on all DOS per CMS record; DOD [DOB] - every DOS before it"},
 # rule A, three UHC rows: 11/11/2025 -> Humana MA (seq 1, active to 11/30/2025); 12/02 + 12/05/2025 -> traditional Medicare (seq 3; no MA plan on DOS per CMS)
 "17474649": {"per_visit": {"19423214": ("1", 1), "19425170": ("3", 3), "19427052": ("3", 3)}, "flip": False, "note": "CMS record: Humana MA ended 11/30/2025, Part D only after; DOD [DOB] (DOS before)"},
 # rule A, Humana rows 04/18-04/21/2025 -> UHC AARP MA HMO-POS active 1/1/2025-9/30/2025 (Stedi 87726); Humana inactive on DOS
 "17472114": {"order": "1", "seq": 1, "flip": False, "note": "UHC AARP MA active 2025-01-01..2025-09-30 per Stedi; Humana begins 08/31/2025"},
 # rule A, UNI20 row 03/13/2025 -> Humana PPO MA (COB 1/1/2023-4/30/2025 per CMS), chart seq 1
 "17473032": {"order": "1", "seq": 1, "flip": False, "note": "Humana PPO MA on DOS per CMS; UHC begins 07/01/2025"},
 # rule A, Humana row 01/23/2024 -> Medicare primary on DOS (CHP ended 1/11/2024, QMB, no MA); Medicare >12 months -> untimely write-off
 "20407":    {"writeoff": {"carrier": "MCAD", "code": "WOCAID2ND", "note": "QMB cost-share: Medicare paid 01/23/2024, leftover coinsurance belongs to Medicaid (FL QMB per CMS), no Medicaid plan on chart and past 12 months - WOCAID2ND (dual rule 10/5, 12-month rule) - chat 10/14"}, "flip": False},
 # rule A, BCBS row 05/25/2023: BCBS seq 2 begins 06/27/2023 -> roll to 06/27/2022, resubmit (William 10/14 literal)
 "23671":    {"rollback": [("ins9511516", "06/27/2023")], "flip": False, "note": "rule A literal - 2023 DOS, payer answers"},
 # rule A, BCBS rows 05/09, 07/24, 07/27/2023: BCBS seq 3 08/01/2023-10/06/2023 -> roll begin to 08/01/2022, resubmit
 "12233534": {"rollback": [("ins9507138", "08/01/2023")], "order": "3", "seq": 3, "flip": False, "note": "rule A literal - 2023 DOS, payer answers"},
 # rule A, UNI20 row 12/28/2022: UHC seq 2 begins 04/28/2023 -> roll to 04/28/2022, resubmit
 "23254":    {"rollback": [("ins9510255", "04/28/2023")], "order": "2", "seq": 2, "flip": False, "note": "rule A literal - 2022 DOS, payer answers"},
 # rule A, UNI20 rows 08/2022: Medicare seq 1 (07/22-08/29/2022) covered them; Medicare >12 months -> untimely write-off
 "20336":    {"writeoff": {"carrier": "UNI20", "code": "WOCLTREQ", "note": "Medicare coinsurance leftover from 08/2022 with no supplement in force (UHC began 09/01/2022); cost-share with no insurance left to bill -> WOCLTREQ (William 10/13) - chat 10/14"}, "flip": False},
 # rule B: Medicare + Medicaid (both AMD 271 active) -> Bill Insurance Yes, MC, order 1,2, rebill Medicare
 "23177":    {"flip": True, "finclass": "MC", "order": "1,2", "seq": 1, "note": "plans added 10/13 (patient-balance review); AMD 271 active on both"},
 # rule B: Medicare only (AMD 271 active; CMS: BCBS 'other' since 2020, no MA) -> Yes, MC, order 1, rebill Medicare
 "24716":    {"flip": True, "finclass": "MC", "order": "1", "seq": 1, "note": "AMD 271 active; traditional Medicare per CMS"},
 # rule B: Medicaid-only chart; Stedi 77027 = Full Medicaid with FLORIDA COMMUNITY CARE (SMMC comprehensive) -> physician claims to FCC (car42008), CCM never payable -> WONCS
 "17469549": {"flip": True, "add_fcc": True, "ccm_writeoff": True, "note": "Medicaid-only (DOB 1983); FCC comprehensive per Stedi 77027 -> FLO99 for E/M, CCM written off (William 10/13 CCM rule)"},
 # rule B HELD: CMS says CHP HMO Medicare Risk since 05/01/2021 (open); UHC inactive; chart has only Medicare -> CHP member id needed (board)
 "24197":    {"hold": "CHP Medicare Advantage is primary on the DOS (CMS record: CHP HMO Medicare Risk since 05/01/2021, open; UHC 87726 inactive 12/10/2025-01/13/2026); CHP needs its own member id - not on the chart, not in discovery. Board row for William; Medicare would deny CO-24."},
 # rule C HELD: HCA admit 10/05/2026, zero plans; Medicare MBILU (SSN) and MBILUNOSSN both ERR 72 not found; discovery 0 coverages -> HCA facesheet
 "17478013": {"hold": "no plan on the chart; Stedi Medicare lookup by SSN and by name/DOB both answer ERR 72 (not on Medicare), discovery found 0 coverages at 10/05/2026 - the HCA facesheet (Omnessa) is the only source left; board row [name]-17478013 updated."},
}

def handle_chart(pid, prows):
    p = PLAN.get(pid)
    rec = {"pid": pid, "rows": len(prows), "actions": []}
    if not p:
        rec["actions"].append("no plan for this chart - left"); REG["left"] += [{"pid": pid, "vid": r["id"], "err": r["_errs"]} for r in prows]; return rec
    if "hold" in p:
        rec["actions"].append("HELD: " + p["hold"]); REG["left"] += [{"pid": pid, "vid": r["id"], "err": r["_errs"], "hold": p["hold"][:120]} for r in prows]; return rec
    pl, order0 = plans(pid)
    # 1. plan edits
    for insid, begin0 in p.get("rollback", []):
        cur = next((x for x in pl if x["id"] == insid), None)
        if not cur: rec["actions"].append("rollback %s: plan not on chart" % insid); continue
        if cur.get("begindate") != begin0: rec["actions"].append("rollback %s: begin is %s (expected %s) - already changed, skipped" % (insid, cur.get("begindate"), begin0)); continue
        nb = year_back(begin0)
        if LIVE:
            ok, msg = ins_update.update(pid, insid, begindate=nb)
            rec["actions"].append("rollback %s begindate %s -> %s: %s %s" % (insid, begin0, nb, ok, msg[:200]))
            if not ok: rec["actions"].append("STOP - plan edit failed, visits of this chart left"); REG["left"] += [{"pid": pid, "vid": r["id"], "err": r["_errs"]} for r in prows]; return rec
            pl, order1 = plans(pid)
            if (order1 or "") != (order0 or "") and order0:
                ok2, m2 = ins_update.update(pid, insid, sequence=order0); rec["actions"].append("patient insorder %r -> %r after the edit; restore -> %s %s" % (order0, order1, ok2, m2[:120]))
        else:
            rec["actions"].append("DRY rollback %s begindate %s -> %s" % (insid, begin0, nb))
    fcc_seq = None
    if p.get("add_fcc"):
        mcd = next((x for x in pl if x.get("carrier") == "car6113"), None)
        fcc = next((x for x in pl if x.get("carrier") == "car42008"), None)
        if fcc: fcc_seq = fcc.get("sequence"); rec["actions"].append("FCC plan already on chart seq %s" % fcc_seq)
        elif LIVE:
            insid, seq = add_ins.add(pid, "car42008", mcd["subscribernum"], mcd.get("begindate") or None, "1", "MD")
            rec["actions"].append("add FLO99 car42008 (member = Medicaid id, begin %s): %s seq %s" % (mcd.get("begindate"), insid, seq))
            if not insid: REG["left"] += [{"pid": pid, "vid": r["id"], "err": r["_errs"]} for r in prows]; return rec
            fcc_seq = str(seq); pl, _ = plans(pid)
        else:
            fcc_seq = "2"; rec["actions"].append("DRY add FLO99 car42008 member=<Medicaid id> begin %s -> seq %s" % (mcd.get("begindate") if mcd else "?", fcc_seq))
    # 2. per visit
    for r in sorted(prows, key=lambda x: x["_chgs"][0]["dos"][-4:] + x["_chgs"][0]["dos"][:5]):
        vid = r["id"]; chs = visit_charges_from_row(r); cid = chs[0][0]
        if vid in DONE: log("skip visit %s - already done in an earlier run of this pass" % vid); continue
        v = {"pid": pid, "vid": vid, "dos": chs[0][2], "cpts": [c[1] for c in chs], "fee": sum(c[3] for c in chs), "errs": r["_errs"], "steps": []}
        try:
            if "writeoff" in p:
                w = p["writeoff"]
                for ccid, cpt, dos, fee, bi in chs:
                    rt = ET.fromstring(resave.detail(ccid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + ccid][0]
                    bal = float(c.get("insbalance") or 0)
                    if bal <= 0: v["steps"].append(("skip writeoff", ccid, "insbalance 0")); continue
                    ok, msg = writeoff(pid, vid, ccid, w["carrier"], bal, w["code"], w["note"]); v["steps"].append(("writeoff", ccid, cpt, bal, ok, msg[:120]))
                if LIVE and all(s[0] != "writeoff" or s[4] for s in v["steps"]): v["steps"].append(("release", release(vid)))
                else: v["steps"].append(("release", "DRY release" if not LIVE else "held - a write-off failed"))
            elif p.get("ccm_writeoff") and all(c[1] in ("99487", "99489", "99490", "99491") for c in chs):
                for ccid, cpt, dos, fee, bi in chs:
                    rt = ET.fromstring(resave.detail(ccid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + ccid][0]
                    bal = float(c.get("insbalance") or 0)
                    if bal <= 0: v["steps"].append(("skip writeoff", ccid, "insbalance 0")); continue
                    ok, msg = writeoff(pid, vid, ccid, "MCAD", bal, "WONCS", "CCM never payable by Medicaid / FCC (William 10/13 rule) - chat 10/14"); v["steps"].append(("writeoff", ccid, cpt, bal, ok, msg[:120]))
                v["steps"].append(("release", release(vid) if (LIVE and all(s[0] != "writeoff" or s[4] for s in v["steps"])) else ("DRY release" if not LIVE else "held")))
            else:
                order = p.get("order"); seq = p.get("seq")
                if "per_visit" in p: order, seq = p["per_visit"].get(vid, (None, None))
                if p.get("add_fcc"): order, seq = fcc_seq, int(fcc_seq)
                if order is None:   # keep the visit's own order (rule A literal rows): rebill its first plan
                    rt = ET.fromstring(resave.detail(cid)); vo = (rt.find(".//visit").get("insorder") or "").replace(" ", "")
                    order = vo or (p.get("order") or "1"); seq = int(order.split(",")[0])
                charge_over = {}
                if p.get("flip"): charge_over = {"billins": "1", "finclasscode": p.get("finclass") or ("MD" if p.get("add_fcc") else "MC")}
                ok, msg = visit_resave(cid, charge_over, {"insorder": order}); v["steps"].append(("resave", ok, msg[:200]))
                if not ok: v["steps"].append(("STOP", "resave not verified - no rebill, no release")); REG["left"].append({"pid": pid, "vid": vid, "err": r["_errs"], "why": msg[:120]})
                else:
                    rb = rebill(vid, cid, seq); v["steps"].append(("rebill", seq, rb))
                    if LIVE and ("-> 204" in rb or "-> 20" in rb) and "BLOCKED" not in rb and "FAULT" not in rb: v["steps"].append(("release", release(vid)))
                    elif not LIVE: v["steps"].append(("release", "DRY release"))
                    else: v["steps"].append(("release", "held - rebill answered: " + rb[:100])); REG["left"].append({"pid": pid, "vid": vid, "err": r["_errs"], "why": rb[:120]})
        except Exception as e:
            v["steps"].append(("ERROR", str(e)[:300])); REG["left"].append({"pid": pid, "vid": vid, "err": r["_errs"], "why": str(e)[:120]})
        REG["visits"].append(v); log(json.dumps(v, default=str)); time.sleep(0.5 if LIVE else 0)
    return rec

TARGET_ERRS = ("Bill Insurance", "outside insurance coverage", "Insurance order is missing")
for pid, prows in by_pid.items():
    prows = [r for r in prows if any(any(t in e for t in TARGET_ERRS) for e in r["_errs"])]
    if not prows: continue
    if ONLY and pid not in ONLY: continue
    rec = handle_chart(pid, prows); REG["charts"][pid] = rec; log("CHART", pid, json.dumps(rec, default=str))
    json.dump(REG, open("registers/unbilled_rules_%s.json" % stamp, "w"), indent=1, default=str)
json.dump(REG, open("registers/unbilled_rules_%s.json" % stamp, "w"), indent=1, default=str)
from collections import Counter
log("SUMMARY visits %d, write-offs %d ($%.2f), left %d, charts %d, live=%s" % (len(REG["visits"]), len(REG["writeoffs"]), sum(w["amount"] for w in REG["writeoffs"]), len(REG["left"]), len(REG["charts"]), LIVE))
