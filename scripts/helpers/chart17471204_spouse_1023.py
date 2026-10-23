#!/usr/bin/env python3
# PLAIN ENGLISH (chart 17471204, William's facesheet paste 10/23/2026: the Aetna plan's subscriber is the patient's SPOUSE)
# Decides: nothing new. The chart's AET07 plan (seq 2, W262669676) already points at the spouse's responsible-party record but still
#   carries relationship SELF (hipaarelationship 18) - that is why Aetna answers 'ENTITY NOT ELIGIBLE ... PATIENT' (the patient was
#   sent as the member). The captured updateinsurance wrapped shape sets hipaarelationship 01 = SPOUSE on the plan (read back), the
#   three HCA visits of run 1700311 get ONE frequency-1 rebill each on seq 2 (visit order already 2), the three exclusion rows are
#   completed and the run re-listed. No captured call writes a responsible party's DOB/sex/address, so the subscriber record stays
#   as it is (reported to William).
#   python3 chart17471204_spouse_1023.py            # dry
#   python3 chart17471204_spouse_1023.py --live
import amd, ins_update, resave, freq1_visit, json, re, sys, time, datetime
import xml.etree.ElementTree as ET

LIVE = "--live" in sys.argv
PID = "17471204"; PLAN = "ins9510367"; SEQ = "2"; RUN = "1700311"
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
REG = {"run": STAMP, "live": LIVE, "pid": PID, "visits": []}
amd.login_cached()

def plan_attrs():
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": PID, "nocookie": "1"}))
    for t in re.findall(r'<insplan [^>]*>', r):
        a = dict(re.findall(r'(\w+)="([^"]*)"', t))
        if a.get("id") == PLAN:
            return {k: a.get(k) for k in ("id", "sequence", "carrier", "subscribernum", "subscriber", "relationship", "hipaarelationship", "enddate")}
    return None

REG["plan_before"] = plan_attrs(); print("plan before:", REG["plan_before"])

y = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": RUN, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
root = ET.fromstring(y.encode("latin-1", "ignore"))
rows = []
for v in root.iter("visit"):
    if re.sub(r"\D", "", v.get("patientid") or "") != PID:
        continue
    rows.append({"vid": v.get("id"), "claimid": v.get("claimid"), "carrier": v.get("carriercodeshort"), "cids": [c.get("id") for c in v.iter("charge")]})
print("run %s rows for chart %s: %s" % (RUN, PID, rows)); REG["rows"] = rows
KNOWN = [{"vid": "19431511", "claimid": None, "carrier": "AET07", "cids": ["23338125"]},   # the three HCA visits of the board row
         {"vid": "19435174", "claimid": None, "carrier": "AET07", "cids": ["23342168"]},
         {"vid": "19435175", "claimid": None, "carrier": "AET07", "cids": ["23342169"]}]
EXCL_ROWS = list(rows)
if not rows:
    print("run %s no longer lists this chart (completed outside this session) - working the three known visits" % RUN); rows = KNOWN

def billdates():
    body = amd.msg("gettxhistory", "demographics", {"patientid": PID, "filterhistory": "0", "pagenumber": "1", "typefilter": "0", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "profileid": "", "getmemo": "false", "nocookie": "1"})
    th = ET.fromstring(amd.post(body, timeout=120).encode("latin-1", "ignore"))
    return {re.sub(r"\D", "", c.get("id") or ""): c.get("billdate") for c in th.iter("charge")}

def state(cid):
    rt = ET.fromstring(resave.detail(cid)); vis = rt.find(".//visit"); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
    e = vis.find("extins")
    return {"insorder": vis.get("insorder"), "billdate": billdates().get(cid), "insbalance": c.get("insbalance"), "void": c.get("void"),
            "resub": e.get("resubmissioncode") if e is not None else None}

if LIVE and rows and (REG["plan_before"] or {}).get("hipaarelationship") == "01":
    REG["plan_after"] = REG["plan_before"]; print("plan already reads SPOUSE (relationship 2 / hipaarelationship 01) - no write")
elif LIVE and rows:
    ok, m = ins_update.update(PID, PLAN, hipaarelationship="01")
    REG["relationship_write"] = (ok, m[:300]); print("hipaarelationship -> 01:", ok, m[:200])
    time.sleep(0.5)
    REG["plan_after"] = plan_attrs(); print("plan after:", REG["plan_after"])
    if not (ok and REG["plan_after"] and REG["plan_after"].get("hipaarelationship") == "01"):
        print("STOP - the plan does not read back as spouse; nothing rebilled"); rows = []

for row in rows:
    rec = dict(row); rec["before"] = {c: state(c) for c in row["cids"]}
    print("visit %s claim %s %s before %s" % (row["vid"], row["claimid"], row["carrier"], rec["before"]))
    if not LIVE:
        rec["plan"] = "freq1_visit.run(vid, cid, %s) - visit order already %s" % (SEQ, rec["before"][row["cids"][0]]["insorder"]); REG["visits"].append(rec); continue
    if (rec["before"][row["cids"][0]]["billdate"] or "") == datetime.date.today().strftime("%m/%d/%Y"):
        rec["freq1"] = "SKIPPED - billdate already today (re-sent by someone else)"; print("   ", rec["freq1"]); REG["visits"].append(rec); continue
    vo = (rec["before"][row["cids"][0]]["insorder"] or "").replace(" ", "")
    if vo != SEQ:
        okx, mx = resave.set_insorder(row["cids"][0], SEQ); rec["set_insorder"] = (okx, mx[:200]); print("   set_insorder", okx, mx[:160])
        if not okx:
            REG["visits"].append(rec); continue
        time.sleep(0.5)
    res = freq1_visit.run(row["vid"], row["cids"][0], SEQ); rec["freq1"] = str(res)[:300]; print("   ", res)
    time.sleep(0.6)
    rec["after"] = {c: state(c) for c in row["cids"]}; print("   after", rec["after"])
    REG["visits"].append(rec)

if LIVE and EXCL_ROWS and all("204" in (v.get("freq1") or "") for v in REG["visits"]):
    lst = "".join('<visit id="%s" claimid="%s"/>' % (r["vid"], r["claimid"]) for r in EXCL_ROWS)
    x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % lst), timeout=120)
    REG["hideexclusions"] = re.sub(r"\s+", " ", x[:200]); print("hideexclusions ->", REG["hideexclusions"])
    time.sleep(1)
    y2 = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": RUN, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
    left = re.findall(r'<visit [^>]*\bid="(\d+)"', y2); REG["relist"] = left; print("re-list run %s: %d left" % (RUN, len(left)))
elif LIVE and not EXCL_ROWS:
    print("no exclusion rows to complete")
elif LIVE:
    print("exclusions NOT completed - a rebill did not answer 204")
json.dump(REG, open("registers/tolliver_spouse_%s%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1)
print("register written")
