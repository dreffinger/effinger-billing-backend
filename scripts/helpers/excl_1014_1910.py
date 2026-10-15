# PLAIN ENGLISH (Exclusions column, 3 PM ET 10/14/2026 run 2026-10-14T1910Z): the first claim runs after the 10/13 BILL-SECONDARY /
#   patient-balance sends (1700296 / 1700297) brought back 31 UNITED HEALTHCARE (UNI20, CPID 3429) payer rejections. Three kinds:
#   A. 13 claims on chart 17469067 (2023 hospital visits, 99232/99233, re-sent 10/13 as frequency 1): UHC answers 'DUPLICATE OF A
#      PREVIOUSLY PROCESSED CLAIM, LINE' = the payer already adjudicated them -> the standing duplicate rule: hideexclusions, NO rebill;
#      the balances are listed in the register for the denial handling (the original adjudication is the answer, not a resend).
#   B. 8 Medicare-SECONDARY claims (Medicare paid 10/7-10/8/2026, check 819928855 / 819938228) on 7 charts whose seq-2 (seq-1 on
#      17471496) plan is an AARP MEDICARE SUPPLEMENT filed under carrier UNI20: AMD's own 271 on every one of those plans names
#      AARP (patient_db/<pid>/amd271_<ins>.json read this run) and UHC rejects 'SUBSCRIBER AND SUBSCRIBER ID NOT FOUND / MEMBER PICK
#      REJECT' because CPID 3429 is UHC commercial/MA, not the AARP Medigap payer. Fix proven 9/22, 10/6 and 10/10 (aarp_fix_1010_1710.py):
#      (1) ins_update.update(pid, insid, carrier="car6600") = the plan moves to AAR01 (AARP Medigap), member id and dates untouched,
#      the chart's patient insurance order restored by the helper if the edit wipes it; (2) per visit ONE re-route =
#      freq1_visit.reroute(vid, cid, order, seq): no-rebill full-visit echo setting Medicare first / Medigap second, then ONE
#      frequency-1 reset + ONE chargerebill at the Medigap sequence (a secondary the payer never adjudicated - frequency 1 is right);
#      (3) hideexclusions for the rejected claim ids once the rebill answered 204.
#   C. 11 charges on charts 25416 / 47643: 2022 Medigap-secondary leftovers ($11.67-$32.91 Medicare coinsurance, Medicare remits
#      10/26/2022-02/08/2023, UHC $0 answers 02/2023) re-sent 10/13 and rejected 'SUBSCRIBER ID NOT FOUND' again. The secondary window
#      (12 months from the primary's remit) closed in early 2024 and no plan on the chart answers for the id -> the v13 rule for
#      2022-23 Medigap balances (William 10/13: aged A/R is fixed or written off, never parked): WOINS write-off with a dated note,
#      check number EXCL1014, then hideexclusions.
#   D. chart 17471414 v19394861 (3/18/2024 99306+99497, Humana MA paid 9/9/2026, $176.20 cost-share sent to UNI20): the UNI20 plan's
#      271 does NOT name AARP, Medicare's own 271 is inactive (MA enrollee) and a Medigap cannot pay MA cost-share -> no write here;
#      board row on William's turn (through the board update file). AET12 chart 24750 = the carrier record, left.
# Never touches: payments, voids, plan dates / member ids, the Medicare plans, any other chart; one rebill per visit (amd.rebill_charge
#   guard), deceased guard on every rebill; writes only through ins_update / freq1_visit / manual_post / amd.post(hideexclusions).
# Usage: cd /home/claude/unbilled && python3 excl_1014_1910.py            # dry run (reads only)
#        cd /home/claude/unbilled && python3 excl_1014_1910.py --live     # act
# Register: registers/excl_2026-10-14T1910Z[_dry].json
import sys, json, time, re
import amd, ins_update, freq1_visit, manual_post, txh
LIVE = "--live" in sys.argv
S = "2026-10-14T1910Z"
ONLY = set(sys.argv[sys.argv.index("--only") + 1].split(",")) if "--only" in sys.argv else {"A", "B", "C"}
REG = "registers/excl_%s%s.json" % (S, "" if LIVE else "_dry")
rec = {"stamp": S, "live": LIVE, "A": [], "B": [], "C": [], "hidden": {}, "faults": 0}
def L(m): print(m, flush=True)
amd.login_cached()
NEWCAR = "car6600"; OLDCAR = "car6404"
# A: duplicates (run, vid, claimid)
DUP = [("1700297", v, c) for v, c in (("19365003", "19365003G"), ("19365028", "19365028G"), ("19365118", "19365118G"), ("19365221", "19365221G"),
       ("19365286", "19365286G"), ("19370156", "19370156E"), ("19370183", "19370183E"), ("19370929", "19370929F"), ("19370958", "19370958F"),
       ("19372497", "19372497F"), ("19372509", "19372509F"), ("19372523", "19372523F"), ("19372541", "19372541F"))]
