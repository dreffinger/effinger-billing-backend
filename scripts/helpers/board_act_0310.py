# PLAIN ENGLISH (Insurance Refresh Board actions, 11 PM ET 9/14/2026 slot - ehpa cloud run 9/15 0310UTC)
# Carries out the board rows William handed back to this run (his 9/14 answers), one chart at a time:
#   Alcott   - write off the 9/1/2026 99308 ($107) as self-pay no-pay bad debt (Sunshine ended 8/31, Medicaid pending).
#   Brown    - correct the first name RANDLE -> RANDY on the chart, then freq-1 rebill the 7/13 and 7/14 Aetna visits.
#   Bull     - add Capital Health Plan (CAP07, member from Stedi, begin 6/1/2024), write the 9/10 admission date, set the
#              visit insurance order to the new plan, release the two visits from Unbilled.
#   Coalson  - WOLATE (timely filing, DOS 9/29-10/4/2025 first billed 9/10/2026) on the six Humana charges.
#   Collins  - freq-1 rebill the five July BCBS visits (write-off only after Florida Blue answers).
#   Ford / Morrow - WOLATE on the 10/25/2025 CCM lines (Humana, first billed 9/10/2026).
#   Morland    - add CAP07 (Stedi: MA plan active 1/1/2026), end-date Florida Blue 12/31/2025, move the two February visits
#              to the CAP07 sequence and freq-1 rebill.
#   Peterson - freq-1 rebill the 1/16/2026 99223 Aetna visit.
#   Penhale   - WOINS the two Medicare residuals ($113.02 + $142.98), no secondary.
# Rules it uses: no group numbers; pay + write-off never above the open insurance balance; full-visit charge echo on every
#   resave (void trap); hospitalizationfrom only, never hospitalizationto.
# Never touches: Clack (needs the CARC first), Gray (already written off), Tillotson (note only), any UNI20/BCBS aged balance.
"""Usage: python3 board_act_0310.py [--dry] [--only alcorn,brown,...]"""
import amd, resave, add_ins, ins_update, freq1_visit, manual_post, patient_patch, json, re, sys, time, datetime
import xml.etree.ElementTree as ET
dry = "--dry" in sys.argv
ALL = ["alcorn", "brown", "bull", "coalson", "collins", "ford", "morris", "moore", "peterson", "powell"]
only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else ALL
amd.login_cached()
LOG = open("board_act_0310.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
OUT = {}
def rec(k, v): OUT.setdefault(k, []).append(v); L("  %s: %s" % (k, v))
L("=== board_act_0310 %s dry=%s only=%s ===" % (datetime.datetime.utcnow().isoformat(), dry, only))
NOTE_DATE = "William 9/14/2026"

def set_admit(vid, code, admit):
    if dry: return "DRY set_admit vst%s %s %s" % (vid, code, admit)
    ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" '
           'employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit))
    r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"}, ext))
    return "ok" if "Fault" not in r else "FAULT " + re.sub(r"\s+", " ", r[:160])

def resave_full(cid, insorder=None, onhcfa="1"):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    if onhcfa: va["onhcfa"] = onhcfa
    if insorder: va["insorder"] = str(insorder)
    if dry: return "DRY resave %d charges insorder %s->%s" % (len(allc), vis.get("insorder"), va.get("insorder"))
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                         "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.6)
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:200])
    v2, p2, c2 = resave.visit_charges(cid)
    return "ok insorder=%s onhcfa=%s live %d (was %d)" % (v2.get("insorder"), v2.get("onhcfa"), len(c2), len(allc))

def plans(pid):
    x = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}), timeout=60)
    rt = ET.fromstring(x); pt = rt.find(".//patient")
    return pt.get("insorder"), [dict(i.attrib) for i in rt.iter("insplan")]

def wo(cid, carrier, amt, code, note):
    ok, msg = manual_post.post(cid, carrier, 0.0, float(amt), code, "", None, note, dry)
    return "%s %s" % ("ok" if ok else "REFUSED", msg)

def f1(vid, cid, seq):
    if dry: return "DRY freq1 %s/%s seq %s" % (vid, cid, seq)
    return freq1_visit.run(vid, cid, seq)

