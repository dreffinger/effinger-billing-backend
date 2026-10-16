# PLAIN ENGLISH (Exclusions pass, 1 AM ET 10/16/2026 slot - run 2026-10-16T0510Z)
# Decides: nothing new - it applies the standing exclusion rules to the 17 rows on claim runs 1700302 / 1700305 read at 05:2xZ:
#   A  chart 17478013 (run 1700305, 8 VA CCN rows PNM10902 'INVALID SUBSCRIBER MEMBER ID'): the VA CCN plan ins9520862 carries the
#      literal placeholder "[ICN]" as its member id (the 10/15 cascade session ran a PHI-scrubbed copy of unbilled_1015_0510.py);
#      the real VA ICN is on William's 10/15 board note and sits in patient_db/17478013/ids.json (never in this file). Write it on
#      the plan (updateinsurance subscribernum, patient order restored by ins_update), then ONE frequency-1 rebill per visit to
#      sequence 1 (clearinghouse front-end rejection - the claims never reached the payer), then hideexclusions for the 8 rows.
#   B  chart 17475064 (run 1700302, 6 Aetna AET07 secondary rows 'SUBSCRIBER AND SUBSCRIBER ID NOT FOUND', Jan-Feb 2026, Medicare paid):
#      RULE C cascade answered: AMD 271 both plans INACTIVE (Medicare: date of death [DOB]), Stedi insurance discovery at the
#      DOS = Aetna 'Choice POS II' ACTIVE with a DIFFERENT member id (patient_db/17475064/ids.json). Write that id on ins9516382,
#      ONE frequency-1 rebill per visit to sequence 1, hideexclusions for the 6 rows. No money moves.
#   C  charts 46253 (v13965945, 99349 01/30/2023) and 20804 (v14003195, 99350 04/27/2023), run 1700302, Aetna AET07 secondary
#      leftovers whose Medicare remit is older than 12 months (05/2023, 07/2023): the secondary window is closed - WOINS untimely
#      (check UNTIMELY1016, dated note) on each charge's live open insurance balance, then hideexclusions (the 10/15 card P rule).
# Rules it uses: one rebill per visit (amd.rebill_charge guard + deceased guard), never a rebill of a visit that carries the
#   payer's own payment (these carry only the PRIMARY's payment - the secondary is the one re-sent), member ids read at run time
#   from patient_db/ (PHI stays in the workspace), a charge whose live balance is 0 is skipped, one hideexclusions call per run.
# Never touches: payments (except the WOINS in C), plans other than the two named, visits other than the 17 listed.
# Usage: python3 excl_1016_0510.py --dry | --live [--only A|B|C]      register: registers/excl_1016_0510[_dry].json
import amd, resave, ins_update, freq1_visit, manual_post, json, sys, re, time, datetime
import xml.etree.ElementTree as ET
a = sys.argv[1:]; LIVE = "--live" in a; ONLY = a[a.index("--only") + 1] if "--only" in a else None
STAMP = "2026-10-16T0510Z"; TODAY = datetime.date.today().strftime("%m/%d/%Y")
REG = {"stamp": STAMP, "live": LIVE, "A": [], "B": [], "C": [], "hidden": {}}
def save(): json.dump(REG, open("registers/excl_1016_0510%s.json" % ("" if LIVE else "_dry"), "w"), indent=1)
def S(sec, *m): print(sec, *m, flush=True)
def num(s): return re.sub(r"\D", "", str(s or ""))
amd.login_cached()
to_hide = {}

def plan_sub(pid, insid):
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}))
    for p in re.findall(r"<insplan [^>]*>", r):
        d = dict(re.findall(r'(\w+)="([^"]*)"', p))
        if d.get("id") == insid: return d.get("subscribernum", ""), (re.search(r'<patient [^>]*insorder="([^"]*)"', r) or [None, None])[1]
    return None, None

def fix_member_id(sec, pid, insid, want, order_want):
    cur, order = plan_sub(pid, insid)
    rec = {"pid": pid, "insid": insid, "before_len": len(cur or ""), "placeholder": cur == "[ICN]", "order_before": order}
    if cur == want:
        rec["result"] = "already set"; S(sec, "member id already correct on", insid); REG[sec].append(rec); return True
    if not LIVE:
        rec["result"] = "DRY would updateinsurance subscribernum (len %d) and keep order %s" % (len(want), order_want); S(sec, rec["result"]); REG[sec].append(rec); return True
    ok, msg = ins_update.update(pid, insid, subscribernum=want)
    rec["update"] = (ok, msg[:200]); time.sleep(0.5)
    cur2, order2 = plan_sub(pid, insid)
    rec["after_ok"] = (cur2 == want); rec["order_after"] = order2
    if order2 is not None and order2.replace(" ", "") != order_want.replace(" ", ""):
        ok3, m3 = ins_update.update(pid, insid, sequence=order_want); rec["order_fix"] = (ok3, m3[:160]); time.sleep(0.5)
        cur2, order2 = plan_sub(pid, insid); rec["order_after"] = order2
    S(sec, "member id written:", rec["after_ok"], "| order", order, "->", order2, "|", msg[:120]); REG[sec].append(rec); save()
    return rec["after_ok"]

