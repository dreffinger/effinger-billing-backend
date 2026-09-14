# PLAIN ENGLISH (Weekly metrics compute)
# Decides: Nothing. Turns the unpaid list, the tx-history cache, the ERA Center list, the claim runs and
# the nightly ERA e-mail tallies into the weekly KPI numbers (aggregates only; patient-level rows go to CSV files).
# Rules it uses: A/R aged by DOS; payments counted by posting date (createtime); denial line = $0 payment line
# carrying a CO/PR/OA/PI pay-reason; write-offs by wocode; voided transactions ignored everywhere.
# Never touches: AMD writes.
# ---
import json, csv, datetime, collections, os, sys
WS = "/home/claude/unbilled"; os.chdir(WS)
TODAY = datetime.date(2026, 9, 14)
D7 = TODAY - datetime.timedelta(days=7)      # 2026-09-07
D30 = TODAY - datetime.timedelta(days=30)
D90 = TODAY - datetime.timedelta(days=90)    # 2026-06-16
D28 = TODAY - datetime.timedelta(days=28)

def pd(s):
    if not s: return None
    s = s[:10]
    for f in ("%m/%d/%Y", "%Y-%m-%d"):
        try: return datetime.datetime.strptime(s, f).date()
        except Exception: pass
    return None
def money(s):
    try: return float(s or 0)
    except Exception: return 0.0

unp = json.load(open("unpaid_20260914.json"))
cache = json.load(open("metrics_txh_cache_20260914.json"))
if os.path.exists("metrics_txh_cache_20260914b.json"):
    cache.update(json.load(open("metrics_txh_cache_20260914b.json")))
cs = json.load(open("[name]_[DOB].json"))
runs = json.load(open("claimruns_20260914.json"))
night = json.load(open("era_autopost_nightly_20260914.json"))
cars = json.load(open("carriers_rich.json"))
cname = {}
for k, v in cars.items():
    if isinstance(v, (list, tuple)) and len(v) > 1: cname[str(v[0])] = str(v[1])
    elif isinstance(v, dict): cname[v.get("code", k)] = v.get("name", k)

out = {"run_date": TODAY.isoformat()}

# ---------- A/R from the unpaid list (open insurance balances, aged by DOS) ----------
B = collections.OrderedDict([("0-30", (0, 30)), ("31-60", (31, 60)), ("61-90", (61, 90)), ("91-120", (91, 120)), ("120+", (121, 10**6))])
def bucket(days):
    for k, (lo, hi) in B.items():
        if lo <= days <= hi: return k
    return "0-30"
ar_car = collections.defaultdict(lambda: {"n": 0, "bal": 0.0, "buckets": {k: 0.0 for k in B}})
ar_tot = {k: 0.0 for k in B}
for v in unp:
    c = (v.get("carriercode") or "").strip() or "NONE"
    d = pd(v["dateofservice"]); days = (TODAY - d).days if d else 0
    b = bucket(days); bal = money(v["insbalance"])
    ar_car[c]["n"] += 1; ar_car[c]["bal"] += bal; ar_car[c]["buckets"][b] += bal; ar_tot[b] += bal
total_ar = sum(ar_tot.values())
out["ar_total"] = round(total_ar, 2); out["ar_buckets"] = {k: round(x, 2) for k, x in ar_tot.items()}
out["unpaid_n"] = len(unp)
out["ar_by_carrier"] = {c: {"n": d["n"], "bal": round(d["bal"], 2), "buckets": {k: round(x, 2) for k, x in d["buckets"].items()}} for c, d in sorted(ar_car.items(), key=lambda kv: -kv[1]["bal"])}

