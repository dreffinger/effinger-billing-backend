# PLAIN ENGLISH (5pm ET 9/21/2026 run 2026-09-21T2110Z): act on the 44 $0 denial lines of Florida Medicaid ERA check 1051726
#   (073041757) by William's standing rules, after reading every visit live (era_denials_0921_2110.py) and AMD's own 271 on the charts.
# Decides, per line: (1) never-paid PRIMARY claims more than 12 months old (2024 DOS) -> WOLATE untimely (William 9/7 + 9/21 'past the
#   12 month rule ... write them off'); (2) a primary Medicaid claim on a chart whose 271 names another primary (Medicare active / UHC
#   Dual Complete D-SNP / SMMC MMA Florida Community Care) -> patient insurance order fixed, visit moved to that plan, freq-1 rebill
#   (Medicare first, MMA per the SMMC rule; never Medicaid FFS first); (3) Medicare-paid lines whose Medicaid crossover answered $0 ->
#   the contractual (CO45) share never adjusted = WOINS, the coinsurance on a QMB/full-Medicaid dual = WOCAID2ND (rule 9/11: dual
#   Medicaid-secondary after Medicare; 9/20: a paid line is never re-rendered); (4) coinsurance on an SLMB-only chart (Medicaid pays the
#   Part B premium only) = patient responsibility -> moved from the insurance to the patient balance (full-visit echo, the reverse of
#   move_to_ins) so the statement goes out; (5) HOLD (no write): FCC duals (the MMA that never pays - Medicaid FFS answered CO256 for the
#   FCC crossover), Sunshine-secondary residuals (Centene M56 payer-id question on William's turn), United American Medigap secondaries
#   in play, CO208/N286 referring-provider denials on re-created Effinger visits (board row), lines already at $0, visits with no live charge.
# Never touches: payments, charges outside this check, hospitalizationto, any plan add/end.
"""Usage: python3 era_1051726_act_2110.py [--dry]"""
import amd, manual_post, resave, move_to_ins, freq1_visit, ins_update, json, re, sys, time
amd.login_cached(); DRY = "--dry" in sys.argv
NOW = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); S = "2026-09-21T2110Z"; CK = "1051726"; CHK = "073041757"; DD = "09/21/2026"
reg = []
def live_bal(cid):
    x = resave.detail(cid); m = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x).group(0)
    return float(re.search(r'insbalance="([^"]*)"', m).group(1) or 0), float(re.search(r'patbalance="([^"]*)"', m).group(1) or 0)
def wo(pid, vid, cid, amt, carrier, code, why):
    ib, pb = live_bal(cid)
    if ib + 0.005 < amt: print("  SKIP pat%s c%s live insbalance %.2f < %.2f" % (pid, cid, ib, amt)); reg.append(dict(pid=pid, vid=vid, cid=cid, code=code, amount=amt, live=ib, outcome="skipped-balance-changed", when=NOW)); return
    ok, msg = manual_post.post(cid, carrier, 0.0, amt, code, checknumber=CHK, depositdate=DD, note="ERA %s FL Medicaid $0 denial - %s - run %s" % (CK, why, S), dry=DRY)
    time.sleep(0.6); after = None if DRY else live_bal(cid)[0]
    print("  WO pat%s v%s c%s %s %.2f (live %.2f) -> %s %s after=%s" % (pid, vid, cid, code, amt, ib, ok, msg[:80], after))
    reg.append(dict(pid=pid, vid=vid, cid=cid, carrier=carrier, code=code, amount=amt, live_before=ib, ok=ok, msg=msg[:160], insbalance_after=after, why=why, outcome="writeoff-" + code.lower() if ok else "post-failed", when=NOW))
def to_patient(pid, vid, cid, amt, why):
    """Reverse of move_to_ins: the charge's open insurance balance becomes patient balance (full-visit echo, updvisitwithcharges)."""
    vis, pat, allc = resave.visit_charges(cid); chg = ""; moved = 0.0
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        if c.get("id") == "charge" + cid and c.get("void") != "1":
            ib = float(c.get("insbalance") or 0)
            if abs(ib - amt) > 0.005: print("  SKIP pat%s c%s live insbalance %.2f != %.2f" % (pid, cid, ib, amt)); reg.append(dict(pid=pid, vid=vid, cid=cid, amount=amt, live=ib, outcome="skipped-balance-changed", when=NOW)); return
            a["patbalance"] = "%.2f" % (float(c.get("patbalance") or 0) + ib); a["insbalance"] = "0.00"
            a["patportion"] = "%.2f" % (float(c.get("patportion") or 0) + float(c.get("insportion") or 0)); a["insportion"] = "0.00"; moved = ib
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    if DRY: print("  DRY to-patient pat%s v%s c%s %.2f" % (pid, vid, cid, moved)); reg.append(dict(pid=pid, vid=vid, cid=cid, amount=moved, outcome="dry-to-patient", why=why, when=NOW)); return
    r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
    ok = "Fault" not in r; time.sleep(0.8); ib2, pb2 = live_bal(cid) if ok else (None, None)
    v2, p2, c2 = resave.visit_charges(cid)
    print("  TO-PATIENT pat%s v%s c%s %.2f -> %s ins=%s pat=%s live=%d/%d" % (pid, vid, cid, moved, ok, ib2, pb2, len(c2), len(allc)))
    reg.append(dict(pid=pid, vid=vid, cid=cid, amount=moved, ok=ok, msg=("" if ok else re.sub(r"\s+", " ", r[:160])), ins_after=ib2, pat_after=pb2, live_after="%d/%d" % (len(c2), len(allc)), why=why, outcome="to-patient" if ok else "post-failed", when=NOW))
