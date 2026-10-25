# PLAIN ENGLISH (Sunday claim-status sweep actions, nightly cascade 2026-10-25)
# Decides: What to do with each row of tonight's claim-status sweep (claimstatus_<stamp>.json): PAID rows become the
# Paid_but_unposted_<date>.csv list for William (unposted remits - never rebilled); NOT ON FILE rows are re-sent as ORIGINAL
# claims (freq1_visit.run) unless a standing hold applies; FINALIZED-$0 / DENIED rows are rolled up per patient for the
# board + report (the payer adjudicated the claim under the chart's member id, so the plan is live and the denial is about
# the claim itself - William's remit reasons are needed, not an insurance lookup); PENDING / ERROR / UNKNOWN rows are listed.
# Rules it uses: never rebill a visit with a payment posted; never touch UNI20/BCBS visits dated before 5/1/2026 (unposted
# ERA backlog); never re-send a claim older than 12 months (held - the aging pass owns the write-off decision); never re-send a
# visit billed in the last 14 days (the 10/18 Sunday resend may still be in the payer's intake); one rebill per visit per run
# (amd.rebill_charge guard); deceased guard inside amd.rebill_charge. Dry by default - --live sends.
# Never touches: balances, plans, codes, the ERA Center.
"""Usage: python3 sweep_act_1025.py [--live] [--max N]"""
import amd, txh, resave, freq1_visit, json, sys, csv, datetime, time, os, collections
STAMP = "20261025"; RUN = "2026-10-25T0535Z"
LIVE = "--live" in sys.argv; mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
today = datetime.date(2026, 10, 25); CUT12 = (today - datetime.timedelta(days=365)).isoformat(); RECENT = (today - datetime.timedelta(days=14)).isoformat()
rows = json.load(open("claimstatus_%s.json" % STAMP))
def act(r): return (r.get("action") or "")
paid = [r for r in rows if act(r).startswith("PAID")]
nof = [r for r in rows if act(r).startswith("NOT ON FILE")]
den = [r for r in rows if act(r).startswith(("FINALIZED", "DENIED"))]
pend = [r for r in rows if act(r).startswith("PENDING")]
other = [r for r in rows if r not in paid + nof + den + pend]
# 1. PAID but unposted -> CSV for William
with open("Paid_but_unposted_%s.csv" % STAMP, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["patient", "amdid", "visitid", "carrier", "dos", "balance", "payer_paid", "check_numbers", "paid_dates", "payer_claim"])
    for r in sorted(paid, key=lambda r: (r["carrier"], r["patient"])):
        st = [s for s in (r.get("status") or []) if s.get("cat") in ("F0", "F1") and float(s.get("paid") or 0) > 0]
        w.writerow([r["patient"], r["patientid"], r["visitid"], r["carrier"], r["dos"], "%.2f" % r["balance"], "%.2f" % sum(float(s["paid"]) for s in st),
                    ";".join(sorted({s.get("check") or "" for s in st})), ";".join(sorted({s.get("paidDate") or "" for s in st})), ";".join(sorted({s.get("payerClaim") or "" for s in st}))])
print("PAID-unposted: %d rows $%.2f on the books, payer says paid $%.2f -> Paid_but_unposted_%s.csv" % (len(paid), sum(r["balance"] for r in paid),
      sum(float(s.get("paid") or 0) for r in paid for s in (r.get("status") or []) if s.get("cat") in ("F0", "F1")), STAMP))
print("  by carrier:", dict(collections.Counter(r["carrier"] for r in paid)))
# 2. NOT ON FILE -> freq-1 resend with holds
amd.login_cached()
reg = {"run": RUN, "live": LIVE, "sent": [], "held": [], "skipped": [], "failed": []}
byp = collections.defaultdict(list)
for r in nof: byp[r["patientid"]].append(r)
n = 0; shown = False
for pid, claims in sorted(byp.items(), key=lambda kv: -sum(r["balance"] for r in kv[1])):
    try: root = txh.fetch(pid)
    except Exception as e: reg["failed"].append({"pid": pid, "why": "txh " + str(e)[:80]}); continue
    vc = {}
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        a = c.attrib
        if not shown: print("  charge attrs:", sorted(a.keys())[:40]); shown = True
        vid = str(a.get("visitid") or a.get("visit"))
        pays = [p for p in c.iter("payment") if p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0.004]   # a $0 denial posting is not a payment
        paidln = bool(pays); payinfo = ["%s %s %.2f" % (p.get("carrier") or "PAT", p.get("date") or "", abs(float(p.get("amount") or 0))) for p in pays][:4]
        bd = a.get("billdate") or a.get("lastbilldate") or a.get("lastbilled") or ""
        if vid not in vc: vc[vid] = {"cid": a.get("id"), "paid": paidln, "pays": payinfo, "billdate": bd, "carrier": a.get("carrier") or a.get("carriercode") or "", "paidamt": a.get("paid"), "insbal": a.get("insbal"), "patbal": a.get("patbal")}
        else: vc[vid]["paid"] = vc[vid]["paid"] or paidln; vc[vid]["pays"] += payinfo
    for r in claims:
        vid = str(r["visitid"]); base = {"vid": vid, "pid": pid, "patient": r["patient"], "carrier": r["carrier"], "dos": r["dos"], "balance": r["balance"]}
        ch = vc.get(vid)
        if not ch: reg["skipped"].append(dict(base, why="no live charge for this visit")); continue
        base["cid"] = ch["cid"]; base["billdate"] = ch["billdate"]
        base["lastbilled_carrier"] = ch["carrier"]; base["charge_paid"] = ch["paidamt"]; base["insbal"] = ch["insbal"]; base["patbal"] = ch["patbal"]
        if ch["paid"]: reg["skipped"].append(dict(base, why="payment posted on the visit - never rebill", pays=ch["pays"])); continue
        if r["carrier"] in ("UNI20", "BCBS") and r["dos"] < "2026-05-01": reg["held"].append(dict(base, why="UNI20/BCBS pre-5/1/2026 unposted-ERA backlog hold")); continue
        if r["dos"] < CUT12: reg["held"].append(dict(base, why="DOS older than 12 months - untimely, aging pass decides the write-off")); continue
        bdiso = ""
        try:
            if ch["billdate"]: bdiso = datetime.datetime.strptime(ch["billdate"][:10], "%m/%d/%Y").date().isoformat() if "/" in ch["billdate"] else ch["billdate"][:10]
        except Exception: bdiso = ""
        if bdiso and bdiso >= RECENT: reg["held"].append(dict(base, why="billed %s (last 14 days, 10/18 resend still in the payer's intake)" % bdiso)); continue
        if n >= mx: reg["held"].append(dict(base, why="--max reached")); continue
        n += 1
        try:
            vis, pat, allc = resave.visit_charges(ch["cid"]); order = (vis.get("insorder") or "1").split(","); seq = order[0]
            base["insorder"] = vis.get("insorder")
            if any(c.get("void") == "1" for c in allc): pass
            if not LIVE: reg["sent"].append(dict(base, seq=seq, result="DRY")); continue
            res = freq1_visit.run(vid, ch["cid"], seq); reg["sent"].append(dict(base, seq=seq, result=res)); time.sleep(0.5)
        except Exception as e: reg["failed"].append(dict(base, why=str(e)[:120]))
    time.sleep(0.2)
