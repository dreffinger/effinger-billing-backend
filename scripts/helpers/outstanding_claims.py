#!/usr/bin/env python3
# PLAIN ENGLISH (Outstanding claims summary - William 10/11/2026: "a new artifact with a summary of all outstanding claims")
# Decides: nothing. READ-ONLY. Pulls the whole unpaid list (POST /api/claim/massrebillsearch {} - every open insurance balance,
#   the same call the Money Ledger and the unpaid audit use) and sums it up: total open, by carrier, by age of the date of
#   service, by month of service, the oldest and the largest visits - chart ids and visit ids only, never a name, member id or DOB.
#   Writes outstanding_claims.json (the "Outstanding Claims" page and the Billing Button report read it).
# Rules it uses: age is counted from the date of service (William's write-off clock for primary claims is 12 months from DOS;
#   a secondary is timely from the primary's remit, so the buckets are a guide, not a verdict). ONE login via amd.login_cached().
# Never touches: AMD writes, claims, balances.
#   cd /home/claude/unbilled && python3 outstanding_claims.py [--out outstanding_claims.json]
import collections, datetime, json, os, sys, time

import amd, era_post, requests

KEEP = ("visitid", "patientid", "carriercode", "dateofservice", "insbalance", "provider", "facility", "lastbilldate")


def rows_from(unp):
    out = []
    for v in unp:
        if not isinstance(v, dict):
            continue
        r = {k: v.get(k) for k in KEEP if k in v}
        try:
            r["insbalance"] = round(float(r.get("insbalance") or 0), 2)
        except (TypeError, ValueError):
            r["insbalance"] = 0.0
        r["carriercode"] = (r.get("carriercode") or "NONE").strip() or "NONE"
        out.append(r)
    return out


def main():
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "outstanding_claims.json"
    amd.login_cached()
    unp = requests.post(era_post.API + "/claim/massrebillsearch", headers=era_post.H(), json={}, timeout=180).json()
    rows = rows_from(unp if isinstance(unp, list) else (unp.get("data") or unp.get("rows") or []))
    today = datetime.date.today()
    buckets = collections.OrderedDict([("0-30", (0, 30)), ("31-60", (31, 60)), ("61-90", (61, 90)), ("91-180", (91, 180)),
                                       ("181-365", (181, 365)), ("over 365", (366, 10 ** 6))])
    try:
        cars = json.load(open("carriers.json"))
        name = {v[0]: v[1] for v in cars.values() if isinstance(v, (list, tuple))} if cars else {}
    except (OSError, ValueError):
        name = {}
    by_car = {}
    by_bucket = collections.OrderedDict((k, {"n": 0, "dollars": 0.0}) for k in buckets)
    by_month = collections.defaultdict(lambda: {"n": 0, "dollars": 0.0})
    charts = set()
    total = 0.0
    for r in rows:
        try:
            dos = datetime.datetime.fromisoformat(str(r.get("dateofservice"))[:19]).date()
        except ValueError:
            dos = None
        age = (today - dos).days if dos else None
        r["days"] = age
        r["dos"] = dos.isoformat() if dos else None
        r.pop("dateofservice", None)
        bal = r["insbalance"]
        total += bal
        charts.add(r.get("patientid"))
        c = by_car.setdefault(r["carriercode"], {"carrier": r["carriercode"], "name": name.get(r["carriercode"], ""), "n": 0, "dollars": 0.0,
                                                 "buckets": {k: 0.0 for k in buckets}, "oldest_days": 0})
        c["n"] += 1
        c["dollars"] += bal
        if age is not None:
            c["oldest_days"] = max(c["oldest_days"], age)
            for k, (lo, hi) in buckets.items():
                if lo <= age <= hi:
                    c["buckets"][k] += bal
                    by_bucket[k]["n"] += 1
                    by_bucket[k]["dollars"] += bal
                    break
        if dos:
            m = by_month[dos.strftime("%Y-%m")]
            m["n"] += 1
            m["dollars"] += bal
    for c in by_car.values():
        c["dollars"] = round(c["dollars"], 2)
        c["buckets"] = {k: round(v, 2) for k, v in c["buckets"].items()}
    for b in by_bucket.values():
        b["dollars"] = round(b["dollars"], 2)
    rows.sort(key=lambda r: (-(r.get("days") or 0), -r["insbalance"]))
    oldest = [dict(r) for r in rows[:40]]
    largest = sorted(rows, key=lambda r: -r["insbalance"])[:40]
    over365 = [r for r in rows if (r.get("days") or 0) > 365]
    summary = {
        "schema": "outstanding-claims/1",
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "as_of": today.isoformat(),
        "total": round(total, 2), "visits": len(rows), "charts": len(charts),
        "over_365": {"n": len(over365), "dollars": round(sum(r["insbalance"] for r in over365), 2)},
        "by_bucket": by_bucket,
        "by_carrier": sorted(by_car.values(), key=lambda c: -c["dollars"]),
        "by_month": [{"month": k, "n": v["n"], "dollars": round(v["dollars"], 2)} for k, v in sorted(by_month.items())],
        "oldest": oldest, "largest": largest,
        "rows": rows,
    }
    json.dump(summary, open(out, "w"), indent=1, default=str)
    print("outstanding claims: %d visits on %d charts, $%.2f open (%d over 365 days, $%.2f) -> %s" % (
        len(rows), len(charts), total, len(over365), summary["over_365"]["dollars"], out))
    for c in summary["by_carrier"][:12]:
        print("  %-6s %-28s %4d  $%10.2f" % (c["carrier"], c["name"][:28], c["n"], c["dollars"]))


if __name__ == "__main__":
    main()
