# PLAIN ENGLISH (William's standing rule 9/22/2026: never submit a claim for a patient who died before the date of service).
# For every imported visit whose DOS is AFTER the chart's date of death (deceased guard / Medicare 271), VOID the visit's charges:
#   with void_tx.void_charge (action=void class=void, proven 9/4/2026); the empty-chargelist resave is refused ("Missing element: <charge/>"). Only charges this import created an hour ago (unpaid, unbilled) are touched; verified by re-reading
#   gettxhistory (void=1). Writes registers/feed_void_deceased_1028.json.
import amd, resave, txh, re, json, os, sys, time
import xml.etree.ElementTree as ET
os.environ.setdefault("DECEASED_CACHE", "/home/claude/unbilled/deceased_cache_local.json")
import deceased_guard
reg = json.load(open("registers/feed_import_1028.json"))
cache = json.load(open(os.environ["DECEASED_CACHE"]))
dry = "--dry" in sys.argv
amd.login_cached(); out = []
for v in reg["created"]:
    num = re.sub(r"\D", "", v["pid"]); rec = cache.get(num) or {}
    dod = rec.get("dod")
    if not dod or not re.match(r"\d{4}-\d{2}-\d{2}$", str(dod)): continue
    if deceased_guard._iso(v["dos"]) <= dod: continue
    cid = re.sub(r"\D", "", v["charges"][0])
    d = ET.fromstring(resave.detail(cid)); vis = d.find(".//visit"); pat = d.find(".//patient")
    live = [c for c in d.iter("charge") if c.get("void") != "1"]
    if vis is None or not live: out.append({"visit": v["visit"], "pid": v["pid"], "dos": v["dos"], "dod": dod, "result": "no live charge found"}); continue
    paid = [p for c in live for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
    if paid: out.append({"visit": v["visit"], "pid": v["pid"], "dos": v["dos"], "dod": dod, "result": "HAS PAYMENT - not voided"}); continue
    if dry: out.append({"visit": v["visit"], "pid": v["pid"], "dos": v["dos"], "dod": dod, "cpts": v["cpts"], "result": "DRY would void"}); print(out[-1]); continue
    # the empty-chargelist resave answers "Missing element: <charge/>" - the proven charge void is void_tx.void_charge (9/4/2026)
    import void_tx
    faults = []
    for c in live:
        ok, msg = void_tx.void_charge(num, c.get("id"))
        if not ok: faults.append(msg)
        time.sleep(0.4)
    r = "Fault" if faults else "ok"
    time.sleep(0.8)
    th = txh.fetch_visit(num, re.sub(r"\D", "", v["visit"]))
    states = [(c.get("id"), c.get("void"), c.get("proccode")) for c in th.iter("charge") if not (c.get("fee") or "").startswith("-")]
    ok = bool(states) and all(s[1] == "1" for s in states)
    out.append({"visit": v["visit"], "pid": v["pid"], "dos": v["dos"], "dod": dod, "cpts": v["cpts"], "fault": "Fault" in r, "after": states, "result": "VOIDED" if ok else "CHECK"})
    print(out[-1])
json.dump(out, open("registers/feed_void_deceased_1028.json", "w"), indent=1)
print("done", len(out))