def reroute(pid, vid, cid, insid, order, seq, why):
    if DRY: print("  DRY reroute pat%s v%s c%s -> patient insorder %s, visit seq %s, freq1 rebill (%s)" % (pid, vid, cid, order, seq, why)); reg.append(dict(pid=pid, vid=vid, cid=cid, outcome="dry-reroute", seq=seq, why=why, when=NOW)); return
    ok, msg = ins_update.update(pid, insid, sequence=order); print("  patient insorder pat%s -> %s: %s %s" % (pid, order, ok, msg[:80]))
    mv = move_to_ins.move(cid, seq); print("  move v%s c%s seq %s: %s" % (vid, cid, seq, str(mv)[:120])); time.sleep(0.6)
    rb = freq1_visit.run(vid, cid, seq); print("  rebill: %s" % rb)
    reg.append(dict(pid=pid, vid=vid, cid=cid, seq=seq, insorder=order, insorder_ok=ok, move=str(mv)[:120], rebill=rb, outcome="rerouted-rebilled" if "204" in rb else "post-failed", why=why, when=NOW))
def hold(pid, vid, cid, amt, why): print("  HOLD pat%s v%s c%s %.2f - %s" % (pid, vid, cid, amt, why)); reg.append(dict(pid=pid, vid=vid, cid=cid, amount=amt, outcome="held", why=why, when=NOW))

print("== (1) WOLATE - never-paid primaries over 12 months (2024 DOS)")
wo("24344", "19374817", "22442833", 61.57, "MCAD", "WOLATE", "COB7/N570; DOS 01/23/2024 never paid (Medicare $0, Humana MMA $0 x2), past the 12-month rule")
wo("24344", "19374817", "22442834", 62.58, "MCAD", "WOLATE", "COB7/N570; DOS 01/23/2024 never paid, past the 12-month rule")
wo("44976", "19454252", "23365306", 44.34, "MCAD", "WOLATE", "CO29 untimely + CO208; DOS 11/12/2024 never paid, past the 12-month rule (patient balance 62.66 left as is)")
wo("44976", "19454252", "23365307", 133.00, "MCAD", "WOLATE", "CO29 untimely + CO208; DOS 11/12/2024 never paid, past the 12-month rule")
wo("17469525", "19374948", "22443059", 61.57, "MCAD", "WOLATE", "COB7/N570; DOS 01/25/2024 never paid (Humana $0), past the 12-month rule")
print("== (2) re-route wrong-order primaries (271 names the real primary) + freq-1 rebill")
reroute("17477184", "19454398", "23365486", "9519145", "2,3", "2", "billed Medicaid FFS primary; 271: Medicare seq 2 ACTIVE (A 2005/B 2015), UNI20 ended 8/2/2026, Medicaid = SLMB only -> Medicare first")
reroute("17469645", "19454249", "23365299", "9519285", "3,1", "3", "billed Medicaid FFS primary, CO22/N598 other payer primary; 271: QMB dual on UHC Dual Complete D-SNP H2509 (UNI20 seq 3 ACTIVE) -> D-SNP first, Medicaid FFS second")
reroute("23161", "19454225", "23365251", "9515768", "2,3", "2", "billed Medicaid FFS primary, CO256/N130; 271: SMMC MMA Capitated FLORIDA COMMUNITY CARE -> FCC (seq 2) per the SMMC rule")
print("== (3) Medicare-paid lines, Medicaid crossover $0: contractual WOINS, dual coinsurance WOCAID2ND")
wo("17473346", "19453034", "23363449", 57.71, "FLO02", "WOINS", "Medicare CO45 contractual on the 8/26/2026 99309 never adjusted (Medicare paid 66.36); the 16.93 coinsurance stays for the Sunshine MMA crossover")
wo("17477607", "19453346", "23363891", 57.71, "FLO02", "WOINS", "Medicare CO45 contractual on the 8/20/2026 99309 never adjusted (paid 66.36); 16.93 stays for the United American Medigap secondary")
wo("17477023", "19452626", "23362974", 126.58, "FLO02", "WOINS", "Medicare CO45 contractual on the 8/23/2026 99487 never adjusted (paid 63.28); 16.14 stays for the United American Medigap secondary")
wo("17477417", "19451523", "23363471", 126.26, "FLO02", "WOINS", "Medicare paid 129.74 on the 5/21/2026 99306; Medicaid FFS crossover CO256 (managed care); patient deceased [DOB] per CMS, no MMA plan on the chart - contractual + coinsurance uncollectable")
wo("17477417", "19451523", "23363473", 80.67, "FLO02", "WOINS", "Medicare paid 52.33 on the 5/21/2026 99497; Medicaid FFS crossover CO170; patient deceased [DOB] per CMS - uncollectable")
wo("44955", "19432512", "23339074", 16.93, "MCAD", "WOCAID2ND", "Medicare coinsurance on a full-Medicaid dual (Humana MMA/LTC); Medicaid FFS $0 (CO16/N290) - crossover coinsurance write-off")
wo("45049", "19425626", "23331653", 17.65, "MCAD", "WOCAID2ND", "Medicare coinsurance on a Medicaid dual; Medicaid FFS $0 (CO16/N290) - crossover coinsurance write-off")
wo("12231996", "19417241", "23320903", 33.75, "MCAD", "WOCAID2ND", "WellCare D-SNP paid 132.31 on the 9/18/2025 99223; Medicaid FFS crossover CO22/N598; patient deceased [DOB] per CMS - dual cost-share write-off")
print("== (4) SLMB-only chart: Medicare coinsurance is patient responsibility -> moved to the patient balance")
for vid, cid in (("19451189", "23361189"), ("19453359", "23363903"), ("19452834", "23363209"), ("19452073", "23362189"), ("19451568", "23361620"), ("19451541", "23361590")):
    to_patient("17477184", vid, cid, 16.93, "Medicare paid, Medicaid = SLMB (Part B premium only) per AMD 271 - coinsurance is the patient's; Medicaid FFS CO16/N290 $0")