os.makedirs("registers", exist_ok=True)
json.dump(reg, open("registers/sweep_resend_%s%s.json" % (RUN, "" if LIVE else "_dry"), "w"), indent=1)
print("NOT ON FILE: %d rows; %s %d ($%.2f), held %d ($%.2f), skipped %d, failed %d" % (len(nof), "SENT" if LIVE else "would send", len(reg["sent"]), sum(x["balance"] for x in reg["sent"]),
      len(reg["held"]), sum(x["balance"] for x in reg["held"]), len(reg["skipped"]), len(reg["failed"])))
print("  send by carrier:", dict(collections.Counter(x["carrier"] for x in reg["sent"])))
print("  hold reasons:", dict(collections.Counter(x["why"].split(" (")[0][:60] for x in reg["held"])))
for x in reg["skipped"][:40] + reg["failed"][:10]: print("   ", x.get("patient", x.get("pid")), x.get("carrier", ""), x.get("dos", ""), x["why"], "| lastbilled", x.get("lastbilled_carrier"), "paid", x.get("charge_paid"), "insbal", x.get("insbal"), "patbal", x.get("patbal"), "|", "; ".join(x.get("pays", [])))
print("  skipped by patient:", dict(collections.Counter(x["patient"] for x in reg["skipped"])))
# 3. denials roll-up per patient
dpat = collections.defaultdict(list)
for r in den: dpat[(r["patientid"], r["patient"])].append(r)
roll = []
for (pid, nm), cl in sorted(dpat.items(), key=lambda kv: -sum(r["balance"] for r in kv[1])):
    codes = collections.Counter("%s %s" % (s.get("code"), (s.get("codev") or "")[:50]) for r in cl for s in (r.get("status") or []) if s.get("cat") in ("F0", "F1", "F2", "F3", "F4"))
    dx = any("diagnos" in (s.get("codev") or "").lower() for r in cl for s in (r.get("status") or []))
    roll.append({"pid": pid, "patient": nm, "carriers": dict(collections.Counter(r["carrier"] for r in cl)), "visits": [r["visitid"] for r in cl], "dos": sorted(r["dos"] for r in cl),
                 "balance": round(sum(r["balance"] for r in cl), 2), "untimely": sum(1 for r in cl if r["dos"] < CUT12), "codes": codes.most_common(4), "dx_denial": dx})
json.dump({"run": RUN, "denials": roll, "pending": [{"vid": r["visitid"], "patient": r["patient"], "carrier": r["carrier"], "dos": r["dos"], "balance": r["balance"]} for r in pend],
           "other": [{"vid": r["visitid"], "patient": r["patient"], "carrier": r["carrier"], "dos": r["dos"], "balance": r["balance"], "action": act(r)[:80]} for r in other]},
          open("registers/sweep_denials_%s.json" % RUN, "w"), indent=1)
with open("Sweep_denials_%s.csv" % STAMP, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["patient", "amdid", "carriers", "visits", "first_dos", "last_dos", "balance", "untimely_visits", "payer_status_codes", "diagnosis_wording"])
    for x in roll: w.writerow([x["patient"], x["pid"], json.dumps(x["carriers"]), len(x["visits"]), x["dos"][0], x["dos"][-1], "%.2f" % x["balance"], x["untimely"], " | ".join("%s x%d" % (c, k) for c, k in x["codes"]), "yes" if x["dx_denial"] else ""])
print("DENIED/FINALIZED-$0: %d rows / %d patients / $%.2f; by carrier %s; diagnosis-wording rows %d; untimely visits %d" % (len(den), len(roll), sum(x["balance"] for x in roll),
      dict(collections.Counter(r["carrier"] for r in den)), sum(1 for x in roll if x["dx_denial"]), sum(x["untimely"] for x in roll)))
print("  top status codes:", collections.Counter(c for x in roll for c, k in x["codes"] for _ in range(k)).most_common(8))
print("PENDING %d ($%.2f); ERROR/UNKNOWN %d ($%.2f)" % (len(pend), sum(r["balance"] for r in pend), len(other), sum(r["balance"] for r in other)))
