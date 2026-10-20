# PLAIN ENGLISH (post-Post-button audit of the four checks the GitHub slot #118 posted + dismissed at 23:25Z 10/20/2026, run 2026-10-20T2310Z - READ ONLY)
# Decides: nothing. The slot's Post button (era_post.py --all-unposted) posted three money lines ($286.55: Ambetter 0935174087 96.60,
#   Humana 203845063261020 106.82, 203845062261020 83.13) and dismissed the checks before any routine cached GET /api/era/checkdetails
#   (AMD answers an empty claim list once a check is dismissed - the 10/20 1310Z lesson). The posted visits were found by diffing the
#   outstanding-claims snapshots the slots wrote before and after (reports/button/outstanding_latest.json at bc71ff8 vs 253fee3):
#   three visits left the open list. This helper reads each visit live (txh.fetch_visit) and prints, per charge: fee, paid, insurance
#   and patient balance, the payments with their check numbers and CARC reasons, and the write-offs - so the CO-45-on-the-patient
#   defect (Humana / Ambetter are on the 9/23-9/25 list) is visible. Output registers/era_audit_2026-10-20T2310Z.json. No AMD write.
import json, time, txh, amd
S = "2026-10-20T2310Z"
VISITS = [("17477640", "19456966", "1053233 HUM01 203845063261020 paid 106.82"), ("17478017", "19457644", "1053231 AMB03 0935174087 paid 96.60"), ("17477972", "19457785", "1053234 'FLORIDA MEDICARE' 203845062261020 paid 83.13")]
amd.login_cached(); out = []
for pid, vid, what in VISITS:
    root = txh.fetch_visit(pid, vid)
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        row = {"pid": pid, "vid": vid, "cid": c.get("id"), "cpt": c.get("proccode"), "dos": c.get("dos"), "fee": c.get("fee"), "paid": c.get("paid"), "insbal": c.get("insbal"), "patbal": c.get("patbal"), "carrier": c.get("carrier"), "billdate": c.get("billdate"),
               "pays": [{"amt": p.get("amount"), "chk": (p.get("checknumber") or "").strip(), "car": p.get("carrier"), "void": p.get("void"), "date": p.get("date"), "reasons": [(r.get("code") or r.get("reasoncode"), r.get("amount")) for r in p.iter() if r.tag.lower().startswith("payreason") and r is not p]} for p in c.iter("payment")],
               "wos": [(w.get("amount"), (w.get("wocode") or w.get("code") or "").strip(), w.get("void"), w.get("date")) for w in c.iter("writeoff")], "remit": what}
        out.append(row); print(json.dumps(row))
    time.sleep(0.4)
json.dump({"stamp": S, "rows": out}, open("registers/era_audit_%s.json" % S, "w"), indent=1)
print("rows", len(out))
