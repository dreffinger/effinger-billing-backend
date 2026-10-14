# PLAIN ENGLISH (Patient-balance review - the executor; William 10/13/2026: "I want all 400k moved or written off")
# Decides: nothing new. Works the buckets of patbal_review_1013.json:
#   --mode writeoff : every write-off bucket (DUAL-WRITEOFF, WRONG-PAYER-UNTIMELY, DENIED-UNTIMELY, NEVER-SENT-UNTIMELY,
#                     SMALL-BALANCE, SELF-PAY-BAD-DEBT) -> a PATIENT-SIDE write-off per charge (patient_writeoff.post) with the
#                     bucket's code (WOCAID2ND / WOMCAD / WOLATE / WOSMBAL / WOBAD), check ref PATBAL1013.
#   --mode moveback : WRONG-PAYER, DENIED-FIX, NEVER-SENT-LIVE-PLAN -> the visit's patient balance moved back to insurance
#                     (move_to_ins.move, no rebill) so the cascade / the next runs re-route it.
#   --mode secondary: BILL-SECONDARY -> the visit moved back to insurance with insorder = <primary seq>,<secondary seq> and ONE
#                     rebill to the secondary sequence (move_to_ins.move(cid, seq, rebill_seq)) - AMD builds the secondary claim
#                     from the posted primary payment; a visit whose primary payment carries no reason codes holds in Unbilled.
# Rules it uses: every charge re-read live before a write (patient balance gone -> skip; a new payment since the scan -> skip);
#   one action per charge/visit, logged DONE so a rerun never repeats; 2 worker threads paced for the AMD gateway.
# Never touches: STATEMENT buckets (the patient's own cost-sharing - William's call), voided charges.
"""Usage: python3 patbal_execute.py --mode writeoff|moveback|secondary [--live] [--max N] [--threads 2]"""
import json, sys, re, os, time, threading, queue, collections
import amd, resave, move_to_ins, patient_writeoff
import xml.etree.ElementTree as ET
a = sys.argv[1:]
def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
MODE = opt("--mode"); LIVE = "--live" in a; MX = int(opt("--max", 10**9)); NT = int(opt("--threads", 2)); STAMP = "1013"
WO = {"DUAL-WRITEOFF", "WRONG-PAYER-UNTIMELY", "DENIED-UNTIMELY", "NEVER-SENT-UNTIMELY", "SMALL-BALANCE", "SELF-PAY-BAD-DEBT", "STATEMENT-MEDICARE"}
MOVE = {"WRONG-PAYER", "DENIED-FIX", "NEVER-SENT-LIVE-PLAN", "DUAL-SEND"}
MEDICAID = {"MCAD", "SUN01", "WEL04", "WEL07", "SIM01", "STA03", "FLO99", "FCC", "GEO05"}
D = json.load(open("patbal_review_%s.json" % STAMP)); scan = json.load(open("patbal_scan_%s.json" % STAMP))["charts"]
if MODE == "writeoff": rows = [r for r in D["rows"] if r["bucket"] in WO]
elif MODE == "writeoff-medicare": rows = [r for r in D["rows"] if r["bucket"] == "STATEMENT-MEDICARE"]
elif MODE == "writeoff-statement": rows = [r for r in D["rows"] if r["bucket"] == "STATEMENT"]
elif MODE == "moveback": rows = [r for r in D["rows"] if r["bucket"] in MOVE]
elif MODE == "secondary": rows = [r for r in D["rows"] if r["bucket"] == "BILL-SECONDARY"]
else: raise SystemExit("mode?")
LOGF = "patbal_execute_%s_%s.log" % (MODE, STAMP); done = set()
if os.path.exists(LOGF):
    for l in open(LOGF):
        m = re.match(r"DONE (\S+)", l)
        if m: done.add(m.group(1))
log = open(LOGF, "a"); lock = threading.Lock()
def L(m):
    with lock: print(m, flush=True); log.write(m + "\n"); log.flush()
def wocode(r): return r.get("wocode") or "WOLATE"
amd.login_cached()
tot = [0.0]; n = [0]; skipped = [0]; failed = [0]
def live_charge(cid):
    x = resave.detail(cid); c = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x)
    if not c: return None, x
    return dict(re.findall(r'(\w+)="([^"]*)"', c.group(0))), x
def do_writeoff(r):
    cid = str(r["cid"]); c, x = live_charge(cid)
    if c is None: L("SKIP %s charge not found" % cid); skipped[0] += 1; return
    pat = float(c.get("patbalance") or 0)
    if pat <= 0.004: L("SKIP %s no patient balance now" % cid); skipped[0] += 1; return
    code = wocode(r)
    if not LIVE: L("DRY %s %s v%s pat%s %s %s patbal %.2f -> %s" % (cid, r["bucket"], r["vid"], r["pid"], r["dos"], r["cpt"], pat, code)); n[0] += 1; tot[0] += pat; return
    ok, msg = patient_writeoff.post(cid, pat, code, checknumber="PATBAL%s" % STAMP, note="patient-balance review 10/13/2026 %s - William: all moved or written off" % r["bucket"])
    if ok: L("DONE %s %s %s %.2f pid %s" % (cid, r["bucket"], code, pat, r["pid"])); n[0] += 1; tot[0] += pat
    else: L("FAIL %s %s %s %.2f %s" % (cid, r["bucket"], code, pat, msg[:120])); failed[0] += 1
