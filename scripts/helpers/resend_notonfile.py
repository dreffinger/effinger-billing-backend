# PLAIN ENGLISH (Resend claims the payer never received)
# Decides: Which visits from the full status sweep the payer says are NOT ON FILE and are still inside the 12-month window, and re-sends each one as an ORIGINAL claim (frequency 1) to the plan it is already assigned to.
# Rules it uses: Only 'NOT ON FILE / rejected' rows from claimstatus_full_<date>.jsonl with DOS within 365 days and an open insurance balance; freq1_visit.run per visit (keeps admission dates); one charge id per visit via the transaction history. Resumable: resend_notonfile.log lines 'SENT <visitid>' are skipped.
# Never touches: Claims older than 12 months (held for William), paid visits, or visits whose charge id cannot be found.
# ---
"""Usage: python3 resend_notonfile.py [--max N] [--dry]"""
import amd, txh, freq1_visit, resave, json, sys, glob, datetime, time, os, re, collections
amd.login_cached(); today = datetime.date.today(); CUT = (today - datetime.timedelta(days=365)).isoformat()
mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9; dry = "--dry" in sys.argv
rs = {}
for l in open(sorted(glob.glob("claimstatus_full_*.jsonl"))[-1]):
    r = json.loads(l); rs[r["visitid"]] = r
skipc = set(sys.argv[sys.argv.index("--skip-carriers") + 1].split(",")) if "--skip-carriers" in sys.argv else set()
todo = [r for r in rs.values() if r["action"].startswith("NOT ON FILE") and r["dos"] >= CUT and r["balance"] > 0 and r["carrier"] not in skipc]
done = set(l.split()[1] for l in open("resend_notonfile.log") if l.startswith("SENT ")) if os.path.exists("resend_notonfile.log") else set()
LOG = open("resend_notonfile.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
byp = collections.defaultdict(list)
for r in todo: byp[r["patientid"]].append(r)
n = 0; sent = 0; amt = 0.0
for pid, claims in byp.items():
    if n >= mx: break
    try: root = txh.fetch(pid)
    except Exception as e: L("ERR txh %s %s" % (pid, str(e)[:80])); continue
    vc = {}
    for c in root.iter("charge"):
        if c.get("void") != "1": vc.setdefault(str(c.get("visit")), c.get("id"))
    for r in claims:
        vid = str(r["visitid"])
        if vid in done: continue
        cid = vc.get(vid)
        if not cid: L("SKIP %s %s no charge id" % (vid, r["patient"])); continue
        vis, pat, allc = resave.visit_charges(cid); order = (vis.get("insorder") or "1").split(",")
        seq = order[0]
        if dry: L("DRY %s %s %s %s seq %s $%.2f" % (vid, r["patient"], r["carrier"], r["dos"], seq, r["balance"])); n += 1; continue
        try: res = freq1_visit.run(vid, cid, seq); L("SENT %s %s %s %s seq %s $%.2f -> %s" % (vid, r["patient"], r["carrier"], r["dos"], seq, r["balance"], res)); sent += 1; amt += r["balance"]
        except Exception as e: L("FAIL %s %s: %s" % (vid, r["patient"], str(e)[:100]))
        n += 1; time.sleep(0.5)
        if n >= mx: break
L("=== done: %d resent, $%.2f ===" % (sent, amt))
