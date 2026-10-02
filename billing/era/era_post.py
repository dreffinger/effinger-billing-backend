# PLAIN ENGLISH (Post ERA payments)
# Decides: Which ERA checks and visits in ERA Center can be posted automatically, and posts them the way the Post button does.
# Rules it uses: Only visits with a payment amount greater than zero and an open insurance balance. $0 denials are NOT posted here (they go to triage: CO24, COB9, PR27...).
# Never touches: Visits already at $0 balance; forced $0 write-offs unless you approved the visit.
# ---
"""Post ERA payments in AMD ERA Center from the backend — replica of the ERA Center SPA's
'Post' action (generatePostEraPaymentMessage in amds-era-center 16.0.25, captured 9/2/2026).

Flow per check:  release-expired locks -> postingstatus -> GET checkdetails ->
  build posterapayments (class autoremitreports) JSON ppmdmsg -> POST processrequest.aspx?long=1
Rules: only visits with processok=true, no errors, claimstatus 1, and paymentamount > 0 are posted
(zero-pay / denied visits are left unposted for review — never auto write-off a denial).
Usage: python3 era_post.py <checkid> [<checkid>...] | --all-unposted [--carrier UNI20,UHCMA,AAR01] [--dry]"""
import amd, requests, json, sys, time, os, datetime

API = "https://pm-api-103.advancedmd.com/api"
XML = "https://pm-wfe-103.advancedmd.com/practicemanager/xmlrpc/processrequest.aspx?long=1"
LOG = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "era_post.log"), "a")
def L(m):
    print(m); LOG.write(m + "\n"); LOG.flush()

def tok():
    return amd.login_cached()[1]
def H():
    return {"Authorization": "Bearer " + tok(), "Accept": "application/json", "Content-Type": "application/json",
            "origin": "https://static-100.advancedmd.com", "referer": "https://static-100.advancedmd.com/"}

def checks():
    r = requests.get(API + "/era/checks", headers=H(), timeout=60); r.raise_for_status(); return r.json()
def details(checkid):
    r = requests.get(API + "/era/checkdetails", params={"checkid": checkid}, headers=H(), timeout=120); r.raise_for_status(); d = r.json()
    # 10/2/2026 lesson: a fully posted check leaves the list as PROCESSED (not dismissed) and checkdetails answers an empty
    # claim list afterwards, so cache the lines in era_details/ BEFORE anything posts them (payreasons and the audits read it).
    try:
        if d.get("eracheckdetails"):
            os.makedirs("era_details", exist_ok=True); json.dump(d, open(os.path.join("era_details", "%s.json" % checkid), "w"))
    except Exception as e: L("   cache write failed for %s: %s" % (checkid, e))
    return d
def batch():
    r = requests.get(API + "/transaction/batch", headers=H(), timeout=60); return r.text.strip().strip('"') or "1"
def locks(checkid, claimids=""):
    fl = "AutoERAProcessingBOT,ERA_ReportID_%s" % checkid
    requests.post(API + "/era/locks/release-expired", headers=H(), data=json.dumps(fl), timeout=60)
    r = requests.post(API + "/era/locks/postingstatus", headers=H(),
                      json={"reportId": int(checkid), "reportClaimIds": claimids, "featureLockList": fl}, timeout=60)
    return r.status_code, r.text[:300]

PAYCODE = {"ACH": "9", "NON": "10", "CHK": "11", "FWT": "12", "BOP": "13"}
S = lambda v: "%s" % v
def fmt_num(v):  # JS `${n}` formatting: 97.59 -> "97.59", 141.0 -> "141", 0.0 -> "0"
    if isinstance(v, float) and v == int(v): return str(int(v))
    return str(v)

def reason(c):
    return {"@id": S(c["reportreasondetailid"]), "@reasonid": S(c["payreasonid"]), "@code": S(c["reasoncode"]),
            "@name": S(c["reasontext"]), "@amount": fmt_num(c["reasonamt"]), "@units": S(c["units"]), "@group": S(c["payreasongroup"])}
def remark(r):
    return {"@id": S(r["remarkid"]), "@remarkcode": r["remarkcode"], "@code": r["remarkcode"], "@name": r["remarktext"]}
