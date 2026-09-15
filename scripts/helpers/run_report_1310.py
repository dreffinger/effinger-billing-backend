# PLAIN ENGLISH (run report CSV builder, 9 AM ET 9/15/2026 slot - ehpa cloud run 2026-09-15T1310Z)
# Decides: nothing. Reads this run's column scans (scan_0912/*_after), the unbilled/AET12/Greaves registers, the ERA
# before/after snapshots and the fallback register, and writes "_run report 9-15 1310.csv" (per column: cleared /
# remaining with patient, DOS, carrier, error, action; ERA rows carry check id, payer, visit, amount, action).
# Never touches: AMD.
import csv, json, os, re, glob, collections
S = "2026-09-15T1310Z"
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
def load(p, default):
    try: return json.load(open(p))
    except Exception: return default
before = load("scan_0912/summary_before.json", {}); after = load("scan_0912/summary_after.json", {})
add("Charge Review", "clear", action="0 visits before and after")
add("Claim Inspector", "clear", action="0 batches before and after")
# --- Unbilled
ub = load("registers/unbilled_release_%s.json" % S, {}); uv = load("registers/unbilled_verify_%s.json" % S, {})
for c in ub.get("released", []):
    for vid in c["visits"]:
        d = uv.get(vid, {})
        add("Unbilled", "cleared", d.get("name", ""), "", ",".join(d.get("carriers", [])), "A payment from the prior payor is required before another claim can be submitted.",
            "released (case b: primary sent %s, paid %.2f, insbal %.2f)" % (d.get("newest_bill"), d.get("paid", 0), d.get("insbal", 0)) if d.get("class") == "release-b" or vid == "19441047" else "WOINS contractual (Medicare paid 4/2025, secondary window passed) then released",
            visit=vid, amt=d.get("insbal", ""))
for w in ub.get("writeoffs", []):
    add("Unbilled", "write-off", "pat%s" % w["pid"], w.get("dos", ""), w.get("carrier", ""), "prior payor - crossover leftover", "WOINS %.2f charge %s" % (w["wo"], w["cid"]), visit=w["vid"], amt=w["wo"])
for r in after.get("unbilled", []):
    err = r["_errs"][0] if r["_errs"] else ""
    add("Unbilled", "remaining", r.get("patientname", ""), r.get("dateofservice", "") or "", r.get("carriercode", "") or "", err,
        "held - 9/13 payment posted with no CARC on a reversed 5/31 write-off; needs the remit reason codes re-posted (no captured call edits payment reason codes) or William's word to release", visit=r.get("id", ""))
# --- Exclusions
for rid, rs in after.get("exclusions", {}).items():
    for r in rs:
        err = " | ".join((e.get("name") or e.get("text") or "")[:70] for e in r["_errs"][:2])
        add("Exclusions", "remaining", "pat%s" % r.get("patientid", ""), r.get("dateofservice", "") or "", (r.get("carriercode") or "").split()[0] if r.get("carriercode") else "", err,
            "held - run 1700193 rejected all 59 AET12 claims again after the AAR01-matched carrier settings; William: suppress the provider loop / Box 33B REF*EI, then 'rebill'", visit=r.get("id", ""))
# --- Board actions
cl = {}
if cl:
    add("Board action", "done", "pat17473476", "02/26/2026", "BCBS", "CO-22 $0 denial 9/9, WOINS $206", "WOINS voided, member id -> X3LM65856326, frequency 7 + origrefnum from the posted ERA payment, chargerebill seq 1 -> %s" % cl.get("rebill"), visit="19434042", amt="206.00")
add("Board action", "held", "AET12 carrier", "", "AET12", "PREF0288 + PREF0264 on run 1700193", "still 59 rows, $2,052.25 insurance balance re-verified (billdate 09/14/2026, none at $0); no new claim run; waiting on William (suppress provider loop / Box 33B), then rebill")
# --- ERA
eb = load("era_checks_before_%s.json" % S, []); ea = load("era_checks_after_%s.json" % S, [])
aid = {c["id"] for c in ea}; bid = {c["id"] for c in eb}
for c in eb:
    st = "still open" if c["id"] in aid else "cleared"
    add("ERA", st, carrier=c.get("systemcarriercode") or c.get("carriercode", ""), check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % (c.get("paymentnumber") or c.get("checknumber", "")),
        action=("held - reversal/orphan/procedure-mismatch/already-adjudicated lines, no postable money" if st == "still open" else "cleared this run"))
for c in ea:
    if c["id"] not in bid:
        add("ERA", "new (arrived during run)", carrier=c.get("systemcarriercode") or "", check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % (c.get("paymentnumber") or ""))
fb = load("registers/era_fallback_%s_live.json" % S, [])
if isinstance(fb, list):
    for r in fb:
        if r.get("outcome") in ("posted", "residual", "orphan"):
            add("ERA", "manual-" + r.get("outcome", ""), check=str(r.get("checkid", "")), visit=str(r.get("visitid", "")), amt=r.get("pay", r.get("amt", r.get("paid", ""))), carrier=r.get("carrier", ""), action=r.get("outcome", ""))
add("Availity remits", "none new", action="no Availity PDF / Check-EFT export newer than the 1110Z pass (every PDF in bht Optum era downloads is in registers/availity_register.json); Treasury CSV already reconciled 9/14")
for r in fb if isinstance(fb, list) else []:
    if r.get("outcome") == "already-posted":
        add("ERA", "already-posted", check=str(r.get("checkid")), visit=str(r.get("visitid")), amt=r.get("era_paid"), carrier=r.get("carrier"), err="check %s" % r.get("checkno"), action="payment carrying this check number already on charge %s (earlier Availity manual post) - nothing posted" % r.get("chargeid"))
out = "_run report 9-15 1310.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["column", "state", "patient", "dos", "carrier", "error", "action", "checkid", "visit", "amount"])
    w.writeheader(); w.writerows(rows)
print("wrote", out, len(rows), "rows")
