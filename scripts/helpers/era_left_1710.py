# PLAIN ENGLISH (ERA remainder table, run 2026-09-30T1710Z): for every claim line still on the ERA Center's unposted checks after the Post pass,
# shows the remit line (visit, CPT, DOS, paid, CO / PR / OA amounts, CARCs) beside the LIVE charge (insurance balance, patient balance,
# payments with check numbers) so the manual-post fallback can be decided line by line. Reads only.
import era_post, txh, json, re
out = []
for ck in ["1052904", "1052905", "1052906", "1052907"]:
    d = era_post.details(ck); json.dump(d, open("era_details/%s.json" % ck, "w"), indent=1)
    for v in d["eracheckdetails"]:
        pid, vid = str(v["patientid"]), str(v["visitid"])
        try:
            root = txh.fetch_visit(pid, vid); live = {}
            for c in root.iter("charge"):
                if c.get("void") == "1": continue
                live[re.sub(r"\D", "", c.get("id"))] = dict(cpt=c.get("proccode"), dos=c.get("dos"), fee=c.get("fee"), insbal=c.get("insbal"), patbal=c.get("patbal"), paid=c.get("paid"), carrier=c.get("carrier"),
                    pays=[(p.get("amount"), p.get("checknumber"), p.get("void")) for p in c.iter("payment")])
        except Exception as e: live = {"err": str(e)[:80]}
        for ch in v["charges"]:
            cid = str(ch.get("chargedetailid")); carcs = [(x["payreasongroup"] + x["reasoncode"][2:] if x["reasoncode"].startswith(x["payreasongroup"]) else x["reasoncode"], x["reasonamt"]) for x in v.get("carc", []) if str(x.get("chargedetailid")) == cid]
            rec = dict(check=ck, vid=vid, pid=pid, claimstatus=v["claimstatus"], cid=cid, cpt=ch.get("chargecode"), dos=(ch.get("dos") or "")[:10], paid=ch.get("paymentamount"), adj=ch.get("adjustmentamount"), patamt=ch.get("patientamount"), carcs=carcs, rarc=[r.get("remarkcode") for r in v.get("rarc", []) if str(r.get("chargedetailid", cid)) == cid][:3], live=live.get(cid) or live.get("err") or "no-live-charge", rem_insbal=v["insurancebalance"])
            out.append(rec); print(json.dumps(rec))
json.dump(out, open("registers/era_left_2026-09-30T1710Z.json", "w"), indent=1)
print("LINES", len(out))
