# PLAIN ENGLISH (Aetna Senior Supplemental (AET12) secondaries - rebill after William fixed the carrier payer id to 62118, 9/7/2026)
# Decides: (1) Voids today's four "untimely" write-offs on Littell Ray - wrong call: a Medigap secondary's clock runs from Medicare's remit (posted 9/6/2026), not the date of service. (2) Every charge with an open AET12 insurance balance (the mass-write-off search William captured: 54 charges, 15 patients) plus Littell Ray's four is sent to AET12 as a frequency-1 secondary claim at the patient's AET12 plan sequence. Nothing is written off.
# Rules it uses: freq1_visit.run(vid, cid, seq) (original claim + rebill to that sequence); void_tx.void_writeoff for the reversal. Resumable via aet12_rebill_0907.log.
# Never touches: AET07 (Aetna commercial - separate carrier, mostly paid-but-unposted), insorder, balances.
# ---
"""Usage: python3 aet12_rebill_0907.py [--dry]"""
import amd, txh, resave, void_tx, freq1_visit, json, sys, re, time, os, collections
amd.login_cached(); dry = "--dry" in sys.argv
LOGF = "aet12_rebill_0907.log"; done = set(l.split()[1] for l in open(LOGF) if l.startswith(("REBILL ", "UNWO "))) if os.path.exists(LOGF) else set(); LOG = open(LOGF, "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
rows = json.load(open("masswriteoff_aet12_0907.json"))["chargedetails"]
# Littell Ray: void today's write-offs, then add her four charges to the batch
LIT = "17473277"
for c in txh.fetch(LIT).iter("charge"):
    if c.get("void") == "1" or c.get("dos") not in ("05/12/2025", "05/13/2025", "05/14/2025", "05/15/2025"): continue
    for w in c.iter("writeoff"):
        if w.get("void") != "1" and w.get("date") == "09/07/2026" and w.get("wocode") == "WOINS":
            if c.get("id") in done: continue
            if dry: L("DRY UNWO %s %s wo %s $%s" % (c.get("id"), c.get("dos"), w.get("id"), w.get("amount"))); continue
            ok, msg = void_tx.void_writeoff(LIT, c.get("id"), w.get("id")); L("%s %s LITTELL RAY,HARRIET %s wo %s $%s %s" % ("UNWO" if ok else "UNWOFAIL", c.get("id"), c.get("dos"), w.get("id"), w.get("amount"), "" if ok else msg[:80])); time.sleep(0.3)
    rows.append({"patientid": int(LIT), "patientname": "LITTELL RAY,HARRIET", "visitid": int(c.get("visit")), "chargedetailid": c.get("id"), "dateofservice": c.get("dos"), "insbalance": 0})
SEQ = {}
def aet_seq(pid):
    if pid not in SEQ:
        r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}))
        pl = re.findall(r'<insplan id="(ins\d+)" carrier="(car\d+)" begindate="([^"]*)" enddate="([^"]*)"[^>]*subscribernum="([^"]*)"[^>]*sequence="(\d+)"', r)
        SEQ[pid] = next((p[5] for p in pl if p[1] == "car42009" and not p[3]), None) or next((p[5] for p in pl if p[1] == "car42009"), None)
    return SEQ[pid]
byv = collections.OrderedDict()
for r in rows: byv.setdefault(str(r["visitid"]), []).append(r)
n = 0; miss = []
for vid, chs in byv.items():
    if vid in done: continue
    r = chs[0]; pid = str(r["patientid"]); seq = aet_seq(pid)
    if not seq: miss.append((r["patientname"], vid)); L("NOPLAN %s %s - no AET12 plan on the chart" % (r["patientname"], vid)); continue
    cid = str(r["chargedetailid"]).strip()
    if dry: L("DRY REBILL %s %s %s -> AET12 seq %s (%d charges)" % (vid, r["patientname"], str(r["dateofservice"])[:10], seq, len(chs))); n += 1; continue
    try: res = freq1_visit.run(vid, cid, seq); L("REBILL %s %s %s -> AET12 seq %s | %s" % (vid, r["patientname"], str(r["dateofservice"])[:10], seq, str(res)[:60])); n += 1
    except Exception as e: L("FAIL %s %s: %s" % (vid, r["patientname"], str(e)[:80]))
    time.sleep(0.5)
L("=== done: %d visits sent to AET12 (62118); no plan: %s ===" % (n, miss))
