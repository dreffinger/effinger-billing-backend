"""Batch WOINS via the PROVEN manual_post.post() helper (proven shape, over-apply guard).
Bounded per invocation (MAXWO) to dodge the gateway connection ceiling; resumable via mcad_woins.log."""
import sys, os, json, time, datetime, re
sys.path[:0]=['/home/claude/unbilled','/home/claude/effinger-billing-backend/core']
import manual_post
MAX=int(os.environ.get("MAXWO","12"))
targets=json.load(open("/home/claude/unbilled/mcad_woins_targets.json"))
LOG="/home/claude/unbilled/mcad_woins.log"
done=set()
if os.path.exists(LOG):
    for l in open(LOG):
        m=re.match(r"(DONE|SKIP0) (\d+)",l)
        if m: done.add(m.group(2))
lf=open(LOG,"a")
def L(m): print(m,flush=True); lf.write(m+"\n"); lf.flush()
todo=[t for t in targets if t["cid"] not in done]
note="Contractual FL Medicaid allowed; residual WOINS %s"%datetime.date.today().isoformat()
ok=0; skip=0; fail=0; money=0.0
for t in todo[:MAX]:
    cid=t["cid"]
    try:
        res_ok,msg=manual_post.post(cid,"MCAD",0.0,t["insbal"],"WOINS",note=note)
    except Exception as e:
        res_ok,msg=False,"EXC "+str(e)[:80]
    if res_ok:
        ok+=1; money+=t["insbal"]; L("DONE %s v%s %s wo=%.2f"%(cid,t["vid"],t["proc"],t["insbal"]))
    else:
        low=str(msg).lower()
        if "over-apply" in low:
            # balance already dropped (payment/adjustment landed since scan) -> nothing to write off
            skip+=1; L("SKIP0 %s v%s over-apply(bal-moved): %s"%(cid,t["vid"],str(msg)[:80]))
        else:
            fail+=1; L("FAIL %s v%s %s"%(cid,t["vid"],re.sub(r'\s+',' ',str(msg))[:120]))
    time.sleep(0.2)
rem=len(todo)-min(MAX,len(todo))
L("=== batch: ok=%d skip=%d fail=%d $%.2f | remaining=%d ==="%(ok,skip,fail,money,rem))
