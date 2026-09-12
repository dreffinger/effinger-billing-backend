import amd, re, time
import xml.etree.ElementTree as ET
amd.login_cached()
root = ET.parse("unbilled_0910.xml").getroot()
prior, insp = [], []
for v in root.iter("visit"):
    e = list(v.iter("error"))[0].get("name")
    if e.startswith("A payment from the prior"): prior.append(v.get("id"))
    elif e.startswith("Unresolved Claim Inspector") or e.startswith("One or more charges"): insp.append(v.get("id"))
print("prior-payor rows:", len(prior), "inspector rows:", insp)
def release(vids):
    ch = "".join('<visit id="%s"/>' % i for i in vids)
    r = amd.post(amd.msg("hideunbillablevisits","claimsreports",{"hide":"-1"},"<visitlist>%s</visitlist>" % ch), timeout=180)
    return "Fault" not in r, r[:200]
# inspector visits are now clean (verified this run) -> release; prrior-payor -> standing rule release
for grp, name in ((prior,"prior-payor"),(insp,"inspector-cleared")):
    for i in range(0, len(grp), 40):
        ok, r = release(grp[i:i+40])
        print(name, i, "->", ok, "" if ok else r)
        time.sleep(1.0)