DUP_PID = "17469067"
# B: AARP Medigap under UNI20 -> AAR01: pid, insid(numeric), visit order, medigap seq, [(vid, cid, claimid, run)]
AARP = [
    ("17471451", "9510767", "1,2", "2", [("19455684", "23367061", "19455684B", "1700296")]),
    ("17473432", "9514508", "1,2", "2", [("19455934", "23367405", "19455934B", "1700296"), ("19455955", "23367447", "19455955B", "1700296")]),
    ("17469426", "9509802", "1,2", "2", [("19455674", "23367048", "19455674B", "1700297")]),
    ("17471495", "9511155", "1,2", "2", [("19455686", "23367063", "19455686B", "1700297")]),
    ("17472732", "9512283", "1,2", "2", [("19455710", "23367099", "19455710B", "1700297")]),
    ("17476917", "9518291", "1,2", "2", [("19455938", "23367413", "19455938B", "1700297")]),
    ("17471496", "9510840", "2,1", "1", [("19449794", "23359632", "19449794C", "1700296")]),
]
# C: 2022 secondary leftovers: pid, run, [(vid, claimid, [cid...], medicare remit date)]
OLD = [
    ("25416", "1700296", [("24826", "24826C", ["3205"], "12/10/2022"), ("28053", "28053C", ["6978"], "12/10/2022"), ("29807", "29807C", ["10197"], "12/10/2022"),
                          ("30078", "30078C", ["10506"], "12/10/2022"), ("30916", "30916D", ["11360", "11361"], "12/10/2022"), ("31869", "31869G", ["12293"], "10/26/2022")]),
    ("47643", "1700297", [("39939", "39939B", ["19946", "19947"], "02/08/2023"), ("41664", "41664B", ["21382"], "02/08/2023"), ("41667", "41667B", ["21385"], "02/08/2023")]),
]
to_hide = {}
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or c.get("visit") != str(vid): continue
        res[c.get("id").replace("charge", "")] = {"cpt": c.get("proccode"), "dos": c.get("dos"), "fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0),
            "insbal": float(c.get("insbal") or 0), "patbal": float(c.get("patbal") or 0), "carrier": c.get("carrier"), "billdate": c.get("billdate"),
            "pays": [(x.get("date"), x.get("carrier"), x.get("amount"), x.get("checknumber")) for x in c.iter("payment") if x.get("void") != "1"]}
    return res
def hide(run, items):
    child = "<visitlist>" + "".join('<visit id="%s" claimid="%s"/>' % (vv, cl) for vv, cl in items) + "</visitlist>"
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, child))
    ok = "Fault" not in r; rec["hidden"][run] = {"n": len(items), "ok": ok, "resp": re.sub(r"\s+", " ", r[:160])}
    L("hideexclusions run %s (%d visits) -> %s" % (run, len(items), "OK" if ok else re.sub(r"\s+", " ", r[:200])))
    return ok
if "A" in ONLY:
    for run, vid, cl in DUP:
        st = live(DUP_PID, vid)
        r = {"vid": vid, "claimid": cl, "charges": st}
        L("A pat%s v%s %s -> %s" % (DUP_PID, vid, cl, [(k, v["cpt"], v["dos"], v["insbal"], v["patbal"], v["carrier"], v["pays"][:3]) for k, v in st.items()]))
        rec["A"].append(r); to_hide.setdefault(run, []).append((vid, cl)); time.sleep(0.3)
