# PLAIN ENGLISH (Complete Florida Blue Medigap-secondary PREF0283 exclusions - the 9/20/2026 crossover-wait rule, 10/8/2026)
# Decides: which CH FH PREF0283 'MISSING PAYER DOC CONTROL NUM' exclusion rows on one claim run are Florida Blue (BCBS) MEDIGAP
#   SECONDARY claims that AMD queued on its own the day Medicare paid - the live chart shows a non-void Medicare (FLO02) payment on
#   every charge of the visit and the open insurance balance equals Medicare's PR coinsurance. Those rows are COMPLETED
#   (hideexclusions, hide=-1) and never re-sent: Medicare's Medigap crossover carries the coinsurance to Florida Blue (William's
#   9/20/2026 rule; the 10/5/2026 run completed 9 such rows the same way). A row whose charges carry no Medicare payment, whose
#   balance is not the coinsurance, or whose carrier is not BCBS is LEFT on the list and printed.
# Never touches: charges, payments, write-offs, claims; nothing is rebilled. --live writes; default dry.
#   10/25/2026: a charge still flagged to Medicare (FLO02) counts when Medicare paid it and only its PR coinsurance is open.
#   python3 excl_crossover_complete.py --scan <scan dir> --run <claimrunid> [--live]
#   register registers/excl_crossover_<run>_<stamp>[_dry].json
import amd, txh, re, json, sys, time, datetime

a = sys.argv[1:]
def opt(name, default=None):
    return a[a.index(name) + 1] if name in a else default
SCAN = opt("--scan"); RUN = opt("--run"); LIVE = "--live" in a
if not SCAN or not RUN:
    print("usage: --scan <dir> --run <claimrunid> [--live]"); sys.exit(2)
STAMP = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
PREF = re.compile(r"PREF0283", re.I)
MEDICARE = {"FLO02"}

s = json.load(open("%s/summary_before.json" % SCAN))
rows = [r for r in s["exclusions"].get(RUN, []) if r.get("carriercodeshort") == "BCBS" and r.get("_errs")
        and all(PREF.search(e.get("name", "")) for e in r["_errs"])]
print("run %s: %d BCBS PREF0283 exclusion rows" % (RUN, len(rows)))
if not rows: sys.exit(0)

amd.login_cached()
reg = {"stamp": STAMP, "run": RUN, "live": LIVE, "complete": [], "left": []}
by_pid = {}
for r in rows:
    pid = r["patientid"]
    if pid not in by_pid:
        by_pid[pid] = txh.fetch(pid)
    root = by_pid[pid]
    live = []
    for c in root.iter("charge"):
        if c.get("void") == "1" or re.sub(r"\D", "", c.get("visit") or "") != str(r["id"]): continue
        pays = [p for p in c.iter("payment") if p.get("void") != "1" and (p.get("carrier") or "") in MEDICARE and float(p.get("amount") or 0) != 0]
        pr = sum(float(x.get("amount") or 0) for p in pays for x in p.iter("payreason") if (x.get("code") or "").startswith("PR"))
        live.append({"cid": re.sub(r"\D", "", c.get("id") or ""), "cpt": c.get("proccode"), "dos": c.get("dos"), "carrier": c.get("carrier"),
                     "billdate": c.get("billdate") or c.get("datebilled"), "insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0),
                     "medicare_paid": sum(-float(p.get("amount") or 0) for p in pays), "medicare_checks": sorted({p.get("checknumber") or "" for p in pays}),
                     "pr": round(pr, 2)})
    # 10/25/2026: a charge whose live carrier still reads Medicare (FLO02) but that Medicare already PAID, with only its PR coinsurance
    # open, is in the same crossover-wait state as its BCBS-flagged sibling (visit 19456319: 99349 flipped to BCBS, 99497 still FLO02,
    # both paid by Medicare, both open = PR) - the row's own carrier is already filtered to BCBS above.
    ok = bool(live) and all(l["medicare_paid"] > 0 and abs(l["insbal"] - l["pr"]) < 0.01 and l["carrier"] in ({"BCBS"} | MEDICARE) for l in live)
    rec = {"visit": r["id"], "claimid": r["claimid"], "pid": pid, "fee": sum(float(c.get("totalfee") or 0) for c in r.get("_chgs") or []),
           "coinsurance_open": round(sum(l["insbal"] for l in live), 2), "live": live}
    (reg["complete"] if ok else reg["left"]).append(rec)
    print("  %s visit %s %s $%.2f coinsurance open $%.2f | %s" % ("COMPLETE" if ok else "LEFT    ", r["id"], r["claimid"], rec["fee"], rec["coinsurance_open"],
          "; ".join("%s %s Medicare paid %.2f chk %s insbal %.2f PR %.2f" % (l["cpt"], l["dos"], l["medicare_paid"], ",".join(l["medicare_checks"]), l["insbal"], l["pr"]) for l in live)))

if not reg["complete"]:
    print("nothing to complete"); json.dump(reg, open("registers/excl_crossover_%s_%s%s.json" % (RUN, STAMP, "" if LIVE else "_dry"), "w"), indent=1); sys.exit(0)
lst = "".join('<visit id="%s" claimid="%s"/>' % (r["visit"], r["claimid"]) for r in reg["complete"])
if not LIVE:
    print("DRY - would hideexclusions run %s for %d rows: %s" % (RUN, len(reg["complete"]), [r["claimid"] for r in reg["complete"]]))
else:
    x = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": RUN, "hide": "-1", "nocookie": "1"}, "<visitlist>%s</visitlist>" % lst), timeout=120)
    reg["hide_result"] = re.sub(r"\s+", " ", x[:300]); print("hideexclusions ->", reg["hide_result"])
    time.sleep(1)
    y = amd.post(amd.msg("getclaimexclusioncharges", "claimsreports", {"claimrunid": RUN, "clearinghouse": "1", "payer": "1", "nocookie": "1"}), timeout=120)
    left = re.findall(r'<visit [^>]*\bid="(\d+)"', y); reg["relist_visits"] = left
    print("re-list run %s: %d exclusion visits left: %s" % (RUN, len(left), left))
json.dump(reg, open("registers/excl_crossover_%s_%s%s.json" % (RUN, STAMP, "" if LIVE else "_dry"), "w"), indent=1)
print("register written")
