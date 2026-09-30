# PLAIN ENGLISH (Unbilled repair - the two row types the 2-hourly / nightly run can clear without new data; William's standing approval 9/30/2026)
# Decides: (a) 'Payment reason codes are missing or do not balance' rows whose ERA line cannot be re-posted (payreasons --list says
#   'no-era-line' because the check is fully posted and the era_details/ cache is empty): the $0 CODE-LESS payment on the charge is
#   VOIDED (the 9/12 rule - the payer's paid line keeps its CARC reasons, the WOINS contractual stays), the visit is re-read and
#   released only when every live payment balances (|paid| + reasons == fee);
#   (b) 'A payment from the prior payor is required before another claim can be submitted' rows are released (rule b, 9/8/2026 -
#   the primary claim is out and unanswered; they re-list on their own if the secondary still cannot bill after the primary posts).
# Rows with any other error text are left alone (facesheet / inspector / duplicate-chart holds belong to their own steps).
# Never touches: payments that carry reasons, write-offs, charges not on the row.
#   python3 unbilled_repair.py            # dry: list what it would do
#   python3 unbilled_repair.py --live     # do it, register -> registers/unbilled_repair_<stamp>.json
import payreasons, void_tx, json, time, sys, datetime, re
LIVE = "--live" in sys.argv
def num(s): return re.sub(r"\D", "", str(s or ""))
stamp = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%MZ")
reg = {"run": stamp, "live": LIVE, "reason_rows": [], "prior_rows": [], "left": []}
rows = payreasons.unbilled_rows(all_rows=True)
for r in rows:
    errs = r.get("errors", "")
    pid, vid = r["pid"], r["visitid"]
    if "Payment reason codes" in errs:
        st = payreasons.visit_state(pid, vid)
        cl = [(c["cid"], p["id"], p["amount"], p["checkno"]) for c, p in payreasons.codeless(st)]
        row = {"pid": pid, "vid": vid, "codeless": cl}
        zero = [x for x in cl if x[2] == 0.0]
        if not zero or len(zero) != len(cl):
            row["outcome"] = "held: code-less payment carries money - needs the ERA-linked re-post (payreasons --unbilled --live) when the cache has the line"
            reg["reason_rows"].append(row); print(json.dumps(row)); continue
        if not LIVE:
            row["outcome"] = "dry: would void %s then release" % [z[1] for z in zero]; reg["reason_rows"].append(row); print(json.dumps(row)); continue
        row["voids"] = [(cid, payid, void_tx.void_payment(pid, cid, payid)) for cid, payid, _, _ in zero]
        time.sleep(0.5)
        st2 = payreasons.visit_state(pid, vid)
        row["balanced_after"] = payreasons.balanced(st2)
        row["insbal_after"] = [(c["cid"], c["cpt"], c["insbalance"], c["patbalance"]) for c in st2]
        row["release"] = payreasons.release_visit(vid) if row["balanced_after"] and all(v[2][0] for v in row["voids"]) else "held (void failed or still unbalanced)"
        reg["reason_rows"].append(row); print(json.dumps(row)); time.sleep(0.4)
    elif "prior payor" in errs:
        row = {"pid": pid, "vid": vid, "release": payreasons.release_visit(vid) if LIVE else "dry: would release"}
        reg["prior_rows"].append(row); print(json.dumps(row)); time.sleep(0.4 if LIVE else 0)
    else:
        reg["left"].append({"pid": pid, "vid": vid, "err": errs[:80]})
print("SUMMARY reason rows %d, prior rows %d, left alone %d" % (len(reg["reason_rows"]), len(reg["prior_rows"]), len(reg["left"])))
json.dump(reg, open("registers/unbilled_repair_%s.json" % stamp, "w"), indent=1, default=str)
