# PLAIN ENGLISH (Feed member number differs from the chart's - which one is right? 11/20/2026) - READ ONLY in AdvancedMD.
# Decides: Nothing. For every insurance block of the feed whose carrier IS on the chart but with a different member number (43 on
#          11/19/2026) it runs AdvancedMD's free eligibility check on the chart's plan and sorts the pair: CHART RIGHT (the chart's
#          plan answers active), CHART PLAN ENDED (nothing to fix), or CHART NOT CONFIRMED (rejected / inactive / no answer) - those
#          are the ones worth a paid check of the feed's number. Output in1_mismatch_review_1120.json (workspace only); the screen
#          shows chart ids, carriers, the SHAPE of each number (length, letters / digits, last 2) and the answers - never a number.
import amd, ins_update, elig_amd, json, re, collections, time
amd.login_cached()
CAR = json.load(open("carriers_rich.json")); CODE2CAR = {v[0]: k for k, v in CAR.items()}
rows = [x for x in json.load(open("feed_in1_compare_1119_new.json")) if x["class"] == "OTHER NUMBER"]
norm = lambda s: re.sub(r"[^A-Z0-9]", "", (s or "").upper())
def shape(s):
    s = norm(s); return "%d:%s..%s" % (len(s), re.sub(r"[A-Z]", "A", re.sub(r"\d", "9", s))[:6], s[-2:]) if s else "-"
out = []; tally = collections.Counter()
for x in rows:
    pid = x["pid"]; car = CODE2CAR[x["code"]]
    _, plans, order = ins_update._plans(pid)
    same = [p for p in plans.values() if p.get("carrier") == car]
    live = [p for p in same if not p.get("enddate")]
    rec = {"pid": pid, "code": x["code"], "feed_name": x["name"][:30], "feed": x["member"], "chart": [p.get("subscribernum") for p in same], "live": len(live), "order": order,
           "in_order": any(p.get("sequence") in (order or "").split(",") for p in live)}
    if not live: rec["verdict"] = "CHART PLAN ENDED"
    else:
        p = live[0]
        try: s = elig_amd.run_plan(pid, p["id"].replace("ins", ""), False); st = str(s.get("status") or ""); rec["aaa"] = [a.get("RejectReasonCode") for a in (s.get("aaa") or [])]
        except Exception as e: st = "check failed %s" % type(e).__name__
        rec["status"] = st[:30]; rec["ins"] = p["id"]
        rec["verdict"] = "CHART RIGHT" if st.upper().startswith("ACTIVE") else "CHART NOT CONFIRMED"
    # a difference that is only a prefix / suffix or leading zeros is the same number written two ways
    a, b = norm(x["member"]), norm((live or same)[0].get("subscribernum"))
    rec["same_core"] = bool(a and b and (a.endswith(b) or b.endswith(a) or a.lstrip("0") == b.lstrip("0") or a.startswith(b) or b.startswith(a)))
    tally[(x["code"], rec["verdict"], "same core" if rec["same_core"] else "different")] += 1; out.append(rec)
    print("pat%s %s feed '%s' %s | chart %s | %s %s %s%s" % (pid, x["code"], rec["feed_name"], shape(x["member"]), [shape(c) for c in rec["chart"]], rec["verdict"], rec.get("status", ""), rec.get("aaa") or "", " | same core" if rec["same_core"] else ""))
    time.sleep(0.2)
json.dump(out, open("in1_mismatch_review_1120.json", "w"))
for k, v in sorted(tally.items()): print(v, k)
