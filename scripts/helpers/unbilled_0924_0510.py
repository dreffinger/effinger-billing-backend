# PLAIN ENGLISH (Unbilled + Exclusions pass, 1am ET 9/24/2026 run 2026-09-24T0510Z): the September CCM batch (127783, DOS 9/20/2026)
#   and a late Claimocity batch (Jan-Feb 2026 DOS) put 98 rows on the Unbilled snapshot; claim run 1700236 rejected 10 Florida Medicaid
#   PRIMARY claims 'PSBR0111 INVALID PAYER RESP SEQ NUM CODE P' (dual / SMMC members billed to Medicaid FFS as primary).
# Decides, from inv_0510.json (getdemographic plans + AMD's free 271 on every open plan + the visit's live state):
#   INSORDER: a visit whose insurance order is empty or points at an end-dated plan gets the live order (Medicare first, MA plan alone,
#     Medicaid/MMA last - the 271 named the SMMC plan) in a full-visit echo (every live charge, updvisitwithcharges), frequency-1 reset +
#     chargerebill on the first sequence (an original claim; the deceased guard runs inside), then release. The PATIENT default order is set
#     to the same string (ins_update sequence=) where it was empty or wrong, so the next monthly batch does not land here again.
#   RULE (b): 'A payment from the prior payor is required' with the primary sent/unanswered -> release (re-queues on its own).
#   EXCLUSIONS: PSBR0111 -> visit insorder = the SMMC MMA plan the 271 names (FCC / Humana / Simply), freq-1 rebill to it, hideexclusions.
#   HOLDS (never touched): pat17472874 April stay, v19441047, v19430630, pat17477183 (William's turn), pat17473232 + pat17471681 (CCM
#     DOS after the date of death on Medicare's 271 -> William), pat45049 (Medicare AAA 72 -> cascade script), the 11 new charts (cascade).
# Never touches: payments, write-offs, hospitalizationto, plans' member ids.
"""Usage: python3 unbilled_0924_0510.py [--dry] [--only vid,vid]"""
import amd, resave, freq1_visit, ins_update, elig_amd, re, json, sys, time, datetime
DRY = "--dry" in sys.argv
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else None
S = "2026-09-24T0510Z"
amd.login_cached()
inv = json.load(open("inv_0510.json"))
def L(m): print(m, flush=True)
out = {"stamp": S, "dry": DRY, "fixed": [], "released_b": [], "excl_fixed": [], "held": [], "faults": [], "patient_order": []}

