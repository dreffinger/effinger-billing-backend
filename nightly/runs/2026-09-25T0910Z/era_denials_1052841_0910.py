# PLAIN ENGLISH (5am ET 9/25/2026 run 2026-09-25T0910Z): denial lines of Medicare ERA 1052841 (349999075, $0) that the standing rules settle:
#   CO-29 untimely on two 9/18/2025 99349 visits first billed 9/20/2026 (pat45668, pat24799) -> WOLATE (William 9/7: primary claims over 12 months
#   from DOS and unpaid are written off); CO-16/N823 on four 10/29-10/30/2024 G0316 add-on lines (pat17470697, $30.97 each) -> WOLATE (same
#   12-month rule; the E/M on those claims was paid 9/20/2026). Each write-off: pay 0, wo = live insurance balance, ERA check number as the
#   check number, dated note; register registers/era_denials_1052841_2026-09-25T0910Z.json. --dry first. Never touches: the 50 OA-18 duplicate
#   lines (recorded only), the CO-16/N382 line (insurance lookup path), any charge whose live balance differs from the ERA line.
import amd, manual_post, resave, json, re, time, sys
amd.login_cached(); dry="--dry" in sys.argv
S="2026-09-25T0910Z"; NOW=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
d=json.load(open("era_details/1052841.json"))
todo=[]
for c in d["eracheckdetails"]:
    for ch in c["charges"]:
        cas=[(x["payreasongroup"],x["reasoncode"]) for x in ch["carc"]]
        rarc=[x["remarkcode"] for x in ch["rarc"] if not x["remarkcode"].startswith("#")]
        if ("CO","CO29") in cas: todo.append((str(c["patientid"]),str(c["visitid"]),str(ch["chargedetailid"]),ch["chargecode"],c["dos"][:10],ch["claimamount"],"CO-29 untimely"))
        elif ("CO","CO16") in cas and "N823" in rarc: todo.append((str(c["patientid"]),str(c["visitid"]),str(ch["chargedetailid"]),ch["chargecode"],c["dos"][:10],ch["claimamount"],"CO-16/N823 aged 2024 add-on"))
reg=[]
for pid,vid,cid,cpt,dos,amt,why in todo:
    x=resave.detail(cid); m=re.search(r'<charge [^>]*id="charge%s"[^>]*>'%cid,x).group(0)
    live=float(re.search(r'insbalance="([^"]*)"',m).group(1) or 0); pb=float(re.search(r'patbalance="([^"]*)"',m).group(1) or 0)
    pays=[p for p in re.findall(r'<payment [^>]*/?>',x) if 'void="1"' not in p and ('charge%s'%cid in x)]
    if abs(live-amt)>0.005 or live<=0:
        print("  SKIP pat%s v%s c%s %s live insbal %.2f != ERA %.2f"%(pid,vid,cid,cpt,live,amt)); reg.append(dict(pid=pid,vid=vid,cid=cid,cpt=cpt,dos=dos,expected=amt,live=live,outcome="skipped-balance-changed",when=NOW)); continue
    note="ERA 1052841 (Medicare 349999075) %s - 12-month rule write-off, run %s"%(why,S)
    ok,msg=manual_post.post(cid,"FLO02",0.0,live,"WOLATE",checknumber="349999075",depositdate="09/28/2026",note=note,dry=dry)
    time.sleep(0.6); after=None
    if not dry and ok:
        x2=resave.detail(cid); m2=re.search(r'<charge [^>]*id="charge%s"[^>]*>'%cid,x2).group(0); after=float(re.search(r'insbalance="([^"]*)"',m2).group(1) or 0)
    print("  WOLATE pat%s v%s c%s %s %s %.2f -> %s %s after=%s"%(pid,vid,cid,cpt,dos,live,ok,str(msg)[:90],after))
    reg.append(dict(pid=pid,vid=vid,cid=cid,cpt=cpt,dos=dos,amount=live,why=why,code="WOLATE",ok=ok,msg=str(msg)[:160],insbalance_after=after,when=NOW,dry=dry))
json.dump(reg,open("registers/era_denials_1052841_%s%s.json"%(S,"_dry" if dry else ""),"w"),indent=1)
print("TOTAL written off:",round(sum(r["amount"] for r in reg if r.get("ok")),2),"dry" if dry else "LIVE")
