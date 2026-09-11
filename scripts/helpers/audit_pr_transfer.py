# PLAIN ENGLISH (Patient-balance audit)
# Decides: Nothing - finds charges pushed to patient balance by denials that really mean 'wrong payer'.
# Rules it uses: PR27, PR26, PR31, PR22/24, PR33/200, PR109, PR204, PR49/119 all count as wrong-payer.
# Never touches: AMD writes.
# ---
"""Audit: charges pushed to PATIENT balance by a payer denial that really means 'wrong payer / not covered by
this plan' (PR27 coverage terminated, PR26 before coverage, PR31 not identified, PR22/PR24 COB/capitation,
PR33/PR200 lapse, PR109/PI109 not this payer, PR204 non-covered under plan, PR49/PR119/PR170...).
Scans gettxhistory for every patient on the unpaid lists; for flagged charges reads the live balance.
Output audit_pr_transfer.json / .md.  Resumable via audit_pr_progress.json."""
import amd, txh, resave, json, re, time, sys, os
FLAG = {"27","26","31","22","24","33","200","109","204","49","119","170","B7","16","4","96"}   # PR-group only, see below
PR_ONLY = {"27","26","31","22","24","33","200","109","204","49","119","170","B7","16","4","96"}
pids = json.load(open("audit_pids.json"))
prog = json.load(open("audit_pr_progress.json")) if os.path.exists("audit_pr_progress.json") else {"done": [], "hits": []}
done = set(prog["done"]); hits = prog["hits"]
t0 = time.time()
for i, pid in enumerate(pids):
    if pid in done: continue
    try:
        root = txh.fetch(pid)
    except Exception as e:
        print(pid, "ERR", str(e)[:80], flush=True); time.sleep(5); continue
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        flagged = []
        for p in c.iter("payment"):
            if p.get("void") == "1": continue
            for r in p.iter("payreason"):
                code = r.get("code") or ""
                grp, num = code[:2], code[2:]
                if grp in ("PR", "PI") and num in PR_ONLY:
                    flagged.append((code, r.get("amount"), p.get("carrier"), p.get("date"), p.get("id")))
        if flagged:
            try:
                x = resave.detail(a.get("id")); m = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % a.get("id"), x)
                st = dict(re.findall(r'(insbalance|patbalance|carrier|pos)="([^"]*)"', m.group(0))) if m else {}
                vis = dict(re.findall(r'(insorder|profile)="([^"]*)"', re.search(r'<visit [^>]*>', x).group(0)))
            except Exception as e:
                st = {"err": str(e)[:60]}; vis = {}
            hits.append({"patientid": pid, "patient": a.get("patient") or next((p.get("patient") for p in c.iter("payment")), ""),
                         "chargeid": a.get("id"), "visit": a.get("visit"), "dos": a.get("dos"), "cpt": a.get("proccode"),
                         "carrier": a.get("carrier"), "prov": a.get("provcode"), "reasons": flagged,
                         "patbalance": st.get("patbalance"), "insbalance": st.get("insbalance"), "insorder": vis.get("insorder")})
    done.add(pid)
    if i % 20 == 0:
        json.dump({"done": sorted(done), "hits": hits}, open("audit_pr_progress.json", "w"))
        print("progress %d/%d hits %d %.0fs" % (len(done), len(pids), len(hits), time.time() - t0), flush=True)
    time.sleep(0.5)
json.dump({"done": sorted(done), "hits": hits}, open("audit_pr_progress.json", "w"))
json.dump(hits, open("audit_pr_transfer.json", "w"), indent=1)
print("DONE patients %d hits %d" % (len(done), len(hits)))
