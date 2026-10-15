# PLAIN ENGLISH (Exclusions pass, 1 AM ET 10/14/2026 run 2026-10-14T0510Z) - the non-crossover rows of claim runs 1700294/96/97.
# Decides per row, from the live chart read this run (work_reads2_0510.json):
#   (a) chart 17473476 Florida Blue Medigap secondaries that carry the stale 'corrected claim' flag (PREF0201 + PREF0283): Medicare paid, the
#       open balance is the coinsurance -> reset extins resubmissioncode=1 / origrefnum blank (no rebill) and COMPLETE under the 9/20 crossover-wait rule;
#   (b) PREF0201 frequency-7-without-ICN rows on secondaries the clearinghouse never passed (AET07 17475064, HUM01 17475638, UNI20 17475777):
#       frequency-1 reset + ONE chargerebill on the secondary's sequence (freq1_visit.run; the only rebill of these visits this run) then complete;
#   (c) chart 17473197 UNI20 rows: UHC already ADJUDICATED these visits $0 PR26/PR27 (not covered on the DOS, 9/4/2026) - the clearinghouse
#       rejection of the resend is moot: COMPLETE, never re-send; the coinsurance residual is handled by cov_1014_0510.py (William 10/13 WOCLTREQ);
#   (d) MUT01 (Mutual of Omaha Medigap) PSBR0134 rows on charts 21471 / 25500: Medicare paid, balance = coinsurance -> COMPLETE (crossover-wait);
#       the payer-responsibility-sequence rejection is the MUT01 carrier record's EDI setting - William's row;
#   (e) CON08 chart 22603 PREF02A8 rows: AMD 271 says CON08 (car42021) is DEAD (AAA 75) and AET12 is the live Medigap -> COMPLETE; chart fix in cov_1014_0510.py.
# Never touches: the AAR01 chart 23969 rows (member id AAA 72 - board row), the AET12 row (carrier-master hold), payments, write-offs.
#   python3 excl_1014_0510.py            # dry
#   python3 excl_1014_0510.py --live     # register registers/excl_1014_0510.json
import amd, resave, freq1_visit, json, re, sys, time
LIVE = "--live" in sys.argv; S = "2026-10-14T0510Z"
amd.login_cached()
scan = json.load(open("scan_2026-10-14T0510Z/summary_before.json"))
PLAN = {  # pid -> (action, seq)
 "17473476": ("freqreset", None), "17475064": ("freq1", 1), "17475638": ("freq1", 1), "17475777": ("freq1", 1),
 "17473197": ("complete", None), "21471": ("complete", None), "25500": ("complete", None), "22603": ("complete", None)}
rows = []
for run, rr in scan["exclusions"].items():
    for r in rr:
        if r["patientid"] in PLAN and not all("PREF0283" in e["name"] for e in r["_errs"]) or (r["patientid"] == "17473476"):
            if r["patientid"] in PLAN:
                rows.append({"run": run, "vid": r["id"], "claimid": r["claimid"], "pid": r["patientid"], "carrier": r["carriercodeshort"],
                             "cid": r["_chgs"][0]["id"], "action": PLAN[r["patientid"]][0], "seq": PLAN[r["patientid"]][1], "errs": [e["name"][:40] for e in r["_errs"]]})
print("rows:", len(rows))
def reset_freq(vid, cid):
    vis, pat, allc = resave.visit_charges(cid); e = vis.find("extins"); base = dict(e.attrib) if e is not None else {}; base.pop("id", None)
    base.update({"resubmissioncode": "1", "origrefnum": ""})
    for k, val in {"patsignature": "1", "emergency": "0", "epsdt": "0", "payprov": "1", "employment": "0", "autoaccident": "0", "otheraccident": "0", "pregnant": "0", "outsidelab": "0"}.items(): base.setdefault(k, val)
    base = resave.clean_extins(base)
    for pc in sorted({c.get("proccode") for c in allc}):
        base["txtChargeCode"] = pc
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": str(vid), "nocookie": "1"}, "<extins %s/>" % " ".join('%s="%s"' % (k, val) for k, val in base.items())))
        if "Fault" in r: return "FAULT extins " + r[:200]
    return "freq reset ok"
reg = {"stamp": S, "live": LIVE, "rows": rows, "complete": {}, "results": []}
for x in rows:
    vis, pat, allc = resave.visit_charges(x["cid"]); e = vis.find("extins")
    x["insorder"] = vis.get("insorder"); x["resub"] = (e.get("resubmissioncode") if e is not None else None); x["live_charges"] = len(allc)
    res = ""
    if x["action"] == "freqreset":
        res = reset_freq(x["vid"], x["cid"]) if LIVE else "DRY freq reset"
    elif x["action"] == "freq1":
        if str(x["seq"]) not in (vis.get("insorder") or "").split(","):
            res = "SKIP rebill - seq %s not in visit insorder %s" % (x["seq"], vis.get("insorder")); x["action"] = "complete-only"
        else:
            res = freq1_visit.run(x["vid"], x["cid"], x["seq"]) if LIVE else "DRY freq1 + rebill seq %s" % x["seq"]
    x["result"] = res; print(x["run"], x["claimid"], "pat" + x["pid"], x["carrier"], x["action"], "insorder", x["insorder"], "resub", x["resub"], "->", res, flush=True)
    if not res.startswith("FAULT"): reg["complete"].setdefault(x["run"], []).append((x["vid"], x["claimid"]))
    time.sleep(0.3)
for run, lst in reg["complete"].items():
    body = "<visitlist>%s</visitlist>" % "".join('<visit id="%s" claimid="%s"/>' % (v, c) for v, c in lst)
    if LIVE:
        r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": run, "hide": "-1", "nocookie": "1"}, body), timeout=120)
        reg["results"].append((run, len(lst), re.sub(r"\s+", " ", r[:200]))); print("hideexclusions", run, len(lst), "->", r[:120])
    else: print("DRY hideexclusions", run, len(lst))
json.dump(reg, open("registers/excl_1014_0510%s.json" % ("" if LIVE else "_dry"), "w"), indent=1)
