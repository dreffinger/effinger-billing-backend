#!/usr/bin/env python3
# PLAIN ENGLISH (the 20 November CCM visits that went out at POS 32 for residents in a skilled stay -> POS 31)
# William 11/26/2026: "Skilled ones at 31", then "Yes thx" to correcting the 20 skilled residents (40 lines, DOS 11/24/2026). The 13
#   unclear charts stay at 32 and are not in the register. Register: practices/ehpa/registers/ccm_pos31_1126.json (chart, visit and
#   charge ids only).
# Decides, per visit, from the payer's answer recorded in the register (answer + icn, filled from the ERA / claim-status answer):
#   - no answer yet ............................ WAITING, no write (a correction before the payer has the claim makes a duplicate);
#   - rejected (the payer never took the claim). resave POS 31 on every live charge + a new claim (frequency 1, freq1_visit);
#   - paid or denied, Medicare Advantage ...... resave POS 31 + a corrected claim (frequency 7 with the payer's claim number, freq7_visit);
#   - paid or denied, FLO02 (First Coast) ..... NO write: First Coast takes no frequency-7 claim; it needs a reopening (SPOT portal).
#     Printed as REOPENING NEEDED for William.
#   A visit whose lines all read 31 already is DONE. Every write is read back; the register line is updated only from the readback.
# Never touches: other visits, diagnoses, balances, payments. Dry unless --live. --only <visit,visit> limits the run.
# Usage: python3 ccm_pos31_1126.py [--live] [--only 19462557,...] [--register PATH]
import json, os, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
REG = os.path.join(HERE, "..", "..", "practices", "ehpa", "registers", "ccm_pos31_1126.json")
MEDICARE = {"FLO02", "RET01"}

def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv and sys.argv.index(name) + 1 < len(sys.argv) else default

def decide(it):
    """What to do with one register line (no AMD call) -> (action, why)."""
    if it.get("done"): return "skip", "done " + it["done"]
    ans = (it.get("answer") or "").strip().lower()
    if not ans: return "wait", "no answer from the payer yet"
    if ans == "rejected": return "freq1", "the payer rejected the claim - a new claim at 31"
    if ans not in ("paid", "denied"): return "wait", "answer '%s' is not one this script acts on" % ans
    if it.get("carrier") in MEDICARE: return "reopen", "First Coast %s it - a reopening to POS 31 is needed (SPOT portal)" % ans
    if not str(it.get("icn") or "").strip(): return "wait", "the payer %s it but no claim number is recorded" % ans
    return "freq7", "the payer %s it - corrected claim at 31 with claim number on file" % ans

def resave_pos31(it):
    import amd, resave
    vis, pat, allc = resave.visit_charges(it["charges"][0])
    live = sorted(c.get("id").replace("charge", "") for c in allc)
    if sorted(it["charges"]) != live: return None, "STOPPED: the visit's live charges %s are not the register's %s" % (live, it["charges"])
    if all(c.get("pos") == "31" for c in allc): return allc, "already 31"
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        a["pos"] = "31"
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, x) for k, x in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
        "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, x) for k, x in va.items()), chg)))
    if "Fault" in r: return None, "FAULT resave: " + re.sub(r"\s+", " ", r[:200])
    time.sleep(1); v2, p2, c2 = resave.visit_charges(it["charges"][0])
    got = [(c.get("proccode"), c.get("pos")) for c in c2]
    if len(c2) != len(allc) or any(p != "31" for _, p in got): return None, "STOPPED: readback after resave %s (live %d of %d)" % (got, len(c2), len(allc))
    return c2, "resaved to 31 %s" % got

def main():
    live = "--live" in sys.argv
    only = set(re.split(r"[,\s]+", arg("--only", "") or "")) - {""}
    path = arg("--register", REG); reg = json.load(open(path))
    todo = [it for it in reg["items"] if not only or it["vid"] in only]
    if live:
        import amd; amd.login_cached()
    n = {}
    for it in todo:
        act, why = decide(it); n[act] = n.get(act, 0) + 1
        head = "v%s chart %s %s" % (it["vid"], it["pid"], it["carrier"])
        if act in ("skip", "wait"): print("%s: %s - %s" % (act.upper(), head, why)); continue
        if act == "reopen": print("REOPENING NEEDED: %s - %s" % (head, why)); it["status"] = "reopening needed (William, SPOT)"; continue
        if not live: print("DRY %s: %s - %s" % (act, head, why)); continue
        c2, said = resave_pos31(it); print("%s: %s" % (head, said))
        if c2 is None: it["status"] = said; continue
        import freq1_visit, freq7_visit
        res = freq7_visit.run(it["vid"], it["charges"][0], 1, it["icn"]) if act == "freq7" else freq1_visit.run(it["vid"], it["charges"][0], 1)
        print("   %s" % res)
        ok = not str(res).startswith(("FAULT", "REFUSED"))
        it["status"] = ("sent " if ok else "resaved to 31, claim not sent: ") + str(res)
        if ok: it["done"] = time.strftime("%Y-%m-%dT%H%MZ", time.gmtime())
    print("summary: %s" % ", ".join("%s %d" % kv for kv in sorted(n.items())))
    if live: json.dump(reg, open(path, "w"), indent=1)
    return 0

if __name__ == "__main__":
    sys.exit(main())
