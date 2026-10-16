# PLAIN ENGLISH (UNI20/BCBS pre-5/1 pass 111, run 2026-10-16T0310Z): READ-ONLY evaluation of claimstatus_20261016.json -
# counts the answers, copies them to the pass register, and for every NOT-ON-FILE row reads the charge's live billdate
# (gettxhistory via txh.fetch_visit) so a D0 inside 30 days of the last send is 'not yet on file', never a candidate.
# Decides nothing, writes nothing in AdvancedMD. Output: registers/uni20_bcbs_pre0501_sweep_2026-10-16T0310Z.json + a summary.
import json, datetime, collections, txh, amd
S="2026-10-16T0310Z"; rows=json.load(open("claimstatus_20261016.json"))
json.dump(rows, open("registers/uni20_bcbs_pre0501_sweep_%s.json"%S,"w"), indent=1)
watch=json.load(open("/home/claude/effinger-billing-backend/practices/ehpa/registers/tf_writeoff_watch.json"))
wv={str(v.get("vid")) for it in watch.get("items",[]) for v in it.get("visits",[])}
rl=set()
try:
    for ln in open("registers/rebill_log.jsonl"):
        try:
            j=json.loads(ln)
            if (j.get("at") or j.get("when") or "")[:10] >= "2026-09-14": rl.add(str(j.get("vid") or j.get("visitid")))
        except Exception: pass
except FileNotFoundError: pass
c=collections.Counter(r["action"].split(" - ")[0] for r in rows); print("asked", len(rows), "$%.2f"%sum(r["balance"] for r in rows)); print(dict(c))
today=datetime.date.today(); cands=[]; notes=[]
for r in rows:
    if not r["action"].startswith("NOT ON FILE"): continue
    cats={s.get("cat") for s in r.get("status") or []}
    ok_cats = cats and cats <= {"D0","A3","A6","A7","A8"}
    try:
        v=txh.fetch_visit(r["patientid"], r["visitid"])   # ElementTree root (PPMDResults) - the 1310Z lesson: read charges with root.iter('charge')
        chs=v.get("charges") if isinstance(v,dict) else [c for c in v.iter("charge") if c.get("visit")==str(r["visitid"]) and c.get("void")!="1"]
        bd=max((ch.get("billdate") or "" for ch in (chs or [])), default="")
    except Exception as e: bd="ERR "+str(e)[:60]
    recent = bd[:10]>= (today-datetime.timedelta(days=30)).isoformat() if bd and not bd.startswith("ERR") and "-" in bd[:10] else None
    if recent is None and bd and not bd.startswith("ERR"):
        try:
            m,d,y=bd[:10].split("/"); recent = datetime.date(int(y),int(m),int(d)) >= today-datetime.timedelta(days=30)
        except Exception: recent=None
    why=[]
    if not ok_cats: why.append("cats %s"%sorted(cats))
    if str(r["visitid"]) in wv: why.append("in tf watch")
    if str(r["visitid"]) in rl: why.append("rebill_log<30d")
    if recent: why.append("billdate %s <30d"%bd[:10])
    if recent is None: why.append("billdate unreadable %s"%bd[:20])
    notes.append((r["visitid"], r["patientid"], r["carrier"], r["dos"], r["balance"], bd[:10], ";".join(why) or "CANDIDATE"))
    if not why: cands.append(r)
for n in notes: print("  ", n)
print("candidates", len(cands))
json.dump({"stamp":S,"asked":len(rows),"by_action":dict(c),"not_on_file_eval":notes,"candidates":[r["visitid"] for r in cands]}, open("registers/uni20_bcbs_pre0501_eval_%s.json"%S,"w"), indent=1, default=str)
