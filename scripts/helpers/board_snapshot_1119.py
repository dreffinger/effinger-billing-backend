# PLAIN ENGLISH (Board-answer chart snapshot, 11/19/2026 chat run)
# Decides: Nothing. For every chart number given, reads the chart's insurance plans, default insurance order, name and DOB
#          (getdemographic) and every live charge with its balances, last-billed carrier, bill date and payments (gettxhistory).
# Rules it uses: Read-only. Output stays in the workspace (board_snapshot_1119.json) - patient data, never mirrored.
# Never touches: Anything in AdvancedMD.
# Usage: python3 board_snapshot_1119.py <pid> [<pid> ...]
import amd, txh, re, sys, json
amd.login_cached()
CAR = json.load(open("carriers_rich.json"))
out = {}
for pid in sys.argv[1:]:
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    pm = re.search(r'<patient [^>]*>', r); pa = dict(re.findall(r'(\w+)="([^"]*)"', pm.group(0))) if pm else {}
    plans = []
    for tag in re.findall(r'<insplan [^>]*>', r):
        a = dict(re.findall(r'(\w+)="([^"]*)"', tag))
        if a.get("id"): plans.append(a)
    print("\n=== pat%s %s dob %s sex %s insorder [%s] ssn4 %s" % (pid, pa.get("name"), pa.get("dob"), pa.get("sex"), pa.get("insorder"), (pa.get("ssn") or "")[-4:]))
    for p in plans:
        print("   plan %s seq %s %s %s id %s begin %s end %s" % (p["id"], p.get("sequence"), p.get("carrier"), (CAR.get(p.get("carrier")) or ["?"])[0], p.get("subscribernum"), p.get("begindate"), p.get("enddate")))
    root = txh.fetch(pid); chs = []
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        pays = [(p.get("amount"), p.get("checknumber") or p.get("checknum"), p.get("carrier") or p.get("carriercode"), p.get("void")) for p in c.iter("payment")]
        wos = [(w.get("amount"), w.get("code") or w.get("writeoffcode"), w.get("void")) for w in c.iter("writeoff")]
        chs.append(dict(a, _pays=pays, _wos=wos))
    openc = [a for a in chs if abs(float(a.get("insbalance") or 0)) + abs(float(a.get("patbalance") or 0)) > 0.005]
    print("   live charges %d, open %d" % (len(chs), len(openc)))
    for a in openc:
        print("   CHG %s v%s dos %s %s fee %s insbal %s patbal %s car %s billdate %s prof %s pays %s wos %s" % (
            a.get("id"), a.get("visit"), a.get("dos"), a.get("proccode"), a.get("fee") or a.get("amount"), a.get("insbalance"), a.get("patbalance"),
            a.get("carrier"), a.get("billdate"), a.get("profile") or a.get("provider"), [p for p in a["_pays"] if p[3] != "1"], [w for w in a["_wos"] if w[2] != "1"]))
    out[pid] = {"patient": pa, "plans": plans, "charges": chs}
json.dump(out, open("board_snapshot_1119.json", "w"))
