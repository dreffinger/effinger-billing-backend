# PLAIN ENGLISH (unpaid-list transaction snapshot, chat 10/15/2026 - William's aging summary)
# Decides: nothing. READ-ONLY. For every patient on the unpaid list (unpaid_raw_1015.json, the massrebillsearch answer) it
#   reads the chart's transaction history once (gettxhistory page 1; a listed visit missing from page 1 is fetched by visitid)
#   and keeps, per live charge: visit, DOS, CPT, modifiers, fee, paid, insurance/patient balance, the LAST-BILLED carrier and
#   bill date, every payment (amount, carrier, date, check number, CARC reasons) and write-off. One JSON per patient in
#   patient_db/<pid>/txh_1015.json. Resumable: a patient whose file exists is skipped. Log: logs/unpaid_txh_1015.log.
# Rules it uses: ONE login via amd.login_cached(); no names written (patient_db stays local, never mirrored).
# Never touches: AMD writes.
import json, os, re, sys, time
import xml.etree.ElementTree as ET
sys.path.insert(0, "/home/claude/unbilled")
import amd, txh

WS = "/home/claude/unbilled"
ROWS = json.load(open(os.path.join(WS, "unpaid_raw_1015.json")))
LOG = open(os.path.join(WS, "logs", "unpaid_txh_1015.log"), "a")
num = lambda s: re.sub(r"\D", "", str(s or ""))
SKIP_ATTR = {"patientname", "name", "subscribername", "respname"}

def charge_rec(c):
    a = {k: v for k, v in c.attrib.items() if k not in SKIP_ATTR}
    a["payments"] = [{k: v for k, v in p.attrib.items() if k not in SKIP_ATTR} | {"reasons": [(r.get("code", ""), r.get("amount", "")) for r in p.iter("payreason")]} for p in c.iter("payment")]
    a["writeoffs"] = [{k: v for k, v in w.attrib.items() if k not in SKIP_ATTR} for w in c.iter("writeoff")]
    return a

def main():
    amd.login_cached()
    by_pid = {}
    for r in ROWS:
        by_pid.setdefault(str(r["patientid"]), set()).add(str(r["visitid"]))
    pids = sorted(by_pid, key=int)
    done = 0
    for i, pid in enumerate(pids, 1):
        out = os.path.join(WS, "patient_db", pid, "txh_1015.json")
        if os.path.exists(out):
            continue
        try:
            root = txh.fetch(pid)
            charges = [charge_rec(c) for c in root.iter("charge")]
            have = {num(c.get("visit") or c.get("visitid")) for c in charges}
            missing = [v for v in by_pid[pid] if v not in have]
            for v in missing:                         # long charts: page 1 misses old visits
                try:
                    r2 = txh.fetch_visit(pid, v)
                    charges += [charge_rec(c) for c in r2.iter("charge")]
                except Exception as e:
                    LOG.write(json.dumps({"pid": pid, "visit": v, "err": str(e)[:200]}) + "\n")
            unapplied = [{k: v for k, v in e.attrib.items() if k not in SKIP_ATTR} | {"tag": e.tag} for e in root.iter() if e.tag in ("unappliedpayment", "unappliedwriteoff")]
            os.makedirs(os.path.dirname(out), exist_ok=True)
            json.dump({"pid": pid, "pulled": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "charges": charges, "unapplied": unapplied,
                       "missing_after_visit_fetch": [v for v in missing if v not in {num(c.get("visit") or c.get("visitid")) for c in charges}]}, open(out, "w"))
            done += 1
            LOG.write(json.dumps({"pid": pid, "charges": len(charges), "n": i, "of": len(pids)}) + "\n"); LOG.flush()
        except Exception as e:
            LOG.write(json.dumps({"pid": pid, "err": str(e)[:300], "n": i}) + "\n"); LOG.flush()
            time.sleep(2)
        time.sleep(0.25)
    LOG.write(json.dumps({"done": done, "patients": len(pids)}) + "\n"); LOG.flush()
    print("DONE", done, "of", len(pids))

if __name__ == "__main__":
    main()
