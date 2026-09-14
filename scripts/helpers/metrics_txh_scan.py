# PLAIN ENGLISH (Weekly metrics transaction-history scan)
# Decides: Nothing. Reads gettxhistory for every patient on today's unpaid list and caches charges,
# payments (with CARC pay-reasons), write-offs and unapplied credits so the weekly metrics run can
# total charges (90d), payments/denials (7d, by carrier and reason), write-offs (7d, by reason) and
# last-payment date per carrier without Report Center.
# Rules it uses: read-only; one call per patient; ~0.4 s spacing (off-peak); HTTP 429 / faults -> wait and retry the same patient (max 3).
# Never touches: AMD writes.
# ---
import amd, txh, json, sys, os, time
import xml.etree.ElementTree as ET

WS = "/home/claude/unbilled"
CF = os.path.join(WS, "metrics_txh_cache_20260914.json")
LOGF = os.path.join(WS, "metrics_txh_scan.log")
unp = json.load(open(os.path.join(WS, "unpaid_20260914.json")))
pids = sorted({int(v["patientid"]) for v in unp})
cache = json.load(open(CF)) if os.path.exists(CF) else {}
log = open(LOGF, "a")
def L(m):
    log.write(time.strftime("%H:%M:%S ") + m + "\n"); log.flush()

CH_KEYS = ("id", "visit", "dos", "createtime", "billdate", "proccode", "modifiers", "provcode", "faccode",
           "fee", "paid", "patbal", "insbal", "totbal", "carrier", "void", "payerinfo", "approvedat")
PAY_KEYS = ("id", "date", "createtime", "checknumber", "paycode", "amount", "carrier", "void", "source")
WO_KEYS = ("id", "date", "createtime", "wocode", "amount", "void", "source")

def slim(root):
    rec = {"charges": [], "unapplied": []}
    for c in root.iter("charge"):
        a = c.attrib
        ch = {k: a.get(k, "") for k in CH_KEYS}
        ch["pays"] = []; ch["wos"] = []
        for p in c.iter("payment"):
            pa = p.attrib
            pr = {k: pa.get(k, "") for k in PAY_KEYS}
            pr["reasons"] = [[r.get("code", ""), r.get("description", "")[:60], r.get("amount", "")] for r in p.iter("payreason")]
            ch["pays"].append(pr)
        for w in c.iter("writeoff"):
            wa = w.attrib
            ch["wos"].append({k: wa.get(k, "") for k in WO_KEYS})
        rec["charges"].append(ch)
    for u in root.iter("unappliedpayment"):
        rec["unapplied"].append({k: u.get(k, "") for k in ("id", "date", "amount", "carrier", "void", "checknumber")})
    return rec

L("scan start: %d patients, %d cached" % (len(pids), len(cache)))
n = 0; t0 = time.time()
for pid in pids:
    if str(pid) in cache:
        continue
    ok = False
    for attempt in range(3):
        try:
            raw = amd.post(txh.__dict__["amd"].msg("gettxhistory", "demographics", {"patientid": str(pid), "filterhistory": "0", "pagenumber": "1", "typefilter": "0", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "profileid": "", "getmemo": "false", "nocookie": "1"}), timeout=120)
            if "429" in raw[:200] and "Too Many" in raw[:400]:
                L("429 on %s - sleeping 60s" % pid); time.sleep(60); continue
            root = ET.fromstring(raw)
            cache[str(pid)] = slim(root); ok = True; break
        except Exception as e:
            msg = str(e)[:120]
            L("ERR pid %s attempt %d: %s" % (pid, attempt + 1, msg))
            time.sleep(10 * (attempt + 1))
    if not ok:
        cache[str(pid)] = {"error": True, "charges": [], "unapplied": []}
    n += 1
    if n % 20 == 0:
        json.dump(cache, open(CF, "w"))
        L("%d scanned (%d total cached) %.0fs" % (n, len(cache), time.time() - t0))
    time.sleep(0.4)
json.dump(cache, open(CF, "w"))
L("scan done: %d cached, %.0fs" % (len(cache), time.time() - t0))
print("DONE", len(cache))
