# PLAIN ENGLISH (Medicare ERA 819814877 - lines the fallback skipped as 'residual', 5am ET 9/19/2026 run 2026-09-19T0910Z)
# Decides: the fallback's 'open insurance balance $0 = already adjudicated' gate was wrong for these lines: the charges carry
#   NO non-zero payment - an earlier wrong-payer $0 denial (BCBS / UNI20 / SUN01 checks of 9/6-9/11) transferred the whole charge
#   to the PATIENT balance, then Medicare paid the re-routed claim on check 819814877. William's standing flag: wrong-payer denials
#   never stay on the patient balance. So for every such line: (1) move_to_ins.move(cid) - full-visit echo, patient balance back to
#   insurance, NO rebill (Medicare has paid); (2) manual_post.post the Medicare payment: pay = min(ERA paid, insurance balance),
#   wo = the CO adjustments capped so pay + wo <= that balance (WOINS), check number = the ERA check, deposit date = the check date.
#   PR coinsurance is never written off - it stays for the secondary / patient. --dry lists what would happen.
# Never touches: a charge with a non-zero payment, a charge with patient balance 0 (true residual - reported), voided charges,
#   denial-only lines, any other check. Stops after 3 consecutive faults.
import json, sys, time, re, collections
import txh, manual_post, move_to_ins, amd
dry = "--dry" in sys.argv; STAMP = "2026-09-19T0910Z"
REGF = "registers/era_manual_register.json"; reg = json.load(open(REGF))
live = json.load(open("registers/era_fallback_%s_live.json" % STAMP))
res = [r for r in live if r["outcome"].startswith("residual") and r.get("chargeid")]
checks = {str(c["id"]): c for c in json.load(open("era_checks_before_%s.json" % STAMP))}
details = {cid: {cl["checkclaimid"]: cl for cl in json.load(open("era_details/%s.json" % cid))["eracheckdetails"]} for cid in checks}
def norm(s):
    s = (s or "")[:10]; y, m, d = s.split("-"); return "%s/%s/%s" % (m, d, y)
TX = {}
def charge(pid, cid):
    if pid not in TX:
        TX[pid] = [c for c in txh.fetch("pat%s" % pid).iter("charge") if c.get("void") != "1"]; time.sleep(0.3)
    return next((c for c in TX[pid] if c.get("id") == str(cid)), None)
out = []; faults = 0; tot = collections.Counter(); dol = collections.Counter(); moved_visits = set()
for r in res:
    c = charge(r["pid"], r["chargeid"])
    rec = dict(r); rec["when"] = STAMP
    if c is None: rec.update(outcome="patbal-skip", why="charge not live"); out.append(rec); tot["skip"] += 1; continue
    pays = [p for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
    if pays: rec.update(outcome="patbal-skip", why="has payment %s" % [(p.get("carrier"), p.get("amount"), p.get("checknumber")) for p in pays][:2]); out.append(rec); tot["skip-paid"] += 1; continue
    insbal = float(c.get("insbal") or 0); patbal = float(c.get("patbal") or 0)
    if insbal <= 0 and patbal <= 0: rec.update(outcome="patbal-skip", why="balance 0 on insurance and patient (true residual)"); out.append(rec); tot["skip-zero"] += 1; dol["true-residual"] += r["era_paid"]; continue
    bal = insbal + patbal; paid = float(r["era_paid"]); pay = min(paid, bal)
    cl = details[r["checkid"]][r["checkclaimid"]]
    co = 0.0; code = "WOINS"
    for a in cl.get("carc") or []:
        if a.get("chargedetailid") not in (None, r.get("chargedetailid")) and r.get("chargedetailid"): continue
        if (a.get("payreasongroup") or "").upper() == "CO":
            co += float(a.get("reasonamt") or 0); rc = str(a.get("reasoncode") or "")
            if rc in ("CO29", "29"): code = "WOLATE"
            elif rc in ("CO96", "CO204", "CO50", "96", "204", "50"): code = "WONCS"
    wo = max(0.0, min(co, bal - pay))
    chk = checks[r["checkid"]]; dd = norm(chk.get("depositdate") or chk.get("receiveddate"))
    rec.update(pay=round(pay, 2), wo=round(wo, 2), wocode=code, residual=round(paid - pay, 2), insbal=insbal, patbal=patbal, moved_from_patient=patbal if insbal <= 0 else 0)
    if dry: rec.update(outcome="DRY move+post"); out.append(rec); tot["would"] += 1; dol["would-pay"] += pay; dol["would-wo"] += wo; dol["would-move"] += patbal; continue
    try:
        mv = "n/a"
        if patbal > 0 and r["visitid"] not in moved_visits:
            mv = move_to_ins.move(str(r["chargeid"]))
            if mv.startswith("FAULT") or mv == "charge not live on visit": raise RuntimeError("move: " + mv)
            moved_visits.add(r["visitid"]); time.sleep(0.8)
        ok, msg = manual_post.post(str(r["chargeid"]), c.get("carrier") or "FLO02", pay, wo, code, str(r["checkno"]), dd, "ERA %s manual post %s (patient balance moved back to insurance after wrong-payer $0 denial)" % (r["checkid"], STAMP))
    except Exception as e: ok, msg = False, str(e)
    rec["move"] = mv
    if ok: rec.update(outcome="posted"); tot["posted"] += 1; dol["pay"] += pay; dol["wo"] += wo; dol["moved"] += rec["moved_from_patient"]; faults = 0
    else: rec.update(outcome="fault", why=str(msg)[:200]); tot["fault"] += 1; faults += 1
    out.append(rec); time.sleep(0.5)
    if faults >= 3: print("3 consecutive faults - stopping"); break
json.dump(out, open("registers/era_patbal_%s_%s.json" % (STAMP, "dry" if dry else "live"), "w"), indent=1)
if not dry:
    # replace the earlier 'residual' register entries for lines now posted
    done = {(x["checkid"], x["checkclaimid"], x.get("chargedetailid")) for x in out if x["outcome"] == "posted"}
    reg = [x for x in reg if not (x["outcome"].startswith("residual") and (x["checkid"], x["checkclaimid"], x.get("chargedetailid")) in done)]
    reg += [x for x in out if x["outcome"] == "posted"]
    json.dump(reg, open(REGF, "w"), indent=1)
print("counts", dict(tot)); print("dollars", {k: round(v, 2) for k, v in dol.items()})
for x in out:
    if x["outcome"] in ("fault", "patbal-skip"): print(" ", x["outcome"], "v", x["visitid"], x["cpt"], x["dos"], "paid", x["era_paid"], x.get("why", "")[:100])
