# PLAIN ENGLISH (Claim Inspector by hand, 12:40Z 11/21 run (copy of insp_bypass_1112.py)): the two visits of chart 17478349 (UMR commercial TPA plan added 11/9) carry
# ONE advisory each - error number 117070083 "The Source of Payment you have chosen is not typical for this carrier" (the 23400 family: bypass to
# clear, Claims Center skill). insp_bypass_ids.py matches 'Pattern NNNN' in the error text and this edit prints none, so this helper re-lists the
# batch, takes the CURRENT error id of exactly that error number on exactly these visits, bypasses it (bypassclaimedits, plain numeric visit id)
# and re-lists. Nothing else is touched. Usage: python3 insp_bypass_1112.py [--live]   register registers/insp_bypass_1121_<stamp>[_dry].json
import amd, re, sys, json, time
live = "--live" in sys.argv; STAMP = "2026-11-21T1240Z"; WANT = {"19462063", "19462064"}; NUMBER = "117070083"
amd.login_cached(); reg = {"stamp": STAMP, "live": live, "items": []}
def listing():
    b = amd.post(amd.msg("getclaiminspectorbatches", "chargeentry", {"nocookie": "1"})); out = {}
    for bid in sorted(set(re.findall(r'<batch [^>]*\bid="([^"]+)"', b))):
        x = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
        for m in re.finditer(r'<visit [^>]*>.*?</visit>', x, re.S):
            vid = re.search(r'\bid="(\d+)"', m.group(0)).group(1)
            errs = [dict(re.findall(r'(\w+)="([^"]*)"', e)) for e in re.findall(r'<error [^>]*>', m.group(0))]
            out[vid] = (bid, errs)
    return out
before = listing(); print("before:", {v: [(e.get("id"), e.get("number"), e.get("name", "")[:50]) for e in errs] for v, (b, errs) in before.items()})
for vid in sorted(WANT):
    bid, errs = before.get(vid, (None, []))
    hits = [e for e in errs if e.get("number") == NUMBER]
    if not hits: reg["items"].append({"visit": vid, "result": "not-listed"}); print("NOT LISTED", vid); continue
    others = [e for e in errs if e.get("number") != NUMBER]
    if others: print("  visit", vid, "also carries", [(e.get("number"), e.get("name", "")[:60]) for e in others], "- left alone")
    for e in hits:
        item = {"visit": vid, "batch": bid, "errorid": e["id"], "number": NUMBER, "name": e.get("name", "")}
        if live:
            body = '<visitlist><visit id="%s"><claimeditlist><claimedit id="%s"/></claimeditlist></visit></visitlist>' % (vid, e["id"])
            r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, body)); item["result"] = "ok" if "Fault" not in r else r[:300]; time.sleep(0.6)
        else: item["result"] = "dry"
        print("BYPASS" if live else "DRY would bypass", vid, "error id", e["id"], "->", item["result"]); reg["items"].append(item)
if live:
    time.sleep(2); after = listing(); reg["after"] = {v: [(e.get("id"), e.get("number")) for e in errs] for v, (b, errs) in after.items()}; print("after:", reg["after"] or "inspector list empty")
json.dump(reg, open("registers/insp_bypass_1121_%s%s.json" % (STAMP, "" if live else "_dry"), "w"), indent=1)
