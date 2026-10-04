# PLAIN ENGLISH (read-only facts for the 7 AM ET 10/4 run, 2026-10-04T1110Z): a new Centene/Sunshine $0 denial remit (ERA check 1052960,
#   14 claim lines) arrived 03:50Z. Before deciding anything this script reads the LIVE chart state of every visit on it: plans
#   (getdemographic), charges/payments (gettxhistory), and AMD 271 on the open plans of the two CO-22 charts. Output:
#   registers/reads_2026-10-04T1110Z.json + a printed summary. Never touches: AMD writes.
import amd, elig_amd, re, json, time
amd.login_cached()
STAMP="2026-10-04T1110Z"; out={"stamp":STAMP,"charts":{},"elig":{}}
def P(*a): print(*a, flush=True)
def demo(pid):
    d = amd.post(amd.msg("getdemographic","demographics",{"patientid":str(pid),"nocookie":"1"}),timeout=120)
    pa = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<patient [^>]*>', d).group(0))) if re.search(r'<patient [^>]*>', d) else {}
    plans=[dict(re.findall(r'(\w+)="([^"]*)"',x)) for x in re.findall(r'<insplan [^>]*/?>',d)]
    return {"name":pa.get("name"),"dob":pa.get("dob"),"insorder":pa.get("insorder"),
            "plans":[{k:p.get(k) for k in ("id","sequence","carrier","subscribernum","begindate","enddate")} for p in plans]}
def hist(pid):
    t = amd.post(amd.msg("gettxhistory","demographics",{"patientid":str(pid),"filterhistory":"0","pagenumber":"1","typefilter":"1","sortbypayment":"false","groupbyvisit":"0","sortdescending":"1","visitid":"0","getmemo":"false","nocookie":"1"}),timeout=120)
    rows=[]
    for m in re.finditer(r'<charge [^>]*/?>',t):
        a=dict(re.findall(r'(\w+)="([^"]*)"',m.group(0)))
        rows.append({k:a.get(k) for k in ("id","visit","dos","proccode","fee","insbal","patbal","paid","carrier","billdate","void","insbilled","modifiers","insorder")})
    pays=[dict(re.findall(r'(\w+)="([^"]*)"',x)) for x in re.findall(r'<payment [^>]*/?>',t)]
    return rows,[{k:p.get(k) for k in ("id","charge","amount","void","carrier","checknumber","date","paymentcode")} for p in pays]
VIS={"17472546":["19454458","19454438","19454311","19454281"],"17472429":["19456182"],"20670":["19456209"],"17471755":["19455292","19448638"],
     "17469541":["19456313"],"20729":["19454394"],"17473346":["19454409"],"17472286":["19454393"],"17471131":["19454414"],"17469007":["19455291"]}
for pid,vids in VIS.items():
    try: dm=demo(pid); hs,pays=hist(pid)
    except Exception as e: P("pat%s ERROR %s"%(pid,e)); out["charts"][pid]={"error":str(e)}; continue
    sub=[r for r in hs if r["visit"] in vids]
    subp=[p for p in pays if p["charge"] in {r["id"] for r in sub}]
    out["charts"][pid]={"demo":dm,"charges":sub,"payments":subp}
    P("\npat%s | %s insorder %s"%(pid,dm["name"],dm["insorder"]))
    for p in dm["plans"]: P("   plan %s seq %s %s %s %s-%s"%(p["id"],p["sequence"],p["carrier"],p["subscribernum"],p["begindate"],p["enddate"]))
    for r in sub: P("   c%s v%s %s %s fee %s ins %s pat %s paid %s last %s billed %s void %s vorder %s"%(r["id"],r["visit"],r["dos"],r["proccode"],r["fee"],r["insbal"],r["patbal"],r["paid"],r["carrier"],r["billdate"],r["void"],r["insorder"]))
    for p in subp: P("      pay %s c%s $%s %s chk %s %s void %s"%(p["id"],p["charge"],p["amount"],p["carrier"],p["checknumber"],p["date"],p["void"]))
    time.sleep(0.3)
for pid in ("17472429","20670","17469541"):
    try:
        pa,pl=elig_amd.plans(pid)
        for p in pl:
            if p.get("enddate"): continue
            s=elig_amd.run_plan(pid,p["id"].replace("ins",""),True); line=elig_amd.one_line(s); out["elig"]["%s %s"%(pid,p["id"])]=line
            P("271 pat%s %s seq %s %s -> %s"%(pid,p["id"],p.get("sequence"),p.get("carrier"),line[:260])); time.sleep(0.3)
    except Exception as e: P("271 pat%s ERROR %s"%(pid,e))
json.dump(out,open("registers/reads_%s.json"%STAMP,"w"),indent=1)
