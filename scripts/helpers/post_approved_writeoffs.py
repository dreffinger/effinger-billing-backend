"""Post William's APPROVED 9/22/2026 write-offs A-D from approved_writeoffs_2026-09-22.csv (389 charges, $16,161.99).
Patient side: per visit move_to_ins.move(cid0) (no rebill) then manual_post per charge; insurance side: manual_post directly.
Live guard before every post; FCC patients / FLO99 hard-blocked; idempotent via posted_2026-09-22.json."""
import sys, os, json, time, re, datetime, pandas as pd
sys.path.insert(0, "/home/claude/unbilled")
import amd, resave, move_to_ins, manual_post
import xml.etree.ElementTree as ET
from openpyxl import Workbook, load_workbook
W="/home/claude/unbilled"; STAMP="2026-09-22"; BUD=float(sys.argv[1]) if len(sys.argv)>1 else 230
LOGF=open(f"{W}/post_approved_{STAMP}.log","a")
def L(m): print(m,flush=True); LOGF.write(m+"\n"); LOGF.flush()
PF=f"{W}/posted_{STAMP}.json"; posted=set(json.load(open(PF))) if os.path.exists(PF) else set()
def mark(c): posted.add(str(c)); json.dump(sorted(posted),open(PF,"w"))
FCC=set(json.load(open(f"{W}/fcc_open_pats_2026-09-22.json")).keys())
RP=f"{W}/Writeoff_register_{STAMP}.xlsx"
if os.path.exists(RP): wb=load_workbook(RP); ws=wb.active
else: wb=Workbook(); ws=wb.active; ws.append(["date","category","code","patient","pid","carrier","dos","cpt","amount","note","chargeid","visit"])
NOTE={"A":"QMB/dual - Medicaid paid as primary, patient not balance-billable","B":"QMB/dual - Medicare/MA paid, Medicaid secondary answered, patient not balance-billable",
      "C":"Medicaid residual after all payers finished","D":"never adjudicated, >12 months from DOS - untimely"}
A=pd.read_csv(f"{W}/approved_writeoffs_2026-09-22.csv",dtype={"cid":str,"pid":str,"visit":str})
class R(dict): __getattr__=dict.get
t0=time.time(); n=0; tot=0.0; skip=0; fail=0
def live_of(cid, side):
    d=ET.fromstring(resave.detail(cid)); c=[y for y in d.iter("charge") if y.get("id")=="charge"+cid][0]
    return float(c.get("insbalance") or 0), float(c.get("patbalance") or 0)
def post(r):
    global n, tot, fail
    note=NOTE[r.cat]+f" (approved write-off {STAMP})"
    try: ok,msg=manual_post.post(r.cid, r.car or "", 0.0, round(r.amt,2), r.code, note=note)
    except Exception as e: ok,msg=False,str(e)
    if ok:
        n+=1; tot+=r.amt; mark(r.cid); ws.append([STAMP,r.cat,r.code,r.name,r.pid,r.car,r.dos,r.cpt,round(r.amt,2),note,r.cid,r.visit]); wb.save(RP)   # save per post: a killed run can't lose rows
    else: fail+=1; L(f"  FAIL c{r.cid} {r.code} ${r.amt:.2f}: {str(msg)[:100]}")
    time.sleep(0.3)
for side in ("insurance","patient"):
    S=A[(A.side==side)&(~A.cid.isin(posted))]
    groups=[(None,S)] if side=="insurance" else list(S.groupby("visit"))
    for vid,g in groups:
        if time.time()-t0>BUD: break
        if side=="patient":
            if g.pid.iloc[0] in FCC or (g.car=="FLO99").any(): L(f"  BLOCK v{vid}: FCC patient"); continue
            try: res=move_to_ins.move(g.cid.iloc[0])
            except Exception as e: L(f"  HOLD v{vid}: move err {str(e)[:60]}"); continue
            if not re.search(r"moved ([0-9.]+)",res or "") and "nothing to move" not in (res or ""): L(f"  HOLD v{vid}: move -> {str(res)[:80]}"); continue
            time.sleep(0.4)
        for rr in g.to_dict("records"):
            r=R(rr)
            if time.time()-t0>BUD+15: break
            if r.pid in FCC or r.car=="FLO99": L(f"  BLOCK c{r.cid}: FCC"); continue
            try: ib,pb=live_of(r.cid, side)
            except Exception as e: L(f"  HOLD c{r.cid}: detail err {str(e)[:50]}"); continue
            avail=ib+pb if side=="patient" else ib
            if (side=="insurance" and abs(ib-r.amt)>0.01) or (side=="patient" and avail<r.amt-0.01):
                L(f"  SKIP c{r.cid}: balance now {avail:.2f} (approved {r.amt:.2f})"); skip+=1; mark(r.cid); continue
            post(r)
    wb.save(RP)
wb.save(RP)
left=len(A[~A.cid.isin(posted)])
L(f"batch: posted {n} ${tot:,.2f} | skipped (changed) {skip} | failed {fail} | remaining {left} of {len(A)}")
