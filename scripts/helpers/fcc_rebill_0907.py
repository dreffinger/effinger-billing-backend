# PLAIN ENGLISH (Florida Community Care re-point + rebill, William 9/7/2026: "yes FCC is FLO99 - rebill them all there and anything else that is Florida Community Care going back a year")
# Decides: (1) Every open visit inside 12 months already on FLO99 (car42008, Florida Community Care) is re-sent as an original claim. (2) Every patient on the unpaid list with a Medicaid-side balance inside 12 months (MCAD, SUN01, SIM01, AMB03, WEL04 Medicaid, FLO99) gets AMD's free eligibility run on their Florida Medicaid plan; when Florida Medicaid says the SMMC MMA plan is FLORIDA COMMUNITY CARE, an FCC plan is added (Medicaid id, no group number) if missing and the open Medicaid-side visits are pointed at FCC and re-sent. Other MMA plans found (Humana, Sunshine, Simply, Molina) are reported, and Jessop Patient850 (chart 4147) is pointed at Humana Medicaid (car6285, the same carrier chart 45001 uses) per today's 271. (3) Visits over 12 months are left alone (written off tonight).
# Rules it uses: elig_amd.run_plan (cached per day), add_ins.add, move_to_ins.move + freq1_visit.run (frequency 1). Resumable via fcc_rebill_0907.log.
# Never touches: Medicare / commercial balances, paid visits, anything over 12 months.
# ---
"""Usage: python3 fcc_rebill_0907.py [--dry] [--max N]"""
import amd, elig_amd, add_ins, move_to_ins, freq1_visit, txh, json, sys, os, re, time, datetime, collections
amd.login_cached(); dry = "--dry" in sys.argv; mx = int(sys.argv[sys.argv.index("--max") + 1]) if "--max" in sys.argv else 10**9
today = datetime.date(2026, 9, 7); CUT = datetime.date(2025, 9, 8)
LOGF = "fcc_rebill_0907.log"; done = set(l.split()[1] for l in open(LOGF) if l.startswith("REBILL ")) if os.path.exists(LOGF) else set(); LOG = open(LOGF, "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
MCD_CARS = {"MCAD", "SUN01", "SIM01", "AMB03", "FLO99", "WEL04", "MOL01", "HUM01"}
FCC = "car42008"; MCAD = "car6113"
unp = json.load(open("unpaid_20260908.json"))
rows = [v for v in unp if datetime.datetime.fromisoformat(v["dateofservice"]).date() >= CUT and v["insbalance"] > 0 and v["carriercode"].strip() in MCD_CARS]
byp = collections.defaultdict(list)
for v in rows: byp[str(v["patientid"])].append(v)
# the five from tonight even if their visits are not on the unpaid snapshot yet
for pid in ("22858", "23161", "17477134", "25553", "17474689"): byp.setdefault(pid, [])
L("=== FCC pass %s: %d patients with Medicaid-side balances inside 12 months ===" % (time.ctime(), len(byp)))
found = collections.Counter(); n = 0; sent = 0; dollars = 0.0
def mma_of(pid, pl):
    """Run AMD eligibility on the Medicaid plan (or FCC plan) and return the SMMC MMA entity name."""
    cand = [p for p in pl if p["carrier"] == MCAD and not p.get("enddate")] or [p for p in pl if p["carrier"] == MCAD] or [p for p in pl if p["carrier"] == FCC]
    if not cand: return None, None
    s = elig_amd.run_plan(pid, cand[0]["id"].replace("ins", ""))
    for e in s.get("eb", []):
        if (e.get("plan") or "").startswith("SMMC MMA"):
            names = [x.get("name") for x in e.get("entities", []) if x.get("name")]; return (names[0] if names else "MMA (plan not named)"), cand[0]
    if any((e.get("plan") or "").startswith("SMMC Long-Term") for e in s.get("eb", [])): return "LTC only", cand[0]
    return s.get("status"), cand[0]
def open_visits(pid, carriers_ok):
    root = txh.fetch(pid); vis = collections.OrderedDict()
    for c in root.iter("charge"):
        if c.get("void") == "1" or float(c.get("insbal") or 0) <= 0: continue
        d = datetime.datetime.strptime(c.get("dos"), "%m/%d/%Y").date()
        if d < CUT or (c.get("carrier") or "") not in carriers_ok: continue
        vis.setdefault(c.get("visit"), (c.get("id"), c.get("dos"), 0.0)); cid, dos, bal = vis[c.get("visit")]; vis[c.get("visit")] = (cid, dos, bal + float(c.get("insbal") or 0))
    return vis
for pid, vs in byp.items():
    if n >= mx: break
    n += 1
    pa, pl = elig_amd.plans(pid); nm = pa.get("name")
    mma, plan = mma_of(pid, pl)
    if mma is None: L("SKIP %s: no Medicaid plan on chart" % nm); continue
    found[mma] += 1
    target = None; carrier_ok = None
    if mma and "FLORIDA COMMUNITY CARE" in mma.upper():
        fcc = [p for p in pl if p["carrier"] == FCC]; num = plan["subscribernum"]
        if not fcc:
            if dry: L("DRY ADD %s FCC %s" % (nm, num)); seq = "?"
            else: ins, seq = add_ins.add(pid, FCC, num, "01/01/2025", finclass="MD"); L("PLAN %s FCC %s added seq %s" % (nm, num, seq)); time.sleep(0.3)
        else: seq = fcc[0]["sequence"]
        target = str(seq); carrier_ok = {"MCAD", "SUN01", "SIM01", "AMB03", "FLO99", "WEL04"}
    elif pid == "17474689" and mma and "HUMANA" in mma.upper():
        hum = [p for p in pl if p["carrier"] == "car6285"]
        if not hum and not dry: ins, seq = add_ins.add(pid, "car6285", plan["subscribernum"], "01/01/2025", finclass="MD"); L("PLAN %s Humana Medicaid %s added seq %s" % (nm, plan["subscribernum"], seq))
        else: seq = hum[0]["sequence"] if hum else "?"
        target = str(seq); carrier_ok = {"MCAD", "SUN01", "FLO99"}
    else:
        L("INFO %-26s MMA = %s (no change)" % (nm, mma)); continue
    vis = open_visits(pid, carrier_ok)
    L("FCC  %-26s MMA = %s -> seq %s; %d open visits inside 12 months" % (nm, mma, target, len(vis)))
    for vid, (cid, dos, bal) in vis.items():
        if vid in done: continue
        if dry: L("DRY REBILL %s %s %s $%.2f -> seq %s" % (nm, vid, dos, bal, target)); continue
        try:
            mv = move_to_ins.move(cid, target); res = freq1_visit.run(vid, cid, target)
            L("REBILL %s %s %s $%.2f -> seq %s | %s | %s" % (vid, nm, dos, bal, target, str(mv)[:50], str(res)[:50])); sent += 1; dollars += bal
        except Exception as e: L("FAIL %s %s %s: %s" % (nm, vid, dos, str(e)[:80]))
        time.sleep(0.4)
L("=== done: MMA plans found %s; re-sent %d visits $%.2f ===" % (dict(found), sent, dollars))
