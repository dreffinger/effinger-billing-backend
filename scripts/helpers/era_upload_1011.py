# PLAIN ENGLISH (835 upload with a processed-check guard - 1 AM ET 10/11/2026 run 2026-10-11T0510Z)
# Decides: which of the 835 files William dropped in Drive 'bht Optum era downloads' (downloaded to inbox/era_1011/) are NEW to
#   AMD's ERA Center and uploads only those (POST /api/era/upload/835, the shape era_upload.py captured 9/2/2026). A file whose
#   TRN check number is already on the UNPOSTED list, on the DISMISSED list (GET /api/era/checks/dismiss since 8/1/2026 - a
#   fully posted or dismissed check leaves the unposted list and must never be uploaded twice: the Post button would post it again),
#   in the era_manual_register, or seen earlier in this run is skipped. Duplicate downloads of the same check ("(1)" copies) count once.
# Never touches: posting, dismissing, any chart. Register registers/era_upload_2026-10-11T0510Z.json
#   python3 era_upload_1011.py          # dry: lists new / skipped
#   python3 era_upload_1011.py --live   # uploads the new ones
import amd, era_upload, payreasons, json, os, re, sys, glob, time
LIVE = "--live" in sys.argv; S = "2026-10-11T0510Z"; D = "inbox/era_1011"
amd.login_cached()
unposted = {c.get("paymentnumber"): c.get("id") for c in era_upload.checks()}
dismissed = {v.get("paymentnumber"): k for k, v in payreasons.dismissed_index().items()}
manual = set()
try:
    for r in json.load(open("registers/era_manual_register.json")): manual.add(str(r.get("checkno") or ""))
except Exception: pass
reg = {"stamp": S, "live": LIVE, "unposted_before": len(unposted), "dismissed_known": len(dismissed), "files": []}
seen = set()
for f in sorted(glob.glob(os.path.join(D, "*.dat"))):
    try: head = open(f, encoding="latin-1").read(3)
    except Exception: continue
    if head != "ISA": reg["files"].append({"file": os.path.basename(f), "skip": "not an X12 file"}); continue
    n, amt = era_upload.trn(f)
    rec = {"file": os.path.basename(f), "trn": n, "amount": amt}
    if not n: rec["skip"] = "no TRN"
    elif n in seen: rec["skip"] = "duplicate download of a check already handled this run"
    elif n in unposted: rec["skip"] = "already on the unposted list (check %s)" % unposted[n]
    elif n in dismissed: rec["skip"] = "already processed/dismissed in the ERA Center (check %s)" % dismissed[n]
    elif n in manual: rec["skip"] = "check number in era_manual_register"
    else:
        seen.add(n)
        if LIVE:
            code, text = era_upload.upload(f); rec["upload"] = {"status": code, "text": re.sub(r"\s+", " ", text)[:200]}; time.sleep(1.0)
        else: rec["upload"] = "DRY would upload"
    reg["files"].append(rec); print(json.dumps(rec), flush=True)
if LIVE:
    time.sleep(3)
    after = era_upload.checks(); reg["unposted_after"] = len(after)
    reg["unposted_after_total"] = round(sum(float(c.get("checkoreftamount") or c.get("checkamount") or 0) for c in after), 2)
    print("unposted after:", reg["unposted_after"], "checks")
json.dump(reg, open("registers/era_upload_%s.json" % S, "w"), indent=1)
print("saved registers/era_upload_%s.json" % S, "new:", sum(1 for r in reg["files"] if "upload" in r), "skipped:", sum(1 for r in reg["files"] if "skip" in r))
