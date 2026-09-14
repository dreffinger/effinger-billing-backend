# PLAIN ENGLISH (Unbilled + inspector read-only scan, 11 PM ET 9/13/2026 slot - ehpa cloud run 9/14 0420UTC)
# Decides: nothing. For the Unbilled rows of scan_0912/summary_before.json it reads (a) getdemographic for every
#   'Insurance order is missing' patient (DOB, address, insplans) and (b) gettxhistory for every patient on a
#   'prior payor' / 'payment reason codes' / 'charges have errors' row and records, per Unbilled visit, each live
#   charge's carrier, billdate, paid, insurance/patient balance and its payments and write-offs, so the run can
#   apply William's release / write-off rules. (c) reads charge detail for the inspector visits (diagcodes + modifiers).
# Never touches: AMD writes.
import amd, txh, resave, json, re, time, sys, os, collections
import xml.etree.ElementTree as ET
amd.login_cached()
S = json.load(open("scan_0912/summary_before.json"))
out = {"demo": {}, "txh": {}, "insp": {}}
def L(m): print(m, flush=True)

# (a) demographics for the no-insurance rows
noins = sorted({r["patientid"] for r in S["unbilled"] if r["_errs"] and "Insurance order" in r["_errs"][0]})
for pid in noins:
    try:
        x = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}), timeout=60)
        root = ET.fromstring(x); p = root.find(".//patient"); a = dict(p.attrib) if p is not None else {}
        addr = root.find(".//address"); ad = dict(addr.attrib) if addr is not None else {}
        plans = [dict(i.attrib) for i in root.iter("insplan")]
        rpl = [dict(i.attrib) for i in root.iter("refplan")]
        d = {"name": a.get("name"), "dob": a.get("dob"), "sex": a.get("sex"), "chart": a.get("chartnumber"), "ssn_last4": (a.get("ssn") or "")[-4:],
             "addr": {k: ad.get(k) for k in ("address1", "address2", "city", "state", "zip")},
             "plans": [{k: i.get(k) for k in ("id", "carrier", "carriername", "subscribernum", "sequence", "begindate", "enddate", "coverage")} for i in plans],
             "refplans": [{k: i.get(k) for k in ("id", "ismain", "preauth", "refnum")} for i in rpl], "insorder": a.get("insorder")}
        out["demo"][pid] = d
        L("DEMO %s %s dob=%s addr=%s plans=%s" % (pid, d["name"], d["dob"], d["addr"], [(p["carrier"], p["subscribernum"], p["sequence"], p["begindate"], p["enddate"]) for p in d["plans"]]))
    except Exception as e:
        L("DEMO ERR %s %s" % (pid, str(e)[:120]))
    time.sleep(0.3)

# (b) tx history for the other rows
rows = [r for r in S["unbilled"] if not (r["_errs"] and "Insurance order" in r["_errs"][0])]
pids = sorted({r["patientid"] for r in rows})
byvisit = {r["id"]: r for r in rows}
for pid in pids:
    try:
        root = txh.fetch(pid)
    except Exception as e:
        L("TXH ERR %s %s" % (pid, str(e)[:100])); continue
    for c in root.iter("charge"):
        a = c.attrib
        v = a.get("visit") or a.get("visitid")
        if v not in byvisit: continue
        rec = {"chargeid": a.get("id"), "proc": a.get("proccode"), "dos": a.get("dos"), "carrier": a.get("carrier"), "billdate": a.get("billdate"),
               "amount": a.get("amount"), "paid": a.get("paid"), "insbal": a.get("insbal"), "patbal": a.get("patbal"), "void": a.get("void"),
               "insbilled": a.get("insbilled"), "payerinfo": a.get("payerinfo"),
               "pays": [{k: p.get(k) for k in ("id", "amount", "date", "carrier", "checknumber", "void", "paycode")} for p in c.iter("payment")],
               "wos": [{k: w.get(k) for k in ("id", "amount", "date", "wocode", "void")} for w in c.iter("writeoff")]}
        out["txh"].setdefault(v, {"pid": pid, "name": byvisit[v].get("patientname"), "err": byvisit[v]["_errs"][0][:40], "charges": []})["charges"].append(rec)
    time.sleep(0.35)
for v, d in sorted(out["txh"].items()):
    L("VISIT %s %s %s | %s" % (v, d["pid"], d["name"], d["err"]))
    for c in d["charges"]:
        if c["void"] == "1": continue
        L("   chg %s %s %s car=%s bill=%s paid=%s insbal=%s patbal=%s pays=%s wos=%s" % (c["chargeid"], c["proc"], c["dos"], c["carrier"], c["billdate"], c["paid"], c["insbal"], c["patbal"],
              [(p["amount"], p["date"], p["carrier"], p["void"]) for p in c["pays"]], [(w["amount"], w["date"], w["wocode"], w["void"]) for w in c["wos"]]))
missing = [v for v in byvisit if v not in out["txh"]]
L("visits with no txh match: %s" % missing)

# (c) inspector charges
for bid, vs in S["inspector"].items():
    for v in vs:
        for cid, _ in v["chgs"]:
            try:
                x = resave.detail(cid)
                ch = re.search(r'<charge [^>]*>', x); ca = dict(re.findall(r'(\w+)="([^"]*)"', ch.group(0))) if ch else {}
                dmap = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', x))
                mmap = dict(re.findall(r'<modcode id="(mcode\d+)"[^>]*?\bcode="([^"]*)"', x))
                out["insp"][cid] = {"vid": v["vid"], "pid": v["pid"], "proc": ca.get("proccode"), "dos": ca.get("dos") or ca.get("begindate"), "diagcodes": ca.get("diagcodes"), "dmap": dmap, "modcodes": ca.get("modcodes"), "mmap": mmap, "pos": ca.get("pos")}
                L("INSP v%s chg %s %s %s dx=%s -> %s mods=%s %s" % (v["vid"], cid, ca.get("proccode"), ca.get("dos") or ca.get("begindate"), ca.get("diagcodes"), [dmap.get(x_, x_) for x_ in (ca.get("diagcodes") or "").split()], ca.get("modcodes"), mmap))
            except Exception as e:
                L("INSP ERR %s %s" % (cid, str(e)[:100]))
            time.sleep(0.3)
json.dump(out, open("scan_0912/unbilled_0914_detail.json", "w"), indent=1)
L("saved scan_0912/unbilled_0914_detail.json")
