# PLAIN ENGLISH (Weekly metrics history row + flags)
# Decides: Nothing. Builds this week's row for the Google Sheet "Practice metrics - weekly", computes deltas vs the
# prior row and the row 4 weeks back when a history CSV is present, applies the standing threshold flags
# (aging bucket +10% wk/wk, carrier at $0 payments for 30 days, days in A/R +10%, ERA failed lines not falling
# two weeks running, denial rate > 4-week average +25%), and writes the summary CSV William receives.
# Rules it uses: first run = BASELINE (no deltas); aggregates only - never a patient row. RUN_DATE env var
# (YYYY-MM-DD, default today) picks metrics_<stamp>.json; the history CSV "Practice metrics - weekly.csv" is the
# local copy of the Drive sheet (downloaded before this runs; re-created + old copy trashed afterwards).
# Never touches: AMD.
# ---
import json, csv, os, sys, datetime
WS = "/home/claude/unbilled"; os.chdir(WS)
RUN = os.environ.get("RUN_DATE") or datetime.date.today().isoformat(); STAMP = RUN.replace("-", "")
m = json.load(open("metrics_%s.json" % STAMP))
assert m["run_date"] == RUN, (m["run_date"], RUN)
HIST = "Practice metrics - weekly.csv"          # local copy of the Drive sheet (downloaded when it exists)
COLS = ["run date", "days in A/R", "total A/R", "A/R 0-30", "31-60", "61-90", "91-120", "120+", "top-8 carriers A/R",
        "charges 7d", "payments 7d", "adjustments 7d", "denials 7d count/$", "top 3 denial reasons", "unpaid count/$ by carrier",
        "ERA lines posted 7d / $", "ERA lines failed (latest night)", "write-offs 7d $", "clean-claim rate (if computed)", "sources used", "notes"]

def f2(x): return "%.2f" % x
top8 = "; ".join("%s %s" % (c, f2(d["bal"])) for c, d in list(m["ar_by_carrier"].items())[:8])
unpaid_by_car = "; ".join("%s %d/%s" % (c, d["n"], f2(d["bal"])) for c, d in list(m["ar_by_carrier"].items())[:12])
den = m["denials_7d"]; ap = m["era_autopost"]
regs = m.get("writeoff_registers") or {"files": []}
reg_txt = "; ".join("%s %s $%s (%s)" % (r["file"], r["date"], f2(r["amount"]), r["reason"][:60]) for r in regs.get("files", [])) or "none dated within the week"
row = {
    "run date": RUN,
    "days in A/R": m["days_in_ar"],
    "total A/R": f2(m["ar_total"]),
    "A/R 0-30": f2(m["ar_buckets"]["0-30"]), "31-60": f2(m["ar_buckets"]["31-60"]), "61-90": f2(m["ar_buckets"]["61-90"]),
    "91-120": f2(m["ar_buckets"]["91-120"]), "120+": f2(m["ar_buckets"]["120+"]),
    "top-8 carriers A/R": top8,
    "charges 7d": f2(m["charges_7d"]),
    "payments 7d": f2(m["payments_7d"]),
    "adjustments 7d": f2(m["adjustments_7d_writeoffs"]),
    "denials 7d count/$": "%d / %s (rate %.1f%% of %d adjudicated lines)" % (den["lines"], f2(den["charge_amt"]), 100 * (den["rate"] or 0), den["adjudicated_lines"]),
    "top 3 denial reasons": "; ".join("%s x%d $%s" % (k, n, f2(a)) for k, n, a in m["denial_reasons_7d"][:3]),
    "unpaid count/$ by carrier": unpaid_by_car,
    "ERA lines posted 7d / $": "%d lines / %s (%d checks; nightly auto-post OK lines this week: %d over %d e-mailed nights)" % (m["era_payments_7d"]["lines"], f2(m["era_payments_7d"]["amt"]), m["era_payments_7d"]["checks"], ap["week_ok_lines"], ap.get("nights_with_email_this_week", 0)),
    "ERA lines failed (latest night)": "%d (night of %s, %d checks)" % (ap["latest_failed"], ap["latest_night"], ap["latest_checks"]),
    "write-offs 7d $": f2(m["adjustments_7d_writeoffs"]),
    "clean-claim rate (if computed)": ("%.1f%%" % (100 * m["clean_claim_rate_7d"])) if m.get("clean_claim_rate_7d") is not None else "",
    "sources used": "backend (massrebillsearch, masswriteoffsearch patient balances, gettxhistory scan of %d patients, ERA Center list, getclaimrunstatus); Gmail nightly ERA auto-post e-mails; Drive write-off registers + 7 PM run reports. Report Center skipped (no browser in the cloud run)." % m["scan"]["patients"],
    "notes": "",
}

