# PLAIN ENGLISH (Exclusions pass, 5pm ET 9/23/2026 run 2026-09-23T2110Z): one NEW exclusion row on claim run 1700229 - UHC (UNI20) answered
#   a payer-level 277 rejection 'ACK/REJECTED ... DUPLICATE OF A PREVIOUSLY PROCESSED CLAIM, LINE' on the CCM 99487 of 8/23/2026
#   (visit 19452663, claim letter C = the third send). Standing rule: duplicate-claim rejections are COMPLETED, never rebilled - the payer
#   already holds the claim. The two PDTP0303 rows (pat17472517 v19423193, pat20863 v19445850) stay held (no 99223 anchor within 45 days).
# Decides: reads the visit's live charges/payments (gettxhistory) for the record, then hideexclusions for the duplicate row only.
# Never touches: payments, write-offs, rebills, insurance plans, the two held rows.
import amd, txh, re, json, time, datetime, sys
STAMP = "2026-09-23T2110Z"; DRY = "--dry" in sys.argv
out = {"stamp": STAMP, "rows": []}
pid, vid, claim, run = "12182506", "19452663", "19452663C", "1700229"
root = txh.fetch_visit(pid, vid)
chg = []
for c in root.iter():
    if c.tag.lower() in ("charge", "chargedetail", "visit") and c.get("proccode"):
        chg.append({k: c.get(k) for k in ("id", "proccode", "dos", "fee", "insbal", "patbal", "paid", "carrier", "billdate", "payerinfo") if c.get(k) is not None})
    if c.tag.lower() == "payment":
        chg.append({"payment": {k: c.get(k) for k in ("id", "date", "amount", "checknumber", "carrier", "void", "paymentcode") if c.get(k) is not None}})
print("live:", json.dumps(chg))
out["rows"].append({"pid": pid, "vid": vid, "claim": claim, "run": run, "carrier": "UNI20", "error": "PA ACK,REJCTD ... DUPLICATE OF A PREVIOUSLY PROCESSED CLAIM, LINE", "live": chg,
                    "action": "complete (duplicate-claim rejection rule) - no rebill"})
if not DRY:
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, '<visitlist><visit id="%s" claimid="%s"/></visitlist>' % (vid, claim)))
    ok = "Fault" not in r
    print("hideexclusions run %s %s -> %s" % (run, claim, "ok" if ok else re.sub(r"\s+", " ", r[:300])))
    out["rows"][-1]["completed"] = ok
out["held"] = [{"pid": "17472517", "vid": "19423193", "claim": "19423193H", "carrier": "HUM01", "amt": "70.17", "why": "PDTP0303 - no 99223 anchor within 45 days (standing hold)"},
               {"pid": "20863", "vid": "19445850", "claim": "19445850B", "carrier": "FLO99", "amt": "14.38", "why": "PDTP0303 - no 99223 anchor within 45 days (standing hold)"}]
json.dump(out, open("registers/excl_%s.json" % STAMP, "w"), indent=1)
print("DONE")
