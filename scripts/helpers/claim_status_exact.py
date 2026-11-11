# PLAIN ENGLISH (Exact-date claim status - one 277 per named visit, raw answer kept; rules added 11/10/2026, look-ups part A step 2)
# Decides: nothing. Asks the payer (Stedi 276/277) for the status of named visits with the EXACT date of service - the weekly check asks
#   with a +/-3-day window, so a daily-visit chart's answer can carry its neighbours' payments too (10/9/2026: four $48.34 lines across
#   three checks on a $111 visit). Writes a deduplicated summary: payments counted once per (check number, paid date, amount), with the
#   payer's claim number and the account numbers the payer echoes, so a posting can carry the right check. Every raw answer is kept under
#   patient_db/claimstatus_raw/ (never in git).
#   11/10/2026: it asks through the same rules as claim_status_sweep.py (cs_rules.py) - a visit is asked only when it is DUE: nothing
#   posted for its payer, last sent 45+ days ago (60 for a secondary balance), under a year old, a working route, and the shared ledger
#   says neither wait nor stop (a final answer on file is not asked again unless the claim was sent again); payers whose claim status does
#   not work are never sent; the run and month caps count its checks too. Every answer is written to the ledger (asked with the exact
#   date, a final answer is final). A live run needs the word --go; without it the helper prints what it WOULD ask and makes no call.
#   --help prints and exits; an unknown word is an error and nothing is asked. A visit that is not due is printed with the reason.
# Never touches: AMD writes.
"""Usage: python3 claim_status_exact.py (--vids <vid,vid,...> | --from-disposition <stamp> [--tiers POST-277,WO-PAID-NOREMIT]) [--go]
       [--aging aging_latest.json] [--ledger PATH] [--out claimstatus_exact_<stamp>.json] [--max N]
Asks only the named visits that are due by the claim-status rules (cs_rules.py), each with the exact date of service."""
import json, sys, os, re, datetime
import claim_status_sweep, cs_rules

def main(argv=None):
    o = claim_status_sweep.parse(sys.argv[1:] if argv is None else argv, "claim_status_exact.py", __doc__, exact_helper=True)   # --help / an unknown word: before any call
    o.carriers = ""; o.new_ledger = getattr(o, "new_ledger", False)
    if o.vids: vids = [v for v in re.split(r"[,\s]+", o.vids) if re.sub(r"\D", "", v)]; stamp = datetime.date.today().strftime("%Y%m%d")
    else:
        stamp = o.from_disposition; tiers = set(o.tiers.split(","))
        try:
            with open("old_claims_disposition_%s.json" % stamp) as fh: vids = [str(r["vid"]) for r in json.load(fh)["visits"] if r.get("tier") in tiers]
        except (OSError, ValueError, KeyError) as e: print("STOPPED: old_claims_disposition_%s.json cannot be read (%s) - nothing is asked" % (stamp, type(e).__name__)); return 2
    out_name = o.out or "claimstatus_exact_%s.json" % stamp
    print("exact-date claim status for %d named visit(s)" % len(vids))
    code, out, say = claim_status_sweep.run(o, "claim_status_exact.py", vids=vids, force_exact=True, keep_every_raw=True)
    if code == 2 or not o.go: return code
    have = {}
    if os.path.exists(out_name):
        try:
            with open(out_name) as fh: have = json.load(fh)
        except (OSError, ValueError): have = {}
    asked = {r["visitid"] for r in out}
    for r in out:
        rec = {"vid": r["visitid"], "pid": r["patientid"], "carrier": r["carrier"], "payer": r["payer"], "dos": r["dos"], "balance": r["balance"], "http": r.get("http"),
               "label": r.get("label"), "final": r.get("final"), "action": r.get("action"), "rows": r.get("status") or [], "errors": r.get("errors") or [],
               "payments": r.get("payments") or [], "paid_unique": round(sum(p["amount"] for p in r.get("payments") or []), 2), "cats": sorted({s.get("cat") or "" for s in r.get("status") or []})}
        have[r["visitid"]] = rec
        print("  v%s %s %s bal %.2f -> %s" % (rec["vid"], rec["carrier"], rec["dos"], rec["balance"] or 0, rec["action"]))
    for v in vids:
        v = re.sub(r"\D", "", v)
        if v not in asked and v not in have: have[v] = {"error": "not asked tonight - not due, or not on tonight's ageing file (see the lines above)"}
    with open(out_name, "w") as fh: json.dump(have, fh, indent=1)
    print("done: %d asked, %d in %s" % (len([r for r in out if r.get("label")]), len(have), out_name))
    return code
if __name__ == "__main__": sys.exit(main())