# ---------- tx-history derived: charges, payments, denials, write-offs ----------
charges_90 = 0.0; charges_90_n = 0; charges_7 = 0.0; charges_7_n = 0
charges_90_by_car = collections.defaultdict(float)
pay7 = collections.defaultdict(float); pay7_n = collections.defaultdict(int)
pay30 = collections.defaultdict(float); pay_last = {}; pay_month = collections.defaultdict(lambda: collections.defaultdict(float))
adj7_wo = collections.defaultdict(float); adj7_wo_n = collections.defaultdict(int)     # by wocode
adj7_wo_car = collections.defaultdict(float)
den7 = collections.defaultdict(lambda: {"n": 0, "amt": 0.0}); den7_reason = collections.defaultdict(lambda: {"n": 0, "amt": 0.0}); den7_car_reason = collections.defaultdict(lambda: collections.defaultdict(int))
adj_lines7 = collections.defaultdict(int)  # all adjudicated payment lines (posted last 7 days) by carrier
era_pay7 = 0.0; era_pay7_n = 0; era_checks7 = set()
pay7_total = 0.0; pay7_lines = 0
seen_charge = set()
patients_err = 0
for pid, rec in cache.items():
    if rec.get("error"): patients_err += 1; continue
    for ch in rec["charges"]:
        if ch.get("void") == "1": continue
        cid = ch["id"]
        if cid in seen_charge: continue
        seen_charge.add(cid)
        dos = pd(ch.get("dos")); fee = money(ch.get("fee")); car = (ch.get("carrier") or "").strip() or "NONE"
        if dos and dos >= D90:
            charges_90 += fee; charges_90_n += 1; charges_90_by_car[car] += fee
        if dos and dos >= D7:
            charges_7 += fee; charges_7_n += 1
        for p in ch["pays"]:
            if p.get("void") == "1": continue
            pcar = (p.get("carrier") or "").strip() or "PAT"
            posted = pd(p.get("createtime")) or pd(p.get("date"))
            amt = abs(money(p.get("amount")))
            if posted:
                if amt > 0:
                    if posted > pay_last.get(pcar, datetime.date(1900, 1, 1)): pay_last[pcar] = posted
                    pay_month[pcar][posted.strftime("%Y-%m")] += amt
                if posted >= D30 and amt > 0: pay30[pcar] += amt
                if posted >= D7:
                    adj_lines7[pcar] += 1
                    if amt > 0:
                        pay7[pcar] += amt; pay7_n[pcar] += 1; pay7_total += amt; pay7_lines += 1
                        if (p.get("checknumber") or "").strip(): era_pay7 += amt; era_pay7_n += 1; era_checks7.add(p.get("checknumber"))
                    else:
                        rs = [r[0] for r in p.get("reasons", []) if r and r[0]]
                        grp = [r for r in rs if r[:2] in ("CO", "PR", "OA", "PI") and r not in ("PR1", "PR2", "PR3")]
                        if grp:
                            den7[pcar]["n"] += 1; den7[pcar]["amt"] += fee
                            key = grp[0]
                            den7_reason[key]["n"] += 1; den7_reason[key]["amt"] += fee
                            den7_car_reason[pcar][key] += 1
        for w in ch["wos"]:
            if w.get("void") == "1": continue
            posted = pd(w.get("createtime")) or pd(w.get("date"))
            if posted and posted >= D7:
                amt = abs(money(w.get("amount"))); code = w.get("wocode") or "?"
                adj7_wo[code] += amt; adj7_wo_n[code] += 1; adj7_wo_car[car] += amt

