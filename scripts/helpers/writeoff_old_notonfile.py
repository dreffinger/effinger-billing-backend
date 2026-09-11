# PLAIN ENGLISH (Write off the 'never received' claims that are past every payer's filing limit)
# Decides: Every claim the full status sweep marked NOT ON FILE whose date of service is more than 12 months old gets its open insurance balance written off as untimely (William, 9/7/2026: "we could probably just write those off if no chance of being paid").
# Rules it uses: manual_post.post WOINS with a dated note on each open charge of the visit. Resumable: 'WO <chargeid>' lines in writeoff_old_notonfile.log are skipped. Reversible: the ERA reversal pipeline restores any of these that a late remit later shows as paid.
# Never touches: Claims inside 12 months, paid charges, or anything not in the sweep.
# ---
"""Usage: python3 writeoff_old_notonfile.py [--dry]"""
import amd, txh, resave, manual_post, json, sys, glob, datetime, time, os, re, collections
amd.login_cached(); today = datetime.date.today(); CUT = (today - datetime.timedelta(days=365)).isoformat(); dry = "--dry" in sys.argv
rs = [json.loads(l) for l in open(sorted(glob.glob("claimstatus_full_*.jsonl"))[-1])]
old = [r for r in rs if r["action"].startswith("NOT ON FILE") and r["dos"] < CUT and r["balance"] > 0]
LOGF = "writeoff_old_notonfile.log"; done = set(l.split()[1] for l in open(LOGF) if l.startswith("WO ")) if os.path.exists(LOGF) else set(); LOG = open(LOGF, "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
byp = collections.defaultdict(list)
for r in old: byp[r["patientid"]].append(r)
n = 0; tot = 0.0
for pid, claims in byp.items():
    vids = {str(r["visitid"]): r for r in claims}
    try: root = txh.fetch(pid)
    except Exception as e: L("ERR txh %s %s" % (pid, str(e)[:80])); continue
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or str(a.get("visit")) not in vids or a["id"] in done: continue
        x = resave.detail(a["id"]); m = re.search(r'<charge [^>]*>', x).group(0); bal = float(re.search(r'insbalance="([^"]*)"', m).group(1) or 0)
        if bal <= 0: continue
        r = vids[str(a.get("visit"))]
        if dry: L("DRY %s %s %s %s $%.2f" % (a["id"], r["patient"], r["carrier"], a.get("dos"), bal)); n += 1; tot += bal; continue
        ok, msg = manual_post.post(a["id"], r["carrier"], 0.0, bal, "WOINS", note="untimely - never received by payer, over 12 months (9/7 William)")
        L("%s %s %s %s %s $%.2f %s" % ("WO" if ok else "FAIL", a["id"], r["patient"], r["carrier"], a.get("dos"), bal, "" if ok else msg[:80])); n += 1; tot += bal if ok else 0; time.sleep(0.3)
L("=== done: %d charges, $%.2f ===" % (n, tot))
