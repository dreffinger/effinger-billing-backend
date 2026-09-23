# PLAIN ENGLISH (7pm ET 9/23/2026 run 2026-09-23T2310Z): the FCC (FLO99) ERA check 1052822 (0917749719, $249.39) paid 3 Rackham
#   99233 lines through the Post button and carried 10 $0 denial lines on 8 visits (RARC M56 payer-id x6, N448 not-in-fee-schedule x3,
#   N650 policy not in effect x1). Decides: nothing. Reads each denied visit live via gettxhistory (charges, balances, non-void payments
#   by carrier, carrier billed) and getdemographic (plans + sequences) so the denial handling can classify each line; also confirms the
#   11 auto-posted money lines (VACCN 1052821 x8, FLO99 1052822 x3) carry the posted payment. Never touches: AMD writes.
import amd, txh, json, re, time
amd.login_cached()
out = {"stamp": "2026-09-23T2310Z", "denials": [], "posted": []}
PL = {}; TX = {}
def load(pid):
    if pid not in TX:
        TX[pid] = txh.fetch("pat" + pid); time.sleep(0.3)
        t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
        PL[pid] = [dict(re.findall(r'(id|carrier|sequence|enddate|begindate)="([^"]*)"', p)) for p in re.findall(r'<insplan [^>]*/?>', t)]
        m = re.search(r'<patient [^>]*insorder="([^"]*)"', t); PL[pid + "_order"] = m.group(1) if m else ""
        time.sleep(0.3)
def visit_rows(pid, vid):
    root = TX[pid]; chg = []
    for ch in root.iter("charge"):
        if ch.get("visit") == vid and ch.get("void") != "1":
            pays = [{"carrier": p.get("carrier"), "amount": p.get("amount"), "void": p.get("void"), "date": p.get("date"), "check": p.get("checknumber"), "code": p.get("paymentcode")} for p in ch.iter("payment")]
            wos = [{"code": w.get("wocode"), "amount": w.get("amount"), "void": w.get("void"), "date": w.get("date")} for w in ch.iter("writeoff")]
            chg.append({k: ch.get(k) for k in ("id", "proccode", "dos", "fee", "carrier", "billdate", "insbilled", "insbal", "patbal", "paid", "insorder", "payerinfo")} | {"payments": pays, "writeoffs": wos})
    return chg
for ck in ("1052822", "1052821"):
    d = json.load(open("era_details/%s.json" % ck))
    for c in d["eracheckdetails"]:
        pid = str(c["patientid"]); vid = str(c["visitid"]); load(pid)
        rem = sorted({r.get("remarkcode") for l in (c.get("charges") or c.get("lines") or []) for r in (l.get("remarks") or l.get("rarc") or []) if r.get("remarkcode") and not r.get("remarkcode").startswith("#")} | {r.get("remarkcode") for r in (c.get("remarks") or []) if r.get("remarkcode") and not r.get("remarkcode").startswith("#")})
        rec = {"check": ck, "pid": pid, "vid": vid, "dos": c["dos"][:10], "claimstatus": c.get("claimstatus"), "era_insbal": c.get("insurancebalance"), "rarc": rem,
               "plans": PL[pid], "order": PL[pid + "_order"], "charges": visit_rows(pid, vid)}
        (out["denials"] if c.get("claimstatus") == 2 else out["posted"]).append(rec)
        print(ck, "pat"+pid, "v"+vid, rec["dos"], "status", rec["claimstatus"], "rarc", rem, "order", rec["order"],
              [(x["proccode"], x["carrier"], x["insbal"], x["patbal"], x["paid"], [(p["carrier"], p["amount"], p["check"]) for p in x["payments"] if p["void"] != "1"]) for x in rec["charges"]])
json.dump(out, open("registers/era_denials_1052822_2026-09-23T2310Z.json", "w"), indent=1)
print("DONE", len(out["denials"]), "denial visits,", len(out["posted"]), "posted visits")