# (pid, [vids], insorder, rebill_seq, note)
FIX = [
 ("17476544", ["19451019", "19451191", "19451353"], "2", 2, "BCBS ended 06/08/2026; Medicare seq 2 ACTIVE"),
 ("17470802", ["19452372", "19453348", "19453495", "19454877"], "2", 2, "UNI20 ended 08/19/2026; Medicare seq 2 ACTIVE (QMB)"),
 ("48163", ["19455310", "19455311", "19455312", "19455313", "19455314", "19455315"], "4,2", 4, "plans seq1/3 ended 12/31/2025; UHC Dual Complete seq 4 ACTIVE from 1/1/2026 (Medicaid 271: D-SNP UHC), Medicaid FFS second"),
 ("17473669", ["19455735"], "2", 2, "UNI20 ended 05/31/2026; Ambetter AMB03 seq 2 ACTIVE"),
 ("17469645", ["19453683", "19455736"], "3,1", 3, "UHC Dual Complete (MA) seq 3 ACTIVE -> Medicare never secondary to an MA plan; Medicaid FFS second (LTC Sunshine is custodial, no MMA entity)"),
 ("17473233", ["19455610"], "1", 1, "AARP MA from UHC seq 1 ACTIVE (H1045) -> MA plan alone; Medicare not secondary"),
 ("25266", ["19455802"], "2,3", 2, "Medicare seq 2 ACTIVE (QMB) first; Sunshine SMMC MMA seq 3 second; Medicaid FFS never first"),
 ("17473208", ["19455630"], "2", 2, "CHP ended 04/21/2025; Medicare seq 2 ACTIVE"),
 ("17473197", ["19455638"], "2", 2, "UNI20 ended 05/16/2026; Medicare seq 2 ACTIVE"),
 ("17475312", ["19455651"], "2", 2, "Medicare ended 08/22/2026; AARP MA (UNI20) seq 2 ACTIVE from 8/23/2026"),
 ("17473199", ["19455653"], "2,3", 2, "BCBS ended 12/31/2025; Medicare seq 2 ACTIVE; AARP Medigap seq 3 (board row berry-priscilla-denials)"),
 ("17473422", ["19455667"], "2", 2, "UNI20 ended 05/06/2026; Medicare seq 2 ACTIVE"),
 ("24655", ["19455697"], "2", 2, "Medicare ended 09/17/2025; AARP MA (UNI20) seq 2 ACTIVE"),
 ("22858", ["19455723"], "4", 4, "SUN01 ended 05/31/2025; Medicaid 271 names SMMC MMA Capitated FLORIDA COMMUNITY CARE -> FCC seq 4 (comprehensive plan)"),
 ("17472517", ["19455740"], "3,2", 3, "CHP ended 08/31/2026; Medicare seq 3 ACTIVE (QMB) first, Humana Medicaid MMA seq 2 second"),
 ("21378", ["19455764"], "1,5", 1, "Medicare seq 1 ACTIVE (QMB); UHCMA ended 12/08/2025, UNI20 INACTIVE; Humana Medicaid MMA seq 5 second"),
 ("17471673", ["19455767"], "3,2", 3, "Medicare ended 10/07/2025; UHC D-SNP (UNI20) seq 3 ACTIVE from 10/8/2025; Medicaid FFS second (LTC FCC custodial, no MMA entity)"),
 ("45008", ["19455787"], "4", 4, "Medicare seq 4 ACTIVE (QMB); every other plan ended"),
 ("24039", ["19455792"], "1,3", 1, "Medicare seq 1 ACTIVE; SUN01 ended 05/17/2026; FCC seq 3 second"),
 ("17477128", ["19455814", "19455905"], "2", 2, "UNI20 ended 08/03/2026; Medicare seq 2 ACTIVE"),
 ("12232512", ["19455818"], "4,3", 4, "Medicare ended 02/09/2026; UHC D-SNP (UNI20) seq 4 ACTIVE from 2/10/2026; Humana Medicaid seq 3 second"),
 ("45001", ["19455826", "19455910"], "4,3", 4, "Medicare seq 4 ACTIVE from 4/1/2026 (QMB); Medicaid 271 names SMMC MMA Humana -> HUM01 seq 3 second"),
 ("17473571", ["19455833"], "2", 2, "UNI20 ended 05/05/2026; Medicare seq 2 ACTIVE"),
 ("17473383", ["19427585", "19430729"], "4,3", 4, "billed to Medicare (ended 10/01/2025, $0 answer 9/6); Medicaid 271 names D-SNP HUMANA; HumanaChoice seq 4 ACTIVE from 10/2/2025 -> wrong payer, re-route"),
 ("21915", ["19455374", "19455375"], "1,3", 1, "Medicare seq 1 ACTIVE; Medicaid 271 names SMMC MMA Humana -> HUM01 seq 3 second (not Medicaid FFS); never billed - original claim to Medicare"),
]
# rule (b): release only (primary sent and unanswered / secondary waiting); never-billed ones also get a freq-1 original to seq 1
RELEASE_B = [
 ("23391", ["19392347"], None, "secondary BCBS residual 23.62 behind a Medicare payment; primary link missing -> release, re-queues on its own"),
 ("17473343", ["19442414"], None, "billed Medicare 9/5, $0 answer 9/6 (check 26143B1000143315) - reason not in the cache; release per rule (b), listed for a look"),
 ("17476868", ["19447648", "19447649", "19447650", "19447651", "19447878", "19448026", "19448251", "19448583", "19448637"], None, "Medicare primary sent 9/13-9/16, unanswered - released again (rule b)"),
 ("17477116", ["19448262"], None, "Medicare primary (seq 2 first) sent, unanswered - release"),
 ("23159", ["19455332"], 1, "late-entered 01/02/2026 visit, never billed; Medicare seq 1 ACTIVE -> original claim to Medicare + release"),
 ("23721", ["19455369"], 1, "late-entered 01/20/2026 visit, never billed; Medicare seq 1 ACTIVE -> original claim + release"),
 ("21021", ["19455372"], 1, "late-entered 01/05/2026 visit, never billed; Medicare (date of death 03/12/2026, DOS before it) -> original claim + release"),
 ("24214", ["19455373"], 1, "late-entered 01/02/2026 visit, never billed; Medicare seq 1 ACTIVE -> original claim + release"),
]
EXCL = [  # (run, vid, claimid, pid, insorder, seq, note)
 ("1700236", "19455364", "19455364A", "20060", "2", 2, "Medicaid 271: SMMC MMA Capitated FLORIDA COMMUNITY CARE -> FCC seq 2"),
 ("1700236", "19455365", "19455365A", "20060", "2", 2, "same"), ("1700236", "19455366", "19455366A", "20060", "2", 2, "same"),
 ("1700236", "19455367", "19455367A", "20060", "2", 2, "same"), ("1700236", "19455368", "19455368A", "20060", "2", 2, "same"),
 ("1700236", "19455781", "19455781A", "20060", "2", 2, "same"),
 ("1700236", "19455737", "19455737A", "17477134", "2", 2, "Medicaid 271: SMMC MMA Capitated FLORIDA COMMUNITY CARE -> FCC seq 2"),
 ("1700236", "19455746", "19455746A", "20514", "3", 3, "Medicaid 271: SMMC MMA Capitated FLORIDA COMMUNITY CARE -> FCC seq 3"),
 ("1700236", "19455782", "19455782A", "17475713", "2", 2, "Medicaid 271: SMMC MMA Capitated HUMANA MEDICAL PLAN -> HUM01 seq 2"),
 ("1700236", "19455810", "19455810A", "17474046", "2", 2, "Medicaid 271: SMMC MMA Capitated SIMPLY HEALTHCARE -> SIM01 seq 2"),
]
PATIENT_ORDER = {"25266": "2,3", "17473208": "2", "17473197": "2", "17475312": "2", "17473199": "2,3", "17473422": "2", "24655": "2", "22858": "4", "17472517": "3,2",
                 "21378": "1,5", "17471673": "3,2", "45008": "4", "24039": "1,3", "17477128": "2", "12232512": "4,3", "45001": "4,3", "17473571": "2", "17473383": "4,3",
                 "21915": "1,3", "17469645": "3,1", "17473233": "1", "20060": "2", "17477134": "2", "20514": "3", "17475713": "2", "17474046": "2"}
