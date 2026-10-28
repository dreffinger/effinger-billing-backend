# PLAIN ENGLISH (for the day Gregg's pickup resumes and re-posts the 10/16-10/27 files): finds, for every visit the 10/28 import
# created, a LATER live charge on the same chart with the same CPT + DOS on a different visit (the integration's duplicate) and
# voids that later visit's charges (void_tx.void_charge). --dry (default) only lists. Skips any visit carrying a payment.
# Usage: python3 feed_dupe_void_1028.py [--live]
import amd, resave, txh, re, json, sys, time, collections
import xml.etree.ElementTree as ET
reg = json.load(open("registers/feed_import_1028.json")); live = "--live" in sys.argv
amd.login_cached(); by = collections.defaultdict(list)
for v in reg["created"]: by[v["pid"]].append(v)
out = []
for pid, visits in by.items():
    num = re.sub(r"\D", "", pid); mine = {re.sub(r"\D", "", v["visit"]) for v in visits}
    want = {(c, v["dos"]) for v in visits for c in v["cpts"]}
    th = txh.fetch(num); dup_visits = collections.defaultdict(list)
    for c in th.iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or (a.get("fee") or "").startswith("-") or a.get("visit") in mine: continue
        if (a.get("proccode"), a.get("dos")) in want and int(a.get("visit") or 0) > max(int(x) for x in mine):
            dup_visits[a.get("visit")].append((a.get("id"), a.get("proccode"), a.get("dos"), a.get("paid")))
    for vid, chs in dup_visits.items():
        rec = {"pid": pid, "dup_visit": vid, "charges": chs}
        if any(float(p or 0) != 0 for *_, p in chs): rec["result"] = "has payment - left"; out.append(rec); continue
        if not live: rec["result"] = "DRY would void"; out.append(rec); print(rec); continue
        import void_tx
        res = [void_tx.void_charge(num, c[0])[0] for c in chs]
        r = "ok" if all(res) else "Fault"
        time.sleep(0.8); rec["result"] = "VOIDED" if "Fault" not in r else "FAULT"; out.append(rec); print(rec)
    time.sleep(0.3)
json.dump(out, open("registers/feed_dupe_void_1028.json", "w"), indent=1); print("duplicates found:", len(out))
