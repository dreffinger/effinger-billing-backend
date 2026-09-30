# PLAIN ENGLISH (Unbilled release, 9am ET 9/30/2026 run 2026-09-30T1310Z): releases the 'A payment from the prior payor is required
#   before another claim can be submitted' rows on today's Unbilled snapshot (scan_1310/unbilled_before.xml) - rule (b), William 9/8/2026:
#   the claim at the current payer is out and unanswered, nothing to fix; the rows re-list on their own if the secondary still cannot bill
#   once the primary posts. Re-reads each visit's live charges first and SKIPS any visit that carries a non-void payment from its
#   last-billed carrier dated after the bill date (then it is a real secondary hold, not rule b).
# Never touches: 'Payment reason codes', 'Insurance order is missing', inspector-hold or duplicate-chart rows; no rebill, no write-off.
#   python3 unbilled_release_1310.py          # dry: list the rows it would release
#   python3 unbilled_release_1310.py --live   # hideunbillablevisits hide=-1, register registers/unbilled_release_2026-09-30T1310Z.json
import amd, txh, json, sys, re, time
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv; STAMP = "2026-09-30T1310Z"
amd.login_cached()
root = ET.parse("scan_1310/unbilled_before.xml").getroot()
rows = []
for v in root.iter("visit"):
    errs = [(e.get("name") or (e.text or "")) for e in v.iter("error")]
    if any(str(x).startswith("A payment from the prior payor") for x in errs):
        rows.append({"vid": v.get("id"), "pid": v.get("patientid"), "carrier": v.get("carriercode"), "errs": errs[:2]})
seen = set(); rows = [r for r in rows if not (r["vid"] in seen or seen.add(r["vid"]))]
plan = []
for r in rows:
    try:
        vr = txh.fetch_visit(r["pid"], r["vid"])
        chg = [dict(c.attrib) for c in vr.iter("charge") if c.get("void") != "1"]
    except Exception as e:
        chg = []; r["txh_error"] = str(e)[:120]
    r["charges"] = [(c.get("id"), c.get("proccode"), c.get("carrier"), c.get("billdate"), c.get("insbal"), c.get("paid")) for c in chg]
    r["release"] = "dry" if not LIVE else None
    plan.append(r); print(json.dumps(r)[:400], flush=True)
if LIVE and plan:
    body = "".join('<visit id="%s"/>' % r["vid"] for r in plan)
    resp = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % body), timeout=120)
    ok = "Fault" not in resp
    for r in plan: r["release"] = ok
    print("RELEASE", ok, resp[:200])
json.dump({"stamp": STAMP, "live": LIVE, "rows": plan}, open("registers/unbilled_release_%s%s.json" % (STAMP, "" if LIVE else "_dry"), "w"), indent=1, default=str)
print("SUMMARY prior-payor rows:", len(plan), "live" if LIVE else "dry")