HELD = [("17470743", "19441047", "MCAD crossover behind a reversed Medicare payment - standing hold"), ("17474541", "19430630", "Claim Inspector hold (Pattern 15775)"),
        ("17477183", "19455471", "cascade exhausted 9/23 - William's turn (row alcorn-alfred-17477183)"), ("17477183", "19455759", "same - second visit (CCM 9/20/2026)"),
        ("17473232", "19455597", "CCM 09/20/2026 AFTER the date of death 06/02/2026 on Medicare's 271 - William: void"),
        ("17471681", "19455606", "CCM 09/20/2026 AFTER the date of death 09/10/2026 on Medicare's 271 - William: DOS on/before 9/10 or void"),
        ("45049", "19455371", "Medicare 271 REJECTED AAA 72 (member id) - cascade (Stedi MBI) in the cascade script")]
for pid, vid, why in HELD: out["held"].append({"pid": pid, "vid": vid, "why": why})

def visit_cid(pid, vid):
    for v in inv.get(pid, {}).get("visits", []):
        if v["vid"] == vid: return v
    return None
def first_cid_from_scan(vid):
    sb = json.load(open("scan_0912/summary_before.json"))
    for r in sb["unbilled"]:
        if r["id"] == vid and r["_chgs"]: return r["_chgs"][0]["id"]
    import xml.etree.ElementTree as ET
    ex = ET.fromstring(open("scan_0912/excl_1700236_before.xml").read())
    for v in ex.iter("visit"):
        if v.get("id") == vid:
            for c in v.iter("charge"): return c.get("id")
    return None
