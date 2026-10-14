# PLAIN ENGLISH (coverage-date Unbilled rows + the chart fixes behind them, 1 AM ET 10/14/2026 run 2026-10-14T0510Z)
# Decides per live chart read (work_reads2/3_0510.json), William's standing rules, in SECTIONS (--only <letter>, one approval card each):
#   A  WOINS = a primary payer's contractual (CO-45 + CO-253 on its own payment reasons) that the posting never wrote off, so the open
#      insurance balance is fee - paid instead of the coinsurance (the 9/23 'CO-45 on the balance' correction pass; the 10/5 lesson):
#      charts 12233534 (CHP), 17471793, 17472114 (UHC), 23671 (Medicare), 17474649 (Medicare 819814877), 22603 (Medicare 819814877; AET12 paid the coinsurance).
#   B  WOCLTREQ = Medicare / MA cost-sharing (PR-2 coinsurance, PR-3 copay) with NO supplement in force on the DOS - the chart's secondary plan
#      begins after the DOS or ended before it, so the 10/13 BILL-SECONDARY send went to a plan that was not in force (William 10/13/2026:
#      'Medicare cost-sharing with no supplement and MA/commercial cost-sharing: write off WOCLTREQ, nothing stays on the patient'):
#      charts 23671, 17474649, 20336, 23254, 20407, 17473032; chart 17473197 where UHC itself answered $0 PR26/PR27 (not covered on the DOS) 9/4/2026.
#   C  chart 48008: Medicare's 271 (Stedi) names CAPITAL HEALTH PLAN as the HMO Medicare Risk plan 10/1/2010-2/28/2026 (date of death 2/3/2026) while
#      the chart's CAP07 plan begins 2/23/2026 -> begin date 10/01/2010 so the 11/2025-1/2026 visits are inside coverage; the nine MV-class visits with
#      no insurance order get order 1 and ONE frequency-1 rebill (freq1_visit.reroute); the chart's 18 Unbilled rows are released.
#   D  chart 22603: AMD 271 says CON08 (car42021) is DEAD (AAA 75) and AET12 (Aetna Senior Supplemental) is the live Medigap -> CON08 end-dated 10/05/2025,
#      patient order 1,3; v19454390 set to order 1,3 with NO rebill (AET12 carrier-master hold); v19438330's $55.76 Part B deductible after AET12 is William's.
#   E  release (hideunbillablevisits) of the 23 'DOS outside coverage' Unbilled rows once A/B have brought their insurance balances to $0.
# Never touches: payments, diagnoses, any visit not listed; every write-off is a bare manual_post (pay 0) capped at the live balance.
#   python3 cov_1014_0510.py [--only A,B]            # dry
#   python3 cov_1014_0510.py --live --only A         # register registers/cov_1014_0510_<letters>.json
import amd, resave, manual_post, payreasons, ins_update, freq1_visit, txh, json, re, sys, time
LIVE = "--live" in sys.argv; S = "2026-10-14T0510Z"
ONLY = set(sys.argv[sys.argv.index("--only") + 1].upper().split(",")) if "--only" in sys.argv else set("ABCDE")
amd.login_cached()
WOINS = [  # (pid, vid, cpt, carrier code, amount, checkno, depositdate, why)
 ("12233534","14016482","99308","CAP07",44.52,"4003111","03/10/2024","CHP CO-45 never adjusted"),
 ("12233534","19362928","99316","CAP07",49.39,"4003111","03/10/2024","CHP CO-45 never adjusted"),
 ("12233534","19362932","99310","CAP07",78.35,"4003111","03/10/2024","CHP CO-45 never adjusted"),
 ("17471793","19386227","99309","FFVA",52.23,"24257B1000368388","09/06/2026","CO-45 never adjusted"),
 ("17471793","19386718","99309","FFVA",52.23,"24257B1000368388","09/06/2026","CO-45 never adjusted"),
 ("17471793","19387410","99309","FFVA",52.23,"24229B1000389434","09/06/2026","CO-45 never adjusted"),
 ("17472114","19404347","99232","UNI20",50.58,"C4984936","09/05/2026","UHC CO-45 never adjusted"),
 ("17472114","19404388","99232","UNI20",50.58,"C4984936","09/05/2026","UHC CO-45 never adjusted"),
 ("17472114","19404389","99232","UNI20",50.58,"C4984936","09/05/2026","UHC CO-45 never adjusted"),
 ("17472114","19404395","99232","UNI20",50.58,"C4984936","09/05/2026","UHC CO-45 never adjusted"),
 ("23671","14025638","99316","FLO02",28.21,"143989917","08/13/2023","Medicare CO-45 never adjusted"),
 ("17474649","19425170","99309","FLO02",54.14,"819814877","09/19/2026","Medicare CO-45 never adjusted"),
 ("17474649","19427052","99316","FLO02",54.73,"819814877","09/19/2026","Medicare CO-45 never adjusted"),
 ("22603","19442384","99487","FLO02",126.58,"819814877","09/19/2026","Medicare CO-45 never adjusted; AET12 paid the coinsurance"),
 ("22603","19442384","99489","FLO02",65.13,"819814877","09/19/2026","Medicare CO-45 never adjusted; AET12 paid the coinsurance"),
]
WOCLT = [
 ("23671","14025638","99316","FLO02",30.00,"143989917","08/13/2023","coinsurance, BCBS plan begins 6/27/2023 (DOS 5/25/2023)"),
 ("17474649","19425170","99309","FLO02",17.65,"819814877","09/19/2026","coinsurance, HUM01 ended 11/30/2025, UNI20 begins 6/1/2026"),
 ("17474649","19427052","99316","FLO02",21.40,"819814877","09/19/2026","coinsurance, HUM01 ended 11/30/2025, UNI20 begins 6/1/2026"),
 ("17474649","19423214","99306","HUM01",87.67,"173469309251201","05/28/2026","MA cost-sharing, no supplement in force"),
 ("17474649","19423214","99497","HUM01",36.36,"173469309251201","05/28/2026","MA cost-sharing, no supplement in force"),
 ("20336","26087","99307","FLO02",7.38,"811473793","10/24/2022","coinsurance, UNI20 begins 9/1/2022 (DOS 8/2022)"),
 ("20336","26191","99307","FLO02",7.38,"811473793","10/24/2022","coinsurance, UNI20 begins 9/1/2022 (DOS 8/2022)"),
 ("20336","27422","99308","FLO02",11.67,"811473793","10/24/2022","coinsurance, UNI20 begins 9/1/2022 (DOS 8/2022)"),
 ("23254","44745","99336","FLO02",22.78,"812109583","02/13/2023","coinsurance, UNI20 begins 4/28/2023 (DOS 12/28/2022)"),
 ("20407","19374762","99306","FLO02",35.53,"814383818","03/08/2024","coinsurance, CAP07 ended 1/11/2024, HUM01 begins 9/4/2024"),
 ("20407","19374762","99497","FLO02",14.72,"814383818","03/08/2024","coinsurance, CAP07 ended 1/11/2024, HUM01 begins 9/4/2024"),
 ("17473032","19402284","99344","HUM01",65.00,"155693767250330","09/09/2026","MA copay, UNI20 begins 7/1/2025 (DOS 3/13/2025)"),
 ("17473032","19402284","99497","HUM01",33.75,"155693767250330","09/09/2026","MA coinsurance, UNI20 begins 7/1/2025 (DOS 3/13/2025)"),
]
UHC_VIDS = ["19427174","19430635","19434034","19434249","19436818","19436968"]   # chart 17473197
COV_ROWS = ["14016482","19362928","19362932","19386227","19386718","19387410","19404347","19404388","19404389","19404395","14025638",
            "19425170","19427052","19423214","26087","26191","27422","44745","19374762","19402284"]
