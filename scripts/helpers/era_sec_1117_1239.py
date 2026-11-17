#!/usr/bin/env python3
# PLAIN ENGLISH (7:39 AM ET 11/17/2026 backend run 2026-11-17T1239Z - prompt step 5(d)/(e), the 10/7/2026 lesson)
# ERA check 1053544 (FLORIDA MEDICARE, paymentnumber 00149732354, $146.78) was held by era_clear: 5 claim lines are SECONDARY
#   payments (claimstatus 2, OA-23 prior-payer adjudication, paid = the coinsurance) on charges the primary Medicare check already
#   paid; the primary's Post put the coinsurance on the patient balance, so the open insurance balance is 0 and era_post's gate skipped
#   them. Standing rule: move_to_ins.move(chargeid, rebill=False), then the ERA-linked post (payreasons.post_line - keeps the reason codes),
#   pay = min(ERA paid, open insurance balance), wo = the CO adjustments (none here - OA-23 is not written off).
# Guards per charge (live read first): a non-void payment carrying this check number already on it -> already-posted; the charge must
#   carry a non-void primary payment; the patient balance must not be smaller than the ERA paid amount by more than a cent (else HOLD).
# --dry (default) prints the plan; --live writes. Stops after 3 consecutive addpayments faults. Register: registers/era_sec_2026-11-17T1239Z[_dry].json
#   + registers/era_manual_register.json (live). Never touches plans, insurance order, claims or rebills.
import amd, payreasons, move_to_ins, txh, json, sys, time, os
a = sys.argv; DRY = "--live" not in a; S = "2026-11-17T1239Z"; CID = "1053544"
VIDS = {"19456842", "19456853", "19456868", "19457073", "19456963"}
def L(m): print(m, flush=True)
amd.login_cached()
det = payreasons.details(CID, fresh=True).get("eracheckdetails") or json.load(open("era_details/%s.json" % CID))["eracheckdetails"]
chk = payreasons.check_meta(CID, det[0]); chkno = str(chk.get("paymentnumber") or "")
L("check %s paymentnumber %s depositdate %s" % (chk.get("id"), chkno, chk.get("depositdate")))
if not chkno: L("HOLD - no check metadata"); sys.exit(2)

def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        pays = [((p.get("checknumber") or "").strip(), p.get("void"), abs(float(p.get("amount") or 0)), p.get("carrier")) for p in c.iter("payment")]
        res[c.get("id").replace("charge", "")] = {"insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "pays": pays}
    return res

out = {"stamp": S, "dry": DRY, "checkid": CID, "lines": []}; faults = 0
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF)) if os.path.exists(REGF) else []
for v in det:
    pid, vid = str(v["patientid"]), str(v["visitid"])
    if vid not in VIDS: continue
    for ch in v["charges"]:
        cid = str(ch["chargedetailid"]); paid = float(ch.get("paymentamount") or 0)
        r = {"checkid": CID, "checkclaimid": v["checkclaimid"], "visitid": vid, "pid": pid, "chargeid": cid, "cpt": ch.get("chargecode"), "era_paid": paid}
        s = live(pid, vid).get(cid)
        if not s: r["outcome"] = "HOLD - no live charge"; out["lines"].append(r); L(r); continue
        r["before"] = {"insbal": s["insbal"], "patbal": s["patbal"]}
        if any(p[0] == chkno and p[1] != "1" for p in s["pays"]): r["outcome"] = "already-posted"; out["lines"].append(r); L(r); continue
        if not any(p[1] != "1" and p[2] > 0 and p[0] != chkno for p in s["pays"]): r["outcome"] = "HOLD - no primary payment"; out["lines"].append(r); L(r); continue
        if s["insbal"] + 0.005 < paid and s["patbal"] + s["insbal"] + 0.011 < paid:
            r["outcome"] = "HOLD - open balance %.2f below ERA paid %.2f" % (s["insbal"] + s["patbal"], paid); out["lines"].append(r); L(r); continue
        if DRY:
            r["outcome"] = "DRY would move %.2f to insurance then ERA-linked post %.2f" % (s["patbal"], paid); out["lines"].append(r); L(r); continue
        if s["insbal"] + 0.005 < paid:
            m = move_to_ins.move(cid, rebill=False); r["move"] = str(m); time.sleep(1.0)
        ok, payid, head = payreasons.post_line(pid, vid, chk, v, cid, ch)
        r.update(ok=ok, paymentid=payid, resp=head); time.sleep(1.0)
        after = live(pid, vid).get(cid) or {}
        r["after"] = {"insbal": after.get("insbal"), "patbal": after.get("patbal")}
        r["outcome"] = "posted" if ok else "post-failed"
        faults = 0 if ok else faults + 1
        out["lines"].append(r); L(r)
        if ok: reg.append({"checkid": CID, "checkclaimid": v["checkclaimid"], "visitid": vid, "chargeid": cid, "outcome": "posted", "pay": paid, "when": S, "via": "era_sec_1117_1239 move_to_ins + post_line"})
        if faults >= 3: L("STOP - 3 consecutive faults"); break
json.dump(out, open("registers/era_sec_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
if not DRY: json.dump(reg, open(REGF, "w"), indent=1)
L("done: %s" % {k: sum(1 for x in out["lines"] if x["outcome"].startswith(k)) for k in ("posted", "already", "HOLD", "DRY", "post-failed")})
