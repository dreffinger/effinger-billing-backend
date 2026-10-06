# PLAIN ENGLISH (Complete payer duplicate-claim exclusions - generic helper, first used 7 AM ET 10/6/2026, run 2026-10-06T1110Z)
# Decides: nothing new - applies the standing Exclusions rule (step 4): a payer rejection that reads "DUPLICATE OF A PREVIOUSLY
#   PROCESSED CLAIM/LINE" means the payer already adjudicated that visit, so the exclusion row is COMPLETED (hideexclusions) and the
#   claim is NEVER rebilled (a frequency-1 resend into an adjudicated claim is exactly what drew the duplicate).
# Reads first: the run's scan summary (scan_<stamp>/summary_before.json) for the rows on --run whose every error names a duplicate,
#   optionally narrowed to one chart (--pid); then the chart's live tx history (gettxhistory) so the report can say what the payer's
#   EARLIER answer on the visit was (a $0 COB9 hospice denial, a payment, nothing on file).
# Writes (only with --live): ONE hideexclusions per claim run with the matching visit/claim ids, then re-lists the run to confirm.
# Never touches: rebills, payments, write-offs, charges, plans. Default is a DRY run. Register: registers/excl_dup_<run>_<stamp>.json
# Usage: cd /home/claude/unbilled && python3 excl_dup_complete.py --scan scan_2026-10-06T1110Z --run 1700266 [--pid 17472396] [--live]
import amd, txh, re, json, sys, time, datetime

a = sys.argv[1:]
def opt(name, default=None):
    return a[a.index(name) + 1] if name in a else default
SCAN = opt("--scan"); RUN = opt("--run"); PID = opt("--pid"); LIVE = "--live" in a
if not SCAN or not RUN:
    print(__doc__ or "usage: --scan <dir> --run <claimrunid> [--pid <pid>] [--live]"); sys.exit(2)
STAMP = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
DUP = re.compile(r"DUPLICATE OF A PREVIOUSLY PROCESSED CLAIM", re.I)

s = json.load(open("%s/summary_before.json" % SCAN))
rows = [r for r in s["exclusions"].get(RUN, []) if (not PID or r.get("patientid") == PID)
        and r.get("_errs") and all(DUP.search(e.get("name", "")) for e in r["_errs"])]
print("run %s: %d duplicate-claim exclusion rows%s" % (RUN, len(rows), " on chart %s" % PID if PID else ""))
if not rows: sys.exit(0)

amd.login_cached()
reg = {"stamp": STAMP, "run": RUN, "pid": PID, "live": LIVE, "rows": []}
by_pid = {}
for r in rows:
    pid = r["patientid"]
    if pid not in by_pid:
        by_pid[pid] = txh.fetch(pid)
    root = by_pid[pid]
    live = []
    for c in root.iter("charge"):
        if c.get("void") == "1" or re.sub(r"\D", "", c.get("visit") or "") != r["id"]: continue
        pays = [(p.get("checknumber") or "", p.get("carrier") or "", p.get("amount"), p.get("void"), [(x.get("code"), x.get("amount")) for x in p.iter("payreason")]) for p in c.iter("payment")]
        live.append({"cid": re.sub(r"\D", "", c.get("id") or ""), "cpt": c.get("proccode"), "dos": c.get("dos"), "carrier": c.get("carrier"),
                     "billdate": c.get("billdate") or c.get("datebilled"), "insbal": c.get("insbal"), "patbal": c.get("patbal"), "paid": c.get("paid"), "pays": pays})
    reg["rows"].append({"visit": r["id"], "claimid": r["claimid"], "carrier": r.get("carriercodeshort"), "dos": [(c.get("dos") or "").strip() for c in r.get("_chgs") or []],
                        "cpt": [c.get("chgcode") for c in r.get("_chgs") or []], "fee": sum(float(c.get("totalfee") or 0) for c in r.get("_chgs") or []),
                        "error": r["_errs"][0]["name"][:160], "live": live})
    print("  visit %s %s %s %s $%.2f | live: %s" % (r["id"], r["claimid"], r.get("carriercodeshort"), ",".join(c.get("chgcode") for c in r.get("_chgs") or []),
          reg["rows"][-1]["fee"], "; ".join("%s %s insbal %s pays %s" % (l["cpt"], l["carrier"], l["insbal"], [(p[0], p[1], p[2], p[3]) for p in l["pays"]]) for l in live)))

lst = "".join('<visit id="%s" claimid="%s"/>' % (r["id"], r["claimid"]) for r in rows)
if not LIVE:
    print("DRY - would hideexclusions run %s for %d rows: %s" % (RUN, len(rows), [r["claimid"] for r in rows]))
else:
    x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % lst), timeout=120)
    reg["hide_result"] = re.sub(r"\s+", " ", x[:300]); print("hideexclusions ->", reg["hide_result"])
    time.sleep(1)
    y = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": RUN, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
    left = re.findall(r'<visit [^>]*\bid="(\d+)"', y); reg["relist_visits"] = left
    print("re-list run %s: %d exclusion visits left: %s" % (RUN, len(left), left))
json.dump(reg, open("registers/excl_dup_%s_%s%s.json" % (RUN, STAMP, "" if LIVE else "_dry"), "w"), indent=1)
print("register written")
