# PLAIN ENGLISH (board patients read-only dump, 11 PM ET 9/14/2026 slot - ehpa cloud run 2026-09-15T0310Z)
# Decides: nothing. For each board patient prints insurance plans (id, carrier, member, seq, begin/end) and every
# non-void charge with an open insurance or patient balance (cid, visit, dos, cpt, fee, insbal, patbal, carrier, billdate,
# payments with check numbers) so the action script can be written from live data. Never touches: AMD writes.
import amd, txh, sys, json, re
import xml.etree.ElementTree as ET
amd.login_cached()
pids = sys.argv[1:]
out = {}
for pid in pids:
    root = ET.fromstring(amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat%s" % pid, "nocookie": "1"}), timeout=60))
    p = root.find(".//patient"); pa = p.attrib if p is not None else {}
    plans = [dict(i.attrib) for i in root.iter("insplan")]
    print("### pat%s %s %s dob=%s insorder=%s" % (pid, pa.get("lastname"), pa.get("firstname"), pa.get("dob"), pa.get("insorder")))
    for i in plans:
        print("   PLAN %s car=%s %s sub=%s seq=%s begin=%s end=%s" % (i.get("id"), i.get("carrier"), i.get("carriercode") or i.get("carriername") or "", i.get("subscribernum"), i.get("sequence"), i.get("begindate"), i.get("enddate")))
    rows = []
    for c in txh.fetch(pid).iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        ib = float(a.get("insbal") or 0); pb = float(a.get("patbal") or 0)
        if ib <= 0 and pb <= 0: continue
        pays = [(q.get("id"), q.get("amount"), q.get("checknumber") or q.get("checkno") or "", q.get("carrier") or "", q.get("date") or q.get("postdate") or "", q.get("void") or "") for q in c.iter("payment")]
        wos = [(w.get("id"), w.get("amount"), w.get("code") or w.get("wocode") or "", w.get("void") or "") for w in c.iter("writeoff")]
        r = {"cid": a.get("id"), "visit": a.get("visit"), "dos": (a.get("dos") or "").strip(), "cpt": a.get("proccode"), "fee": a.get("amount"), "insbal": ib, "patbal": pb, "carrier": a.get("carrier"), "billdate": a.get("billdate"), "insorder": a.get("insorder"), "pays": pays, "wos": wos}
        rows.append(r)
        print("   CHG %s v%s %s %s fee=%s insbal=%.2f patbal=%.2f car=%s bill=%s pays=%s wos=%s" % (r["cid"], r["visit"], r["dos"], r["cpt"], r["fee"], ib, pb, r["carrier"], r["billdate"], pays, wos))
    out[pid] = {"patient": pa, "plans": plans, "open": rows}
json.dump(out, open("board_read_0310.json", "w"), indent=1)
