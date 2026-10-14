# PLAIN ENGLISH (Patient-balance review - the apply step, one bucket at a time; William 10/13/2026)
# Decides: nothing new. Applies one bucket of patbal_review_<stamp>.json (patbal_classify.py):
#   WRITE-OFF buckets (DUAL-WRITEOFF, WRONG-PAYER-UNTIMELY, DENIED-UNTIMELY, NEVER-SENT-UNTIMELY, SMALL-BALANCE): the charge's
#     patient balance is moved back to the insurance side (move_to_ins.move) and written off there with the bucket's code
#     (manual_post.post pay 0, wo = live balance) - the same two calls the insurances-cleaning pass uses.
#   RETRIEVABLE buckets (WRONG-PAYER, DENIED-FIX, NEVER-SENT-LIVE-PLAN, DUAL-SEND): the patient balance is moved back to
#     insurance only (move_to_ins.move) so the denial cascade / the next run sees it on the unpaid list; nothing is rebilled here.
# Rules it uses: dry by default (--live); every charge is RE-READ live first and skipped when its patient balance is gone or a
#   non-void payment landed since the scan; a charge with no carrier on the chart (self-pay) is listed, never posted - that
#   bucket (SELF-PAY-BAD-DEBT) needs the patient-side write-off William does in Payment Entry. Resumable via the log.
# Never touches: STATEMENT buckets, BILL-SECONDARY (the crossover / secondary claim path), voided charges.
"""Usage: python3 patbal_apply.py --bucket DUAL-WRITEOFF [--live] [--stamp 1013] [--max N]"""
import json, sys, re, os, datetime
import amd, manual_post, move_to_ins, resave
import xml.etree.ElementTree as ET
a = sys.argv[1:]
def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
STAMP = opt("--stamp", "1013"); BUCKET = opt("--bucket"); LIVE = "--live" in a; MX = int(opt("--max", 10**9))
WO = {"DUAL-WRITEOFF", "WRONG-PAYER-UNTIMELY", "DENIED-UNTIMELY", "NEVER-SENT-UNTIMELY", "SMALL-BALANCE"}
MOVE = {"WRONG-PAYER", "DENIED-FIX", "NEVER-SENT-LIVE-PLAN", "DUAL-SEND"}
assert BUCKET in WO | MOVE, "bucket must be one of %s" % sorted(WO | MOVE)
R = [r for r in json.load(open("patbal_review_%s.json" % STAMP))["rows"] if r["bucket"] == BUCKET]
LOGF = "patbal_apply_%s.log" % STAMP; done = set()
if os.path.exists(LOGF):
    for l in open(LOGF):
        m = re.match(r"DONE (\S+) (\S+)", l)
        if m and m.group(2) == BUCKET: done.add(m.group(1))
log = open(LOGF, "a")
def L(m): print(m, flush=True); log.write(m + "\n"); log.flush()
amd.login_cached(); n = 0; tot = 0.0; skipped = 0
for r in R:
    cid = str(r["cid"])
    if cid in done: continue
    if n >= MX: break
    rt = ET.fromstring(resave.detail(cid)); c = next((x for x in rt.iter("charge") if x.get("id") == "charge" + cid), None)
    if c is None: L("SKIP %s %s charge not found" % (cid, BUCKET)); skipped += 1; continue
    pat = float(c.get("patbalance") or 0); ins = float(c.get("insbalance") or 0)
    pays = [p for p in c.iter("payment") if p.get("void") != "1" and abs(float(p.get("amount") or 0)) > 0]
    if pat <= 0.004: L("SKIP %s %s no patient balance now (ins %.2f)" % (cid, BUCKET, ins)); skipped += 1; continue
    if BUCKET in WO and r.get("paid", 0) == 0 and pays: L("SKIP %s %s a payment landed since the scan" % (cid, BUCKET)); skipped += 1; continue
    car = (r.get("carrier") or "").strip()
    if BUCKET in WO and not car: L("SKIP %s %s no carrier on the charge - patient-side write-off by hand" % (cid, BUCKET)); skipped += 1; continue
    code = r.get("wocode") or "WOLATE"
    if not LIVE:
        L("DRY %s %s v%s pat%s %s %s patbal %.2f -> %s" % (cid, BUCKET, r["vid"], r["pid"], r["dos"], r["cpt"], pat, ("move to insurance + write off %s %s" % (code, car)) if BUCKET in WO else "move to insurance only"))
        n += 1; tot += pat; continue
    ok = move_to_ins.move(cid, rebill=False)
    if BUCKET in MOVE:
        L("DONE %s %s moved %.2f to insurance (%s)" % (cid, BUCKET, pat, ok)); n += 1; tot += pat; continue
    rt = ET.fromstring(resave.detail(cid)); c = next(x for x in rt.iter("charge") if x.get("id") == "charge" + cid); bal = float(c.get("insbalance") or 0)
    ok2, msg = manual_post.post(cid, car, 0.0, bal, code, checknumber="PATBAL%s" % STAMP, note="patient-balance review 10/13/2026 %s - William approved" % BUCKET)
    L("%s %s %s wo %.2f %s %s %s" % ("DONE" if ok2 else "FAIL", cid, BUCKET, bal, code, car, str(msg)[:60]))
    if ok2: n += 1; tot += bal
L("=== %s %s: %d charges $%.2f, %d skipped ===" % ("LIVE" if LIVE else "DRY", BUCKET, n, tot, skipped))
