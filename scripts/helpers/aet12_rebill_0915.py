import amd, freq1_visit, json, sys, time, os, datetime
amd.login_cached()
dry = "--dry" in sys.argv
plan = json.load(open("aet12_rebill_plan.json"))
LOGF="aet12_rebill_0915.log"
done=set(l.split()[1] for l in open(LOGF) if l.startswith("REBILL ")) if os.path.exists(LOGF) else set()
LOG=open(LOGF,"a")
def L(m): print(m,flush=True); LOG.write(m+"\n"); LOG.flush()
L("=== AET12 rebill (settings matched to AAR01) %s dry=%s n=%d done=%d ===" % (datetime.datetime.utcnow().isoformat(), dry, len(plan), len(done)))
n=0; fail=0; results=[]
for v in plan:
    vid=v["visit"]
    if vid in done: continue
    if dry:
        L("DRY REBILL %s %s -> AET12 seq %s cid %s" % (vid, v["name"], v["seq"], v["cid"])); n+=1; continue
    try:
        res=freq1_visit.run(vid, v["cid"], v["seq"])
        ok="-> 20" in res or "204" in res or "200" in res
        L("REBILL %s %s seq %s | %s" % (vid, v["name"], v["seq"], str(res)[:80]))
        results.append({"visit":vid,"name":v["name"],"res":str(res)[:120],"ok":ok})
        if ok: n+=1
        else: fail+=1
    except Exception as e:
        L("FAIL %s %s: %s" % (vid, v["name"], str(e)[:100])); fail+=1
    time.sleep(0.5)
json.dump({"stamp":datetime.datetime.utcnow().isoformat(),"sent":n,"fail":fail,"results":results}, open("registers/aet12_rebill_2026-09-15.json","w"), indent=1)
L("=== done: %d sent, %d fail ===" % (n, fail))
