# PLAIN ENGLISH (payer re-route, 1 AM ET 10/2/2026 run 2026-10-02T0510Z - ehpa cloud)
# Decides: (1) pat17472396 - the chart's Medicare plan (seq 1) is end-dated 04/30/2026 and AMD's own 271 names HUMANA (seq 2,
#   HumanaChoice, ACTIVE) as the Medicare Advantage payer; five May-July 2026 visits (19441616, 19442523, 19444342, 19446223,
#   19447320 - 7 charges, $1,152.00, no live payment) sit in Unbilled 'Date of service is outside insurance coverage effective dates'
#   because their visit insurance order still points at the ended Medicare plan -> set the visit order to the Humana sequence
#   (full-visit echo via move_to_ins.move, every live charge preserved), reset frequency 1 and rebill on that sequence
#   (freq1_visit.run), then release the five rows (hideunbillablevisits hide=-1).
#   (2) pat17472849 - Medicare (seq 2) ACTIVE and Simply (seq 3) is a Medicaid LTSS dual plan; the chart's default order is '3'
#   (Simply alone) so the 9/20 CCM (v19455798) and the 9/24 99309 (v19456476) went to Simply as PRIMARY and Simply rejected the
#   9/24 claim on run 1700250 ('rendering provider NPI must be registered with the state'). William's standing rule: Medicare
#   first, Medicaid/LTC last -> patient default order 2,3 (ins_update.update sequence='2,3'), both visits set to order 2,3 and
#   frequency-1 rebilled on the Medicare sequence, then the 1700250 exclusion row completed (hideexclusions).
# Rules it uses: live re-read before every write (charge must be live, carry no non-void payment); full-visit echo (void trap);
#   every rebill goes out as frequency 1; never rebill a visit with a payment posted; release only after the data is fixed.
# Never touches: payments, write-offs, diagnosis lists, hospitalization dates, any visit not listed; the Thackeray (pat17472874)
#   rows stay held (inspector admission-date hold, William's turn).
#   python3 reroute_0510.py          # dry (default): re-read and print the plan, write nothing
#   python3 reroute_0510.py --live   # do it; register registers/reroute_2026-10-02T0510Z.json
import sys, json, os, re, time
import amd, resave, txh, move_to_ins, freq1_visit, ins_update

LIVE = "--live" in sys.argv
STAMP = "2026-10-02T0510Z"
REG = "registers/reroute_%s%s.json" % (STAMP, "" if LIVE else "_dry")
PLAN = [
    # pid, visit, lead charge id, target order, rebill seq, column, extra
    {"pid": "17472396", "vid": "19441616", "cid": "23349530", "order": "2", "seq": 2, "col": "unbilled"},
    {"pid": "17472396", "vid": "19442523", "cid": "23350697", "order": "2", "seq": 2, "col": "unbilled"},
    {"pid": "17472396", "vid": "19444342", "cid": "23353047", "order": "2", "seq": 2, "col": "unbilled"},
    {"pid": "17472396", "vid": "19446223", "cid": "23355217", "order": "2", "seq": 2, "col": "unbilled"},
    {"pid": "17472396", "vid": "19447320", "cid": "23356503", "order": "2", "seq": 2, "col": "unbilled"},
    {"pid": "17472849", "vid": "19455798", "cid": "23367250", "order": "2,3", "seq": 2, "col": "none"},
    {"pid": "17472849", "vid": "19456476", "cid": "23368122", "order": "2,3", "seq": 2, "col": "exclusion", "claimrun": "1700250", "claimid": "19456476A"},
]
PATIENT_ORDER = {"17472849": ("ins9519135", "2,3")}   # Medicare plan id, new default order

