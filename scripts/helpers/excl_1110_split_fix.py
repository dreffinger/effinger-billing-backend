# PLAIN ENGLISH (10/15 go, cards A-2026-10-15T1110Z-L and -M): on the split lines of charts 17477190 and 17471834 the WOINS
#   contractual part posted under the secondary and AMD moved the remaining Medicare cost-share (PR share) to the PATIENT
#   balance, so the script's WOCLTREQ on the insurance side had nothing left ("over-apply ... insbalance 0.00"). William's
#   10/13 rule (nothing stays on the patient balance; the cost-share takes WOCLTREQ) -> patient-side write-off WOCLTREQ
#   (patient_writeoff.post, the back-end Payment Entry patient tab) of exactly the live patient balance, then hideexclusions
#   for the chart's still-open rows on run 1700296. One chart per run: --chart 17477190 | 17471834. --live writes.
# Never touches: insurance balances, payments, other charges; refuses when the live patient balance differs from the expected share.
import sys, json, re, time, amd, patient_writeoff, txh
LIVE = "--live" in sys.argv; PID = sys.argv[sys.argv.index("--chart") + 1]
PLAN = {"17477190": {"run": "1700296", "lines": [("19451201", "19451201C", "23361203", 16.93), ("19453807", "19453807B", "23364716", 11.59), ("19455738", "19455738B", "23367153", 16.14), ("19455738", "19455738B", "23367154", 8.92)]},
        "17471834": {"run": "1700296", "lines": [("19387411", "19387411E", "22457691", 17.73), ("19389094", "19389094D", "22459701", 18.11), ("19392888", "19392888C", "22464974", 22.10)]}}
P = PLAN[PID]; rec = {"stamp": "2026-10-15T2327Z go split fix", "pid": PID, "live": LIVE, "steps": [], "hidden": {}}
amd.login_cached()
ok_all = True; settled_visits = {}
for vid, claim, cid, share in P["lines"]:
    root = txh.fetch_visit(PID, vid)
    c = next((x for x in root.iter("charge") if str(x.get("id") or "").replace("charge", "") == cid and x.get("void") != "1"), None)
    step = {"vid": vid, "cid": cid, "expect": share, "live_insbal": c.get("insbal") if c is not None else None, "live_patbal": c.get("patbal") if c is not None else None}
    if c is None or abs(float(c.get("patbal") or 0) - share) > 0.005 or float(c.get("insbal") or 0) > 0.005:
        step["result"] = "HOLD - live balances differ from the expected share"; rec["steps"].append(step); ok_all = False; print(step); continue
    note = "Medicare cost-share after the primary paid; secondary rejected run %s (no supplement in force) - WOCLTREQ (William 10/13 rule); moved to patient by the WOINS posting 10/15 go" % P["run"]
    if LIVE:
        r = patient_writeoff.post(cid, share, "WOCLTREQ", checknumber="EXCL1015B", note=note)
        ok, msg = (r if isinstance(r, tuple) else (bool(r), str(r)))
        step["post"] = (ok, str(msg)[:160]); print("  patient WOCLTREQ %.2f on c%s -> %s %s" % (share, cid, ok, str(msg)[:120])); time.sleep(0.6)
        if not ok: step["result"] = "FAULT"; rec["steps"].append(step); ok_all = False; continue
    else:
        step["post"] = "DRY"
    step["result"] = "settled"; rec["steps"].append(step); settled_visits.setdefault(vid, claim)
if LIVE and ok_all and settled_visits:
    child = "<visitlist>" + "".join('<visit id="%s" claimid="%s"/>' % (v, cl) for v, cl in settled_visits.items()) + "</visitlist>"
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"claimrunid": P["run"], "hide": "-1", "nocookie": "1"}, child))
    rec["hidden"][P["run"]] = {"n": len(settled_visits), "ok": "Fault" not in r, "resp": re.sub(r"\s+", " ", r[:160])}
    print("hideexclusions run %s (%d rows) -> %s" % (P["run"], len(settled_visits), "OK" if "Fault" not in r else r[:200]))
elif LIVE:
    print("NOT hiding - a line did not settle")
after = {}
for vid, claim, cid, share in P["lines"]:
    root = txh.fetch_visit(PID, vid); c = next((x for x in root.iter("charge") if str(x.get("id") or "").replace("charge", "") == cid), None)
    after[cid] = (c.get("insbal"), c.get("patbal")) if c is not None else None
rec["after"] = after; print("after (insbal, patbal):", after)
json.dump(rec, open("registers/excl_2026-10-15T1110Z_splitfix_%s%s.json" % (PID, "" if LIVE else "_dry"), "w"), indent=1, default=str)
print("DONE live=%s settled %d/%d hidden %s" % (LIVE, sum(1 for s in rec["steps"] if s.get("result") == "settled"), len(P["lines"]), {k: v.get("ok") for k, v in rec["hidden"].items()}))