def release(vids):
    if dry: return "DRY release %s" % vids
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in vids)), timeout=120)
    return "ok" if "Fault" not in r else "FAULT " + re.sub(r"\s+", " ", r[:200])

# ---------------- Alcott pat17477183 ----------------
if "alcorn" in only:
    L("-- Alcott 9/1/2026 99308 cid 23364736 v19453827 $107 -> WOBAD")
    r = wo("23364736", "SUN01", 107.00, "WOBAD", "Self-pay no-pay bad debt - no insurance on 9/1/2026 (Sunshine ended 8/31/2026), Medicaid pending - " + NOTE_DATE)
    if "REFUSED" in r and not dry:
        L("  WOBAD refused, retrying WOINS"); r = wo("23364736", "SUN01", 107.00, "WOINS", "Self-pay no-pay - no insurance on 9/1/2026 (Sunshine ended 8/31/2026), Medicaid pending - " + NOTE_DATE)
    rec("alcorn", r)

# ---------------- Brown pat17477112 ----------------
if "brown" in only:
    L("-- Brown rename RANDLE -> RANDY then freq-1 7/13 + 7/14 AET07")
    p = patient_patch.get("17477112"); flat = patient_patch.flatten(p)
    names = json.loads(json.dumps(flat.get("names") or []))
    cur = [n for n in names if n.get("isbilling")] or names
    rec("brown", "current names %s" % [(n.get("firstname"), n.get("middlename"), n.get("lastname")) for n in names])
    if cur and cur[0].get("firstname") == "RANDY":
        rec("brown", "already RANDY - no rename")
    elif dry:
        rec("brown", "DRY would PATCH names firstname RANDY")
    else:
        for n in cur: n["firstname"] = "RANDY"
        code, txt, before = patient_patch.patch("17477112", {"names": names})
        after = patient_patch.flatten(patient_patch.get("17477112"))
        rec("brown", "PATCH %s -> names now %s" % (code, [(n.get("firstname"), n.get("lastname")) for n in after.get("names") or []]))
        x = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat17477112", "nocookie": "1"}), timeout=60)
        rec("brown", "getdemographic name=%s" % re.search(r'name="([^"]*)"', x).group(1))
    for vid, cid in (("19448269", "23357529"), ("19448235", "23357494")):
        rec("brown", "v%s/%s %s" % (vid, cid, f1(vid, cid, 1)))

# ---------------- Bull pat17477723 ----------------
if "bull" in only:
    L("-- Bull add CAP07 CHP01052326 begin 06/01/2024, admit 09/10/2026, insorder, release")
    io, pl = plans("17477723"); have = [p for p in pl if p.get("carrier") == "car41826" and not p.get("enddate")]
    if have:
        seq = have[0]["sequence"]; rec("bull", "CAP07 already on chart %s seq %s" % (have[0]["id"], seq))
    elif dry:
        seq = "1"; rec("bull", "DRY would add_ins car41826 CHP01052326 06/01/2024 (no group)")
    else:
        insid, seq = add_ins.add("17477723", "car41826", "CHP01052326", "06/01/2024"); rec("bull", "add_ins -> %s seq %s" % (insid, seq))
        if not insid: seq = None
    if seq:
        for vid, cid, code in (("19454465", "23365553", "99223"), ("19454443", "23365531", "99232")):
            rec("bull", "v%s admit %s" % (vid, set_admit(vid, code, "09/10/2026")))
            rec("bull", "v%s resave %s" % (vid, resave_full(cid, insorder=seq, onhcfa="1")))
        rec("bull", "release %s" % release(["19454465", "19454443"]))

# ---------------- Coalson pat17474210 ----------------
if "coalson" in only:
    L("-- Coalson WOLATE six HUM01 charges")
    for cid, amt, dos in (("23323286", 310, "9/29/2025"), ("23323283", 111, "9/30/2025"), ("23323448", 111, "10/1/2025"), ("23323535", 111, "10/2/2025"), ("23323620", 111, "10/3/2025"), ("23323673", 160, "10/4/2025")):
        rec("coalson", "%s %s $%s %s" % (cid, dos, amt, wo(cid, "HUM01", amt, "WOLATE", "Timely filing - DOS %s first billed 9/10/2026, Humana CO-29 - %s" % (dos, NOTE_DATE))))