def rebill_all(sec, pid, run, rows, seq):
    for vid, cid, claimid in rows:
        if not LIVE:
            S(sec, "DRY would freq1 + rebill v%s charge %s seq %s, then hide %s/%s" % (vid, cid, seq, run, claimid)); REG[sec].append({"vid": vid, "cid": cid, "dry": True}); continue
        res = freq1_visit.run(vid, cid, seq); S(sec, "v%s" % vid, res[:160]); REG[sec].append({"vid": vid, "cid": cid, "rebill": res[:200]}); save()
        if "FAULT" in res or "409" in res or "BLOCKED" in res: S(sec, "NOT hidden (rebill failed) v%s" % vid); continue
        to_hide.setdefault(run, []).append((vid, claimid)); time.sleep(0.6)

ids13 = json.load(open("patient_db/17478013/ids.json")); ids64 = json.load(open("patient_db/17475064/ids.json"))

# A - chart 17478013: VA CCN member id + 8 rebills seq 1 (run 1700305)
if ONLY in (None, "A"):
    rowsA = [("19457280", "23369137", "19457280A"), ("19457281", "23369138", "19457281A"), ("19457321", "23369178", "19457321A"),
             ("19457471", "23369378", "19457471A"), ("19457476", "23369383", "19457476A"), ("19457519", "23369447", "19457519A"),
             ("19457529", "23369457", "19457529A"), ("19457647", "23369559", "19457647A")]
    if fix_member_id("A", "17478013", "ins9520862", ids13["vaccn_subscribernum"], "1") or not LIVE:
        rebill_all("A", "17478013", "1700305", rowsA, 1)
    else: S("A", "member id NOT written - no rebill, rows left open")

# B - chart 17475064: Aetna member id from discovery + 6 secondary rebills seq 1 (run 1700302)
if ONLY in (None, "B"):
    rowsB = [("19428140", "23334604", "19428140E"), ("19429862", "23336335", "19429862E"), ("19430966", "23337522", "19430966E"),
             ("19430967", "23337523", "19430967E"), ("19432541", "23339103", "19432541E"), ("19432986", "23339606", "19432986E")]
    if fix_member_id("B", "17475064", "ins9516382", ids64["aet07_subscribernum"], "2") or not LIVE:
        rebill_all("B", "17475064", "1700302", rowsB, 1)
    else: S("B", "member id NOT written - no rebill, rows left open")

# C - 2023 Aetna secondary leftovers: WOINS untimely + complete (run 1700302)
if ONLY in (None, "C"):
    for pid, vid, cid, claimid, remit in (("46253", "13965945", "20964737", "13965945D", "05/04/2023"), ("20804", "14003195", "21330142", "14003195B", "07/13/2023")):
        rt = ET.fromstring(resave.detail(cid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
        bal = float(c.get("insbalance") or 0); rec = {"pid": pid, "vid": vid, "cid": cid, "insbalance": bal}
        if bal <= 0.004: rec["result"] = "balance already 0 - complete only"; S("C", "v%s balance 0" % vid)
        else:
            note = "WOINS untimely %s: Aetna secondary rejected 'ACK returned as unprocessable' on run 1700302 (10/14/2026 resend); Medicare remit %s is older than 12 months - secondary filing window closed (excl_1016_0510 C)" % (TODAY, remit)
            ok, msg = manual_post.post(cid, "AET07", 0.0, round(bal, 2), "WOINS", "UNTIMELY1016", None, note, dry=not LIVE)
            rec["woins"] = (ok, str(msg)[:200]); S("C", "v%s WOINS %.2f ->" % (vid, bal), ok, str(msg)[:120])
            if LIVE and not ok: REG["C"].append(rec); save(); continue
        REG["C"].append(rec); save(); to_hide.setdefault("1700302", []).append((vid, claimid))

for run, items in to_hide.items():
    child = "<visitlist>" + "".join('<visit id="%s" claimid="%s"/>' % (vv, cl) for vv, cl in items) + "</visitlist>"
    if not LIVE: REG["hidden"][run] = {"n": len(items), "dry": True, "visits": [v for v, _ in items]}; continue
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, child))
    REG["hidden"][run] = {"n": len(items), "ok": "Fault" not in r, "resp": re.sub(r"\s+", " ", r[:160])}; time.sleep(0.5)
save()
print("SUMMARY live=%s only=%s A=%d B=%d C=%d hidden=%s" % (LIVE, ONLY, len(REG["A"]), len(REG["B"]), len(REG["C"]), {k: v.get("n") for k, v in REG["hidden"].items()}))