def charge(ch):
    rl = [reason(c) for c in ch.get("carc", [])]
    sl = [remark(r) for r in ch.get("rarc", []) if r["remarkcode"] != "#AM"]
    return {"@id": S(ch["reportreasondetailid"]), "@chargedetailid": S(ch["chargedetailid"]), "@chargecode": S(ch["chargecode"]),
            "@paymentamount": fmt_num(ch["paymentamount"]), "@adjustmentamount": fmt_num(ch["adjustmentamount"]),
            "@claimamount": fmt_num(ch["claimamount"]), "@patientamount": fmt_num(ch["patientamount"]),
            "@allowedamount": fmt_num(ch["allowedamount"]), "@takebackamount": fmt_num(ch["takebackamount"]),
            "@dos": ch["dos"], "@subcarriercode": ch["subcarriercode"], "@paymentid": S(ch["paymentid"]),
            "@paymentdetailid": S(ch["paymentdetailid"]), "@paymentvoided": "1" if ch["paymentvoided"] else "0",
            "@paymentreversed": "1" if ch["paymentreversed"] else "0", "@payreasonwocode": S(ch["payreasonwocode"]),
            "@payreasonwoamount": fmt_num(ch["payreasonwoamount"]), "@expectedamount": fmt_num(ch["expectedamount"]),
            "@nextaction": ch["nextaction"], "reasonlist": ({"reason": rl} if rl else {}),
            "serviceremarkcodelist": ({"serviceremarkcode": sl} if sl else {})}
def visit(v):
    return {"@id": S(v["visitid"]), "@claimid": S(v["checkclaimid"]), "@amount": fmt_num(v["paymentamount"]),
            "@patientid": S(v["patientid"]), "@patientname": v["patientname"], "@chartnumber": S(v["chartnum"]),
            "@profileid": S(v["profileid"]), "@profilecode": v["profilecode"], "@profilename": v["profilename"],
            "@calculatedamount": fmt_num(v["calculatedamount"]), "@chargecount": S(v["chargecount"]), "@dos": v["dos"],
            "@carrierid": S(v["carrierid"]), "@remarkcodes": "None", "@claimstatus": S(v["claimstatus"]),
            "@hasreversals": "1" if v["hasreversals"] else "0", "@interestamount": S(v["interestamount"]),
            "@insurancebalance": fmt_num(v["insurancebalance"]), "errorlist": {},
            "chargelist": {"@dopayreasonwo": "0", "@doexpectedwo": "0", "charge": [charge(c) for c in v["charges"]]}}

FORCE_VISITS = set()   # visit ids William approved for $0 posting (= write-off with the CARC reason)
def postable(v):
    if not v.get("processok") or v.get("errors"): return False
    if v["visitid"] in FORCE_VISITS: return True
    # 9/6: a visit already at $0 insurance balance is settled (payment posted earlier or written off) - AMD refuses it
    if float(v.get("insurancebalance") or 0) <= 0: return False
    return v.get("claimstatus") in (1, 2) and float(v.get("paymentamount") or 0) > 0

def build(chk, det, visits, batchid):
    msg = {"@nocookie": 1, "usercontext": tok(), "@action": "posterapayments", "@class": "autoremitreports",
           "@msgtime": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000Z"),
           "@dopatientunapplyreapply": "1" if det.get("dopatientunapplyreapply") else "0",
           "@eracustomruletwo": "1" if det.get("chargeequalswriteoff") else "0",
           "@controlerawriteoffssystemdefault": "0", "@batch": S(batchid), "@reportid": S(chk["id"]),
           "@check": chk["paymentnumber"], "@depositdate": chk["depositdate"],
           "@paymethod": PAYCODE.get(chk["paymentcode"], "14"), "visitlist": {"visit": [visit(v) for v in visits]}}
    am = None
    for v in visits:
        for r in v.get("rarc", []):
            if r["remarkcode"] == "#AM": am = r; break
        if am: break
    if am:
        msg["systemreasonlist"] = {"reason": [{"@reasonid": S(am["remarkid"]), "@code": am["remarkcode"], "@name": am["remarktext"],
                                              "@amount": "0.00", "@units": "", "@group": ""}]}
    # Blank write-off code (charges in a financial class without an auto write-off, e.g. XX) -> AMD refuses to post.
    # Proven fix 9/2/2026: fill WOINS and set controlerawriteoffssystemdefault=1 + chargelist dopayreasonwo=1.
    blank = False
    for vis in msg["visitlist"]["visit"]:
        for ch in vis["chargelist"]["charge"]:
            if not ch["@payreasonwocode"].strip() and float(ch["@adjustmentamount"] or 0) != 0:
                ch["@payreasonwocode"] = "WOMCAD" if chk.get("systemcarriercode") == "MCAD" else "WOINS"; blank = True
    if blank:
        msg["@controlerawriteoffssystemdefault"] = "1"
        for vis in msg["visitlist"]["visit"]: vis["chargelist"]["@dopayreasonwo"] = "1"
    # Over-apply guard (proven 9/3/2026): when the remaining insurance balance already equals the payment
    # (adjustments were posted earlier / by the primary), AMD refuses "payment could not be posted".
    # Post the payment only: zero the adjustments and drop the CARC reasons on those visits.
    for v, vis in zip(visits, msg["visitlist"]["visit"]):
        pay = float(v.get("paymentamount") or 0); adj = sum(float(c.get("adjustmentamount") or 0) for c in v["charges"])
        bal = float(v.get("insurancebalance") or 0)
        if pay > 0 and adj > 0 and pay + adj > bal + 0.005:
            for ch in vis["chargelist"]["charge"]:
                ch["@adjustmentamount"] = "0"; ch["@payreasonwoamount"] = "0"; ch["reasonlist"] = {}
            vis["chargelist"]["@dopayreasonwo"] = "0"
            L("   over-apply guard: visit %s pay %.2f adj %.2f bal %.2f -> posting payment only" % (v["visitid"], pay, adj, bal))
    return {"ppmdmsg": msg}

