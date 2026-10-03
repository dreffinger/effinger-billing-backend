import txh, time, json
import xml.etree.ElementTree as ET
out={}
for pid, vid in [("23391","19392347"), ("17470743","19441047"), ("17473343","19442414")]:
    root = txh.fetch_visit(pid, vid)
    print("VISIT", vid, "pat", pid)
    for c in root.iter("charge"):
        a=c.attrib
        print("  CHG", a.get("id"), a.get("dos") or a.get("dateofservice"), a.get("proccode"), "car", a.get("carrier") or a.get("carriercode"), "billdate", a.get("billdate"), "amt", a.get("amount"), "insbal", a.get("insbalance") or a.get("insbal"), "patbal", a.get("patbalance") or a.get("patbal"), "void", a.get("void"), "payer", a.get("payerinfo"))
        for p in c.iter("payment"):
            pa=p.attrib; print("     PAY", {k:pa.get(k) for k in ("id","date","amount","checknumber","carrierfid","paymentcode","void","origrefnum","payreasoncode") if pa.get(k) is not None})
        for w in c.iter("writeoff"):
            wa=w.attrib; print("     WO ", {k:wa.get(k) for k in ("id","date","amount","code","void","checknumber") if wa.get(k) is not None})
    out[vid]=ET.tostring(root).decode()[:20000]
    time.sleep(0.3)
json.dump(out, open("registers/priorpayor_reads_2026-10-03T0510Z.json","w"))
