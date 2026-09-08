# PLAIN ENGLISH (Full claim-status sweep - every open insurance balance)
# Decides: For every unpaid visit older than 30 days on a payer Stedi can reach, what the payer says happened to the claim (paid / denied / pending / never received), one Stedi 276/277 check per visit.
# Rules it uses: Same status/summarize/action logic as claim_status_sweep.py. Resumable: results append to claimstatus_full_<date>.jsonl and visits already answered (there or in claimstatus_<date>.json) are skipped. Largest balances first. William approved the ~$1,500 one-time cost on 9/6.
# Never touches: AMD writes, balances, claims. It only records what the payer says.
# ---
"""Usage: python3 sweep_full.py [--min-age 30] [--max N] [--carriers A,B]"""
import amd, era_post, stedi, requests, json, sys, datetime, time, os, collections
from precheck import CAR2STEDI, CARRIERS, plans
from claim_status_sweep import status, summarize, action
CAR2STEDI = dict(CAR2STEDI, BCBS1="BCBSF")
for k in ("FLO02","RET01","VACCN"): CAR2STEDI[k] = None   # Medicare and VA CCN do not offer 276 claim status through Stedi
a = sys.argv[1:]; minage = int(a[a.index("--min-age") + 1]) if "--min-age" in a else 30; mx = int(a[a.index("--max") + 1]) if "--max" in a else 10**9
only = a[a.index("--carriers") + 1].split(",") if "--carriers" in a else None
amd.login_cached(); today = datetime.date.today(); stamp = today.strftime("%Y%m%d"); OUT = "claimstatus_full_%s.jsonl" % stamp
done = set()
for f in ["claimstatus_%s.json" % stamp]:
    if os.path.exists(f): done |= {r["visitid"] for r in json.load(open(f)) if r.get("status") is not None}
if os.path.exists(OUT): done |= {json.loads(l)["visitid"] for l in open(OUT) if l.strip() and json.loads(l).get("http") != 400}
unp = requests.post(era_post.API + "/claim/massrebillsearch", headers=era_post.H(), json={}, timeout=120).json()
keep = [v for v in unp if CAR2STEDI.get(v["carriercode"].strip()) and (not only or v["carriercode"].strip() in only)
        and (today - datetime.datetime.fromisoformat(v["dateofservice"]).date()).days >= minage and v["visitid"] not in done and v["insbalance"] > 0]
keep.sort(key=lambda v: -v["insbalance"]); print("unpaid %d, to check %d (already done %d)" % (len(unp), len(keep), len(done)), flush=True)
cache = {}; cnt = collections.Counter(); n = 0
with open(OUT, "a") as fo:
    for v in keep[:mx]:
        pid = v["patientid"]; car = v["carriercode"].strip(); payer = CAR2STEDI[car]
        if pid not in cache: cache[pid] = plans(pid)
        pa, pl = cache[pid]; nm = pa.get("name") or v["patientname"]; last, first = nm.split(",")[0].strip(), nm.split(",")[-1].strip().split(" ")[0]
        dob = pa.get("dob", ""); dobc = dob[6:] + dob[:2] + dob[3:5] if dob else ""
        mine = [p for p in pl if p[1] == CARRIERS.get(car)]; member = mine[0][4] if mine else ""
        rec = {"visitid": v["visitid"], "patientid": pid, "patient": v["patientname"], "carrier": car, "dos": v["dateofservice"][:10], "balance": v["insbalance"], "amount": v["totalvisitamount"], "member": member, "icn": v.get("icn"), "when": stamp}
        if not member: rec["action"] = "SKIP - no chart plan for this carrier"
        else:
            try:
                code, j = status(payer, first, last, dobc, member, v["dateofservice"][:10].replace("-", ""), v["totalvisitamount"] or v["insbalance"])
                rows, errs = summarize(j); rec["status"] = rows; rec["errors"] = errs; rec["action"] = action(rows, errs); rec["http"] = code
            except Exception as e: rec["action"] = "ERROR " + str(e)[:100]
            time.sleep(0.25)
        fo.write(json.dumps(rec) + "\n"); fo.flush(); n += 1; cnt[rec["action"].split(" - ")[0].split(" $")[0]] += 1
        if n % 50 == 0: print(n, dict(cnt), flush=True)
print("done", n, dict(cnt), flush=True)
