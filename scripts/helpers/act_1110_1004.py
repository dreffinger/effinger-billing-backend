# PLAIN ENGLISH (AMD writes for the 7 AM ET 10/4 run, 2026-10-04T1110Z) - ERA check 1052960 (Sunshine Health $0 denial remit X319720720, 14 lines):
#   (1) pat17472546 x4 99233 9/9-9/12/2026: Medicare paid 138.20 each, the Sunshine Medicaid-MMA secondary answered $0 OA-23/CO-45 -> the
#       21.80 coinsurance residual is contractual on a dual: WOCAID2ND (rules.md 10/4 line) with the remit's trace number as check #.
#   (2) CO-22 'other payer primary' on two visits billed to Sunshine FIRST while Medicare is ACTIVE on the chart (AMD 271 this run):
#       pat17472429 v19456182 99308 9/21 $107 -> patient order 4,5 (Medicare, Sunshine), visit insorder 4,5, freq-1 rebill seq 4;
#       pat20670 v19456209 99309 9/24 $141 -> patient order 1,2, visit insorder 1,2, freq-1 rebill seq 1.
#   (3) then DISMISS check 1052960 (no money on it; M56 lines stay on the centene-m56 board row, the CO-222 line goes to William's row,
#       the CO-18 lines are already at $0).  --dry prints the plan and posts nothing.  Register: registers/act_2026-10-04T1110Z.json
import amd, manual_post, move_to_ins, freq1_visit, ins_update, era_post, requests, json, sys, time
DRY = "--dry" in sys.argv; amd.login_cached(); STAMP="2026-10-04T1110Z"; CHK="X319720720"; DD="10/05/2026"; log=[]
def L(s): print(s, flush=True); log.append(s)
# (1) WOCAID2ND
for cid in ("23365353","23365384","23365526","23365546"):
    ok,msg = manual_post.post(cid,"SUN01",0.0,21.80,"WOCAID2ND",CHK,DD,"ERA 1052960 Sunshine $0 OA-23 dual crossover - WOCAID2ND run %s"%STAMP,DRY)
    L("WOCAID2ND c%s -> %s %s"%(cid,ok,msg)); time.sleep(0.4)
# (2) COB re-routes
for pid,insid,vid,cid,order,seq in (("17472429","9519143","19456182","23367806","4,5",4),("20670","6406","19456209","23367833","1,2",1)):
    if DRY:
        L("DRY pat%s: ins_update sequence=%s; freq1 v%s c%s seq %s; move_to_ins %s"%(pid,order,vid,cid,seq,move_to_ins.move(cid,order,dry=True)))
        continue
    L("pat%s ins_update order %s -> %s"%(pid,order,ins_update.update(pid,insid,sequence=order))); time.sleep(0.4)
    L("pat%s freq1 v%s c%s seq %s -> %s"%(pid,vid,cid,seq,freq1_visit.run(vid,cid,str(seq)))); time.sleep(0.4)
    L("pat%s move_to_ins c%s %s -> %s"%(pid,cid,order,move_to_ins.move(cid,order,rebill_seq=seq))); time.sleep(0.4)
# (3) dismiss
if DRY: L("DRY dismiss 1052960")
else:
    bad=[l for l in log if "FAULT" in l or "-> False" in l]
    if bad: L("NOT dismissing 1052960 - earlier step failed: %s"%bad)
    else:
        r=requests.post("https://pm-api-103.advancedmd.com/api/era/checks/dismiss",headers=era_post.H(),data=json.dumps("1052960"),timeout=60)
        L("dismiss 1052960 -> %s %s"%(r.status_code,r.text[:120]))
        time.sleep(1); L("checks after: %s"%[c["id"] for c in era_post.checks()])
json.dump({"stamp":STAMP,"dry":DRY,"log":log},open("registers/act_%s%s.json"%(STAMP,"_dry" if DRY else ""),"w"),indent=1)