# ---------- history / deltas / flags ----------
prev = None; prev4 = None; hist_rows = []
if os.path.exists(HIST):
    with open(HIST, newline="") as f:
        hist_rows = [r for r in csv.DictReader(f) if r.get("run date") and r["run date"] != RUN]
    hist_rows.sort(key=lambda r: r["run date"])
    if hist_rows: prev = hist_rows[-1]
    # 4 weeks ago = the newest row dated <= RUN - 28 days (by DATE, not position: a missed week - 9/28 - breaks [-4]); 10/12/2026
    _t = (datetime.date.fromisoformat(RUN) - datetime.timedelta(days=28)).isoformat()
    _c = [r for r in hist_rows if r["run date"] <= _t]
    if _c: prev4 = _c[-1]
flags = []; notes = []; deltas = {}
def num(s):
    try: return float(str(s).replace(",", "").replace("%", "").split()[0])
    except Exception: return None
def pct(a, b):
    return (a - b) / b * 100 if (a is not None and b not in (None, 0)) else None
def rate_of(s):
    try: return float(s.split("rate ")[1].split("%")[0])
    except Exception: return None
if prev:
    for k in ["days in A/R", "total A/R", "A/R 0-30", "31-60", "61-90", "91-120", "120+", "charges 7d", "payments 7d", "adjustments 7d", "write-offs 7d $", "clean-claim rate (if computed)"]:
        a, b = num(row[k]), num(prev.get(k)); p = pct(a, b)
        deltas[k] = {"prev": b, "pct": round(p, 1) if p is not None else None}
        if k in ("A/R 0-30", "31-60", "61-90", "91-120", "120+") and p is not None and p > 10: flags.append("aging bucket %s up %.1f%% wk/wk (%s -> %s)" % (k, p, f2(b), f2(a)))
        if k == "days in A/R" and p is not None and p > 10: flags.append("days in A/R up %.1f%% wk/wk (%s -> %s)" % (p, b, a))
    # denial lines + rate
    a, b = num(row["denials 7d count/$"]), num(prev.get("denials 7d count/$")); deltas["denial lines 7d"] = {"prev": b, "pct": round(pct(a, b), 1) if pct(a, b) is not None else None}
    ra, rb = rate_of(row["denials 7d count/$"]), rate_of(prev.get("denials 7d count/$", "")); deltas["denial rate 7d"] = {"prev": rb, "pct": round(pct(ra, rb), 1) if pct(ra, rb) is not None else None}
    # ERA failed lines (latest night)
    a, b = num(row["ERA lines failed (latest night)"]), num(prev.get("ERA lines failed (latest night)")); deltas["ERA lines failed (latest night)"] = {"prev": b, "pct": round(pct(a, b), 1) if pct(a, b) is not None else None}
    if len(hist_rows) >= 2:
        c = num(hist_rows[-2].get("ERA lines failed (latest night)"))
        if a is not None and b is not None and c is not None and a >= b and b >= c: flags.append("ERA failed lines not falling for two consecutive weeks (%s -> %s -> %s)" % (c, b, a))
    elif a is not None and b is not None and a >= b:
        notes.append("ERA failed lines rose %s -> %s (one prior week only; the two-consecutive-weeks flag needs a third row)" % (int(b), int(a)))
    rates = [r for r in (rate_of(x.get("denials 7d count/$", "")) for x in hist_rows[-4:]) if r is not None]
    if rates and den["rate"] is not None:
        avg = sum(rates) / len(rates)
        if 100 * den["rate"] > avg * 1.25: flags.append("denial rate %.1f%% above the %d-week avg %.1f%% by >25%%" % (100 * den["rate"], len(rates), avg))
