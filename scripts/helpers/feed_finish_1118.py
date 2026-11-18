# Finish the 20261118T1240Z ingest after the 600 s command cap stopped it in the verify step (import had completed).
# Same steps/order as claimocity_ingest.py lines 123-150: patient map, verify, inspector, report, recon, file register.
import json, os, sys, subprocess, hashlib, datetime, re
WS="/home/claude/unbilled"; os.chdir(WS); stamp="20261118T1240Z"
env=dict(os.environ, FEED_STAMP=stamp, FEED_DX_CACHE="dx_cache_feed.json", FEED_CHART_PREFIX="F"+stamp[2:8], PYTHONPATH=WS, FEED_HL7_DIR=os.path.join("hl7",stamp))
pmap=json.load(open("registers/claimocity_patient_map.json"))
for v in json.load(open("feed_match_%s.json"%stamp)).values():
    if v.get("resolved"):
        for fid in v.get("feed_ids",[]): pmap[fid]=v["resolved"]
json.dump(pmap,open("registers/claimocity_patient_map.json","w"),indent=0,sort_keys=True)
for name,cmd in [("verify",["claimocity_verify.py"]),("inspector",["claimocity_inspector.py"]),("report",["claimocity_report.py"]),("recon",["claimocity_recon.py",stamp])]:
    log="logs/claimocity_%s_%s.log"%(stamp,name)
    with open(log,"w") as fh: r=subprocess.run([sys.executable]+cmd,cwd=WS,env=env,stdout=fh,stderr=subprocess.STDOUT,text=True)
    print("[%s] exit %d %s"%(name,r.returncode," | ".join(t[:110] for t in open(log).read().strip().splitlines()[-3:])),flush=True)
reg=json.load(open("registers/claimocity_ingest.json")); parsed=json.load(open("feed_parsed_%s.json"%stamp))
batch=os.path.join("hl7",stamp); now=datetime.datetime.utcnow().isoformat()+"Z"
for b in os.listdir(batch):
    msgs=[m for m in parsed if m["file"]==b[:8] or b.startswith(m["file"])]
    reg["files"][b]={"stamp":stamp,"sha256":hashlib.sha256(open(os.path.join(batch,b),"rb").read()).hexdigest(),"messages":len(msgs),"at":now}
reg["runs"].append({"stamp":stamp,"at":now,"live":True,"files":os.listdir(batch),"exit":0,"note":"finished by feed_finish_1118.py after the 600 s cap"})
json.dump(reg,open("registers/claimocity_ingest.json","w"),indent=1)
print("register: files registered",os.listdir(batch))
