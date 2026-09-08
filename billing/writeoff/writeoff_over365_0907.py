# PLAIN ENGLISH (Write off every open claim more than a year old - all carriers, William 9/7/2026)
# Decides: William's call tonight: "write off every claim past one year with any carrier - no chance of it being resubmitted for actual payment." Every visit on the unpaid list with a date of service more than 365 days old gets its open insurance balance written off (WOINS, dated note) - UNLESS the visit is a secondary remnant with a primary payment posted inside the last 12 months (the secondary's clock runs from that remit - William's rule earlier tonight); those are listed for rebill instead.
# Rules it uses: manual_post.post WOINS per open charge; balance carrier = the unpaid list's carriercode. Resumable via writeoff_over365_0907.log ('WO <chargeid>'). Reversible: void_tx.void_writeoff / the ERA reversal pipeline.
# Never touches: Claims inside 12 months, paid charges, secondaries with a recent primary remit.
# ---
"""Usage: python3 writeoff_over365_0907.py [--dry] [--max N]"""
import amd, txh, resave, manual_post, json, sys, datetime, time, os, re, collections
amd.login_cached(); today = datetime.date(2026, 9, 7); dry = "--dry" in sys.argv; mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
RECENT = datetime.date(2025, 9, 8)
unp = json.load(open("unpaid_20260908.json"))
old = [v for v in unp if (today - datetime.datetime.fromisoformat(v["dateofservice"]).date()).days > 365 and v["insbalance"] > 0]
LOGF = "writeoff_over365_0907.log"; done = set(l.split()[1] for l in open(LOGF) if l.startswith("WO ")) if os.path.exists(LOGF) else set(); LOG = open(LOGF, "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
NOTE = "untimely - over 12 months, past all filing limits (9/7 William: write off every claim past one year)"
byp = collections.defaultdict(list)
for v in old: byp[str(v["patientid"])].append(v)
n = 0; tot = 0.0; keep = []; nv = 0
def pdate(s):
    try: return datetime.datetime.strptime(s, "%m/%d/%Y").date()
    except Exception: return None
for pid, vs in byp.items():
    if nv >= mx: break
    try: root = txh.fetch(pid)
    except Exception as e: L("ERR txh %s %s" % (pid, str(e)[:80])); continue
    vids = {str(v["visitid"]): v for v in vs}
    chs = collections.defaultdict(list)
    for c in root.iter("charge"):
        if c.get("void") != "1" and str(c.get("visit")) in vids: chs[str(c.get("visit"))].append(c)
    for vid, v in vids.items():
        nv += 1; car = v["carriercode"].strip() or "OTHER"
        pays = [pdate(p.get("date")) for c in chs[vid] for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
        recent = [d for d in pays if d and d >= RECENT]
        if recent:
            keep.append((v["patientname"], v["dateofservice"][:10], car, v["insbalance"], max(recent).isoformat())); L("KEEP %s %s %s $%.2f - primary paid %s, secondary still timely" % (v["patientname"], v["dateofservice"][:10], car, v["insbalance"], max(recent))); continue
        for c in chs[vid]:
            cid = c.get("id")
            if cid in done: continue
            bal = float(c.get("insbal") or 0)
            if bal <= 0: continue
            if dry: L("DRY WO %s %s %s %s $%.2f" % (cid, v["patientname"], car, c.get("dos"), bal)); n += 1; tot += bal; continue
            ok, msg = manual_post.post(cid, car, 0.0, bal, "WOINS", note=NOTE)
            L("%s %s %s %s %s $%.2f %s" % ("WO" if ok else "FAIL", cid, v["patientname"], car, c.get("dos"), bal, "" if ok else msg[:80])); n += 1; tot += bal if ok else 0; time.sleep(0.25)
L("=== done: %d charges written off $%.2f; kept for rebill (recent primary remit): %d ===" % (n, tot, len(keep)))
json.dump(keep, open("over365_keep_for_rebill_0907.json", "w"), indent=1)
