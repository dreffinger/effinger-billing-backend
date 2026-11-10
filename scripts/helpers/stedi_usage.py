# PLAIN ENGLISH (Stedi usage reader - look-ups part A, 11/10/2026)
# Decides: nothing. Reads the usage log stedi.py writes - one line per paid call: time (UTC), who asked, kind of call, payer id, chart id,
#   first error code or ok, first-tier price - and prints one month's calls by helper and by kind, priced on the vendor's monthly ladders
#   from stedi_prices.py (the one price table). With --units it prices statement units instead, e.g. October 2026:
#   --units "claim status=6770,look-up without SSN=986,look-up with SSN=78,discovery=187,eligibility=505"
#   -> $889.50, $783.50 for the two look-up lines, $237.00 and $113.25.
# Rules it uses: a helper's share of a kind is that kind's month total split by its number of calls (the tiers are per month, not per
#   helper). Calls that ended in an HTTP error are counted apart and not priced: the vendor's claim-status page says a call that returns
#   an HTTP 4xx or 5xx error is not charged; the same is assumed for the other kinds (the statement will show if it is not so).
# Never touches: the vendor, AdvancedMD, any file but the log it reads. Prints counts and dollars, never a chart id.
# Usage: python3 stedi_usage.py [YYYY-MM] [--log PATH]      (default: this month, $STEDI_USAGE_LOG or patient_db/stedi_usage.log)
#        python3 stedi_usage.py --units "kind=N,kind=N"
import os, sys, datetime, collections
import stedi_prices
HERE = os.path.dirname(os.path.abspath(__file__))
def log_path():
    return os.environ.get("STEDI_USAGE_LOG") or os.path.join(HERE, "patient_db", "stedi_usage.log")
def read(path):
    """The log's lines as dicts (time, who, kind, payer, chart, code, price); lines that are not log lines are skipped."""
    out = []
    try: lines = open(path, errors="replace").read().splitlines()
    except OSError: return out
    for ln in lines:
        f = ln.split("\t")
        if len(f) >= 7 and f[0][:4].isdigit(): out.append(dict(zip(("time", "who", "kind", "payer", "chart", "code", "price"), f[:7])))
    return out
def month_report(rows, month):
    """One month's calls: by kind (priced on its ladder) and by helper (its share of each kind)."""
    rows = [r for r in rows if r["time"].startswith(month)]
    billed = [r for r in rows if not r["code"].startswith("http")]
    units = collections.Counter(r["kind"] for r in billed)
    ladders = collections.Counter()
    for k, n in units.items():
        try: ladders[stedi_prices.ladder_of(k)] += n
        except KeyError: pass
    dollars = {lad: stedi_prices.price(lad, n) for lad, n in ladders.items()}
    kinds = {}
    for k, n in sorted(units.items()):
        try: lad = stedi_prices.ladder_of(k)
        except KeyError: kinds[k] = {"calls": n, "dollars": None}; continue
        kinds[k] = {"calls": n, "dollars": round(dollars[lad] * n / ladders[lad], 2)}
    helpers = collections.defaultdict(lambda: {"calls": 0, "dollars": 0.0, "kinds": collections.Counter()})
    for r in billed:
        h = helpers[r["who"] or "?"]; h["calls"] += 1; h["kinds"][r["kind"]] += 1
        try: lad = stedi_prices.ladder_of(r["kind"]); h["dollars"] += dollars[lad] / ladders[lad]
        except KeyError: pass
    return {"month": month, "calls": len(billed), "http_errors": len(rows) - len(billed), "dollars": round(sum(dollars.values()), 2),
            "ladders": {lad: {"calls": n, "dollars": dollars[lad], "how": stedi_prices.breakdown(lad, n)} for lad, n in ladders.items()},
            "kinds": kinds, "helpers": {w: {"calls": h["calls"], "dollars": round(h["dollars"], 2), "kinds": dict(h["kinds"])} for w, h in helpers.items()}}
def units_report(units):
    """Statement units {kind: n} -> {kind: (dollars, how)} on the price table, each kind on its own ladder."""
    return {k: (stedi_prices.price(k, n), stedi_prices.breakdown(k, n)) for k, n in units.items()}
def main(argv):
    if "--units" in argv:
        spec = argv[argv.index("--units") + 1] if argv.index("--units") + 1 < len(argv) else ""
        units = {}
        for part in spec.split(","):
            if "=" in part: k, n = part.rsplit("=", 1); units[k.strip()] = int(n)
        rep = units_report(units)
        for k, (d, how) in rep.items(): print("%-20s %6d calls  $%9.2f  (%s)" % (k, units[k], d, how))
        print("%-20s %6d calls  $%9.2f" % ("total", sum(units.values()), sum(d for d, _ in rep.values())))
        return 0
    month = next((a for a in argv if len(a) == 7 and a[4] == "-" and a[:4].isdigit()), datetime.date.today().strftime("%Y-%m"))
    path = argv[argv.index("--log") + 1] if "--log" in argv and argv.index("--log") + 1 < len(argv) else log_path()
    rep = month_report(read(path), month)
    print("Stedi calls in %s (%s): %d calls, $%.2f at list prices%s" % (month, path, rep["calls"], rep["dollars"],
          "; %d more ended in an HTTP error and are not priced" % rep["http_errors"] if rep["http_errors"] else ""))
    print("  by kind:")
    for k, v in rep["kinds"].items(): print("    %-22s %6d   %s" % (k, v["calls"], "$%.2f" % v["dollars"] if v["dollars"] is not None else "no price"))
    for lad, v in rep["ladders"].items(): print("    ladder %-15s %6d   $%.2f  (%s)" % (lad, v["calls"], v["dollars"], v["how"]))
    print("  by helper:")
    for w, v in sorted(rep["helpers"].items(), key=lambda kv: -kv[1]["dollars"]):
        print("    %-40s %6d   $%8.2f   %s" % (w[:40], v["calls"], v["dollars"], ", ".join("%s %d" % kv for kv in sorted(v["kinds"].items()))))
    return 0
if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