out["scan"] = {"patients": len(cache), "errors": patients_err, "charges_seen": len(seen_charge)}
out["charges_90d"] = round(charges_90, 2); out["charges_90d_n"] = charges_90_n
out["charges_7d"] = round(charges_7, 2); out["charges_7d_n"] = charges_7_n
out["charges_90d_by_carrier"] = {k: round(v, 2) for k, v in sorted(charges_90_by_car.items(), key=lambda kv: -kv[1])}
out["days_in_ar"] = round(total_ar / (charges_90 / 90.0), 1) if charges_90 else None
out["payments_7d"] = round(pay7_total, 2); out["payments_7d_lines"] = pay7_lines
out["payments_7d_by_carrier"] = {k: {"amt": round(v, 2), "lines": pay7_n[k]} for k, v in sorted(pay7.items(), key=lambda kv: -kv[1])}
out["era_payments_7d"] = {"amt": round(era_pay7, 2), "lines": era_pay7_n, "checks": len(era_checks7)}
out["adjustments_7d_writeoffs"] = round(sum(adj7_wo.values()), 2)
out["writeoffs_7d_by_code"] = {k: {"amt": round(v, 2), "n": adj7_wo_n[k]} for k, v in sorted(adj7_wo.items(), key=lambda kv: -kv[1])}
out["writeoffs_7d_by_carrier"] = {k: round(v, 2) for k, v in sorted(adj7_wo_car.items(), key=lambda kv: -kv[1])}
den_total_n = sum(d["n"] for d in den7.values()); adj_total = sum(adj_lines7.values())
out["denials_7d"] = {"lines": den_total_n, "charge_amt": round(sum(d["amt"] for d in den7.values()), 2), "adjudicated_lines": adj_total,
                     "rate": round(den_total_n / adj_total, 4) if adj_total else None}
out["denials_7d_by_carrier"] = {k: {"lines": d["n"], "charge_amt": round(d["amt"], 2), "adjudicated": adj_lines7[k],
                                     "rate": round(d["n"] / adj_lines7[k], 3) if adj_lines7[k] else None,
                                     "top_reasons": sorted(den7_car_reason[k].items(), key=lambda kv: -kv[1])[:5]}
                                for k, d in sorted(den7.items(), key=lambda kv: -kv[1]["n"])}
out["denial_reasons_7d"] = [(k, d["n"], round(d["amt"], 2)) for k, d in sorted(den7_reason.items(), key=lambda kv: -kv[1]["n"])[:10]]

# ---------- carriers with A/R but no payment in 30 days ----------
silent = []
for c, d in ar_car.items():
    lp = pay_last.get(c)
    if d["bal"] >= 500 and (lp is None or lp < D30):
        silent.append({"carrier": c, "name": cname.get(c, ""), "ar": round(d["bal"], 2), "n": d["n"], "last_paid": lp.isoformat() if lp else "none in scan", "paid_30d": round(pay30.get(c, 0.0), 2)})
out["silent_carriers_30d"] = sorted(silent, key=lambda x: -x["ar"])
out["last_paid_by_carrier"] = {c: lp.isoformat() for c, lp in sorted(pay_last.items())}
out["paid_30d_by_carrier"] = {k: round(v, 2) for k, v in sorted(pay30.items(), key=lambda kv: -kv[1])}

# ---------- ERA Center (unposted list) ----------
out["era_center"] = {"checks": len(cs), "paid": round(sum(money(c.get("paymentamount")) for c in cs), 2), "unposted": round(sum(money(c.get("unpostedamount")) for c in cs), 2)}
by = collections.defaultdict(lambda: {"checks": 0, "paid": 0.0, "unposted": 0.0})
for c in cs:
    k = c.get("systemcarriercode") or c.get("eracarriername") or "OTHER"; by[k]["checks"] += 1; by[k]["paid"] += money(c.get("paymentamount")); by[k]["unposted"] += money(c.get("unpostedamount"))
out["era_center_by_carrier"] = {k: {"checks": v["checks"], "paid": round(v["paid"], 2), "unposted": round(v["unposted"], 2)} for k, v in sorted(by.items(), key=lambda kv: -kv[1]["unposted"])}
recv7 = [c for c in cs if (pd(c.get("receiveddate")) or datetime.date(1900, 1, 1)) >= D7]
out["era_center_received_7d"] = {"checks": len(recv7), "paid": round(sum(money(c.get("paymentamount")) for c in recv7), 2)}

# ---------- nightly auto-post e-mails ----------
nights = sorted(night["nights"], key=lambda n: n["email_date"])
out["era_autopost"] = {"latest_night": nights[-1]["night_of"], "latest_failed": nights[-1]["failed"], "latest_ok": nights[-1]["ok"], "latest_checks": nights[-1]["checks"],
                       "first_night": nights[0]["night_of"], "first_failed": nights[0]["failed"], "first_ok": nights[0]["ok"],
                       "week_ok_lines": sum(n["ok"] for n in nights if n["night_of"] >= D7.isoformat()),
                       "series": [(n["night_of"], n["checks"], n["ok"], n["failed"]) for n in nights]}