def set_insorder(cid, order):
    """full-visit echo with the new insorder (every live charge), no balance change."""
    vis, pat, allc = resave.visit_charges(cid)
    if not allc: return "no live charges"
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = order; va["onhcfa"] = "1"
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                         "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:200])
    time.sleep(0.6)
    x2 = resave.detail(cid); v2 = re.search(r'insorder="([^"]*)"', x2)
    return "insorder now %s (%d charges echoed)" % (v2.group(1) if v2 else "?", len(allc))
def release(vids):
    vids = [re.sub(r"\D", "", v) for v in vids]
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in vids)))
    return ('success="1"' in r and "<Fault" not in r), re.sub(r"\s+", " ", r)[:160]

to_release = []
# --- Thackeray K (pat17472874): only the three NEW September visits - the April stay stays on hold
tk = "17472874"
try:
    for insid in ("9518478", "9512361"):
        s = elig_amd.run_plan(tk, insid); L("pat%s plan ins%s -> %s" % (tk, insid, elig_amd.one_line(s)[:200]))
    s3 = json.load(open("patient_db/%s/elig_9518478_%s.json" % (tk, datetime.date.today().strftime("%Y%m%d"))))
    if s3.get("status") == "ACTIVE":
        FIX.append((tk, ["19455321", "19455322", "19455323"], "3,2", 3, "September visits on plan seq 1 (ended 12/31/2025); UNI20 seq 3 ACTIVE per AMD 271, Sunshine seq 2 second; the April stay hold is untouched"))
        PATIENT_ORDER[tk] = "3,2"
    else:
        out["held"].append({"pid": tk, "vid": "19455321-23", "why": "UNI20 seq 3 not ACTIVE on the 271: %s" % s3.get("status")})
except Exception as e:
    out["held"].append({"pid": tk, "vid": "19455321-23", "why": "271 read failed %s" % str(e)[:80]})

for pid, vids, order, seq, note in FIX:
    for vid in vids:
        if ONLY and vid not in ONLY: continue
        rec = {"pid": pid, "vid": vid, "insorder": order, "seq": seq, "note": note, "steps": []}
        cid = first_cid_from_scan(vid)
        if not cid: rec["steps"].append("no charge id"); out["faults"].append(rec); continue
        if DRY: rec["steps"].append("DRY would set insorder %s, freq1+rebill seq %s, release" % (order, seq)); out["fixed"].append(rec); L("DRY pat%s v%s -> %s seq %s" % (pid, vid, order, seq)); continue
        try:
            r1 = set_insorder(cid, order); rec["steps"].append(r1); L("pat%s v%s set_insorder -> %s" % (pid, vid, r1))
            if r1.startswith("FAULT") or r1.startswith("no live"): out["faults"].append(rec); continue
            time.sleep(0.4)
            r2 = freq1_visit.run(vid, cid, seq); rec["steps"].append(r2); L("pat%s v%s %s" % (pid, vid, r2))
            if "204" not in r2:
                # rebill refused (deceased guard or 500) - still release only if the guard did not block
                if "death" in r2.lower() or "guard" in r2.lower(): out["held"].append({"pid": pid, "vid": vid, "why": r2}); continue
            out["fixed"].append(rec); to_release.append(vid); time.sleep(0.3)
        except Exception as e:
            rec["steps"].append("EXC %s" % str(e)[:160]); out["faults"].append(rec); L("pat%s v%s EXC %s" % (pid, vid, str(e)[:160]))

