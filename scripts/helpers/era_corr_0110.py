# PLAIN ENGLISH (run 2026-09-26T0110Z contractual corrections): (A) the Post button posted Humana check 201060565260925 (ERA 1052849) on
#   pat17477640 with the CO-45/CO-253 reasons but payreasonwoamount 0, so every posted charge shows patient balance = fee - paid (the 9/23
#   CO-45 defect, now seen on HUM01 too); the remit's patient amount is 0.00 on every line, so the whole patient balance is the contractual:
#   move_to_ins.move(cid) then manual_post pay 0 + WOINS with the trace number and check date. (B) the Medicaid FFS check 201060564260925
#   (ERA 1052850) money lines were posted 'payment only' (over-apply guard) and AMD transferred the OA-23 residual of a DUAL to the patient
#   balance - a Medicaid crossover residual never sits on the patient: move back + WOCAID2ND. --dry = read only. Stops after 3 faults.
import amd, txh, move_to_ins, manual_post, json, sys, time
DRY = "--dry" in sys.argv; S = "2026-09-26T0110Z"
amd.login_cached()
CHK = {c["id"]: c for c in json.load(open("era_checks_before_%s.json" % S))}
def dd(cid): y, m, d = CHK[cid]["depositdate"][:10].split("-"); return "%s/%s/%s" % (m, d, y)
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        res[c.get("id").replace("charge", "")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "cpt": c.get("proccode"),
                            "wos": [(w.get("amount"), (w.get("wocode") or "").strip(), w.get("void")) for w in c.iter("writeoff")], "pays": [(p.get("amount"), p.get("checknumber"), p.get("void")) for p in c.iter("payment")]}
    return res
# (pid, vid, carrier, checkid, wocode) - every non-void charge of the visit carrying a payment from that check with a patient balance
A = [("17477640", v, "HUM01", 1052849, "WOINS") for v in ("19453722", "19453851", "19453830", "19453947", "19454086")]
A += [("21378", "19437369", "MCAD", 1052850, "WOCAID2ND"), ("21378", "19420287", "MCAD", 1052850, "WOCAID2ND"), ("17472517", "19423193", "MCAD", 1052850, "WOCAID2ND"), ("17472517", "19423205", "MCAD", 1052850, "WOCAID2ND")]
out = {"stamp": S, "dry": DRY, "lines": []}; faults = 0
def L(m): print(m, flush=True)
for pid, vid, car, ck, code in A:
    chkno = CHK[ck]["paymentnumber"]
    for cid, st in live(pid, vid).items():
        rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": st["cpt"], "check": chkno, "code": code, "before": {k: st[k] for k in ("fee", "paid", "patbal", "insbal")}}
        if not any(p[1] == chkno and p[2] != "1" for p in st["pays"]): rec["result"] = "no payment from this check on the charge - untouched"; out["lines"].append(rec); continue
        if st["patbal"] <= 0.005: rec["result"] = "patient balance 0 - nothing to correct"; L("pat%s v%s c%s %s" % (pid, vid, cid, rec["result"])); out["lines"].append(rec); continue
        wo = round(st["patbal"], 2); rec["wo"] = wo
        L("pat%s v%s c%s %s fee %.2f paid %.2f patbal %.2f insbal %.2f -> move back + %s %.2f (check %s %s)" % (pid, vid, cid, st["cpt"], st["fee"], st["paid"], st["patbal"], st["insbal"], code, wo, chkno, dd(ck)))
        if DRY: rec["result"] = "DRY"; out["lines"].append(rec); continue
        m = move_to_ins.move(cid); rec["move"] = str(m)[:120]; L("   move_to_ins -> %s" % str(m)[:120]); time.sleep(0.8)
        ok, msg = manual_post.post(cid, car, 0.0, wo, code, checknumber=chkno, depositdate=dd(ck), note="ERA %s contractual correction run %s" % (ck, S)); rec["post"] = (ok, str(msg)[:160]); L("   manual_post %s %.2f -> %s %s" % (code, wo, ok, str(msg)[:120]))
        faults = 0 if ok else faults + 1
        time.sleep(0.8); after = live(pid, vid).get(cid) or {}; rec["after"] = {k: after.get(k) for k in ("patbal", "insbal", "paid")}; L("   after patbal %s insbal %s" % (after.get("patbal"), after.get("insbal")))
        rec["result"] = "posted" if ok else "FAULT"; out["lines"].append(rec)
        if faults >= 3: L("3 consecutive addpayments faults - stopping"); break
    if faults >= 3: break
json.dump(out, open("registers/era_corr_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
L("=== %s: %s" % ("DRY" if DRY else "LIVE", {k: sum(1 for r in out["lines"] if r.get("result","").startswith(k)) for k in ("DRY", "posted", "FAULT", "no payment", "patient balance 0")}))
L("corrected dollars: %.2f" % sum(r.get("wo", 0) for r in out["lines"] if r.get("result") in ("posted", "DRY")))