# ---------------- Collins pat17477059 ----------------
if "collins" in only:
    L("-- Collins freq-1 five July BCBS visits seq 1")
    for vid, cid in (("19447727", "23356955"), ("19447678", "23356905"), ("19447677", "23356904"), ("19447879", "23357076"), ("19448232", "23357491")):
        rec("collins", "v%s/%s %s" % (vid, cid, f1(vid, cid, 1))); time.sleep(0.4)

# ---------------- Ford pat17471384 / Morrow pat44976 ----------------
if "ford" in only:
    L("-- Ford WOLATE 10/25/2025 CCM HUM01")
    for cid, amt in (("23326416", 206), ("23326417", 109)):
        rec("ford", "%s $%s %s" % (cid, amt, wo(cid, "HUM01", amt, "WOLATE", "Timely filing - DOS 10/25/2025 first billed 9/10/2026, Humana CO-29 - " + NOTE_DATE)))
if "morris" in only:
    L("-- Morrow WOLATE 10/25/2025 CCM HUM01")
    for cid, amt in (("23326386", 206), ("23326387", 109)):
        rec("morris", "%s $%s %s" % (cid, amt, wo(cid, "HUM01", amt, "WOLATE", "Timely filing - DOS 10/25/2025 first billed 9/10/2026, Humana CO-29 - " + NOTE_DATE)))

# ---------------- Morland pat17475407 ----------------
if "moore" in only:
    L("-- Morland add CAP07 CIO60023770 01/01/2026, end BCBS 12/31/2025, move Feb visits")
    io, pl = plans("17475407"); have = [p for p in pl if p.get("carrier") == "car41826" and not p.get("enddate")]
    if have:
        seq = have[0]["sequence"]; rec("moore", "CAP07 already on chart %s seq %s" % (have[0]["id"], seq))
    elif dry:
        seq = "2"; rec("moore", "DRY would add_ins car41826 CIO60023770 01/01/2026 (no group); patient insorder now %s" % io)
    else:
        insid, seq = add_ins.add("17475407", "car41826", "CIO60023770", "01/01/2026"); rec("moore", "add_ins -> %s seq %s" % (insid, seq))
        if not insid: seq = None
    bc = [p for p in pl if p.get("id") == "ins9516490"]
    if bc and bc[0].get("enddate"):
        rec("moore", "BCBS ins9516490 already ended %s" % bc[0]["enddate"])
    elif dry:
        rec("moore", "DRY would end-date ins9516490 12/31/2025")
    else:
        rec("moore", "end-date BCBS %s" % (ins_update.update("17475407", "ins9516490", enddate="12/31/2025"),))
    if seq:
        if dry: rec("moore", "DRY would set patient insorder %s" % seq)
        else:
            newid = have[0]["id"] if have else insid
            rec("moore", "patient insorder -> %s: %s" % (seq, ins_update.update("17475407", newid, sequence=str(seq))))
            io2, pl2 = plans("17475407"); rec("moore", "chart now insorder=%s plans=%s" % (io2, [(p["id"], p["carrier"], p["sequence"], p["begindate"], p["enddate"]) for p in pl2]))
        for vid, cid in (("19431787", "23338435"), ("19431884", "23338525")):
            rec("moore", "v%s resave %s" % (vid, resave_full(cid, insorder=seq, onhcfa="1")))
            rec("moore", "v%s %s" % (vid, f1(vid, cid, seq)))

# ---------------- Peterson pat17475237 ----------------
if "peterson" in only:
    L("-- Peterson freq-1 1/16/2026 99223 AET07")
    rec("peterson", "v19429563/23336090 %s" % f1("19429563", "23336090", 1))

# ---------------- Penhale pat17471681 ----------------
if "powell" in only:
    L("-- Penhale WOINS Medicare residuals, no secondary")
    for cid, amt, dos in (("23347358", 113.02, "4/21/2026"), ("23350367", 142.98, "5/17/2026")):
        rec("powell", "%s %s $%s %s" % (cid, dos, amt, wo(cid, "FLO02", amt, "WOINS", "Write off, no secondary (Humana ended 12/3/2024) - DOS %s - %s" % (dos, NOTE_DATE))))

json.dump(OUT, open("registers/board_act_0310_%s.json" % ("dry" if dry else "live"), "w"), indent=1)
L("=== done ===")