def live_state(pid, vid):
    root = txh.fetch_visit(pid, vid)
    out = []
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        pays = [p.attrib for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
        out.append({"cid": c.get("id"), "dos": c.get("dos"), "cpt": c.get("proccode"), "carrier": c.get("carrier"),
                    "billdate": c.get("billdate"), "insbal": c.get("insbal"), "patbal": c.get("patbal"), "paid": c.get("paid"),
                    "nonvoid_money_payments": len(pays)})
    return out

def release_unbilled(vids):
    r = amd.post(amd.msg("hideunbillablevisits", "claimsreports", {"nocookie": "1", "hide": "-1"},
                         "<visitlist>%s</visitlist>" % "".join('<visit id="%s"/>' % v for v in vids)))
    return "Fault" not in r, re.sub(r"\s+", " ", r[:200])

def complete_exclusion(run, vid, claimid):
    r = amd.post(amd.msg("hideexclusions", "claimsreports", {"nocookie": "1", "claimrunid": run, "hide": "-1"},
                         '<visitlist><visit id="%s" claimid="%s"/></visitlist>' % (vid, claimid)))
    return "Fault" not in r, re.sub(r"\s+", " ", r[:200])

amd.login_cached()
reg = {"stamp": STAMP, "live": LIVE, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "items": [], "patient_order": {}, "released": [], "exclusions": []}
# 1. patient default order
for pid, (insid, order) in PATIENT_ORDER.items():
    if LIVE:
        ok, msg = ins_update.update(pid, insid, sequence=order)
        reg["patient_order"][pid] = {"insid": insid, "order": order, "ok": ok, "msg": msg}
        print("patient order pat%s -> %s : %s %s" % (pid, order, ok, msg))
    else:
        reg["patient_order"][pid] = {"insid": insid, "order": order, "ok": None, "msg": "dry"}
        print("DRY patient order pat%s -> %s" % (pid, order))
# 2. per visit
to_release = []
for it in PLAN:
    st = live_state(it["pid"], it["vid"])
    row = dict(it); row["live"] = st
    money = sum(c["nonvoid_money_payments"] for c in st)
    if not st:
        row["outcome"] = "skip: no live charge on visit"; reg["items"].append(row); print(row["outcome"], it["vid"]); continue
    if money:
        row["outcome"] = "skip: a non-void payment is on the visit - never rebill a paid visit"; reg["items"].append(row); print(row["outcome"], it["vid"]); continue
    if not LIVE:
        row["outcome"] = "DRY would: move_to_ins.move(%s, '%s') + freq1_visit.run(%s, %s, %s)" % (it["cid"], it["order"], it["vid"], it["cid"], it["seq"])
        reg["items"].append(row); print(row["outcome"], "|", [(c["cpt"], c["dos"], c["carrier"], c["insbal"]) for c in st]); continue
    r1 = move_to_ins.move(it["cid"], it["order"], rebill_seq=it["seq"])
    time.sleep(0.8)
    r2 = freq1_visit.run(it["vid"], it["cid"], it["seq"])
    time.sleep(0.8)
    x = resave.detail(it["cid"]); v2 = re.search(r'<visit [^>]*>', x)
    row["readback_insorder"] = re.search(r'insorder="([^"]*)"', v2.group(0)).group(1) if v2 else None
    row["move"] = r1; row["freq1"] = r2
    sent = ("204" in str(r2)) or ("204" in str(r1))
    row["outcome"] = "rerouted + rebilled" if sent else "rebill did not answer 204 - row left on its column"
    print(it["vid"], r1, "|", r2, "| insorder", row["readback_insorder"])
    reg["items"].append(row)
    if sent and it["col"] == "unbilled": to_release.append(it["vid"])
    if sent and it["col"] == "exclusion":
        ok, msg = complete_exclusion(it["claimrun"], it["vid"], it["claimid"])
        reg["exclusions"].append({"run": it["claimrun"], "vid": it["vid"], "claimid": it["claimid"], "ok": ok, "msg": msg})
        print("hideexclusions", it["claimrun"], it["vid"], ok, msg)
if LIVE and to_release:
    ok, msg = release_unbilled(to_release)
    reg["released"] = {"vids": to_release, "ok": ok, "msg": msg}
    print("hideunbillablevisits", to_release, ok, msg)
os.makedirs("registers", exist_ok=True)
json.dump(reg, open(REG, "w"), indent=1)
print("register", REG)
