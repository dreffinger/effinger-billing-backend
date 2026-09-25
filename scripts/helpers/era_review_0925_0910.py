# PLAIN ENGLISH (5am ET 9/25/2026 run 2026-09-25T0910Z): two Medicare ERAs arrived - 1052840 (819853087, $7,615.62, 93 paid claims, Post button)
#   and 1052841 (349999075, $0, 57 denial lines on 35 claims: 50 OA-18 duplicates, 4 CO-16 N823 on 2024 G0316 lines, 2 CO-29, 1 CO-16 N382).
#   Decides: nothing. Reads every denied visit live (gettxhistory: charges, balances, non-void payments with check numbers, last-billed carrier)
#   and the chart's plans (getdemographic) so the denial handling can classify each line; samples the posted check's visits so the
#   Post button's balances can be audited. Never touches: AMD writes.
import amd, txh, json, re, time, sys
import xml.etree.ElementTree as ET
amd.login_cached()
S="2026-09-25T0910Z"
out={"stamp":S,"denials":[],"posted":[]}
PL={}; TX={}
def load(pid):
    if pid not in TX:
        TX[pid]=txh.fetch("pat"+pid); time.sleep(0.3)
        t=amd.post(amd.msg("getdemographic","demographics",{"patientid":pid,"nocookie":"1"}),timeout=120)
        PL[pid]=[dict(re.findall(r'(id|carrier|sequence|enddate|begindate|subscribernum)="([^"]*)"',p)) for p in re.findall(r'<insplan [^>]*/?>',t)]
        m=re.search(r'<patient [^>]*insorder="([^"]*)"',t); PL[pid+"_order"]=m.group(1) if m else ""
        m=re.search(r'<patient [^>]*deathdate="([^"]*)"',t); PL[pid+"_death"]=m.group(1) if m else ""
        time.sleep(0.3)
def visit_rows(pid,vid):
    root=TX[pid]; chg=[]
    for ch in root.iter("charge"):
        if ch.get("visit")==vid and ch.get("void")!="1":
            pays=[{k:p.get(k) for k in ("carrier","amount","void","date","checknumber","paymentcode","origrefnum","id")} for p in ch.iter("payment")]
            wos=[{k:w.get(k) for k in ("wocode","amount","void","date","id")} for w in ch.iter("writeoff")]
            chg.append({k:ch.get(k) for k in ("id","proccode","dos","fee","carrier","billdate","insbilled","insbal","patbal","paid","insorder","payerinfo","provcode")}|{"payments":pays,"writeoffs":wos})
    return chg
first=True
for ck in ("1052841","1052840"):
    d=json.load(open("era_details/%s.json"%ck))
    for c in d["eracheckdetails"]:
        pid=str(c["patientid"]); vid=str(c["visitid"])
        if ck=="1052840" and len(out["posted"])>=12: break
        load(pid)
        if first:
            for ch in TX[pid].iter("charge"):
                for p in ch.iter("payment"): print("PAYMENT ATTRS:",p.attrib); first=False; break
                if not first: break
        lines=[{"cpt":ch["chargecode"],"paid":ch["paymentamount"],"cas":[(x["payreasongroup"],x["reasoncode"],x["reasonamt"]) for x in ch["carc"]],"rarc":[x["remarkcode"] for x in ch["rarc"] if not x["remarkcode"].startswith("#")]} for ch in c["charges"]]
        rec={"check":ck,"pid":pid,"vid":vid,"dos":c["dos"][:10],"claimstatus":c.get("claimstatus"),"era_insbal":c.get("insurancebalance"),"era_lines":lines,
             "plans":PL[pid],"order":PL[pid+"_order"],"death":PL[pid+"_death"],"charges":visit_rows(pid,vid)}
        (out["denials"] if ck=="1052841" else out["posted"]).append(rec)
        print(ck,"pat"+pid,"v"+vid,rec["dos"],"st",rec["claimstatus"],"order",rec["order"],"death",rec["death"],"plans",[(p.get("carrier"),p.get("sequence"),p.get("enddate")) for p in PL[pid]])
        for x in rec["charges"]:
            print("    ",x["proccode"],x["dos"],"car",x["carrier"],"bill",x["billdate"],"insbal",x["insbal"],"patbal",x["patbal"],"paid",x["paid"],"order",x["insorder"],"prov",x["provcode"],
                  "PAY",[(p["carrier"],p["amount"],p["checknumber"],p["date"],p.get("origrefnum")) for p in x["payments"] if p["void"]!="1"],
                  "WO",[(w["wocode"],w["amount"],w["date"]) for w in x["writeoffs"] if w["void"]!="1"])
json.dump(out,open("registers/era_review_%s.json"%S,"w"),indent=1)
print("DONE",len(out["denials"]),"denial visits,",len(out["posted"]),"posted sample")
