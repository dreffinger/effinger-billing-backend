# 9/11 3pm ET run - scan every inspector batch, categorize errors
import amd, re, json, time, sys
amd.login_cached()
r = amd.call('action="getclaiminspectorbatches" class="chargeentry"')
bids = re.findall(r'<batch id="([^"]+)"', r)
print("batches:", len(bids), flush=True)
out = {}
for bid in bids:
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid}))
    vis = []
    for m in re.finditer(r'<visit id="(\d+)"(.*?)</visit>', t, re.S):
        vid, body = m.group(1), m.group(2)
        head = t[m.start():m.start()+1200]
        pat = re.search(r'patientid="([^"]*)"', body) or re.search(r'patientid="([^"]*)"', head)
        nm = re.search(r'patientname="([^"]*)"', body) or re.search(r'patientname="([^"]*)"', head)
        st = re.search(r'claimstatus="([^"]*)"', body) or re.search(r'claimstatus="([^"]*)"', head)
        errs = [(e.group(1), re.sub(r'\s+',' ',e.group(2))[:160]) for e in re.finditer(r'<error id="(\d+)"[^>]*>(.*?)</error>', body, re.S)]
        if not errs:
            errs = [(e.group(1), '') for e in re.finditer(r'<error id="(\d+)"', body)]
        charges = re.findall(r'<charge id="(\d+)"[^>]*proccode="([^"]*)"', body)
        dos = re.search(r'dateofservice="([^"]*)"', body) or re.search(r'\bdos="([^"]*)"', body)
        vis.append({"vid": vid, "pat": pat.group(1) if pat else "", "name": nm.group(1) if nm else "",
                    "status": st.group(1) if st else "", "errs": errs, "charges": charges,
                    "dos": dos.group(1) if dos else ""})
    if vis:
        out[bid] = vis
    time.sleep(0.35)
json.dump(out, open("insp_scan_0911.json", "w"), indent=1)
n = sum(len(v) for v in out.values())
print("visits with rows:", n)
# categorize
from collections import Counter
c = Counter()
for bid, vs in out.items():
    for v in vs:
        for eid, txt in v["errs"]:
            mm = re.search(r'Pattern (\d+)', txt)
            key = mm.group(1) if mm else (txt[:60] or "no-text")
            c[key] += 1
for k, v in c.most_common(40):
    print(v, k)