# ---------- claim runs ----------
r7 = [r for r in runs if (pd(r.get("date")) or datetime.date(1900, 1, 1)) >= D7]
r90 = [r for r in runs if (pd(r.get("date")) or datetime.date(1900, 1, 1)) >= D90]
out["claim_runs_7d"] = {"runs": len(r7), "claims": sum(int(r.get("totalsent") or 0) for r in r7), "amount": round(sum(money(r.get("totalamount")) for r in r7), 2), "exclusions": sum(int(r.get("totalexclusions") or 0) for r in r7)}
out["claim_runs_90d"] = {"runs": len(r90), "claims": sum(int(r.get("totalsent") or 0) for r in r90), "amount": round(sum(money(r.get("totalamount")) for r in r90), 2)}
out["claim_runs_7d_list"] = [(r["date"][:10], r["id"], r.get("totalsent"), r.get("totalamount"), r.get("totalexclusions")) for r in sorted(r7, key=lambda r: r["date"])]


# ---------- PROPOSED metrics (cheap) ----------
lags = []
for pid, rec in cache.items():
    for ch in rec["charges"]:
        if ch.get("void") == "1": continue
        dos = pd(ch.get("dos")); ct = pd(ch.get("createtime"))
        if dos and ct and dos >= D90: lags.append((ct - dos).days)
