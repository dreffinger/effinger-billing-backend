# PLAIN ENGLISH (Which charts have a Medicare number Medicare no longer accepts? 11/20/2026) - READ ONLY.
# Decides: Nothing. Takes the whole unpaid list, keeps the visits last billed to Medicare, and for each chart runs AdvancedMD's FREE
#          eligibility check on the chart's open Medicare plan. Prints the charts whose number is REJECTED or INACTIVE with the
#          dollars open at Medicare - the charts where a claim can never be paid until the number is fixed.
import amd, ins_update, elig_amd, json, collections, time
amd.login_cached()
code, body = amd.rest_post("/api/claim/massrebillsearch", {}); rows = json.loads(body)
by = collections.defaultdict(lambda: [0, 0.0])
for x in rows:
    if x["carriercode"].strip() == "FLO02": by[str(x["patientid"])][0] += 1; by[str(x["patientid"])][1] += float(x["insbalance"] or 0)
print("charts with an open balance at Medicare: %d (%d visits, $%.2f)" % (len(by), sum(v[0] for v in by.values()), sum(v[1] for v in by.values())))
out = []; tally = collections.Counter()
for pid, (n, amt) in sorted(by.items(), key=lambda kv: -kv[1][1]):
    try:
        _, plans, order = ins_update._plans(pid)
        mp = [p for p in plans.values() if p.get("carrier") == "car6085" and not p.get("enddate")]
        if not mp: tally["no open Medicare plan"] += 1; out.append({"pid": pid, "n": n, "amt": amt, "status": "NO OPEN MEDICARE PLAN"}); continue
        s = elig_amd.run_plan(pid, mp[0]["id"].replace("ins", ""), False); st = str(s.get("status") or "?").split()[0]
        aaa = [a.get("RejectReasonCode") for a in (s.get("aaa") or [])]
    except Exception as e: st = "ERROR"; aaa = [type(e).__name__]
    tally[st + (" " + ",".join(str(a) for a in aaa) if aaa else "")] += 1
    out.append({"pid": pid, "n": n, "amt": round(amt, 2), "status": st, "aaa": aaa, "ins": mp[0]["id"] if mp else None, "death": s.get("date_of_death") if st != "ERROR" else None,
                "others": [(o.get("type"), [e.get("name") for e in o.get("entities") or []]) for o in (s.get("other_payers") or [])][:3] if st != "ERROR" else None})
    time.sleep(0.15)
json.dump(out, open("medicare_number_scan_1120.json", "w"))
print("answers:", dict(tally))
for o in out:
    if o["status"] not in ("ACTIVE",): print("  pat%s %d visits $%.2f: %s %s" % (o["pid"], o["n"], o["amt"], o["status"], o.get("aaa") or ""))
