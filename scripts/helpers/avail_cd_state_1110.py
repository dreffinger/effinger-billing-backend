# PLAIN ENGLISH (Availity ClaimDetails live check, 7am ET 9/15/2026 run - step 5(g)(3))
# Decides: for every remit line in avail_cd_rows_1110.ROWS, reads the LIVE charge (resave.detail by charge id) and the
#   chart's tx history once per patient, then classifies the line:
#     paid line   -> 'already-posted' when a non-void payment carrying the Availity trace number is on the charge,
#                    'residual' when the open insurance balance is $0, else 'post' (handed to avail_post.py, --dry first)
#     reversal    -> 'reversal' (status 22 / negative charge) - recorded and listed, no takeback posting rule yet
#     denial      -> 'denial-<reason>' with the live balance so the report says what the standing rule does next
#     deductible  -> 'patient-resp' (PR-1/PR-2 only, paid 0) - never written off
#   and writes registers/availity_cd_state_<stamp>.json plus the avail_post.py input registers/availity_vs_amd_<stamp>.json
#   (paid lines only) so the existing poster runs unchanged.
# Never touches: AMD writes (read-only).
import amd, resave, txh, json, re, sys, time, datetime
import xml.etree.ElementTree as ET
from avail_cd_rows_1110 import ROWS, DUP_COPIES
STAMP = sys.argv[1] if len(sys.argv) > 1 else "2026-09-15T1110Z"
amd.login_cached()
tx_cache = {}
def txc(pid):
    if pid not in tx_cache:
        d = {}
        for c in txh.fetch(pid).iter("charge"):
            d[re.sub(r"\D", "", c.get("id") or "")] = {"carrier": c.get("carrier"), "insbal": c.get("insbal"), "patbal": c.get("patbal"),
                "paid": c.get("paid"), "datebilled": c.get("datebilled") or c.get("billdate"),
                "pays": [dict(p.attrib) for p in c.iter("payment")]}
        tx_cache[pid] = d
        time.sleep(0.3)
    return tx_cache[pid]
out = []; cmp_checks = {}
for fid, trace, cdate, payer, icn, visit, letter, status, cchg, cpaid, lines in ROWS:
    for cid, dos, cpt, chg, adj, paid, rarc in lines:
        rec = {"fid": fid, "trace": trace, "check_date": cdate, "payer": payer, "icn": icn, "visit": visit, "letter": letter,
               "status": status, "cid": cid, "dos": dos, "cpt": cpt, "charge": chg, "adj": adj, "paid": paid, "rarc": rarc}
        try:
            rt = ET.fromstring(resave.detail(cid))
            ch = [x for x in rt.iter("charge") if x.get("id") == "charge" + cid]
            pat = rt.find(".//patient"); pid = re.sub(r"\D", "", pat.get("id")) if pat is not None else ""
            rec["pid"] = pid
            if ch:
                rec["live_insbal"] = float(ch[0].get("insbalance") or 0); rec["live_patbal"] = float(ch[0].get("patientbalance") or 0)
                rec["live_cpt"] = ch[0].get("proccode") or ch[0].get("procedurecode"); rec["live_void"] = ch[0].get("void")
            t = txc(pid).get(cid) if pid else None
            if t:
                rec["live_carrier"] = t["carrier"]; rec["live_paid"] = t["paid"]; rec["live_datebilled"] = t["datebilled"]
                rec["tx_insbal"] = t["insbal"]; rec["tx_patbal"] = t["patbal"]
                rec["pays"] = [{"chk": p.get("checknumber"), "amt": p.get("amount"), "date": p.get("date"), "void": p.get("void"), "carrier": p.get("carrierfid") or p.get("carrier"), "code": p.get("paymentcode")} for p in t["pays"]]
                rec["has_trace"] = any(p.get("checknumber") and trace in p["checknumber"] and p.get("void") != "1" for p in t["pays"])
        except Exception as e:
            rec["error"] = repr(e)[:160]
        # classify
        grp_codes = {(g, c) for g, c, a in adj}
        insbal = rec.get("live_insbal", rec.get("tx_insbal"))
        try: insbal = float(insbal or 0)
        except Exception: insbal = 0.0
        if status == 22 or chg < 0:
            cls = "reversal"
        elif paid > 0:
            cls = "already-posted" if rec.get("has_trace") else ("residual-zero-balance" if insbal <= 0.005 else "post")
        elif grp_codes and all(g == "PR" and c in ("1", "2", "3") for g, c in grp_codes) or (("CO","45") in grp_codes and any(g == "PR" and c in ("1","2","3") for g, c in grp_codes) and not any(c in ("22","177","204","39","32","252") for g, c in grp_codes)):
            cls = "patient-resp"
        elif any(c == "22" for g, c in grp_codes) or "N598" in rarc or "MA04" in rarc or ("CO","252") in grp_codes:
            cls = "denial-cob-other-primary"
        elif any(c == "177" for g, c in grp_codes) or any(c == "32" for g, c in grp_codes):
            cls = "denial-not-eligible-on-dos"
        elif any(c == "204" for g, c in grp_codes):
            cls = "denial-non-covered"
        elif any(c == "39" for g, c in grp_codes):
            cls = "denial-auth"
        else:
            cls = "denial-other"
        rec["class"] = cls
        out.append(rec)
        if cls == "post":
            ck = cmp_checks.setdefault(trace, {"trace": trace, "check_date": cdate, "payer": payer, "missing": []})
            ck["missing"].append({"cid": cid, "pid": rec.get("pid", ""), "visit": visit, "patient": "", "dos": dos, "cpt": cpt, "paid": paid, "adj": adj})
        print("%-12s %s v%s c%s %s %s paid %.2f insbal %s carrier %s trace_on_charge %s" % (cls, trace, visit, cid, dos, cpt, paid, rec.get("live_insbal"), rec.get("live_carrier"), rec.get("has_trace")), flush=True)
plans = {}
for r in out:
    pid = r.get("pid")
    if not pid or pid in plans or r["class"] in ("already-posted", "post", "residual-zero-balance"): continue
    try:
        d = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
        plans[pid] = [dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) for m in re.finditer(r'<insplan [^>]*/?>', d)]
        plans[pid] = [{k: p.get(k) for k in ("id", "carrier", "carriercode", "carriername", "subscribernum", "sequence", "begindate", "enddate", "insorder")} for p in plans[pid]]
        time.sleep(0.3)
    except Exception as e:
        plans[pid] = [{"error": repr(e)[:120]}]
for r in out: r["insplans"] = plans.get(r.get("pid"))
json.dump(out, open("registers/availity_cd_state_%s.json" % STAMP, "w"), indent=1)
json.dump({"checks": list(cmp_checks.values())}, open("registers/availity_vs_amd_%s.json" % STAMP, "w"), indent=1)
from collections import Counter
print(Counter(r["class"] for r in out))
print("post candidates:", sum(len(c["missing"]) for c in cmp_checks.values()), "$%.2f" % sum(l["paid"] for c in cmp_checks.values() for l in c["missing"]))
