#!/usr/bin/env python3
# Nightly cascade 2026-09-24T0530Z: post Medicare check 1052828 the maximum AMD accepts.
# The whole-check post was refused (PaymentEntry=1). Post in chunks; a refused chunk is bisected
# until the single refused visit(s) are isolated for era_manual_post. Excludes 19420915 (over-apply
# guard visit) up front so it goes the manual route too.
import sys, json, time, requests, era_post
CHECK = int(sys.argv[1]) if len(sys.argv) > 1 else 1052828
EXCLUDE = {19420915}
chk = [c for c in era_post.checks() if c["id"] == CHECK][0]
det = era_post.details(CHECK)
vs = [v for v in det["eracheckdetails"] if era_post.postable(v) and v["visitid"] not in EXCLUDE]
print("check", CHECK, chk["systemcarriercode"], chk["paymentnumber"], "candidates", len(vs), "$%.2f" % sum(v["paymentamount"] for v in vs))
b = era_post.batch()
posted, refused = [], []

def post(chunk):
    code, txt = era_post.locks(CHECK, ",".join(era_post.S(v["visitid"]) for v in chunk))
    body = era_post.build(chk, det, chunk, b)
    r = requests.post(era_post.XML, headers=era_post.H(), data=json.dumps(body), timeout=300)
    ok = r.status_code == 200 and "Fault" not in r.text and "faultstring" not in r.text
    era_post.L("   POST %d visits $%.2f -> HTTP %s ok=%s %s" % (len(chunk), sum(v["paymentamount"] for v in chunk), r.status_code, ok, r.text[:300].replace("\n", " ")))
    time.sleep(1)
    return ok

def work(chunk):
    if not chunk: return
    if post(chunk): posted.extend(chunk); return
    if len(chunk) == 1: refused.extend(chunk); return
    h = len(chunk) // 2
    work(chunk[:h]); work(chunk[h:])

for i in range(0, len(vs), 20): work(vs[i:i+20])
print("=== posted %d visits $%.2f; refused %d: %s" % (len(posted), sum(v["paymentamount"] for v in posted), len(refused),
      [(v["visitid"], v["patientname"], v["dos"][:10], v["paymentamount"], v.get("insurancebalance")) for v in refused]))
json.dump({"check": CHECK, "posted": [v["visitid"] for v in posted], "posted_amount": round(sum(v["paymentamount"] for v in posted), 2),
           "refused": [{"visitid": v["visitid"], "patient": v["patientname"], "dos": v["dos"][:10], "paid": v["paymentamount"], "insbal": v.get("insurancebalance")} for v in refused],
           "excluded_upfront": sorted(EXCLUDE)}, open("registers/era_chain_2026-09-24T0530Z.json", "w"), indent=1)
