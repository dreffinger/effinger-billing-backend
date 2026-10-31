# PLAIN ENGLISH (read-only): compact plan lists for the Humana denial charts + diagnosis codes of the MA63 / M76 visits.
import json, precheck, resave
for pid in [17471793,17469512,17475713,17472397,17471384,46048,17478018,20407,17473065,44953]:
    p = precheck.plans(pid)
    demo, plans = p[0], p[1]
    print("PLANS", pid, "insorder", demo.get("insorder"), [tuple(x[:6]) for x in plans])
for cid in ["23370984","23371225","23371226"]:
    d = resave.detail(cid)
    s = json.dumps(d, default=str)
    import re
    print("DX", cid, re.findall(r'(?:diag|dcode|icd)[^,]{0,80}', s)[:12])
    print("DETAILKEYS", cid, (list(d.keys())[:40] if isinstance(d, dict) else type(d)))
