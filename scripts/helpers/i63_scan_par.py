# PLAIN ENGLISH (I63.9 scanner (parallel))
# Decides: Nothing - same scan, five workers.
# Rules it uses: Read-only.
# Never touches: AMD writes.
# ---
"""Parallel I63.9-in-outpatient scanner for the remaining claims. 5 workers, 30s
timeout per call, resumes from checkpoint, appends to i63_matches.json. Read-only."""
import amd, json, time, os
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed

I639 = "dcode1034545006"
CKPT = "i63_scan_ckpt.txt"
MATCHES = "i63_matches.json"
LOG = open("i63_scan_par.log", "a")
def L(m):
    print(m); LOG.write(m + "\n"); LOG.flush()

def scan_one(r):
    cids = (r.get("chargedetailids") or "").split(",")
    if not cids or not cids[0]:
        return None
    try:
        x = amd.post(amd.msg("getchargedetaildataicd10", "demographics",
                    {"chargeid": str(cids[0]), "nocookie": "1"}), timeout=30)
        vis = ET.fromstring(x).find(".//visit")
    except Exception:
        return None
    if vis is None:
        return None
    for c in vis.findall(".//charge"):
        if I639 in (c.get("diagcodes") or "") and (c.get("pos") or "").strip() != "21":
            return {"visitid": r.get("visitid"), "patient": r.get("patientname"),
                    "dos": r.get("dateofservice", "")[:10], "payer": r.get("carriercode"),
                    "pos": (c.get("pos") or "").strip(), "chargeid": c.get("id"),
                    "before": c.get("diagcodes"), "insbalance": r.get("insbalance"),
                    "firstcid": cids[0]}
    return None

def main():
    rows = json.load(open("unpaid_20260902.json"))
    start = int(open(CKPT).read().strip()) if os.path.exists(CKPT) else 0
    matches = json.load(open(MATCHES)) if os.path.exists(MATCHES) else []
    seen = {m.get("visitid") for m in matches}
    amd.login_cached()  # warm the token before fanning out
    todo = rows[start:]
    L("=== parallel scan from %d/%d, existing matches=%d %s ===" % (start, len(rows), len(matches), time.ctime()))
    done = 0
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(scan_one, r): r for r in todo}
        for fut in as_completed(futs):
            done += 1
            try:
                m = fut.result()
            except Exception:
                m = None
            if m and m["visitid"] not in seen:
                seen.add(m["visitid"]); matches.append(m)
            if done % 300 == 0:
                json.dump(matches, open(MATCHES, "w"), indent=1)
                open(CKPT, "w").write(str(start + done))
                L("  processed %d/%d  matches=%d" % (done, len(todo), len(matches)))
    json.dump(matches, open(MATCHES, "w"), indent=1)
    open(CKPT, "w").write(str(len(rows)))
    L("=== PARALLEL SCAN COMPLETE. total matches=%d ===" % len(matches))

if __name__ == "__main__":
    main()
