# PLAIN ENGLISH (Sunday sweep: resend NOT ON FILE claims as originals)
# Decides: Which 'NOT ON FILE' rows of claimstatus_<today>.json are inside the 12-month window with an open balance, and re-sends each as a frequency-1 original to the first plan of the visit order.
# Rules it uses: DOS within 365 days; UNI20/BCBS visits older than 5/1/2026 are never touched (unposted-ERA backlog); deceased guard inside amd.rebill_charge; resumable via resend_sweep_1018.log.
# Never touches: paid visits, claims older than 12 months, UNI20/BCBS before 5/1/2026.
# ---
import amd, txh, freq1_visit, resave, json, sys, datetime, time, os, collections
amd.login_cached(); today = datetime.date.today(); CUT = (today - datetime.timedelta(days=365)).isoformat()
dry = "--dry" in sys.argv; stamp = today.strftime("%Y%m%d")
rows = json.load(open("claimstatus_%s.json" % stamp))
todo = []; held = []
for r in rows:
    if not r["action"].startswith("NOT ON FILE") or r["balance"] <= 0: continue
    if r["dos"] < CUT: held.append((r, "older than 12 months")); continue
    if r["carrier"] in ("UNI20", "BCBS") and r["dos"] < "2026-05-01": held.append((r, "UNI20/BCBS backlog rule")); continue
    todo.append(r)
LOGF = "resend_sweep_1018.log"
done = set(l.split()[1] for l in open(LOGF) if l.startswith("SENT ")) if os.path.exists(LOGF) else set()
LOG = open(LOGF, "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
for r, why in held: L("HELD %s %s %s %s $%.2f (%s)" % (r["visitid"], r["patient"], r["carrier"], r["dos"], r["balance"], why))
byp = collections.defaultdict(list)
for r in todo: byp[r["patientid"]].append(r)
sent = 0; amt = 0.0
for pid, claims in byp.items():
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
        vis, pat, allc = resave.visit_charges(cid); seq = (vis.get("insorder") or "1").split(",")[0]
        if dry: L("DRY %s %s %s %s seq %s $%.2f" % (vid, r["patient"], r["carrier"], r["dos"], seq, r["balance"])); continue
        try: res = freq1_visit.run(vid, cid, seq); L("SENT %s %s %s %s seq %s $%.2f -> %s" % (vid, r["patient"], r["carrier"], r["dos"], seq, r["balance"], res)); sent += 1; amt += r["balance"]
        except Exception as e: L("FAIL %s %s: %s" % (vid, r["patient"], str(e)[:100]))
        time.sleep(0.5)
L("=== done: %d resent, $%.2f, %d held ===" % (sent, amt, len(held)))
