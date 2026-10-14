# PLAIN ENGLISH (Exclusions column - William's 10/14/2026 rules on the 88 rejected claims of the 10/14 chat pass)
# Decides, per rejection text:
#  - 'MISSING PAYER DOC CONTROL NUM' (PREF0283 / PREF02A8 / PREF0264) and 'MISSING ORIGINAL REF NUMBER' (PREF0201): a corrected
#    claim (frequency 7) went out without the payer's claim number. William 10/14: "find the number and resubmit, or just resubmit
#    the claim as an original" -> the visit is reset to frequency 1 (no reference number) and ONE rebill goes to the plan the
#    rejection names (the chart's sequence for that carrier), then the exclusion is completed (hideexclusions).
#  - 'SUBSCRIBER AND SUBSCRIBER ID NOT FOUND' (payer acknowledgment): wrong member id = wrong insurance (William 10/14) -> the
#    cascade decides the plan: for chart 23969 the AARP plan answers AAA 72 and Cigna's 271 + discovery show the live Medigap, so
#    the dead plan is end-dated the day before the first rejected DOS, the visits are pointed at the live secondary and rebilled.
#  - 'INVALID PAYER RESP SEQ NUM CODE S' (Mutual of Omaha, 2022-23 Medigap coinsurance after a Medicare remit of 02/2023-07/2023):
#    the secondary window (12 months from the primary's remit) is long closed and the clearinghouse will not take the claim ->
#    WOINS write-off with a dated note, exclusion completed (William 10/13: aged A/R is fixed or written off, never parked).
#  - AET12 PREF0288 (carrier CPID) is the carrier record, not the claim -> left, on the AET12 board row.
# Never touches: payments, charges, voids; one rebill per visit (amd.rebill_charge guard); the deceased guard stays on every rebill.
#   python3 excl_rules_1014.py            # dry
#   python3 excl_rules_1014.py --live     # act; register -> registers/excl_rules_<stamp>.json
import amd, resave, freq1_visit, ins_update, manual_post, json, re, sys, time, datetime, collections
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv
amd.login_cached()
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
REG = {"run": stamp, "live": LIVE, "visits": [], "writeoffs": [], "hidden": {}, "left": [], "chart_actions": []}
cars = json.load(open("carriers.json"))   # code -> carN
def num(s): return re.sub(r"\D", "", str(s or ""))
def log(*a):
    print(*a, flush=True); open("excl_rules_1014.log", "a").write(time.strftime("%Y-%m-%dT%H:%M:%SZ ", time.gmtime()) + " ".join(str(x) for x in a) + "\n")
DONE = set()
import os
if os.path.exists("excl_rules_1014.log"):
    for line in open("excl_rules_1014.log"):
        if '"vid"' in line and '"done": true' in line:
            try: DONE.add(json.loads(line.split(" ", 1)[1])["vid"])
            except Exception: pass

