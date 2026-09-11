# PLAIN ENGLISH (Medicare $0 denial scan)
# Decides: Nothing - finds every 2025+ Medicare $0 denial that means 'bill someone else' (CO24, COB9, CO109, CO16, CO22).
# Rules it uses: Resumable, read-only. Output feeds gv_rebill and co24_restore.
# Never touches: AMD writes.
# ---
"""Practice-wide scan of Medicare (FLO02) $0 denials that mean 'bill someone else / fix and rebill':
CO24 (Advantage plan responsible), COB9 (hospice -> GV/GW), CO109 (wrong contractor e.g. Railroad), CO16 (missing info),
CO22 (COB). DOS 2025+. Resumable: scan_co24_progress.json -> scan_co24.json"""
import amd, txh, json, re, time, os, string
amd.login_cached()
CODES={"CO24","COB9","CO109","CO16","CO22","PR24","PRB9","PI24"}
if not os.path.exists("all_pids.json"):
    pids=set()
    for a in string.ascii_uppercase:
        r=amd.post('<ppmdmsg action="lookuppatient" class="lookup" msgtime="%s" name="%s%%" nocookie="1"/>' % (amd._msgtime(), a))
        for m in re.finditer(r'<patient id="pat(\d+)" name="([^"]*)"', r): pids.add(m.group(1))
        time.sleep(0.3)
    json.dump(sorted(pids), open("all_pids.json","w")); print("patients", len(pids), flush=True)
pids=json.load(open("all_pids.json"))
prog=json.load(open("scan_co24_progress.json")) if os.path.exists("scan_co24_progress.json") else {"done":[],"hits":[]}
done=set(prog["done"]); hits=prog["hits"]
for i,pid in enumerate(pids):
    if pid in done: continue
    try: root=txh.fetch(pid)
    except Exception as e: print(pid,"ERR",str(e)[:60],flush=True); time.sleep(5); continue
    for c in root.iter("charge"):
        a=c.attrib
        if a.get("void")=="1" or (a.get("fee") or "").startswith("-") or (a.get("dos") or "")[-4:]<"2025": continue
        for p in c.iter("payment"):
            if p.get("void")=="1" or float(p.get("amount") or 0)!=0: continue
            codes=[r.get("code") for r in p.iter("payreason")]
            if set(codes)&CODES:
                hits.append({"pid":pid,"patient":a.get("patient"),"cid":a.get("id"),"visit":a.get("visit"),"dos":a.get("dos"),"cpt":a.get("proccode"),
                             "fee":a.get("fee"),"insbal":a.get("insbal"),"patbal":a.get("patbal"),"paycarrier":p.get("carrier"),"paydate":p.get("date"),
                             "codes":codes,"chargecarrier":a.get("carrier"),"fac":a.get("faccode")})
    done.add(pid)
    if i%25==0:
        json.dump({"done":sorted(done),"hits":hits}, open("scan_co24_progress.json","w")); print(i,len(hits),flush=True)
json.dump({"done":sorted(done),"hits":hits}, open("scan_co24_progress.json","w")); json.dump(hits, open("scan_co24.json","w"))
print("=== done", len(hits), flush=True)