if "B" in ONLY:
    for pid, insid, order, seq, visits in AARP:
        _, plans, porder = ins_update._plans(pid)
        cur = plans.get("ins" + insid)
        r = {"pid": pid, "insid": insid, "plans_before": [(k, v.get("carrier"), v.get("sequence"), v.get("enddate")) for k, v in plans.items()], "porder": porder, "visits": []}
        L("B pat%s plan ins%s carrier %s seq %s patient order %r" % (pid, insid, cur.get("carrier") if cur else None, cur.get("sequence") if cur else None, porder))
        if not cur or cur.get("carrier") not in (OLDCAR, NEWCAR):
            r["result"] = "ABORT - plan ins%s carries %s" % (insid, cur.get("carrier") if cur else None); rec["B"].append(r); L("   " + r["result"]); continue
        if cur.get("carrier") == NEWCAR: r["carrier"] = "already AAR01"
        elif LIVE:
            ok, msg = ins_update.update(pid, insid, carrier=NEWCAR); r["carrier"] = (ok, str(msg)[:200]); L("   updateinsurance carrier -> AAR01: %s %s" % (ok, str(msg)[:160])); time.sleep(0.6)
            if not ok: rec["B"].append(r); continue
        else: r["carrier"] = "DRY - would move ins%s %s -> %s" % (insid, OLDCAR, NEWCAR)
        for vid, cid, cl, run in visits:
            st = live(pid, vid); v = {"vid": vid, "cid": cid, "claimid": cl, "run": run, "before": st}
            L("   v%s %s" % (vid, [(k, x["cpt"], x["insbal"], x["carrier"], x["billdate"]) for k, x in st.items()]))
            if sum(x["insbal"] for x in st.values()) <= 0.005: v["result"] = "insbal 0 - nothing to send; hide"; to_hide.setdefault(run, []).append((vid, cl)); r["visits"].append(v); continue
            if any(x["patbal"] > 0.005 for x in st.values()): v["result"] = "HOLD - patient balance on the visit"; r["visits"].append(v); continue
            if not LIVE: v["result"] = "DRY - would reroute order %s seq %s then hide" % (order, seq); r["visits"].append(v); continue
            try: res = freq1_visit.reroute(vid, cid, order, seq)
            except Exception as e: res = "EXC %s" % e
            v["reroute"] = str(res)[:300]; L("   reroute v%s order %s seq %s -> %s" % (vid, order, seq, str(res)[:200]))
            if "204" in str(res) and "FAULT" not in str(res).upper() and "BLOCK" not in str(res).upper(): v["result"] = "sent"; to_hide.setdefault(run, []).append((vid, cl))
            else: v["result"] = "NOT SENT"
            r["visits"].append(v); time.sleep(0.6)
        rec["B"].append(r)
if "C" in ONLY:
    faults = 0
    for pid, run, visits in OLD:
        for vid, cl, cids, remit in visits:
            st = live(pid, vid); v = {"pid": pid, "vid": vid, "claimid": cl, "run": run, "lines": []}; allok = True
            for cid in cids:
                x = st.get(cid)
                if not x: v["lines"].append({"cid": cid, "result": "not live"}); allok = False; continue
                ln = {"cid": cid, "cpt": x["cpt"], "dos": x["dos"], "insbal": x["insbal"], "patbal": x["patbal"], "carrier": x["carrier"]}
                L("C pat%s v%s c%s %s dos %s insbal %.2f patbal %.2f carrier %s" % (pid, vid, cid, x["cpt"], x["dos"], x["insbal"], x["patbal"], x["carrier"]))
                if x["insbal"] <= 0.005: ln["result"] = "already $0"; v["lines"].append(ln); continue
                if x["patbal"] > 0.005: ln["result"] = "HOLD - patient balance"; allok = False; v["lines"].append(ln); continue
                note = "secondary window closed - Medicare remit %s, UHC subscriber not found on claim run %s (10/13/2026 resend); run %s" % (remit, run, S)
                if not LIVE: ln["result"] = "DRY - would WOINS %.2f" % x["insbal"]; v["lines"].append(ln); continue
                ok, msg = manual_post.post(cid, "UNI20", 0.0, round(x["insbal"], 2), "WOINS", checknumber="EXCL1014", depositdate=None, note=note)
                ln["post"] = (ok, str(msg)[:160]); ln["result"] = "written off %.2f" % x["insbal"] if ok else "FAULT"; L("   manual_post WOINS %.2f -> %s %s" % (x["insbal"], ok, str(msg)[:120]))
                faults = 0 if ok else faults + 1
                if not ok: allok = False
                v["lines"].append(ln); time.sleep(0.6)
                if faults >= 3: L("3 consecutive addpayments faults - stopping C"); rec["faults"] = faults; break
            if allok and LIVE: to_hide.setdefault(run, []).append((vid, cl))
            rec["C"].append(v)
            if faults >= 3: break
        if faults >= 3: break
if LIVE:
    for run, items in to_hide.items(): hide(run, items); time.sleep(0.5)
else:
    rec["would_hide"] = {run: items for run, items in to_hide.items()}
    L("DRY would hide: %s" % {run: len(items) for run, items in to_hide.items()})
json.dump(rec, open(REG, "w"), indent=1, default=str)
L("DONE A %d B %d C %d hidden %s live=%s" % (len(rec["A"]), len(rec["B"]), len(rec["C"]), {k: v.get("ok") for k, v in rec["hidden"].items()}, LIVE))
