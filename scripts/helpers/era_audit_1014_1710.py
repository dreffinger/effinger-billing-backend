# PLAIN ENGLISH (post-Post-button audit of the five Florida Blue checks, run 2026-10-14T1710Z - READ ONLY)
# Decides: nothing. The Billing Button pressed the ERA Center Post button on checks 1053163-1053167 between this run's dry
# (17:3xZ) and live (17:4xZ) passes, so almost every line came back 'already posted'. The Post button posts Florida Blue lines with
# the CO-45 reason on the payment but writes off nothing (the 9/23 lesson): the contractual - and a $0 denial's whole charge - can
# land on the PATIENT balance. This helper reads every line's live charge (txh.fetch_visit) and prints, beside the dry pass's
# before-state and the remit's paid / CO / PR amounts, what is on the charge now: insurance balance, patient balance, the payments
# carrying this check's trace number. Output: registers/era_audit_2026-10-14T1710Z.json + one line per charge. No AMD write.
import json, sys, time, txh, amd
S = "2026-10-14T1710Z"
dry = json.load(open("registers/era_new_%s_dry.json" % S))["lines"]
chk = json.load(open("registers/era_checks_before_%s.json" % S)); chk = chk.get("checks") if isinstance(chk, dict) else chk
trace = {str(c["id"]): c.get("paymentnumber") for c in chk}
amd.login_cached()
out = []; cache = {}
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0),
            "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "billdate": c.get("billdate"),
            "pays": [(float(p.get("amount") or 0), (p.get("checknumber") or "").strip(), p.get("carrier"), p.get("void"), p.get("id")) for p in c.iter("payment")],
            "wos": [(float(w.get("amount") or 0), (w.get("code") or w.get("wocode") or "").strip(), w.get("void")) for w in c.iter("writeoff")]}
    return res
for r in dry:
    key = (r["pid"], r["visitid"])
    if key not in cache:
        try: cache[key] = live(r["pid"], r["visitid"]); time.sleep(0.25)
        except Exception as e: cache[key] = {"ERR": str(e)[:80]}
    st = cache[key]; cid = str(r.get("chargedetailid")); s = st.get(cid) if isinstance(st, dict) else None
    tn = trace.get(r["checkid"])
    mine = [p for p in (s or {}).get("pays", []) if p[1] == tn and p[3] != "1"] if s else []
    row = {"checkid": r["checkid"], "trace": tn, "vid": r["visitid"], "pid": r["pid"], "cid": cid, "cpt": r["cpt"], "dos": r["dos"], "paid": r["paid"], "carcs": r["carcs"],
           "dry_outcome": r["outcome"][:60], "before": r.get("before"), "now": ({k: s[k] for k in ("fee", "paid", "insbal", "patbal", "carrier")} if s else st.get("ERR") if isinstance(st, dict) else None),
           "this_check_pays": mine, "wos": (s or {}).get("wos", [])}
    out.append(row)
    print("%s v%s c%s %s %s paid %.2f %s | dry %s | before ins %s pat %s | NOW ins %s pat %s car %s | pays %s | wos %s" % (
        r["checkid"], r["visitid"], cid, r["cpt"], r["dos"], r["paid"], "+".join(r["carcs"]), r["outcome"][:28],
        (r.get("before") or {}).get("insbal"), (r.get("before") or {}).get("patbal"),
        row["now"]["insbal"] if isinstance(row["now"], dict) else row["now"], row["now"]["patbal"] if isinstance(row["now"], dict) else "-", row["now"]["carrier"] if isinstance(row["now"], dict) else "-",
        [(p[0], p[2]) for p in mine], [w for w in row["wos"] if w[2] != "1"]), flush=True)
json.dump(out, open("registers/era_audit_%s.json" % S, "w"), indent=1)