reg = {"stamp": S, "live": LIVE, "only": sorted(ONLY), "writeoffs": [], "charts": [], "released": [], "left": []}
_roots = {}
def root(pid):
    if pid not in _roots: _roots[pid] = txh.fetch(pid)
    return _roots[pid]
def charge(pid, vid, cpt):
    st = payreasons.visit_state(pid, vid, root=root(pid))
    if not st: st = payreasons.visit_state(pid, vid, root=txh.fetch_visit(pid, str(vid)))
    for c in st:
        if c["cpt"] == cpt: return c
    return None
def wo_line(pid, vid, cpt, carrier, amt, code, chk, dep, why):
    c = charge(pid, vid, cpt)
    if c is None: print("  NO CHARGE", vid, cpt); reg["left"].append((pid, vid, cpt, "charge not found")); return
    amt = round(min(amt, c["insbalance"]), 2)
    if amt <= 0: print("  skip", vid, c["cid"], code, "balance", c["insbalance"]); reg["writeoffs"].append((pid, vid, c["cid"], code, 0, "skip balance %.2f" % c["insbalance"])); return
    if not LIVE: print("  DRY", vid, c["cid"], carrier, code, amt, "bal", c["insbalance"], why); reg["writeoffs"].append((pid, vid, c["cid"], code, amt, "dry")); return
    ok, msg = manual_post.post(c["cid"], carrier, 0.0, amt, code, checknumber=chk, depositdate=dep, note="cov pass %s: %s" % (S, why))
    print("  WO", vid, c["cid"], carrier, code, amt, ok, str(msg)[:80]); reg["writeoffs"].append((pid, vid, c["cid"], code, amt, ok, str(msg)[:120]))
    time.sleep(0.4)
def release(vids):
    for v in sorted(set(vids)):
        if LIVE:
            ok, msg = payreasons.release_visit(v); reg["released"].append((v, ok))
            if not ok: print("  release FAIL", v, msg[:100])
        else: print("  DRY release", v)