lags.sort()
out["charge_lag_90d"] = {"n": len(lags), "median_days": lags[len(lags)//2] if lags else None, "p90_days": lags[int(len(lags)*0.9)] if lags else None, "mean_days": round(sum(lags)/len(lags), 1) if lags else None}
tot90 = sum(charges_90_by_car.values()) or 1
out["payer_mix_90d"] = [(k, round(v, 2), round(100*v/tot90, 1)) for k, v in sorted(charges_90_by_car.items(), key=lambda kv: -kv[1])[:8]]
cr = out["claim_runs_7d"]
out["clean_claim_rate_7d"] = round(1 - cr["exclusions"]/cr["claims"], 4) if cr["claims"] else None
# cross-check silent carriers against the 9/7 full-universe pay scan (payments_by_carrier_0907.json)
try:
    ref = json.load(open("payments_by_carrier_0907.json"))["carriers"]
    for s_ in out["silent_carriers_30d"]:
        r_ = ref.get(s_["carrier"]); s_["ref_0907_paid_12mo"] = r_["paid_12"] if r_ else "not in 9/7 scan"; s_["ref_0907_paid_all"] = r_["paid_all"] if r_ else ""
    out["silent_carriers_30d"] = [s_ for s_ in out["silent_carriers_30d"] if not (isinstance(s_["ref_0907_paid_12mo"], (int, float)) and s_["ref_0907_paid_12mo"] > 0 and s_["last_paid"] == "none in scan")]
except Exception as e:
    out["silent_xcheck_error"] = str(e)

json.dump(out, open("metrics_20260914.json", "w"), indent=1, default=str)

# ---------- CSV files (aggregates by carrier; no patient rows) ----------
with open("Weekly metrics 2026-09-14 - unpaid by carrier.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["carrier", "carrier_name", "open_visits", "open_ins_balance", "0-30", "31-60", "61-90", "91-120", "120+", "last_payment_posted", "paid_last_30d"])
    for c, d in out["ar_by_carrier"].items():
        w.writerow([c, cname.get(c, ""), d["n"], d["bal"]] + [d["buckets"][k] for k in B] + [out["last_paid_by_carrier"].get(c, ""), out["paid_30d_by_carrier"].get(c, 0.0)])
    w.writerow(["TOTAL", "", out["unpaid_n"], out["ar_total"]] + [out["ar_buckets"][k] for k in B] + ["", ""])
with open("Weekly metrics 2026-09-14 - AR by carrier.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["carrier", "carrier_name", "ar_total", "pct_of_ar", "0-30", "31-60", "61-90", "91-120", "120+", "charges_90d_on_scan", "payments_7d", "denial_lines_7d"])
    for c, d in out["ar_by_carrier"].items():
        w.writerow([c, cname.get(c, ""), d["bal"], round(100 * d["bal"] / total_ar, 1) if total_ar else 0] + [d["buckets"][k] for k in B] + [out["charges_90d_by_carrier"].get(c, 0.0), out["payments_7d_by_carrier"].get(c, {}).get("amt", 0.0), out["denials_7d_by_carrier"].get(c, {}).get("lines", 0)])
with open("Weekly metrics 2026-09-14 - denials.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["carrier", "carrier_name", "denial_lines_7d", "denied_charge_amt", "adjudicated_lines_7d", "denial_rate", "top_reasons"])
    for c, d in out["denials_7d_by_carrier"].items():
        w.writerow([c, cname.get(c, ""), d["lines"], d["charge_amt"], d["adjudicated"], d["rate"], "; ".join("%s x%d" % (k, n) for k, n in d["top_reasons"])])
    w.writerow([]); w.writerow(["reason (all carriers)", "lines", "charge_amt"])
    for k, n, a in out["denial_reasons_7d"]: w.writerow([k, n, a])
with open("Weekly metrics 2026-09-14 - ERA throughput.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["night_of", "checks_in_autopost", "ok_lines", "failed_lines"])
    for row in out["era_autopost"]["series"]: w.writerow(row)
    w.writerow([]); w.writerow(["ERA Center unposted list (as of run)", "checks", "paid", "unposted"])
    for k, v in out["era_center_by_carrier"].items(): w.writerow([k, v["checks"], v["paid"], v["unposted"]])
    w.writerow(["TOTAL", out["era_center"]["checks"], out["era_center"]["paid"], out["era_center"]["unposted"]])
    w.writerow([]); w.writerow(["posted payments last 7d (tx-history scan)", "amount", "lines", "checks"])
    w.writerow(["ERA/check-numbered", out["era_payments_7d"]["amt"], out["era_payments_7d"]["lines"], out["era_payments_7d"]["checks"]])
    w.writerow(["all insurance payments", out["payments_7d"], out["payments_7d_lines"], ""])
with open("Weekly metrics 2026-09-14 - writeoffs.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["writeoff_code", "amount_7d", "count_7d"])
    for k, v in out["writeoffs_7d_by_code"].items(): w.writerow([k, v["amt"], v["n"]])
    w.writerow([]); w.writerow(["carrier", "writeoff_amount_7d"])
    for k, v in out["writeoffs_7d_by_carrier"].items(): w.writerow([k, v])

print(json.dumps({k: out[k] for k in ("ar_total", "ar_buckets", "unpaid_n", "charges_90d", "charges_90d_n", "charges_7d", "days_in_ar", "payments_7d", "payments_7d_lines", "era_payments_7d", "adjustments_7d_writeoffs", "denials_7d", "era_center", "era_center_received_7d", "claim_runs_7d", "claim_runs_90d", "scan")}, indent=1))
print("TOP8 AR:", [(c, d["bal"]) for c, d in list(out["ar_by_carrier"].items())[:8]])
print("PAY7 by carrier:", list(out["payments_7d_by_carrier"].items())[:12])
print("DENIAL reasons:", out["denial_reasons_7d"])
print("DENIALS by carrier:", {k: (v["lines"], v["adjudicated"], v["rate"]) for k, v in list(out["denials_7d_by_carrier"].items())[:10]})
print("WO by code:", out["writeoffs_7d_by_code"])
print("SILENT carriers:", out["silent_carriers_30d"][:15])
print("ERA autopost:", {k: v for k, v in out["era_autopost"].items() if k != "series"})
print("claim runs 7d:", out["claim_runs_7d_list"])
print("charge lag:", out["charge_lag_90d"], "| payer mix:", out["payer_mix_90d"], "| clean claim:", out["clean_claim_rate_7d"])
