import amd, txh, re
amd.login_cached()
r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat17474798", "nocookie": "1"}))
for m in re.findall(r'<insplan ([^>]*)>', r):
    d = dict(re.findall(r'(\w+)="([^"]*)"', m)); print("plan", d.get("id"), d.get("sequence"), d.get("carrier"), d.get("subscribernum"), d.get("begindate"), "-", d.get("enddate"))
p = re.search(r'<patient [^>]*>', r); print("insorder", dict(re.findall(r'(\w+)="([^"]*)"', p.group(0))).get("insorder"))
root = txh.fetch_visit("17474798", "19459520")
for ch in root.iter("charge"):
    c = ch.attrib; print("CHG", c.get("id"), c.get("date"), c.get("proccode"), c.get("carrier"), "bill", c.get("billdate"), "amt", c.get("amount"), "void", c.get("void"), [(pm.attrib.get("date"), pm.attrib.get("amount"), pm.attrib.get("carrier")) for pm in ch.iter("payment")])
