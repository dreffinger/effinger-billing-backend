# PLAIN ENGLISH (1am ET 9/21 run write-offs + Unbilled releases, William's board words 05:02-05:11Z 9/21):
# (1) obrien-patrick-denials 'write-off' -> WOINS on the 12 Humana processed-per-contract $0 claims (16 charges, $2,777);
# (2) duncan-joseph 'wrie off same as obrien' -> WOINS on the 10/25 + 11/15/2025 Humana CCM charges ($521);
# (3) cap07-recoupments-0920 'past the 12 month rule ... write them off' -> WOLATE (untimely) on the 15 CHP Sept-2024 charges ($1,879.18);
# (4) Unbilled 'A payment from the prior payor is required' rows whose primary claim is out and unanswered -> release (rule b).
# Never touches: charges with a live balance not on William's lists; Garrett's held $16.93 crossover.
import amd, manual_post, resave, json, re, time, sys
amd.login_cached(); dry="--dry" in sys.argv
NOW=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
OB=[("44953","23320921",206),("44953","23320922",109),("44953","23326192",206),("44953","23326193",109),("44953","23333502",206),("44953","23333503",109),("44953","23347001",206),("44953","23350371",206),("44953","23350372",109),("44953","23358558",198),("44953","23360206",160),("44953","23360400",160),("44953","23360425",163),("44953","23360608",310),("44953","23360695",160),("44953","23360713",160)]
DU=[("17473383","23326084",206),("17473383","23326085",109),("17473383","23329259",206)]
CHP=[("22194","22460028",168.93),("22194","22460029",73.34),("17468971","22460020",168.93),("17468971","22460021",73.34),
     ("17472078","22459779",76.93),("17472078","22459780",76.93),("17472078","22459781",76.93),("17472078","22459714",76.93),
     ("17472089","22459716",168.93),("17472096","22459845",168.93),("17472099","22459886",168.93),("17472099","22459887",73.34),
     ("17472113","22460134",168.93),("17472138","22460724",168.93),("17472144","22461248",168.93)]
reg=[]
def wo(pid,cid,bal,carrier,code,chk,note,tag):
    x=resave.detail(cid); m=re.search(r'<charge [^>]*id="charge%s"[^>]*>'%cid,x).group(0); live=float(re.search(r'insbalance="([^"]*)"',m).group(1) or 0)
    if abs(live-bal)>0.005: print("  SKIP",cid,"live insbalance",live,"!= expected",bal); reg.append(dict(tag=tag,pid=pid,cid=cid,expected=bal,live=live,outcome="skipped-balance-changed",when=NOW)); return
    ok,msg=manual_post.post(cid,carrier,0.0,live,code,checknumber=chk,note=note,dry=dry)
    time.sleep(0.6)
    after=None
    if not dry and ok:
        x2=resave.detail(cid); m2=re.search(r'<charge [^>]*id="charge%s"[^>]*>'%cid,x2).group(0); after=float(re.search(r'insbalance="([^"]*)"',m2).group(1) or 0)
    print("  %s pat%s c%s %s %.2f -> %s %s after=%s"%(tag,pid,cid,code,live,ok,msg[:90],after))
    reg.append(dict(tag=tag,pid=pid,cid=cid,carrier=carrier,code=code,amount=live,ok=ok,msg=msg[:160],insbalance_after=after,when=NOW))
print("== O'Brien WOINS (board obrien-patrick-denials, William 'write-off' 05:11Z)")
for pid,cid,b in OB: wo(pid,cid,b,"HUM01","WOINS","WO-HUM01-0921","Humana processed-per-contract $0 x2 adjudications - William write-off 9/21/2026 (board obrien-patrick-denials)","obrien")
print("== Duncan WOINS (board duncan-joseph, William 'wrie off same as obrien' 05:03Z)")
for pid,cid,b in DU: wo(pid,cid,b,"HUM01","WOINS","WO-HUM01-0921","Humana processed-per-contract $0 - William write-off 9/21/2026 same as O'Brien (board duncan-joseph)","duncan")
print("== CHP 2024 recoupments WOLATE (board cap07-recoupments-0920, William 05:02Z)")
for pid,cid,b in CHP: wo(pid,cid,b,"CAP07","WOLATE","WO-CAP07-0921","CHP paid 2024 then recouped; past the 12-month filing window - William write-off 9/21/2026 (board cap07-recoupments-0920)","cap07")
json.dump(reg,open("registers/writeoffs_2026-09-21T0510Z%s.json"%("_dry" if dry else ""),"w"),indent=1)
tot={}
for r in reg:
    if r.get("ok"): tot[r["tag"]]=round(tot.get(r["tag"],0)+r["amount"],2)
print("TOTALS written off:",tot)
# (4) Unbilled prior-payor releases
REL=["19447648","19447649","19447650","19447651","19447878","19448026","19448251","19448583","19448637","19448262","19448609","19442414","19427585","19430729"]
if not dry:
    r=amd.post(amd.msg('hideunbillablevisits','claimsreports',{'nocookie':'1','hide':'-1'},'<visitlist>%s</visitlist>'%''.join('<visit id="%s"/>'%v for v in REL)))
    print("RELEASE",len(REL),"visits ->", "ok" if "Fault" not in r else "FAULT "+re.sub(r"\s+"," ",r[:200]))
else: print("DRY release",REL)