if "A" in ONLY:
    print("== A WOINS contractual")
    for x in WOINS: wo_line(*x[:4], x[4], "WOINS", *x[5:])
if "B" in ONLY:
    print("== B WOCLTREQ cost-sharing with no supplement in force")
    for x in WOCLT: wo_line(*x[:4], x[4], "WOCLTREQ", *x[5:])
    for v in UHC_VIDS:
        for c in payreasons.visit_state("17473197", v, root=root("17473197")):
            mpay = [p for p in c["pays"] if p["void"] != "1" and p["carrier"] == "FLO02" and p["amount"] > 0]
            pr = sum(a for p in mpay for code, a in p["reasons"] if code.startswith("PR"))
            if c["insbalance"] > 0 and mpay and abs(c["insbalance"] - pr) < 0.011:
                wo_line("17473197", v, c["cpt"], "FLO02", c["insbalance"], "WOCLTREQ", mpay[0]["checkno"], mpay[0]["date"], "coinsurance, UHC answered $0 PR26/PR27 9/4/2026 (no supplement on DOS)")
            else: print("  LEFT", v, c["cid"], c["cpt"], "ins", c["insbalance"], "PR", pr); reg["left"].append(("17473197", v, c["cid"], c["insbalance"], pr))
if "C" in ONLY:
    print("== C chart 48008 CAP07 begin date 10/01/2010, order 1, nine MV visits re-routed, rows released")
    if LIVE:
        ok, msg = ins_update.update("48008", "9518597", begindate="10/01/2010"); print("  CAP07 begindate ->", ok, msg[:160]); reg["charts"].append(("48008", "begindate", ok, msg[:160]))
        ok, msg = ins_update.update("48008", "9518597", sequence="1"); print("  48008 order 1 ->", ok, msg[:160]); reg["charts"].append(("48008", "order", ok, msg[:160]))
    else: print("  DRY ins_update 48008 ins9518597 begindate 10/01/2010; order 1")
    s = json.load(open("scan_2026-10-14T0510Z/summary_before.json"))
    rows48 = [r for r in s["unbilled"] if r["patientid"] == "48008"]
    mv = [r for r in rows48 if any("Insurance order" in e for e in r["_errs"])]
    for r in mv:
        res = freq1_visit.reroute(r["id"], r["_chgs"][0]["id"], "1", 1, dry=not LIVE); print("  reroute", r["id"], "->", res[:140]); reg["charts"].append(("48008", r["id"], res[:160]))
        if LIVE: time.sleep(0.4)
    release([r["id"] for r in rows48])
if "D" in ONLY:
    print("== D chart 22603 CON08 end-date 10/05/2025 + order 1,3; v19454390 order 1,3 (no rebill, AET12 hold)")
    if LIVE:
        ok, msg = ins_update.update("22603", "1855", enddate="10/05/2025"); print("  CON08 enddate ->", ok, msg[:160]); reg["charts"].append(("22603", "enddate", ok, msg[:160]))
        ok, msg = ins_update.update("22603", "5598", sequence="1,3"); print("  22603 order 1,3 ->", ok, msg[:160]); reg["charts"].append(("22603", "order", ok, msg[:160]))
        c = charge("22603", "19454390", "99308")
        ok, msg = resave.set_insorder(c["cid"], "1,3"); print("  v19454390 insorder 1,3 ->", ok, msg[:120]); reg["charts"].append(("22603", "19454390", ok, msg[:120]))
    else: print("  DRY ins_update 22603 ins1855 enddate 10/05/2025; order 1,3; set_insorder v19454390 1,3")
if "E" in ONLY:
    print("== E release the coverage-date Unbilled rows (balances now $0 after A/B)")
    left = []
    for v in COV_ROWS + UHC_VIDS:
        pid = {"14016482":"12233534","19362928":"12233534","19362932":"12233534","19386227":"17471793","19386718":"17471793","19387410":"17471793",
               "19404347":"17472114","19404388":"17472114","19404389":"17472114","19404395":"17472114","14025638":"23671","19425170":"17474649",
               "19427052":"17474649","19423214":"17474649","26087":"20336","26191":"20336","27422":"20336","44745":"23254","19374762":"20407","19402284":"17473032"}.get(v, "17473197")
        st = payreasons.visit_state(pid, v, root=root(pid)) or payreasons.visit_state(pid, v, root=txh.fetch_visit(pid, str(v)))
        bal = sum(c["insbalance"] for c in st)
        if bal > 0.005: left.append((v, bal)); print("  LEFT (balance %.2f)" % bal, v); continue
        release([v])
    reg["left"] += left
json.dump(reg, open("registers/cov_1014_0510_%s%s.json" % ("".join(sorted(ONLY)), "" if LIVE else "_dry"), "w"), indent=1)
print("done; writeoffs", len(reg["writeoffs"]), "charts", len(reg["charts"]), "released", len(reg["released"]), "left", len(reg["left"]))
