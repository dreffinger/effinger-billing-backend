#!/usr/bin/env python3
# PLAIN ENGLISH (chart 17470713, William 10/23/2026 04:20Z board answer: no AARP plan at all - the 25 coinsurance balances go to the
#   patient statement cycle, no secondary)
# Decides: nothing new. End-dates the chart's AARP plan (no such plan exists), keeps the chart order on Medicare, and for every
#   AAR01-excluded visit of claim run 1700302 sets the visit order to Medicare alone (full-visit echo, no portions touched - the
#   9/22 lesson), then posts a $0 Medicare payment (addpayments, no write-off) so AMD moves the coinsurance that remains after the
#   final payer to the PATIENT balance (the 9/18 behaviour: AMD transfers whatever is left after the last insurance's payment),
#   reads the balances back, and completes the 25 exclusion rows (hideexclusions). The first visit is done alone and verified
#   before the rest. No write-off tonight: the no-pay write-off follows the statement cycle (Alcott precedent 10/4).
#   python3 chart17470713_nosec_1023.py            # dry
#   python3 chart17470713_nosec_1023.py --live
import amd, ins_update, resave, manual_post, json, re, sys, time, datetime
import xml.etree.ElementTree as ET

LIVE = "--live" in sys.argv
PID = "17470713"; AARP = "ins9520543"; MEDICARE_SEQ = "3"; RUN = "1700302"
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
TODAY = datetime.date.today().strftime("%m/%d/%Y")
REG = {"run": STAMP, "live": LIVE, "pid": PID, "visits": []}
amd.login_cached()

# 1. the excluded rows of run 1700302 (visit + claim ids + charge ids)
y = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": RUN, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
root = ET.fromstring(y.encode("latin-1", "ignore"))
rows = []
for v in root.iter("visit"):
    if re.sub(r"\D", "", v.get("patientid") or "") != PID or v.get("carriercodeshort") != "AAR01":
        continue
    cids = [c.get("id") for c in v.iter("charge")]
    rows.append({"vid": v.get("id"), "claimid": v.get("claimid"), "cids": cids})
print("run %s AAR01 rows for chart %s: %d" % (RUN, PID, len(rows)))
REG["rows"] = rows

def balances(cid):
    rt = ET.fromstring(resave.detail(cid)); c = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid][0]
    vis = rt.find(".//visit")
    return {"insbalance": c.get("insbalance"), "patbalance": c.get("patbalance"), "insorder": vis.get("insorder"), "void": c.get("void")}

def work(row, first=False):
    rec = dict(row); rec["before"] = [balances(c) for c in row["cids"]]
    print("visit %s charges %s before %s" % (row["vid"], row["cids"], rec["before"]))
    if not LIVE:
        rec["plan"] = "set_insorder %s; $0 FLO02 payment per charge with insbalance > 0; readback" % MEDICARE_SEQ; return rec
    ok, m = resave.set_insorder(row["cids"][0], MEDICARE_SEQ); rec["set_insorder"] = (ok, m[:160]); print("   set_insorder:", ok, m[:120])
    if not ok:
        return rec
    time.sleep(0.4)
    posts = []
    for cid in row["cids"]:
        b = balances(cid)
        if float(b["insbalance"] or 0) <= 0:
            posts.append((cid, "skip - no insurance balance", b)); continue
        r = manual_post.post(cid, "FLO02", 0.0, 0.0, "WOINS", "NOSEC1023", TODAY, "no secondary (William 10/23) - balance to patient statement")
        time.sleep(0.5)
        after = balances(cid)
        posts.append((cid, str(r)[:160], after)); print("   $0 post %s -> %s | after %s" % (cid, str(r)[:100], after))
    rec["posts"] = posts
    return rec

if rows:
    if LIVE:
        ok, m = ins_update.update(PID, AARP, enddate="01/01/2026"); print("AARP plan end-dated:", ok, m[:160]); REG["aarp_enddate"] = (ok, m[:200])
        ok2, m2 = ins_update.update(PID, "ins9519283", sequence=MEDICARE_SEQ); print("chart order ->", MEDICARE_SEQ, ok2, m2[:160]); REG["chart_order"] = (ok2, m2[:200])
    first = work(rows[0], first=True); REG["visits"].append(first)
    moved = LIVE and any(p[2].get("patbalance") not in (None, "0.00", "0") and float(p[2].get("insbalance") or 0) == 0 for p in first.get("posts", []) if isinstance(p[2], dict))
    print("FIRST VISIT transferred to patient:", moved)
    if LIVE and not moved:
        print("STOP - the $0 Medicare post did not move the balance to the patient; nothing else touched")
    else:
        for row in rows[1:]:
            REG["visits"].append(work(row))
        if LIVE:
            lst = "".join('<visit id="%s" claimid="%s"/>' % (r["vid"], r["claimid"]) for r in rows)
            x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % lst), timeout=120)
            REG["hideexclusions"] = re.sub(r"\s+", " ", x[:200]); print("hideexclusions ->", REG["hideexclusions"])
            time.sleep(1)
            y2 = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": RUN, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
            left = re.findall(r'<visit [^>]*\bid="(\d+)"', y2); REG["relist"] = left; print("re-list run %s: %d left" % (RUN, len(left)))
json.dump(REG, open("registers/poulter_nosec_%s%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1)
print("register written")
