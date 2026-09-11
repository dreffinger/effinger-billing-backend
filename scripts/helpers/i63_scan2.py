# PLAIN ENGLISH (I63.9 scanner (resumable))
# Decides: Nothing - finds outpatient I63.9 charges and checkpoints.
# Rules it uses: Read-only.
# Never touches: AMD writes.
# ---
"""Resilient I63.9-in-outpatient scanner. Resumes from checkpoint, 30s per-call
timeout so no single hung socket stalls the job, appends matches, checkpoints every
50 visits. Merges with matches already found (i63_matches.json)."""
import amd, json, time, os
import xml.etree.ElementTree as ET

I639 = "dcode1034545006"
CKPT = "i63_scan_ckpt.txt"
MATCHES = "i63_matches.json"
LOG = open("i63_scan2.log", "a")
def L(m):
    print(m); LOG.write(m + "\n"); LOG.flush()

def detail(chargeid):
    return amd.post(amd.msg("getchargedetaildataicd10", "demographics",
                    {"chargeid": str(chargeid), "nocookie": "1"}), timeout=30)

def load_matches():
    try:
        return json.load(open(MATCHES))
    except Exception:
        return []

def main():
    rows = json.load(open("unpaid_20260902.json"))
    start = 0
    if os.path.exists(CKPT):
        try: start = int(open(CKPT).read().strip())
        except Exception: start = 0
    matches = load_matches()
    seen_vis = {m.get("visitid") for m in matches}
    L("=== scan2 resume at %d/%d  existing matches=%d  %s ===" % (start, len(rows), len(matches), time.ctime()))
    i = start
    fails = 0
    for i in range(start, len(rows)):
        r = rows[i]
        cids = (r.get("chargedetailids") or "").split(",")
        if not cids or not cids[0]:
            continue
        try:
            x = detail(cids[0]); root = ET.fromstring(x); fails = 0
        except Exception:
            fails += 1
            if fails >= 25:
                L("  25 consecutive failures at idx %d -- pausing 60s" % i); time.sleep(60); fails = 0
            continue
        vis = root.find(".//visit")
        if vis is None:
            continue
        for c in vis.findall(".//charge"):
            if I639 in (c.get("diagcodes") or "") and (c.get("pos") or "").strip() != "21":
                if r.get("visitid") in seen_vis:
                    continue
                seen_vis.add(r.get("visitid"))
                matches.append({"visitid": r.get("visitid"), "patient": r.get("patientname"),
                                "dos": r.get("dateofservice", "")[:10], "payer": r.get("carriercode"),
                                "pos": (c.get("pos") or "").strip(), "chargeid": c.get("id"),
                                "before": c.get("diagcodes"), "insbalance": r.get("insbalance"),
                                "firstcid": cids[0]})
        if (i + 1) % 50 == 0:
            open(CKPT, "w").write(str(i + 1))
            json.dump(matches, open(MATCHES, "w"), indent=1)
            if (i + 1) % 500 == 0:
                L("  scanned %d/%d  matches=%d" % (i + 1, len(rows), len(matches)))
        time.sleep(0.5)
    open(CKPT, "w").write(str(len(rows)))
    json.dump(matches, open(MATCHES, "w"), indent=1)
    L("=== SCAN COMPLETE. scanned to %d  total matches=%d ===" % (len(rows), len(matches)))

if __name__ == "__main__":
    main()
