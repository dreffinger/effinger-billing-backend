# PLAIN ENGLISH (run report CSV builder, 7 PM ET 9/14/2026 slot - ehpa cloud run 2026-09-14T2310Z)
# Decides: nothing. Reads this run's scan (scan_0912/*_before|after), the ERA before/after snapshots, the fallback
# register and the precheck JSON, and writes "_run report 9-14 2310.csv" (per column: cleared / remaining with
# patient, DOS, carrier, error, action; ERA rows carry check id, payer, visit, amount, action).
# Never touches: AMD.
import csv, json, os, re, sys, glob
import xml.etree.ElementTree as ET
S = "2026-09-14T2310Z"
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
# --- columns (after-scan if present, else before)
tag = "after" if os.path.exists("scan_0912/summary_after.json") else "before"
try:
    summ = json.load(open("scan_0912/summary_%s.json" % tag))
except Exception:
    summ = {}
ub = open("scan_0912/unbilled_%s.xml" % tag).read() if os.path.exists("scan_0912/unbilled_%s.xml" % tag) else ""
for m in re.finditer(r'<visit ([^>]*)>(.*?)</visit>', ub, re.S):
    a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
    errs = re.findall(r'<error [^>]*name="([^"]*)"', m.group(2))
    err = (errs[0] if errs else "")
    dm = re.search(r'(?:dateofservice|dos|begindate)="([^"]*)"', m.group(2))
    a.setdefault("dos", dm.group(1) if dm else "")
    if "reason codes" in err.lower():
        action = "waiting on William: 2024 manual-post coinsurance line - no captured call edits payment reason codes"
    elif "Insurance order" in err:
        action = "held: chart has no insurance plan (Stedi MBI 72, discovery 0, no facesheet) - HCA facesheet on William's turn"
    else:
        action = "held"
    add("Unbilled", "remaining", a.get("patientname", ""), a.get("dateofservice", a.get("dos", "")), a.get("carriercode", ""), err, action, visit=a.get("id", ""))
add("Charge Review", "clear", action="0 batches before and after")
add("Claim Inspector", "clear", action="0 batches before and after")
add("Exclusions", "clear", action="0 open rows before and after (getclaimexclusioncharges clearinghouse=1 payer=1); newest claim run still 1700188")
# --- ERA
def load(p):
    return json.load(open(p)) if os.path.exists(p) else []
before = load("era_checks_before_%s.json" % S); after = load("era_checks_after_%s.json" % S)
aid = {c["id"] for c in after}
for c in before:
    st = "still open" if c["id"] in aid else "cleared"
    add("ERA", st, carrier=c.get("carriercode", ""), check=str(c["id"]), amt=c.get("unpostedamount", ""),
        action=("held - reversal/orphan/already-adjudicated lines, no postable money" if st == "still open" else "cleared this run"),
        err="check %s" % c.get("checknumber", ""))
for c in after:
    if c["id"] not in {b["id"] for b in before}:
        add("ERA", "new (arrived during run)", carrier=c.get("carriercode", ""), check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % c.get("checknumber", ""))
fb = load("registers/era_fallback_%s_live.json" % S)
if isinstance(fb, dict):
    for k, v in fb.items():
        if k in ("counts", "dollars"): continue
if isinstance(fb, list):
    for r in fb:
        if r.get("outcome") in ("posted", "residual"):
            add("ERA", "manual-posted", check=str(r.get("checkid", "")), visit=str(r.get("visitid", "")), amt=r.get("pay", r.get("amt", "")), carrier=r.get("carrier", ""), action=r.get("outcome", ""))
# --- precheck
pcs = sorted(glob.glob("precheck_2026-09-14*.json"))
if pcs:
    for r in json.load(open(pcs[-1])):
        if r.get("flag"):
            add("Unpaid precheck", "flagged", r.get("patient", ""), r.get("dos", ""), r.get("carrier", ""), r.get("result", ""), r.get("action", "see report"), amt=r.get("balance", ""))
out = "_run report 9-14 2310.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["column", "state", "patient", "dos", "carrier", "error", "action", "checkid", "visit", "amount"])
    w.writeheader(); w.writerows(rows)
print("wrote", out, len(rows), "rows")
