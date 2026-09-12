# Working Denials scan - pull every $0-paid / denied ERA line and its CARC/RARC reasons.
import era_post, json, sys, time, datetime, collections
from era_post import checks, details
API="https://pm-api-103.advancedmd.com/api"
mx=int(sys.argv[sys.argv.index("--max")+1]) if "--max" in sys.argv else 10**9
rows=[]; codefreq=collections.Counter(); grpfreq=collections.Counter(); carrfreq=collections.Counter()
allc=checks(); print("checks on list:", len(allc))
for i,chk in enumerate(allc):
    if i>=mx: break
    try: det=details(chk["id"])
    except Exception as e: print("ERR",chk["id"],str(e)[:60]); continue
    for v in det["eracheckdetails"]:
        pay=float(v.get("paymentamount") or 0)
        for ch in (v.get("charges") or []):
            adjc=ch.get("carc") or []
            chgpay=float(ch.get("paymentamount") or 0)
            # a denial line: no payment on the charge but a CARC reason present
            if chgpay==0 and adjc:
                for c in adjc:
                    grp=str(c.get("payreasongroup") or ""); code=str(c.get("reasoncode") or "")
                    amt=float(c.get("reasonamt") or 0)
                    key="%s-%s"%(grp,code)
                    codefreq[key]+=1; grpfreq[grp]+=1; carrfreq[chk.get("systemcarriercode") or "?"]+=1
                    rarc=sorted({str(r.get("remarkcode")) for r in (ch.get("rarc") or []) if r.get("remarkcode") and not str(r.get("remarkcode")).startswith("#")})
                    rows.append({"check":chk.get("paymentnumber"),"checkid":chk["id"],"carrier":chk.get("systemcarriercode"),"rarc":rarc,
                        "patient":v.get("patientname"),"pid":v.get("patientid"),"visitid":v.get("visitid"),
                        "dos":(v.get("dos") or "")[:10],"cpt":ch.get("chargecode"),"billed":ch.get("chargeamount") or ch.get("expectedamount"),
                        "group":grp,"carc":code,"reason":c.get("reasontext"),"amt":amt})
    time.sleep(0.15)
stamp=datetime.date.today().strftime("%Y%m%d")
json.dump(rows, open("denials_%s.json"%stamp,"w"), indent=1)
print("denial lines:", len(rows), "unique patients:", len({r['pid'] for r in rows}), "visits:", len({r['visitid'] for r in rows}))
print("\nTop CARC group+code (count, $ adj):")
byamt=collections.Counter()
for r in rows: byamt["%s-%s"%(r['group'],r['carc'])]+=r['amt']
for k,c in codefreq.most_common(20):
    print("  %-10s n=%-5d $%-12.2f %s"%(k,c,byamt[k], next((r['reason'] for r in rows if "%s-%s"%(r['group'],r['carc'])==k),"")[:60]))
print("\nBy group:", dict(grpfreq))
print("By carrier:", dict(carrfreq.most_common(12)))
