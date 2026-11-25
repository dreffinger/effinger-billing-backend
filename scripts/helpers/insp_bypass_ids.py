#!/usr/bin/env python3
# PLAIN ENGLISH (Claim Inspector - bypass ONE named pattern on ONE visit, on William's word)
# Decides: nothing on its own. William has looked at a Claim Inspector hold and said the claim is right as coded
#   (e.g. Pattern 692 "initial hospital care after subsequent care" on a new admission he confirmed on the board - since William's standing word of
#   11/25/2026 the runs bypass 692 themselves, claimocity_inspector.py and insp_bypass_advisories.py; this helper is for a 692 that stands beside a
#   data error on the same visit, and for any other edit he clears by name).
#   This helper re-lists every inspector batch, finds the CURRENT error id of that pattern on that visit (error ids
#   change on every re-inspection), and bypasses exactly that edit with bypassclaimedits. Nothing else is touched.
# Rules it uses: one visit + one pattern per argument; the board note / William's words are cited in the register.
# Never touches: charges, diagnoses, other visits, other patterns on the same visit, missing-data holds.
# Usage: python3 insp_bypass_ids.py <visitid>:<pattern> [<visitid>:<pattern> ...] --why "<William's words / row>" [--stamp <run stamp>] [--live]
#   default = dry run (lists what it would bypass). Register: registers/insp_bypass_ids_<stamp>.json
import amd, re, sys, json, time, os, datetime

live = "--live" in sys.argv
why = sys.argv[sys.argv.index("--why") + 1] if "--why" in sys.argv else ""
stamp = sys.argv[sys.argv.index("--stamp") + 1] if "--stamp" in sys.argv else datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
_skip = {why, stamp}
args = [a for a in sys.argv[1:] if not a.startswith("--") and a not in _skip and re.match(r"^(vst)?\d+:\d+$", a)]
if not args:
    print(__doc__ or "usage: insp_bypass_ids.py <visitid>:<pattern> ... --why '...' [--live]"); sys.exit(2)
want = {}
for a in args:
    vid, pat = a.split(":"); want[(vid.replace("vst", ""), pat)] = None

amd.login_cached()
import xml.etree.ElementTree as ET
ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"')
batches = sorted(set(re.findall(r'<batch id="([^"]+)"', ib)))
found = {}
for bid in batches:
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
    try:
        root = ET.fromstring(t)
    except ET.ParseError:
        continue
    for v in root.iter("visit"):            # same layout columns_scan.py reads: <visit id=...><error id=... number=...>text</error>
        vid = (v.get("id") or "").replace("vst", "")
        for e in v.iter("error"):
            txt = re.sub(r"\s+", " ", (e.text or "") + "".join((c.text or "") for c in e.iter()))
            pm = re.search(r"Pattern (\d+)", txt) or re.search(r"Pattern (\d+)", e.get("number") or "")
            if e.get("id") and pm:
                found[(vid, pm.group(1))] = (bid, e.get("id"), txt[:120])
reg = {"stamp": stamp, "why": why, "live": live, "items": []}
for key in want:
    hit = found.get(key)
    if not hit:
        print("NOT LISTED visit %s pattern %s (nothing to bypass - already clear?)" % key); reg["items"].append({"visit": key[0], "pattern": key[1], "result": "not-listed"}); continue
    bid, eid, desc = hit
    print("%s visit %s pattern %s batch %s error id %s: %s" % ("BYPASS" if live else "DRY would bypass", key[0], key[1], bid, eid, desc))
    item = {"visit": key[0], "pattern": key[1], "batch": bid, "errorid": eid, "desc": desc}
    if live:
        body = '<visitlist><visit id="%s"><claimeditlist><claimedit id="%s"/></claimeditlist></visit></visitlist>' % (key[0], eid)
        r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, body))
        ok = "Fault" not in r
        item["result"] = "ok" if ok else r[:300]
        print("   ->", item["result"])
        time.sleep(0.6)
    else:
        item["result"] = "dry"
    reg["items"].append(item)
os.makedirs("registers", exist_ok=True)
json.dump(reg, open("registers/insp_bypass_ids_%s%s.json" % (stamp, "" if live else "_dry"), "w"), indent=1)
print("register saved; live=%s" % live)