for pid, vids, seq, note in RELEASE_B:
    for vid in vids:
        if ONLY and vid not in ONLY: continue
        rec = {"pid": pid, "vid": vid, "note": note, "steps": []}
        if seq and not DRY:
            cid = first_cid_from_scan(vid)
            try:
                r2 = freq1_visit.run(vid, cid, seq); rec["steps"].append(r2); L("pat%s v%s %s" % (pid, vid, r2))
                if "death" in r2.lower(): out["held"].append({"pid": pid, "vid": vid, "why": r2}); continue
            except Exception as e:
                rec["steps"].append("EXC %s" % str(e)[:160])
        out["released_b"].append(rec); to_release.append(vid)

# --- exclusions
for run, vid, claimid, pid, order, seq, note in EXCL:
    if ONLY and vid not in ONLY: continue
    rec = {"run": run, "vid": vid, "claimid": claimid, "pid": pid, "insorder": order, "seq": seq, "note": note, "steps": []}
    cid = first_cid_from_scan(vid)
    if DRY: rec["steps"].append("DRY"); out["excl_fixed"].append(rec); continue
    try:
        r1 = set_insorder(cid, order); rec["steps"].append(r1); L("EXCL pat%s v%s set_insorder -> %s" % (pid, vid, r1))
        if r1.startswith("FAULT") or r1.startswith("no live"): out["faults"].append(rec); continue
        time.sleep(0.4)
        r2 = freq1_visit.run(vid, cid, seq); rec["steps"].append(r2); L("EXCL pat%s v%s %s" % (pid, vid, r2))
        if "204" not in r2: out["faults"].append(rec); continue
        out["excl_fixed"].append(rec); time.sleep(0.3)
    except Exception as e:
        rec["steps"].append("EXC %s" % str(e)[:160]); out["faults"].append(rec)

# --- patient default order
for pid, order in PATIENT_ORDER.items():
    cur = inv.get(pid, {}).get("insorder")
    if cur == order: continue
    plans = inv.get(pid, {}).get("plans", [])
    tgt = next((p for p in plans if p["seq"] == order.split(",")[0]), None)
    if not tgt: out["patient_order"].append({"pid": pid, "order": order, "result": "plan for seq not found"}); continue
    if DRY: out["patient_order"].append({"pid": pid, "order": order, "was": cur, "result": "DRY"}); continue
    try:
        ok, msg = ins_update.update(pid, tgt["id"], sequence=order); out["patient_order"].append({"pid": pid, "order": order, "was": cur, "result": "ok" if ok else msg[:120]}); L("pat%s patient order %s -> %s : %s" % (pid, cur, order, ok))
    except Exception as e:
        out["patient_order"].append({"pid": pid, "order": order, "was": cur, "result": "EXC %s" % str(e)[:100]})
    time.sleep(0.3)

if not DRY:
    if to_release:
        ok, msg = release(to_release); L("hideunbillablevisits x%d -> %s %s" % (len(to_release), ok, msg)); out["release_call"] = {"n": len(to_release), "ok": ok, "msg": msg}
    byrun = {}
    for rec in out["excl_fixed"]: byrun.setdefault(rec["run"], []).append((rec["vid"], rec["claimid"]))
    for rid, lst in byrun.items():
        r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": rid, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in lst)))
        ok = "Fault" not in r; L("hideexclusions run %s x%d -> %s" % (rid, len(lst), ok)); out.setdefault("excl_completed", []).append({"run": rid, "n": len(lst), "ok": ok})
json.dump(out, open("registers/unbilled_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
L("SUMMARY fixed %d released_b %d excl_fixed %d held %d faults %d patient_order %d" % (len(out["fixed"]), len(out["released_b"]), len(out["excl_fixed"]), len(out["held"]), len(out["faults"]), len(out["patient_order"])))
