import json, re, time, os, sys, amd
import fix_referring_provider as frp
rows=json.load(open("/home/claude/unbilled/insbal_all_2026-09-22.json")); byp={}
for x in rows: byp.setdefault(str(x["patientid"]),[]).append(x)
OUT="/home/claude/unbilled/refprov15_scan.jsonl"; done=set()
if os.path.exists(OUT):
    for ln in open(OUT):
        try: done.add(json.loads(ln)["pid"])
        except: pass
f=open(OUT,"a"); t0=time.time(); n=0
for pid in sorted(byp):
    if pid in done: continue
    if time.time()-t0>235: break
    try: ref,ins=frp.plans(pid)
    except Exception as e: f.write(json.dumps({"pid":pid,"err":str(e)[:60]})+"\n"); continue
    main=[p for p in ref if p.get("ismain")=="1"]; rp=main[0].get("refprov") if main else None
    eff=[x for x in byp[pid] if str(x.get("profileid"))=="13"]; gar=[x for x in byp[pid] if str(x.get("profileid"))=="15"]
    f.write(json.dumps({"pid":pid,"main_refprov":rp,"main":main[0]["id"] if main else None,"eff_charges":len(eff),"eff_bal":round(sum(float(x.get("insbalance") or 0) for x in eff),2),"gar_charges":len(gar),"gar_bal":round(sum(float(x.get("insbalance") or 0) for x in gar),2)})+"\n"); f.flush(); n+=1
    time.sleep(0.05)
print(f"scanned {n} this call; total {len(done)+n}/{len(byp)}")
