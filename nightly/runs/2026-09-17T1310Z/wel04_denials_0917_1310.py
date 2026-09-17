# PLAIN ENGLISH (9am ET 9/17/2026 run): two WellCare (WEL04) $0 denial checks (1051696, 1051697) arrived in the ERA Center.
# Reads gettxhistory on the 4 charts and records each denied visit's LIVE charge state (carrier, insurance/patient balance,
# paid, billdate) beside the ERA line's CARC so the denials board note says what is really open. Never touches: AMD writes.
import amd, re, json, time, collections
lines=[]
for cid in ("1051696","1051697"):
    d=json.load(open("era_details/%s.json"%cid))
    for l in d["eracheckdetails"]:
        carcs=[(c["reasoncode"],c["reasonamt"]) for c in l["carc"]]
        rarcs=[r["remarkcode"] for r in l["rarc"]]
        lines.append({"checkid":cid,"checkclaimid":l["checkclaimid"],"pid":str(l["patientid"]),"visit":str(l["visitid"]),"dos":l["dos"][:10],"pay":l["paymentamount"],"wo":l["woamt"],"stored_insbal":l["insurancebalance"],"carc":carcs,"rarc":rarcs,"chargedetailid":[c["chargedetailid"] for c in l["carc"]]})
amd.login_cached()
live={}
for pid in sorted({l["pid"] for l in lines}):
    t=amd.post(amd.msg("gettxhistory","demographics",{"patientid":pid,"filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}),timeout=120)
    for m in re.finditer(r'<charge [^>]*/?>', t):
        a=dict(re.findall(r'(\w+)="([^"]*)"', m.group(0)))
        live.setdefault(a.get("visit"),[]).append({k:a.get(k) for k in ("id","proccode","dos","carrier","lastbilledcarrier","billdate","datebilled","insbal","patbal","paid","insorder","void","paymentcount")})
    time.sleep(0.3)
for l in lines:
    l["live"]=live.get(l["visit"],[])
    print(l["checkid"],"pat"+l["pid"],"vst",l["visit"],l["dos"],"carc",l["carc"],"rarc",l["rarc"],"stored_insbal",l["stored_insbal"])
    for c in l["live"]: print("    live",c)
json.dump(lines,open("registers/wel04_denials_2026-09-17T1310Z.json","w"),indent=1)
print("saved",len(lines),"lines")
