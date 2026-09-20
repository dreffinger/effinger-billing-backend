# PLAIN ENGLISH (7am ET 9/20/2026 run 2026-09-20T1110Z): claim run 1700211 (AMD clock 9/20 02:04) rejected the same 11 Florida Blue
#   SECONDARY claims again with CH FH PREF0283 'MISSING PAYER DOC CONTROL NUM' after the 1am run re-sent them (5 freq 7 + ICN, 6 freq 1).
# Decides: nothing. Reads every charge live (resave.detail by charge id): extins resubmissioncode/origrefnum, insorder, insurance balance,
#   every non-void payment with carrier / check / origrefnum - to tell whether the primary (Medicare) payment record carries a payer claim
#   control number (the hand-posted 9/19 payments carry none - the likely value Change Healthcare wants for a secondary claim).
# Never touches: AMD writes.
import amd, resave, json, re, sys
import xml.etree.ElementTree as ET
amd.login_cached()
S_ = json.load(open("scan_0912/summary_before.json")); rows = S_["exclusions"]["1700211"]
out = []
for v in rows:
    for c in v["_chgs"]:
        rt = ET.fromstring(resave.detail(c["id"]))
        vis = rt.find(".//visit"); ch = [x for x in rt.iter("charge") if x.get("id") == "charge" + c["id"]][0]
        ext = ch.find("extins") if ch.find("extins") is not None else rt.find(".//extins")
        rec = {"vid": v["id"], "claimid": v["claimid"], "pid": v["patientid"], "cid": c["id"], "cpt": c["chgcode"], "dos": c["dos"].strip(),
               "insorder": (vis.get("insorder") if vis is not None else None), "insbalance": ch.get("insbalance"), "patbalance": ch.get("patbalance"),
               "resub": (ext.get("resubmissioncode") if ext is not None else "NO-EXTINS"), "origref": (ext.get("origrefnum") if ext is not None else None),
               "pays": [{"id": p.get("id"), "car": p.get("carrierfid"), "amt": p.get("amount"), "date": p.get("date"), "chk": p.get("checknumber"), "origref": p.get("origrefnum"), "code": p.get("paymentcode"), "void": p.get("void")} for p in ch.iter("payment") if p.get("void") != "1"]}
        out.append(rec); print(json.dumps(rec))
json.dump(out, open("registers/excl_1700211_verify_2026-09-20T1110Z.json", "w"), indent=1)
