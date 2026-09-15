# PLAIN ENGLISH (Availity check register vs AMD - what money never landed)
# Decides: Nothing. For every Florida Blue / Health Options check in registers/availity_checks_<stamp>.json it asks AMD
#   (a) is the check still sitting unposted in the ERA Center (GET /api/era/checks), and (b) for every paid line, does the
#   live charge (line control number = AMD charge id) carry a non-void payment with that check number (gettxhistory).
#   Lines with money on the remit and no matching payment in AMD are the "missing" list the manual-post step works from.
# Rules it uses: read-only; caches charge->patient and patient tx history on disk so re-runs are cheap.
# Never touches: AMD writes.
"""Usage: python3 avail_vs_amd.py [stamp] [--only-new]"""
import amd, resave, txh, era_post, json, os, re, sys, time
STAMP = [a for a in sys.argv[1:] if not a.startswith("--")][0] if [a for a in sys.argv[1:] if not a.startswith("--")] else "2026-09-15T0310Z"
REG = "registers/availity_checks_%s.json" % STAMP
OUT = "registers/availity_vs_amd_%s.json" % STAMP
CACHE = "registers/avail_cache.json"
amd.login_cached()
cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {"cid_pid": {}, "pid_tx": {}}
prev = json.load(open(OUT)) if os.path.exists(OUT) and "--only-new" in sys.argv else {}
LOG = open("avail_vs_amd.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()

# (a) ERA Center unposted list
era = era_post.checks()
era_txt = json.dumps(era)
def in_era(trace): return trace in era_txt
L("ERA Center unposted checks: %d" % len(era))

def pid_of(cid):
    if cid in cache["cid_pid"]: return cache["cid_pid"][cid]
    try:
        rt = resave.detail(cid)
        m = re.search(r'<patient id="(?:pat)?(\d+)"', rt)
        pid = m.group(1) if m else None
    except Exception as e:
        pid = None
    cache["cid_pid"][cid] = pid; return pid

def tx_of(pid, fresh=False):
    if pid in cache["pid_tx"] and not fresh: return cache["pid_tx"][pid]
    root = txh.fetch(pid); d = {}
    for c in root.iter("charge"):
        a = c.attrib
        d[re.sub(r"\D", "", a.get("id") or "")] = {
            "dos": a.get("dos") or a.get("dateofservice"), "proccode": a.get("proccode"), "carrier": a.get("carrier") or a.get("carriercode"),
            "insbal": a.get("insbal"), "patbal": a.get("patbal"), "void": a.get("void"), "amount": a.get("fee"), "paid": a.get("paid"),
            "payments": [{"chk": p.get("checknumber"), "amt": p.get("amount"), "void": p.get("void"), "date": p.get("date") or p.get("depositdate"), "carrier": p.get("carrier") or p.get("carriercode")} for p in c.iter("payment")],
            "writeoffs": [{"code": w.get("wocode") or w.get("code"), "amt": w.get("amount"), "void": w.get("void")} for w in c.iter("writeoff")]}
    cache["pid_tx"][pid] = d; return d

R = json.load(open(REG)); res = []; n = 0
for ck in R:
    if ck.get("claim_only"): continue
    if prev and any(p["trace"] == ck["trace"] for p in prev.get("checks", [])):
        res.append([p for p in prev["checks"] if p["trace"] == ck["trace"]][0]); continue
    row = {"trace": ck["trace"], "payer": ck["payer"], "amount": ck["amount"], "check_date": ck["check_date"], "in_era_center": in_era(ck["trace"]),
           "n_claims": ck["n_claims"], "paid_lines": 0, "posted_lines": 0, "missing": [], "missing_total": 0.0, "posted_total": 0.0, "unresolved": []}
    for c in ck["claims"]:
        for ln in c["lines"]:
            if not ln["paid"] or ln["paid"] <= 0: continue
            row["paid_lines"] += 1; cid = ln["chargeid"]
            pid = pid_of(cid)
            if not pid:
                row["unresolved"].append({"cid": cid, "visit": c["visit"], "patient": c["patient"], "dos": ln["dos"], "cpt": ln["cpt"], "paid": ln["paid"], "why": "charge not found"}); continue
            tx = tx_of(pid); ch = tx.get(cid)
            if not ch:
                row["unresolved"].append({"cid": cid, "pid": pid, "visit": c["visit"], "patient": c["patient"], "dos": ln["dos"], "cpt": ln["cpt"], "paid": ln["paid"], "why": "charge not in tx history"}); continue
            hit = [p for p in ch["payments"] if p["chk"] and ck["trace"] in p["chk"] and p["void"] not in ("1", "true", "True")]
            if hit:
                row["posted_lines"] += 1; row["posted_total"] += ln["paid"]
            else:
                row["missing"].append({"cid": cid, "pid": pid, "visit": c["visit"], "patient": c["patient"], "dos": ln["dos"], "cpt": ln["cpt"], "paid": ln["paid"], "adj": ln["adj"],
                                       "insbal": ch["insbal"], "patbal": ch["patbal"], "carrier": ch["carrier"],
                                       "other_payments": [p for p in ch["payments"] if p["void"] not in ("1", "true", "True")]})
                row["missing_total"] += ln["paid"]
    row["missing_total"] = round(row["missing_total"], 2); row["posted_total"] = round(row["posted_total"], 2)
    res.append(row); n += 1
    L("%s %s $%.2f era=%s paid_lines %d posted %d missing %d ($%.2f) unresolved %d" % (ck["trace"], ck["check_date"], ck["amount"] or 0, row["in_era_center"], row["paid_lines"], row["posted_lines"], len(row["missing"]), row["missing_total"], len(row["unresolved"])))
    if n % 5 == 0: json.dump(cache, open(CACHE, "w"))
json.dump(cache, open(CACHE, "w"))
summ = {"checks": res, "totals": {"checks": len(res), "check_amount": round(sum(r["amount"] or 0 for r in res), 2),
        "posted": round(sum(r["posted_total"] for r in res), 2), "missing": round(sum(r["missing_total"] for r in res), 2),
        "missing_lines": sum(len(r["missing"]) for r in res), "in_era_center": sum(1 for r in res if r["in_era_center"]),
        "unresolved_lines": sum(len(r["unresolved"]) for r in res)}}
json.dump(summ, open(OUT, "w"), indent=1)
L("TOTALS %s" % json.dumps(summ["totals"]))
