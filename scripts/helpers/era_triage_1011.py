# PLAIN ENGLISH (read-only triage of the ERA Center unposted list after the 835 upload - 1 AM ET 10/11/2026 run 2026-10-11T0510Z)
# Decides: nothing in AMD. For every unposted check: caches its details (era_details/<id>.json through payreasons.details), then for every
#   claim line reads the LIVE charge (gettxhistory by visit) and sorts the line into: posted-with-reasons (a non-void payment carrying this
#   check number WITH reason codes - already posted), codeless-hand-post (a non-void payment carrying this check number with NO reason
#   codes - the 10/9 'per 277' posts: the payreasons repost path voids it and re-posts the ERA line ERA-linked), open (no payment with this
#   check number and an open insurance balance - the Post button / fallback can post it), zero-balance (open balance 0 - adjudicated),
#   denial ($0 line), orphan (no visit). Prints one line per check and writes registers/era_triage_<stamp>.json.
# Never touches: AMD writes.
import amd, payreasons, era_post, txh, json, re, sys, time, os
from collections import Counter
S = "2026-10-11T0510Z"
amd.login_cached()
checks = era_post.checks()
reg = {"stamp": S, "checks": []}
tot = Counter(); dol = Counter()
cache = {}
def state(pid, vid):
    k = (pid, vid)
    if k not in cache:
        try: cache[k] = payreasons.visit_state(pid, vid, root=txh.fetch_visit(pid, vid))
        except Exception as e: cache[k] = []
    return cache[k]
for chk in checks:
    cid = str(chk["id"]); chkno = str(chk.get("paymentnumber") or ""); car = chk.get("carriername") or chk.get("eracarriername")
    try: det = payreasons.details(cid)
    except Exception as e: reg["checks"].append({"checkid": cid, "err": str(e)[:200]}); continue
    claims = det.get("eracheckdetails") or []
    rec = {"checkid": cid, "checkno": chkno, "carrier": car, "amount": chk.get("checkoreftamount") or chk.get("checkamount"), "claims": len(claims), "lines": []}
    for cl in claims:
        vid = str(cl.get("visitid") or ""); pid = str(cl.get("patientid") or ""); cpaid = float(cl.get("paymentamount") or 0)
        for ln in cl.get("charges") or []:
            lpaid = float(ln.get("paymentamount") or 0); cdid = str(ln.get("chargedetailid") or "")
            row = {"vid": vid, "pid": pid, "claim": cl.get("checkclaimid"), "cdid": cdid, "cpt": ln.get("chargecode") or ln.get("cptcode"), "paid": lpaid, "status": cl.get("claimstatus") or cl.get("claimstatuscode")}
            if not vid or vid == "0" or not pid: row["kind"] = "orphan"
            else:
                st = state(pid, vid)
                ch = next((c for c in st if cdid and c["cid"] == re.sub(r"\D", "", cdid)), None)
                if ch is None and len(st) == 1: ch = st[0]
                if ch is None: row["kind"] = "no-charge-match"
                else:
                    row["insbal"] = ch["insbalance"]; row["patbal"] = ch["patbalance"]; row["cid"] = ch["cid"]
                    same = [p for p in ch["pays"] if p["void"] != "1" and chkno and p["checkno"].split("(")[0] == chkno]
                    if same and any(p["reasons"] for p in same): row["kind"] = "posted-with-reasons"
                    elif same: row["kind"] = "codeless-hand-post"; row["payid"] = same[0]["id"]; row["hand_amt"] = same[0]["amount"]
                    elif lpaid <= 0: row["kind"] = "denial"
                    elif ch["insbalance"] <= 0.005: row["kind"] = "zero-balance"
                    else: row["kind"] = "open"
            tot[row["kind"]] += 1; dol[row["kind"]] += lpaid
            rec["lines"].append(row)
    rec["kinds"] = dict(Counter(r["kind"] for r in rec["lines"]))
    rec["paid_open"] = round(sum(r["paid"] for r in rec["lines"] if r["kind"] == "open"), 2)
    rec["paid_codeless"] = round(sum(r["paid"] for r in rec["lines"] if r["kind"] == "codeless-hand-post"), 2)
    print("CHECK", cid, chkno, car, rec["amount"], "claims", len(claims), rec["kinds"], "open$", rec["paid_open"], "codeless$", rec["paid_codeless"], flush=True)
    reg["checks"].append(rec); time.sleep(0.2)
reg["totals"] = {"lines": dict(tot), "dollars": {k: round(v, 2) for k, v in dol.items()}, "checks": len(checks), "check_total": round(sum(float(c.get("checkoreftamount") or c.get("checkamount") or 0) for c in checks), 2)}
print("TOTALS", json.dumps(reg["totals"]))
json.dump(reg, open("registers/era_triage_%s.json" % S, "w"), indent=1)
print("saved registers/era_triage_%s.json" % S)
