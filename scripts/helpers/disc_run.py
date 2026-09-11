# PLAIN ENGLISH (Stedi Insurance Discovery over the held board cards)
# Decides: Nothing on its own. First checks whether the DISCOVERY enrollment is LIVE (one cheap test call). If it is, runs discovery (name + DOB + state, $1.50 each) for every Insurance Refresh Board card that is holding for it and writes what discovery found - payer, member id, plan dates, confidence - to disc_results_<date>.json for the acting step.
# Rules it uses: one call per patient (the most recent denied date of service), never an SSN, results cached so a rerun costs nothing. --check only tests the enrollment.
# Never touches: AMD charts or the board.
# ---
"""Usage: python3 disc_run.py [--check] [--max N]"""
import stedi, json, glob, sys, os, datetime, time, re
stamp = datetime.date.today().strftime("%Y%m%d"); OUT = "disc_results_%s.json" % stamp
def live():
    try:
        e = next((x for x in stedi.enrollments() if x["payer"]["submittedPayerIdOrAlias"] == "DISCOVERY"), None); st = e["status"] if e else "MISSING"
    except Exception as ex: st = "enrollments error %s" % str(ex)[:60]
    # REDACTED: the probe identity is patient data and stays out of git (rules.md).
    # Set PROBE=first,last,yyyymmdd,state,dos -- the value used in practice is in the workspace copy.
    p = (os.environ.get("PROBE") or "").split(",")
    if len(p) != 5: return False, {"errors": [{"code": "", "description": "set PROBE=first,last,yyyymmdd,state,dos to test the enrollment"}]}
    j = stedi.disc(p[0], p[1], p[2], p[3], p[4]); err = [x.get("code") + " " + (x.get("description") or "") for x in j.get("errors") or []]
    ok = not any(x.startswith("41") for x in err)
    print("enrollment status:", st, "| test call:", "LIVE - answered" if ok else "not live (%s)" % "; ".join(err)[:80]); return ok, j
if __name__ == "__main__":
    ok, j = live()
    if "--check" in sys.argv or not ok: sys.exit(0 if ok else 3)
    mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
    c = {r["pid"]: r for r in (json.loads(l) for l in open(sorted(glob.glob("denial_cascade2_*.jsonl"))[-1]))}
    held = [json.load(open(f)) for f in glob.glob("/tmp/claude-0/-home-claude/f8f2f49c-f474-51d0-8966-696579307f2a/scratchpad/board_new/docs/*-denials.json")]
    ids = [os.path.basename(f)[:-5] for f in glob.glob("/tmp/claude-0/-home-claude/f8f2f49c-f474-51d0-8966-696579307f2a/scratchpad/board_new/docs/*-denials.json")]
    todo = [(i, d) for i, d in zip(ids, held) if any("Holding for Stedi Insurance Discovery" in (n.get("text") or "") for n in d.get("notes") or [])]
    done = json.load(open(OUT)) if os.path.exists(OUT) else {}
    print(len(todo), "held cards;", len(done), "already run")
    n = 0
    for cid, d in todo:
        if cid in done or n >= mx: continue
        pid = int(re.sub(r"\D", "", str(d.get("amdid") or "0")) or 0); rec = c.get(pid)
        if not rec: done[cid] = {"error": "no cascade record"}; continue
        nm = rec["patient"]; first, last = nm.split(",")[-1].strip().split(" ")[0], nm.split(",")[0].strip(); dob = rec["dob"]; dobc = dob[6:] + dob[:2] + dob[3:5]
        try:
            j = stedi.disc(first, last, dobc, "FL", rec["last"].replace("-", "")); s = stedi.disc_summ(j)
            done[cid] = {"pid": pid, "patient": nm, "dos": rec["last"], "claims": rec["claims"], "balance": rec["balance"], "verdict_before": rec["verdict"][:90], "found": s, "errors": [x.get("code") + " " + (x.get("description") or "")[:60] for x in j.get("errors") or []], "raw_id": j.get("id")}
            print("%-24s %2d $%-6.0f -> %s" % (nm[:24], rec["claims"], rec["balance"], "; ".join("%s %s %s %s" % (x.get("payer"), x.get("member"), x.get("status"), x.get("dates")) for x in s)[:150] or done[cid]["errors"]), flush=True)
        except Exception as ex: done[cid] = {"pid": pid, "patient": nm, "error": str(ex)[:120]}; print(nm, "ERR", str(ex)[:80])
        n += 1; json.dump(done, open(OUT, "w"), indent=1, default=str); time.sleep(0.4)
    print("done", n)