def post_check(chk, dry=False, maxvisits=500):
    cid = chk["id"]
    det = details(cid)
    vs = det["eracheckdetails"]
    go = [v for v in vs if postable(v) and (not FORCE_VISITS or v["visitid"] in FORCE_VISITS)]
    skip = [v for v in vs if not postable(v)]
    L("check %s %s %s $%s unposted=%s visits=%d postable=%d skipped=%d" % (cid, chk["systemcarriercode"], chk["paymentnumber"], chk["paymentamount"], chk["unpostedamount"], len(vs), len(go), len(skip)))
    for v in skip:
        L("   skip visit %s %s dos %s paid=%s status=%s ok=%s err=%s" % (v["visitid"], v["patientname"], v["dos"][:10], v["paymentamount"], v["claimstatus"], v.get("processok"), [e.get("paymententrymessage") or e for e in v.get("errors", [])][:2]))
    if not go or dry: return 0, 0.0
    b = batch()
    total = 0.0; n = 0
    for i in range(0, len(go), maxvisits):
        chunk = go[i:i+maxvisits]
        code, txt = locks(cid, ",".join(S(v["visitid"]) for v in chunk))
        body = build(chk, det, chunk, b)
        r = requests.post(XML, headers=H(), data=json.dumps(body), timeout=300)
        ok = r.status_code == 200 and "Fault" not in r.text and "faultstring" not in r.text  # UI response is Results:null/Error:null on success; verify via /era/checks
        L("   POST %d visits $%.2f -> HTTP %s ok=%s %s" % (len(chunk), sum(v["paymentamount"] for v in chunk), r.status_code, ok, r.text[:1200].replace("\n", " ")))
        if ok: n += len(chunk); total += sum(v["paymentamount"] for v in chunk)
        time.sleep(1)
    return n, total

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    carriers = None
    if "--carrier" in sys.argv: carriers = set(sys.argv[sys.argv.index("--carrier") + 1].split(","))
    if "--visits" in sys.argv:
        FORCE_VISITS.update(int(x) for x in sys.argv[sys.argv.index("--visits") + 1].split(","))
        print("FORCE (write-off) visits:", sorted(FORCE_VISITS))
    allc = checks()
    if "--all-unposted" in sys.argv:
        todo = [c for c in allc if (FORCE_VISITS or float(c["unpostedamount"] or 0) > 0) and (not carriers or c["systemcarriercode"] in carriers)]
    else:
        todo = [c for c in allc if str(c["id"]) in args]
    L("=== ERA POST %s: %d checks, dry=%s ===" % (time.ctime(), len(todo), dry))
    N = 0; T = 0.0
    for c in sorted(todo, key=lambda x: x["depositdate"]):
        try:
            n, t = post_check(c, dry=dry)
        except Exception as e:
            L("   ERROR check %s: %s" % (c["id"], e)); continue
        N += n; T += t
    L("=== done: posted %d visits, $%.2f ===" % (N, T))
