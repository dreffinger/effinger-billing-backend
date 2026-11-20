# PLAIN ENGLISH (Which charts carry a Medicare number Medicare does not accept - and fix the ones a look-up can fix)
# Decides: which charts go to the Medicare-number fixer. Takes the whole unpaid list, keeps the visits last billed to Medicare, and
#   for each chart runs AdvancedMD's FREE eligibility check on the chart's open Medicare plan. Built 11/20/2026 (William: "review and
#   fix the charges and the process") after the first scan: of 289 charts with $135,002 open at Medicare, 16 carried a number
#   Medicare rejected as invalid ($11,805) - every claim on those charts was unpayable until the number changed, and nothing in the
#   routine looked. Seven were corrected the same night (feed number or Medicare's look-up) and their visits re-sent.
# Rules it uses: a chart answered ACTIVE in the last 30 days is not asked again (register medicare_number_scan.json: chart id, date,
#   answer - no number, no name). REJECTED 72 (invalid number) -> with --fix, medicare_number_fix.fix() (feed number first, then
#   Medicare's look-up; the number stays only when Medicare then knows it; one re-send per unpaid visit, never a visit with a payment,
#   never past 12 months without William's word). A chart the fixer already listed 'no other number found' in the last 30 days is
#   not looked up again (the look-up is a paid call). REJECTED 71 / 73 (birth date / name does not match) and 'no open Medicare
#   plan' are listed for the board - a person or the facesheet settles those. INACTIVE with a date of death: charges dated AFTER
#   that date with a balance are LISTED (the standing rule writes them off; manual_post.py does it, with --dry first).
# Never touches: a chart Medicare accepts. Without --fix it is read only.
# Usage: python3 medicare_number_scan.py [--fix] [--all]      (--all asks every chart again, ignoring the 30-day memory)
import amd, ins_update, elig_amd, txh, json, collections, time, datetime, os, sys
FIX = "--fix" in sys.argv; ALL = "--all" in sys.argv; REG = "registers/medicare_number_scan.json"; FIXREG = "registers/medicare_number_fix.json"
def recent(day, n=30):
    try: return (datetime.date.today() - datetime.date.fromisoformat(day)).days < n
    except Exception: return False
if __name__ == "__main__":
    amd.login_cached(); today = datetime.date.today().isoformat()
    reg = json.load(open(REG)) if os.path.exists(REG) else {}; fixreg = json.load(open(FIXREG)) if os.path.exists(FIXREG) else {}
    code, body = amd.rest_post("/api/claim/massrebillsearch", {}); by = collections.defaultdict(lambda: [0, 0.0])
    for x in json.loads(body):
        if x["carriercode"].strip() == "FLO02": by[str(x["patientid"])][0] += 1; by[str(x["patientid"])][1] += float(x["insbalance"] or 0)
    print("charts with an open balance at Medicare: %d (%d visits, $%.2f)" % (len(by), sum(v[0] for v in by.values()), sum(v[1] for v in by.values())))
    tally = collections.Counter(); bad = []; dead = []
    for pid, (n, amt) in sorted(by.items(), key=lambda kv: -kv[1][1]):
        r = reg.get(pid) or {}
        if not ALL and r.get("answer") == "ACTIVE" and recent(r.get("day")): tally["ACTIVE (asked in the last 30 days)"] += 1; continue
        try:
            _, plans, order = ins_update._plans(pid)
            mp = [p for p in plans.values() if p.get("carrier") == "car6085" and not p.get("enddate")]
            if not mp: ans = "NO OPEN MEDICARE PLAN"; s = {}
            else:
                s = elig_amd.run_plan(pid, mp[0]["id"].replace("ins", ""), False)
                ans = " ".join([str(s.get("status") or "?").split()[0]] + [str(a.get("RejectReasonCode")) for a in (s.get("aaa") or [])])
        except Exception as e: ans = "ERROR " + type(e).__name__; s = {}
        tally[ans] += 1; reg[pid] = {"day": today, "answer": ans, "visits": n, "open": round(amt, 2)}
        if ans.startswith("INACTIVE") and len(str(s.get("date_of_death") or "")) == 8: reg[pid]["died"] = True; dead.append((pid, str(s["date_of_death"])))
        elif ans != "ACTIVE": bad.append((pid, ans, n, amt))
        time.sleep(0.15)
    print("answers:", dict(tally))
    for pid, ans, n, amt in bad: print("  pat%s %d visits $%.2f: %s" % (pid, n, amt, ans))
    late = 0
    for pid, dod in dead:
        for c in txh.fetch(pid).iter("charge"):
            a = c.attrib; d8 = a.get("dos")[6:] + a.get("dos")[:2] + a.get("dos")[3:5]
            if a.get("void") != "1" and d8 > dod and float(a.get("insbal") or 0) + float(a.get("patbal") or 0) > 0.005:
                late += 1; print("  AFTER DEATH pat%s chg%s v%s %s %s insbal %s patbal %s at %s - write off (standing rule) and put on the board" % (pid, a.get("id"), a.get("visit"), a.get("dos"), a.get("proccode"), a.get("insbal"), a.get("patbal"), a.get("carrier")))
    json.dump(reg, open(REG, "w"), indent=1)
    todo = [pid for pid, ans, n, amt in bad if ans == "REJECTED 72" and not ("no other number found" in str((fixreg.get(pid) or {}).get("number")) and recent((fixreg.get(pid) or {}).get("day")))]
    print("RESULT Medicare number scan: asked %d | invalid number %d | name or birth date mismatch %d | no open Medicare plan %d | charges after death with a balance %d | to the fixer %d%s" % (
        sum(v for k, v in tally.items() if "last 30 days" not in k), sum(1 for b in bad if b[1] == "REJECTED 72"), sum(1 for b in bad if b[1] in ("REJECTED 71", "REJECTED 73")),
        sum(1 for b in bad if b[1].startswith("NO OPEN")), late, len(todo), "" if FIX else " (read only - add --fix)"))
    if FIX and todo:
        import medicare_number_fix
        for pid in todo:
            try: medicare_number_fix.fix(pid, True, True, fixreg); fixreg[pid]["day"] = today
            except Exception as e: print("pat%s: stopped - %s: %s" % (pid, type(e).__name__, str(e)[:120]))
            json.dump(fixreg, open(FIXREG, "w"), indent=1)
        print("RESULT fixer: numbers corrected %d | visits re-sent %d" % (sum(1 for p in todo if str(fixreg[p].get("number", "")).startswith("corrected")), sum(1 for p in todo for t in fixreg[p]["visits"].values() if "204" in t)))