def plans(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    pl = [dict(re.findall(r'(\w+)="([^"]*)"', t)) for t in re.findall(r'<insplan [^>]*>', r)]
    m = re.search(r'<patient [^>]*?insorder="([^"]*)"', r)
    return [p for p in pl if p.get("id")], (m.group(1) if m else "")

def seq_for_carrier(pid, carrier_code):
    pl, order = plans(pid); car = cars.get(carrier_code)
    cands = [p for p in pl if p.get("carrier") == car]
    return (cands[0].get("sequence") if cands else None), pl, order

def first_charge(vid, pid):
    """One live charge id of the visit via gettxhistory visitid=."""
    import txh
    root = txh.fetch_visit(pid, vid)
    for c in root.iter("charge"):
        if c.get("void") != "1" and num(c.get("visit")) == str(vid) and not (c.get("fee") or "").startswith("-"): return num(c.get("id"))
    return None

rows = json.load(open("excl_rows_1014.json"))
# only rows still on the list at the fresh re-read (the in-flight 0510Z routine completed 39 rows between 05:40Z and 06:25Z)
_fresh = {(x["run"], str(x["vid"])) for x in json.load(open("excl_rows_1014_fresh.json"))}
rows = [r for r in rows if (r["run"], str(r["vid"])) in _fresh]
print("rows still open:", len(rows))
FREQ = re.compile(r"PREF0283|PREF02A8|PREF0264|PREF0201")
NOTFOUND = re.compile(r"SUBSCRIBER ID NOT FOUND", re.I)
SEQS = re.compile(r"PSBR0134")
to_hide = collections.defaultdict(list)

# chart-level fix for 23969 (AARP dead, Cigna live): end-date AARP ins9520805 the day before the first rejected DOS, patient order 1,2
if LIVE:
    pl, order = plans("23969")
    aarp = next((p for p in pl if p["id"] == "ins9520805"), None)
    if aarp and not aarp.get("enddate"):
        ok, msg = ins_update.update("23969", "ins9520805", enddate="09/15/2026")
        REG["chart_actions"].append(("23969 end-date AARP ins9520805 09/15/2026", ok, msg[:200])); log("23969 end-date AARP ->", ok, msg[:200])
        ok2, msg2 = ins_update.update("23969", "ins2246", sequence="1,2")
        REG["chart_actions"].append(("23969 patient insorder 1,2 via Cigna ins2246", ok2, msg2[:200])); log("23969 insorder 1,2 ->", ok2, msg2[:200])
else:
    REG["chart_actions"].append(("DRY 23969: end-date AARP ins9520805 09/15/2026; patient insorder 1,2", None, ""))

for r in sorted(rows, key=lambda x: (x["pid"], x["dos"])):
    vid, pid, car = num(r["vid"]), r["pid"], r["carrier"].split(" ")[0]
    errs = " | ".join(r["errs"]); v = {"pid": pid, "vid": vid, "claimid": r["claimid"], "run": r["run"], "carrier": car, "dos": r["dos"], "errs": errs[:120], "steps": [], "done": False}
    if vid in DONE: continue
    try:
        if car == "AET12":
            v["steps"].append(("left", "AET12 carrier CPID record - board row aet12-carrier-cpid")); REG["left"].append(v)
        elif NOTFOUND.search(errs) and pid == "23969":
            cid = first_charge(vid, pid)
            if LIVE:
                res = freq1_visit.reroute(vid, cid, "1,2", 2); v["steps"].append(("reroute 1,2 rebill seq 2 (Cigna)", res[:220]))
                if "-> 204" in res and "NOT rebilled" not in res and "BLOCKED" not in res: v["done"] = True; to_hide[r["run"]].append((vid, r["claimid"]))
                else: REG["left"].append(v)
            else: v["steps"].append(("DRY reroute 1,2 rebill seq 2 (Cigna car6687)", cid))
        elif SEQS.search(errs):
            import txh
            root = txh.fetch_visit(pid, vid); tot = 0.0
            for c in root.iter("charge"):
                if c.get("void") == "1" or num(c.get("visit")) != vid: continue
                bal = float(c.get("insbal") or 0)
                if bal <= 0: continue
                ok, msg = manual_post.post(num(c.get("id")), "MUT01", 0.0, round(bal, 2), "WOINS", "UNTIMELY1014", None,
                                           "Medigap secondary balance 2022-23: Medicare remit 02-07/2023, secondary window closed, clearinghouse PSBR0134 rejects seq S - WOINS untimely (chat 10/14)", dry=not LIVE)
                v["steps"].append(("writeoff MUT01 WOINS", num(c.get("id")), c.get("proccode"), round(bal, 2), ok, msg[:100])); tot += bal
                REG["writeoffs"].append({"pid": pid, "vid": vid, "cid": num(c.get("id")), "amount": round(bal, 2), "code": "WOINS", "ok": ok})
            if LIVE and all(s[4] for s in v["steps"] if s[0].startswith("writeoff")): v["done"] = True; to_hide[r["run"]].append((vid, r["claimid"]))
        elif FREQ.search(errs):
            seq, pl, order = seq_for_carrier(pid, car)
            if not seq: v["steps"].append(("no plan for carrier on chart", car)); REG["left"].append(v)
            else:
                cid = first_charge(vid, pid)
                if LIVE:
                    res = freq1_visit.run(vid, cid, seq); v["steps"].append(("freq1 + rebill seq %s (%s)" % (seq, car), res[:160]))
                    if "-> 204" in res and "BLOCKED" not in res and "FAULT" not in res: v["done"] = True; to_hide[r["run"]].append((vid, r["claimid"]))
                    else: REG["left"].append(v)
                else: v["steps"].append(("DRY freq1 + rebill seq %s (%s)" % (seq, car), cid))
        else:
            v["steps"].append(("unclassified", errs[:100])); REG["left"].append(v)
    except Exception as e:
        v["steps"].append(("ERROR", str(e)[:200])); REG["left"].append(v)
    REG["visits"].append(v); log(json.dumps(v, default=str)); time.sleep(0.5 if LIVE else 0)
    json.dump(REG, open("registers/excl_rules_%s.json" % stamp, "w"), indent=1, default=str)

for run, items in to_hide.items():
    child = "<visitlist>" + "".join('<visit id="%s" claimid="%s"/>' % (vv, cl) for vv, cl in items) + "</visitlist>"
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, child))
    ok = "Fault" not in r; REG["hidden"][run] = {"n": len(items), "ok": ok, "resp": re.sub(r"\s+", " ", r[:160])}
    log("hideexclusions run %s (%d visits) -> %s" % (run, len(items), "OK" if ok else re.sub(r"\s+", " ", r[:200])))
json.dump(REG, open("registers/excl_rules_%s.json" % stamp, "w"), indent=1, default=str)
log("SUMMARY visits %d done %d, write-offs %d ($%.2f), left %d, hidden runs %d, live=%s" % (len(REG["visits"]), sum(1 for v in REG["visits"] if v["done"]), len(REG["writeoffs"]), sum(w["amount"] for w in REG["writeoffs"]), len(REG["left"]), len(REG["hidden"]), LIVE))
