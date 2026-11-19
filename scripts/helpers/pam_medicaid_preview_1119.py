# PLAIN ENGLISH (Preview of the 11/19/2026 re-render of Pam's open Medicaid-plan claims to Dr. Effinger) - READ ONLY.
# Decides: Nothing. For every visit in pam_medicaid_targets_1119.json it reads the live visit and says what the re-render
#          helper (medicaid_garland_g_fix.py) would do: A = clinician prof15 -> prof13 (AdvancedMD voids the lines and
#          re-creates them under the physician) when NO payment is posted on any line; SETTLING = a payment is posted
#          (never re-rendered - the standing settling gate); ALREADY = the visit is already under the physician.
# Never touches: AdvancedMD (reads only). Output: pam_medicaid_preview_1119.json (visit ids, dollars).
import amd, resave, json, re
import xml.etree.ElementTree as ET
amd.login_cached()
tgt = json.load(open("pam_medicaid_targets_1119.json")); out = []; tot = {}
for pid, parts in tgt.items():
    for vid, chs in parts["A"].items():
        try: v, pat, allc = resave.visit_charges(chs[0]["cid"])
        except Exception as e: out.append({"pid": pid, "vid": vid, "kind": "READ-FAIL", "bal": 0}); continue
        if v is None or not allc: out.append({"pid": pid, "vid": vid, "kind": "NO-LIVE", "bal": 0}); continue
        bal = sum(float(c.get("insbalance") or 0) for c in allc); paid = False; pays = []
        for cx in allc:
            dx = ET.fromstring(resave.detail(re.sub(r"\D", "", cx.get("id"))))
            for p in dx.iter("payment"):
                if p.get("void") != "1" and float(p.get("amount") or 0) != 0: paid = True; pays.append(p.get("amount"))
        kind = "ALREADY" if v.get("profile") == "prof13" else ("SETTLING" if paid else ("A" if v.get("profile") == "prof15" else "OTHER-" + str(v.get("profile"))))
        out.append({"pid": pid, "vid": vid, "kind": kind, "bal": round(bal, 2), "car": chs[0]["car"], "date": v.get("date"), "n": len(allc), "insorder": v.get("insorder"),
                    "cpt": [c.get("proccode") for c in allc], "pays": pays})
        t = tot.setdefault((kind, chs[0]["car"]), [0, 0.0]); t[0] += 1; t[1] += bal
json.dump(out, open("pam_medicaid_preview_1119.json", "w"), indent=0)
for k, v in sorted(tot.items()): print(k, v[0], round(v[1], 2))