if prev4:
    for k in ["days in A/R", "total A/R", "120+"]:
        a, b = num(row[k]), num(prev4.get(k)); p = pct(a, b)
        deltas[k + " vs 4wk"] = {"prev": b, "pct": round(p, 1) if p is not None else None}
for s in m["silent_carriers_30d"]:
    flags.append("carrier %s (%s) $0 payments >30 days: A/R %s on %d visits, last payment %s" % (s["carrier"], s["name"], f2(s["ar"]), s["n"], s["last_paid"]))
if ap.get("gap"): flags.append("ERA auto-post e-mails: " + ap["gap"])
row["notes"] = ("BASELINE run. " if not prev else "") + ("FLAGS: " + " | ".join(flags) if flags else "no flags") + ((" NOTES: " + " | ".join(notes)) if notes else "")
json.dump({"row": row, "deltas": deltas, "flags": flags, "notes": notes, "baseline": not prev}, open("metrics_row_%s.json" % STAMP, "w"), indent=1)

# ---------- write the history CSV (all rows + this one) ----------
with open(HIST, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=COLS); w.writeheader()
    for r in hist_rows:
        if r["run date"] != RUN: w.writerow({k: r.get(k, "") for k in COLS})
    w.writerow(row)

# ---------- summary CSV for William (aggregates only) ----------
with open("Weekly metrics %s - summary.csv" % RUN, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["metric", "this week", "delta vs last week", "delta vs 4 weeks ago", "flag / note"])
    def d(k):
        x = deltas.get(k); y = deltas.get(k + " vs 4wk")
        return [("%+.1f%% (was %s)" % (x["pct"], x["prev"])) if x and x["pct"] is not None else ("baseline" if not prev else "n/a"), ("%+.1f%%" % y["pct"]) if y and y["pct"] is not None else "n/a (needs 4 rows)"]
    w.writerow(["Days in A/R (A/R / (charges 90d / 90))", row["days in A/R"]] + d("days in A/R") + ["charges from the backend tx-history scan (Report Center unavailable); " + ", ".join(x for x in flags if x.startswith("days in A/R"))])
    w.writerow(["Total open insurance A/R", row["total A/R"]] + d("total A/R") + ["%d open visits (massrebillsearch)" % m["unpaid_n"]])
    for k in ["A/R 0-30", "31-60", "61-90", "91-120", "120+"]:
        w.writerow(["A/R bucket %s (by DOS)" % k, row[k]] + d(k) + [", ".join(x for x in flags if x.startswith("aging bucket %s" % k))])
    w.writerow(["Charges 7d (DOS in last 7 days, scanned patients)", row["charges 7d"]] + d("charges 7d") + ["Claimocity feed lags a few days"])
    w.writerow(["Charges 90d (DOS in last 90 days, scanned patients)", f2(m["charges_90d"]), "n/a", "n/a", "%d charges" % m["charges_90d_n"]])
    w.writerow(["Payments posted 7d (insurance)", row["payments 7d"]] + d("payments 7d") + ["%d lines, %d checks" % (m["payments_7d_lines"], m["era_payments_7d"]["checks"])])
    w.writerow(["Adjustments / write-offs posted 7d", row["adjustments 7d"]] + d("adjustments 7d") + ["; ".join("%s %s" % (k, f2(v["amt"])) for k, v in list(m["writeoffs_7d_by_code"].items())[:5])])
    w.writerow(["Denials 7d (lines / denied charge $ / rate)", row["denials 7d count/$"], ("%+.1f%% lines, rate %s%% -> %.1f%%" % (deltas["denial lines 7d"]["pct"], deltas["denial rate 7d"]["prev"], 100 * (den["rate"] or 0))) if prev and deltas.get("denial lines 7d", {}).get("pct") is not None else ("baseline" if not prev else "n/a"), "n/a (needs 4 rows)", "top: " + row["top 3 denial reasons"] + "; " + ", ".join(x for x in flags if x.startswith("denial rate"))])
    for c, dd in list(m["denials_7d_by_carrier"].items())[:6]:
        w.writerow(["  denials by carrier: %s" % c, "%d lines / %s / %.1f%% of %d" % (dd["lines"], f2(dd["charge_amt"]), 100 * (dd["rate"] or 0), dd["adjudicated"]), "", "", "; ".join("%s x%d" % (k, n) for k, n in dd["top_reasons"][:3])])
    w.writerow(["Unpaid claims by carrier (count/$)", row["unpaid count/$ by carrier"], ("open visits %d (was %s)" % (m["unpaid_n"], prev["unpaid count/$ by carrier"].split(";")[0] if prev else "")) if prev else "baseline", "n/a", "last week's row holds the prior split"])
    w.writerow(["ERA lines posted 7d / $", row["ERA lines posted 7d / $"], "see payments 7d", "n/a", "ERA Center still unposted: %d checks, $%s unposted of $%s paid" % (m["era_center"]["checks"], f2(m["era_center"]["unposted"]), f2(m["era_center"]["paid"]))])
    w.writerow(["ERA auto-post failed lines (latest night)", row["ERA lines failed (latest night)"]] + [("%+.1f%% (was %s)" % (deltas["ERA lines failed (latest night)"]["pct"], deltas["ERA lines failed (latest night)"]["prev"])) if prev and deltas.get("ERA lines failed (latest night)", {}).get("pct") is not None else ("baseline" if not prev else "n/a"), "n/a"] + ["nightly series: " + "; ".join("%s ok %d/fail %d" % (n[0], n[2], n[3]) for n in ap["series"]) + ((". " + ap["gap"]) if ap.get("gap") else "")])
    w.writerow(["Write-offs 7d $ (posted, tx-history)", row["write-offs 7d $"]] + d("write-offs 7d $") + ["Drive registers this week: " + reg_txt])
    w.writerow(["Clean-claim rate 7d (claims sent minus clearinghouse exclusions)", row["clean-claim rate (if computed)"]] + d("clean-claim rate (if computed)") + ["%d claims / %d exclusions in %d runs" % (m["claim_runs_7d"]["claims"], m["claim_runs_7d"]["exclusions"], m["claim_runs_7d"]["runs"])])
    w.writerow(["Charge lag 90d (DOS -> charge entry, days)", "median %s / p90 %s / mean %s" % (m["charge_lag_90d"]["median_days"], m["charge_lag_90d"]["p90_days"], m["charge_lag_90d"]["mean_days"]), "n/a", "n/a", "PROPOSED metric"])
    w.writerow(["Payer mix 90d (charges)", "; ".join("%s %.1f%%" % (c, p) for c, a, p in m["payer_mix_90d"][:6]), "n/a", "n/a", "PROPOSED metric"])
    w.writerow(["Carriers with $0 payments for 30+ days", "; ".join("%s $%s (last %s)" % (s["carrier"], f2(s["ar"]), s["last_paid"]) for s in m["silent_carriers_30d"]), "", "", "FLAG"])
    if m.get("claims_center_trend"):
        w.writerow(["Claims Center trend (7 PM ET run, rows after)", "; ".join("%s U%s/E%s/ERA%s" % (dd["day"][5:], dd.get("unbilled_rows_after", "-"), dd.get("exclusions_rows_after", "-"), dd.get("era_checks_after", "-")) for dd in m["claims_center_trend"]["days"] if dd.get("file")), "", "", "U = unbilled rows, E = exclusion rows, ERA = unposted checks; charge review / claim inspector 0 every day"])
    w.writerow(["Sources", row["sources used"], "", "", ""])
    w.writerow(["Notes", row["notes"], "", "", ""])
print(json.dumps({"flags": flags, "notes": notes, "baseline": not prev, "deltas": deltas}, indent=1))