def do_moveback(r):
    cid = str(r["cid"]); c, x = live_charge(cid)
    if c is None: L("SKIP %s charge not found" % cid); skipped[0] += 1; return
    pat = float(c.get("patbalance") or 0)
    if pat <= 0.004: L("DONE %s already on insurance (moved with its visit)" % cid); n[0] += 1; return
    if not LIVE: L("DRY %s %s v%s patbal %.2f -> move to insurance" % (cid, r["bucket"], r["vid"], pat)); n[0] += 1; tot[0] += pat; return
    res = move_to_ins.move(cid, rebill=False)
    if str(res).startswith("moved"): L("DONE %s %s %s" % (cid, r["bucket"], res)); n[0] += 1; tot[0] += pat
    else: L("FAIL %s %s %s" % (cid, r["bucket"], str(res)[:120])); failed[0] += 1
def do_secondary(r):
    cid = str(r["cid"]); ch = scan.get(str(r["pid"])) or {}
    plans = ch.get("plans") or []
    # the plan that paid (primary) and the first non-Medicaid plan after it (the supplement / secondary)
    paid = set(r.get("pay_carriers") or []); MEDICARE = {"FLO02", "RET01"}
    prim = next((p for p in plans if p["code"] in MEDICARE and p["code"] in paid), None) or next((p for p in plans if p["code"] in paid), None) or (plans[0] if plans else None)
    secs = [p for p in plans if p is not prim and p["code"] not in MEDICAID and p["code"] not in MEDICARE and p["code"] not in paid and p["code"] in (r.get("plans") or [])]
    if prim and not secs and any(p["code"] in paid for p in plans if p is not prim):
        L("SKIP %s the secondary (%s) already answered - the residual is the patient's (statement)" % (cid, "/".join(sorted(paid - {prim["code"]})))); skipped[0] += 1; return
    if not prim or not secs: L("SKIP %s no primary/secondary pair on the chart (%s)" % (cid, [p["code"] for p in plans])); skipped[0] += 1; return
    sec = secs[0]; seq = "%s,%s" % (prim["seq"], sec["seq"])
    c, x = live_charge(cid)
    if c is None: L("SKIP %s charge not found" % cid); skipped[0] += 1; return
    pat = float(c.get("patbalance") or 0); insb = float(c.get("insbalance") or 0)
    if pat <= 0.004 and insb <= 0.004: L("DONE %s settled since the scan" % cid); n[0] += 1; return
    vis = re.search(r'<visit [^>]*>', x).group(0); order = re.search(r'insorder="([^"]*)"', vis).group(1)
    if not LIVE: L("DRY %s v%s patbal %.2f insorder %s -> %s rebill seq %s (%s -> %s)" % (cid, r["vid"], pat, order, seq, sec["seq"], prim["code"], sec["code"])); n[0] += 1; tot[0] += pat; return
    res = move_to_ins.move(cid, seq=seq, rebill_seq=sec["seq"])
    if str(res).startswith("moved"): L("DONE %s v%s %s -> %s : %s" % (cid, r["vid"], prim["code"], sec["code"], res)); n[0] += 1; tot[0] += pat
    else: L("FAIL %s v%s %s" % (cid, r["vid"], str(res)[:140])); failed[0] += 1
fn = {"writeoff": do_writeoff, "writeoff-medicare": do_writeoff, "writeoff-statement": do_writeoff, "moveback": do_moveback, "secondary": do_secondary}[MODE]
todo = [r for r in rows if str(r["cid"]) not in done][:MX]
seen_visit = set()
if MODE not in ("writeoff", "writeoff-medicare", "writeoff-statement"):   # one move per VISIT (move_to_ins moves every charge on the visit)
    t2 = []
    for r in todo:
        if r["vid"] in seen_visit: continue
        seen_visit.add(r["vid"]); t2.append(r)
    todo = t2
L("=== %s %s: %d to do (%d already done) ===" % ("LIVE" if LIVE else "DRY", MODE, len(todo), len(done)))
q = queue.Queue(); [q.put(r) for r in todo]
def worker():
    while True:
        try: r = q.get_nowait()
        except queue.Empty: return
        try: fn(r)
        except Exception as e: L("ERR %s %s" % (r.get("cid"), str(e)[:120])); failed[0] += 1
        time.sleep(0.4)
ts = [threading.Thread(target=worker, daemon=True) for _ in range(NT)]; [t.start() for t in ts]; [t.join() for t in ts]
L("=== %s %s done: %d actions $%.2f, %d skipped, %d failed ===" % ("LIVE" if LIVE else "DRY", MODE, n[0], tot[0], skipped[0], failed[0]))
