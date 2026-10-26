# PLAIN ENGLISH (Sunday 10/25/2026 sweep write-offs - William 10/25 11:02 PM ET: "if we can't collect more on these we should
#   write them off rather than leave them on the books ... just write them off as paid and not posted is fine")
# Decides: which rows of tonight's claim-status sweep get written off and with which code, then posts the write-offs.
#   - Paid_but_unposted_20261025.csv (payer says PAID, remit never posted)      -> WOINSBANK  (paid to bank, not posted)
#   - sweep_denials UNI20 "65 claim/line has been paid"                          -> WOINSBANK  (same thing, payer says paid)
#   - UNI20 / SIM01 "585 denied or non-covered charge"                            -> WONCS      (non-covered service)
#   - HUM01 "107 processed according to contract provisions"                      -> WOINS      (contractual)
#   - SUN01 "1 see remittance advice"                                             -> WOCLTREQ   (William's call, no better code)
#   - AET07 "20 accepted for processing" older than 6 months with no adjudication -> WOCLTREQ   (accepted 30-40x, never adjudicated)
#   HELD (left on the books as genuinely pending): BCBS "38 awaiting next periodic adjudication cycle" and AET07 code 20 inside 6 months.
# Rules it uses: re-reads every charge live (gettxhistory) and writes off exactly the live balance, insurance side with the
#   carrier the sweep answered for, patient side with patient_writeoff; skips charges already at $0; never rebills, never voids.
# Never touches: plans, claims, ERA Center, charges not on tonight's two lists.
"""Usage: python3 sweep_writeoff_1025.py [--live] [--include-bcbs38]"""
import amd, txh, manual_post, patient_writeoff, csv, json, sys, time, datetime, collections, re
LIVE = "--live" in sys.argv; INC38 = "--include-bcbs38" in sys.argv
STAMP = "20261025"; NOTE = "Sweep 10/25/26 - William: write off, not collectible / paid not posted"
reg_path = "registers/sweep_writeoff_%s%s.json" % (STAMP, "" if LIVE else "_dry")
HOLD_PIDS = set()
targets = []   # (pid, vid, carrier, code, why)
# 1. paid but unposted
for r in csv.DictReader(open("Paid_but_unposted_%s.csv" % STAMP)):
    targets.append((int(r["amdid"]), int(r["visitid"]), r["carrier"], "WOINSBANK", "payer paid %s on %s chk %s, never posted" % (r["payer_paid"], r["paid_dates"], r["check_numbers"])))
# 2. denials register
den = json.load(open("registers/sweep_denials_2026-10-25T0535Z.json"))
cut6 = (datetime.date(2026, 10, 25) - datetime.timedelta(days=180)).isoformat()
for x in den["denials"]:
    pid = x["pid"]; car = max(x["carriers"], key=x["carriers"].get); code0 = x["codes"][0][0].split(" ")[0]; codes = x["codes"][0][0]
    if car == "BCBS" and code0 == "38" and not INC38: HOLD_PIDS.add(pid); continue
    if car == "AET07" and code0 == "20" and x["dos"][-1] >= cut6: HOLD_PIDS.add(pid); continue
    if code0 == "65": wo = "WOINSBANK"
    elif code0 == "585": wo = "WONCS"
    elif code0 == "107": wo = "WOINS"
    else: wo = "WOCLTREQ"
    for vid in x["visits"]:
        targets.append((pid, int(vid), car, wo, "277 %s" % codes[:60]))
print("targets: %d visit rows, %d charts; held charts: %d" % (len(targets), len({t[0] for t in targets}), len(HOLD_PIDS)))
amd.login_cached()
reg = {"live": LIVE, "posted": [], "skipped": [], "failed": [], "held_pids": sorted(HOLD_PIDS)}
byp = collections.defaultdict(list)
for t in targets: byp[t[0]].append(t)
tot = collections.Counter(); amt = collections.Counter()
for pid, rows in byp.items():
    try: root = txh.fetch(pid)
    except Exception as e: reg["failed"].append({"pid": pid, "why": "txh " + str(e)[:100]}); continue
    want = {vid: (car, code, why) for _, vid, car, code, why in rows}
    seen = set()
    charges = list(root.iter("charge"))
    have = {int(c.get("visitid") or c.get("visit") or 0) for c in charges}
    for vid in set(want) - have:   # long charts: page 1 misses old visits - ask for the visit itself
        try: charges += list(txh.fetch_visit(pid, vid).iter("charge"))
        except Exception as e: reg["failed"].append({"pid": pid, "vid": vid, "why": "fetch_visit " + str(e)[:80]})
    for c in charges:
        if c.get("void") == "1": continue
        a = c.attrib; vid = int(a.get("visitid") or a.get("visit") or 0)
        if vid not in want: continue
        seen.add(vid); car, code, why = want[vid]
        cid = re.sub(r"\D", "", a.get("id") or "")
        insb = float(a.get("insbal") or a.get("insbalance") or 0); patb = float(a.get("patbal") or a.get("patbalance") or 0)
        base = {"pid": pid, "vid": vid, "cid": cid, "cpt": a.get("cpt") or a.get("proccode") or "", "dos": a.get("dos") or a.get("date") or "", "carrier": car, "code": code, "why": why, "insbal": insb, "patbal": patb}
        if insb < 0.005 and patb < 0.005: reg["skipped"].append(dict(base, why2="already $0")); continue
        if insb > 0.004:
            ok, msg = manual_post.post(cid, car, 0.0, insb, code, "", None, NOTE, dry=not LIVE)
            (reg["posted"] if ok else reg["failed"]).append(dict(base, side="ins", wo=insb, msg=msg))
            if ok: tot[code] += 1; amt[code] += insb
            time.sleep(0.3)
        if patb > 0.004:
            ok, msg = patient_writeoff.post(cid, patb, code, "", NOTE, dry=not LIVE)
            (reg["posted"] if ok else reg["failed"]).append(dict(base, side="pat", wo=patb, msg=msg))
            if ok: tot[code] += 1; amt[code] += patb
            time.sleep(0.3)
    for vid in set(want) - seen: reg["skipped"].append({"pid": pid, "vid": vid, "why2": "no live charge found on txh"})
json.dump(reg, open(reg_path, "w"), indent=1)
print("%s: posted %d lines $%.2f | skipped %d | failed %d -> %s" % ("LIVE" if LIVE else "DRY", len(reg["posted"]), sum(p["wo"] for p in reg["posted"]), len(reg["skipped"]), len(reg["failed"]), reg_path))
for k in tot: print("  %-10s %3d lines $%.2f" % (k, tot[k], amt[k]))
for f in reg["failed"][:10]: print("  FAIL", f)
for s in [s for s in reg["skipped"] if s.get("why2") != "already $0"][:10]: print("  SKIP", s)
