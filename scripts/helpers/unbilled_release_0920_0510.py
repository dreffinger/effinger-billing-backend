# PLAIN ENGLISH (1am ET 9/20/2026 run, 2026-09-20T0510Z): the 9/19 claim run (1700210) refreshed the Unbilled snapshot - 33 rows now read
#   'A payment from the prior payor is required before another claim can be submitted'.
# Decides: William's 9/8 rule - the primary claim is out (billed on/after the 9/13-9/19 re-routes and claim run) and unanswered, so there is
#   nothing to fix: release them with hideunbillablevisits hide=-1 (they re-queue on their own if the secondary still cannot bill after the
#   primary posts). Before releasing, each visit's live charges are read: a visit whose charges carry a payment older than 60 days with the
#   secondary still unbilled is NOT released (that is the write-off case, reported instead). 'Payment reason codes' rows are never touched
#   (9/15 rule). Register: registers/unbilled_release_2026-09-20T0510Z.json
# Never touches: rows with any other error text.
import amd, txh, json, re, time, sys, datetime
DRY = "--dry" in sys.argv
amd.login_cached()
S_ = json.load(open("scan_0912/summary_before.json"))
rows = [r for r in S_["unbilled"] if (r.get("_errs") or [""])[0].startswith("A payment from the prior payor")]
reg = {"stamp": "2026-09-20T0510Z", "candidates": len(rows), "released": [], "held": []}
def L(m): print(m, flush=True)
today = datetime.date.today(); tx = {}
go = []
for r in rows:
    vid, pid = r["id"], r["patientid"]
    if pid not in tx:
        try: tx[pid] = list(txh.fetch("pat" + pid).iter("charge"))
        except Exception as e: tx[pid] = []; L("txh err %s %s" % (pid, str(e)[:80]))
        time.sleep(0.3)
    chs = [c for c in tx[pid] if c.get("visit") == vid and c.get("void") != "1"]
    lastbill = max([c.get("billdate") or "" for c in chs] or [""])
    pays = [(p.get("date"), p.get("amount"), p.get("carrier")) for c in chs for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
    old_paid = False
    for dte, amt, car in pays:
        try:
            if (today - datetime.datetime.strptime(dte, "%m/%d/%Y").date()).days > 60: old_paid = True
        except Exception: pass
    rec = {"vid": vid, "pid": pid, "carriers": sorted({c.get("carrier") or "" for c in chs}), "lastbill": lastbill, "insbal": sum(float(c.get("insbal") or 0) for c in chs), "payments": pays[:4]}
    if old_paid and not any((today - datetime.datetime.strptime(dte, "%m/%d/%Y").date()).days <= 60 for dte, a, c in pays):
        rec["why"] = "primary paid > 60 days ago and the secondary is still unbilled - not released (write-off/secondary-window case for the report)"; reg["held"].append(rec); L("HOLD v%s %s" % (vid, rec)); continue
    go.append(rec)
L("release candidates %d, held %d" % (len(go), len(reg["held"])))
for i in range(0, len(go), 10):
    chunk = go[i:i + 10]
    if DRY: L("DRY release %s" % [c["vid"] for c in chunk]); continue
    xml = amd.call('action="hideunbillablevisits" class="claimsreports" hide="-1" nocookie="1"', "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % c["vid"] for c in chunk))
    ok = 'success="1"' in xml or '<Error/>' in xml or '<Error />' in xml
    for c in chunk: c["released"] = ok
    reg["released"].extend(chunk); L("release chunk %d ok=%s %s" % (len(chunk), ok, re.sub(r"\s+", " ", xml)[:140])); time.sleep(0.6)
json.dump(reg, open("registers/unbilled_release_2026-09-20T0510Z.json", "w"), indent=1)
L("=== release done: released %d, held %d" % (len(reg["released"]), len(reg["held"])))