to_patient("17477184", "19452413", "23362661", 16.14, "99487 CCM: Medicare paid, Medicaid = SLMB per AMD 271 - coinsurance is the patient's")
print("== (5) HOLD")
hold("17473346", "19453034", "23363449", 16.93, "coinsurance -> Sunshine MMA seq 3 crossover; Centene answered CO16/M56 (board centene-m56-denials-0920, SUN01 payer id on William's turn)")
hold("17473346", "19452838", "23363213", 16.93, "coinsurance -> Sunshine MMA seq 3 crossover; same Centene M56 question")
hold("17477383", "19451168", "23361168", 74.64, "Sunshine MMA seq 2 secondary in play (Centene M56 on the board); Medicaid FFS also answered CO16/N290")
hold("17471131", "19453037", "23363452", 74.64, "CHP seq 1 secondary claim in play (visit carrier CAP07); Medicaid FFS answered the CMS crossover CO16/N290")
hold("17477607", "19453346", "23363891", 16.93, "United American Medigap (UNI01 car42005 seq 2) secondary in play after the WOINS")
hold("17477023", "19452626", "23362974", 16.14, "United American Medigap seq 2 secondary in play after the WOINS")
for vid, cid, amt in (("19453357", "23363901", 16.93), ("19453385", "23363932", 21.80), ("19453377", "23363924", 21.80), ("19453215", "23363779", 31.94), ("19452833", "23363208", 16.93), ("19452852", "23363226", 16.93)):
    hold("24039", vid, cid, amt, "Medicare coinsurance on an FCC dual (SMMC MMA Capitated Florida Community Care): Medicaid FFS answered the crossover CO256 'managed care contract' - FCC (car42008) is the payer and has never paid (AAA 41; FCC payer id / contracting open)")
for vid, cid, amt in (("19453374", "23363920", 31.94), ("19453379", "23363926", 21.80)):
    hold("20863", vid, cid, amt, "QMB dual on FCC: Medicaid FFS answered the crossover CO256 - FCC is the payer (never paid, AAA 41)")
for pid, vid, cid in (("17472419", "19454237", "23365275"), ("17472419", "19454238", "23365277"), ("17472518", "19454239", "23365279"), ("17472518", "19454240", "23365281"), ("17472518", "19454241", "23365283"), ("17472518", "19454242", "23365285"), ("17472518", "19454243", "23365287"), ("17472518", "19454244", "23365289"), ("17472518", "19454245", "23365291")):
    hold(pid, vid, cid, 141.00, "Medicaid-primary 99309 re-created under Effinger (prof13) 9/13: CO208/N286 NPI not matched / referring provider identifier - every prof13 Medicaid claim on this remit answers N286 while Garland-G-rendered ones answer N290; referring provider on the re-created visits needs William (board row)")
hold("47039", "19452849", "23363223", 0.0, "already settled (WOMCAD 16.93 posted earlier) - insurance balance 0")
hold("20379", "19453358", "23363902", 0.0, "already settled (WOINS 16.93 per the 9/20 Humana N767 rule) - balance 0")
hold("20379", "19452854", "23363228", 0.0, "already settled - balance 0")
hold("20709", "19374650", "", 33.91, "no live charge on the visit (all void) - nothing to post")
json.dump(reg, open("registers/era_1051726_act_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1)
tot = {}
for r in reg:
    if r.get("ok") and r.get("code"): tot[r["code"]] = round(tot.get(r["code"], 0) + r["amount"], 2)
print("TOTALS:", tot, "| outcomes:", {o: sum(1 for r in reg if r["outcome"] == o) for o in set(r["outcome"] for r in reg)})
