# PLAIN ENGLISH (Florida Blue ERA follow-up, 3pm ET 9/23/2026 run 2026-09-23T1910Z): five Florida Blue 835s (checks 1052814-1052818,
#   trace 423802576 / 2609231016 / 2609230762 / 2609230531 / 213436603) arrived this slot. AMD's Post button posted the 35 money lines
#   ($2,002.65) WITH the CO-45 reason code on each payment but WITHOUT the contractual write-off (the Florida Blue ERA setup carries
#   payreasonwoamount 0), so every posted charge shows patient balance = fee - paid. era_clear's Process-Accepted $0 pass then transferred
#   several $0 PR-22 'other payer primary' denials to the patient balance too. This script applies the standing corrections:
#   (A) posted money lines: move_to_ins.move(cid) (balance back to insurance, no rebill) then manual_post pay 0 + WOINS = the non-patient
#       part of the balance (patbal minus the line's PR amounts; = the remit CO-45 on a primary line) with the check number and deposit date -
#       AMD auto-transfers the PR remainder (deductible / coinsurance) back to the patient (captured 9/18, registry line 'Contractual correction').
#   (B) PR-22 / MA04 wrong-payer denials: balance back to insurance; a visit already at Medicare (last-billed FLO02) is left pending; a visit
#       still at BCBS with Medicare on the chart gets insorder Medicare-first + freq-1 rebill (the 9/16 Florida Blue PR-22 recipe).
#   (C) PR-177 pat17477059 (William 9/14: 'if these bcbs plans are inactive ... write that balance off as no pay bad patient debt'; Florida Blue
#       now answered PR-177 not eligible on all five July-2026 HCA claims): WOBAD write-off of the open insurance balance.
#   (D) pat17477777 v19454919 (Florida Blue primary, $0 paid, CO-45 + PR-1 deductible, not posted): WOINS the CO-45, PR-1 stays patient.
#   Everything else (PR-177 Medigap-inactive coinsurance, PR-50/PR-197, CO-252/MA04 secondaries, reversals, OA-18, PR-119, CO-29) is reported only.
# Never touches: visits with a $0 balance on both sides, insurance plans, hospitalization dates.
"""Usage: python3 era_fb_fix_1910.py [--dry] [--part A,B,C,D]"""
import amd, resave, txh, move_to_ins, manual_post, freq1_visit, re, json, time, sys, csv
DRY = "--dry" in sys.argv
PARTS = set(sys.argv[sys.argv.index("--part") + 1].split(",")) if "--part" in sys.argv else {"A", "B", "C", "D"}
S = "2026-09-23T1910Z"; NOTE = "ERA %s Florida Blue correction run " + S
amd.login_cached()
CHK = {c["id"]: c for c in json.load(open("era_checks_before_%s.json" % S))}
def chkno(cid): return CHK[int(cid)]["paymentnumber"]
def chkdate(cid): return CHK[int(cid)]["depositdate"][:10].split("-");
def dd(cid): y, m, d = chkdate(cid); return "%s/%s/%s" % (m, d, y)
lines = list(csv.DictReader(open("registers/era_lines_%s.csv" % S)))
zero = json.load(open("registers/era_zeroposted_%s.json" % S))
out = {"stamp": S, "dry": DRY, "A": [], "B": [], "C": [], "D": [], "faults": 0}
def L(m): print(m, flush=True)
def live(pid, vid):
    root = txh.fetch_visit(pid, vid); res = {}
    for c in root.iter("charge"):
        if c.get("void") == "1": continue
        res[c.get("id")] = {"fee": float(c.get("fee") or 0), "paid": float(c.get("paid") or 0), "patbal": float(c.get("patbal") or 0), "insbal": float(c.get("insbal") or 0), "carrier": c.get("carrier"), "billdate": c.get("billdate"), "cpt": c.get("proccode"),
                            "pays": [(p.get("id"), p.get("amount"), p.get("checknumber"), p.get("void")) for p in c.iter("payment")], "wos": [(w.get("id"), w.get("amount"), w.get("wocode"), w.get("void")) for w in c.iter("writeoff")]}
    return res
def pr_amount(check, vid, cpt):
    tot = 0.0
    for r in lines:
        if r["check"] == check and r["visit"] == vid and r["cpt"] == cpt and float(r["paid"]) > 0:
            for part in r["carcamts"].split(";"):
                if part.startswith("PR"): tot += float(part.split("=")[1])
    return round(tot, 2)
faults = 0
# ---------------- A: contractual correction on the 35 posted money lines ----------------
if "A" in PARTS:
    for r in zero:
        if float(r["payamt"]) == 0: continue
        pid, vid, cid, cpt, chk = r["pid"], r["vid"], r["cid"], r["cpt"], r["check"]
        st = live(pid, vid).get(cid)
        if not st: L("A pat%s v%s c%s: not live" % (pid, vid, cid)); continue
        if st["patbal"] <= 0.005: out["A"].append((pid, vid, cid, cpt, "patbal 0 - nothing")); L("A pat%s v%s c%s %s patbal 0 - nothing" % (pid, vid, cid, cpt)); continue
        if any(w[3] != "1" and w[2] and w[2].strip() == "WOINS" and float(w[1] or 0) < 0 and w[0] and int(w[0]) > 22470000 for w in st["wos"]) and st["insbal"] == 0 and False: pass
        pr = pr_amount(chk, vid, cpt); wo = round(st["patbal"] - pr, 2)
        if wo <= 0.005: out["A"].append((pid, vid, cid, cpt, "patbal %.2f = PR %.2f - patient responsibility, nothing" % (st["patbal"], pr))); L("A pat%s v%s c%s %s patbal %.2f = PR - nothing" % (pid, vid, cid, cpt, st["patbal"])); continue
        L("A pat%s v%s c%s %s fee %.2f paid %.2f patbal %.2f insbal %.2f PR %.2f -> move back + WOINS %.2f (check %s %s)" % (pid, vid, cid, cpt, st["fee"], st["paid"], st["patbal"], st["insbal"], pr, wo, chkno(chk), dd(chk)))
        rec = {"pid": pid, "vid": vid, "cid": cid, "cpt": cpt, "patbal_before": st["patbal"], "pr": pr, "wo": wo, "check": chkno(chk)}
        if DRY: rec["result"] = "DRY"; out["A"].append(rec); continue
        m = move_to_ins.move(cid); rec["move"] = str(m)[:120]; L("   move_to_ins -> %s" % str(m)[:120])
        time.sleep(0.6)
        ok, msg = manual_post.post(cid, "BCBS", 0.0, wo, "WOINS", checknumber=chkno(chk), depositdate=dd(chk), note=NOTE % chkno(chk)); rec["post"] = (ok, str(msg)[:160]); L("   manual_post WOINS %.2f -> %s %s" % (wo, ok, str(msg)[:120]))
        if not ok: faults += 1
        else: faults = 0
        time.sleep(0.8); after = live(pid, vid).get(cid, {}); rec["after"] = {k: after.get(k) for k in ("patbal", "insbal", "paid")}; L("   after patbal %.2f insbal %.2f" % (after.get("patbal", -1), after.get("insbal", -1)))
        out["A"].append(rec)
        if faults >= 3: L("3 consecutive addpayments faults - stopping part A"); break
# ---------------- B: PR-22 wrong-payer denials ----------------
B = [  # (pid, vid, cids, action)  action: 'move' (already at Medicare) | 'medfirst' (set Medicare first + freq-1 rebill)
    ("12180329", "19436591", ["23343643"], "move"),
    ("12180329", "19436536", ["23343591"], "medfirst"), ("12180329", "19436825", ["23343873"], "medfirst"), ("12180329", "19436828", ["23343876"], "medfirst"),
    ("12180329", "19436829", ["23343877"], "medfirst"), ("12180329", "19437116", ["23344191"], "medfirst"),
    ("17471968", "19431880", ["23338519", "23338520"], "medfirst"),
    ("17473245", "19449458", ["23359095"], "medfirst"),
]
def plans(pid):
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    ps = []
    for m in re.finditer(r'<insplan [^>]*>', r):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))); ps.append((a.get("id"), a.get("carrier"), a.get("sequence"), a.get("enddate") or "", a.get("begindate") or ""))
    io = re.search(r'<patient [^>]*insorder="([^"]*)"', r)
    return ps, (io.group(1) if io else "")
if "B" in PARTS:
    for pid, vid, cids, action in B:
        st = live(pid, vid); ps, porder = plans(pid)
        med = [p for p in ps if p[1] == "car6085" and not p[3]]
        bcbs = [p for p in ps if p[1] == "car6062"]
        L("B pat%s v%s %s plans %s patient insorder %s | live %s" % (pid, vid, action, ps, porder, [(c, s["cpt"], s["carrier"], s["billdate"], "pat", s["patbal"], "ins", s["insbal"]) for c, s in st.items()]))
        rec = {"pid": pid, "vid": vid, "action": action, "plans": ps, "porder": porder, "steps": []}
        if action == "medfirst" and not med: rec["steps"].append("no Medicare plan on the chart - HOLD (cascade)"); L("   no Medicare plan on the chart - HOLD"); out["B"].append(rec); continue
        if DRY: rec["steps"].append("DRY"); out["B"].append(rec); continue
        medseq = med[0][2] if med else None
        for i, cid in enumerate(cids):
            s = st.get(cid, {})
            if action == "move":
                if s.get("patbal", 0) > 0: m = move_to_ins.move(cid); rec["steps"].append(("move", cid, str(m)[:100])); L("   move_to_ins %s -> %s" % (cid, str(m)[:100]))
                else: rec["steps"].append(("move", cid, "patbal 0 - nothing"))
            else:
                if s.get("carrier") == "FLO02": rec["steps"].append(("skip", cid, "already at Medicare")); L("   %s already at Medicare (billdate %s) - move only" % (cid, s.get("billdate")))
                order = medseq + ("," + bcbs[0][2] if bcbs else "")
                if s.get("patbal", 0) > 0 or i == 0:
                    m = move_to_ins.move(cid, order, rebill_seq=(medseq if i == 0 and s.get("carrier") != "FLO02" else None)); rec["steps"].append(("move+order", cid, order, str(m)[:120])); L("   move_to_ins %s order %s rebill %s -> %s" % (cid, order, medseq if i == 0 else None, str(m)[:120]))
            time.sleep(0.6)
        if action == "medfirst" and porder and porder.split(",")[0] != medseq:
            import ins_update
            try: r = ins_update.update(pid, med[0][0], sequence=medseq + ("," + bcbs[0][2] if bcbs else "")); rec["steps"].append(("patient order", str(r)[:100])); L("   patient insorder -> %s" % str(r)[:100])
            except Exception as e: rec["steps"].append(("patient order FAILED", str(e)[:100]))
        time.sleep(0.6); rec["after"] = {c: (s["carrier"], s["billdate"], s["patbal"], s["insbal"]) for c, s in live(pid, vid).items()}; L("   after %s" % rec["after"])
        out["B"].append(rec)
# ---------------- C: pat17477059 PR-177 -> WOBAD (William 9/14) ----------------
if "C" in PARTS:
    for vid, cid in (("19447677", "23357"), ("19447678", ""), ("19447727", ""), ("19447879", ""), ("19448232", "")):
        st = live("17477059", vid)
        for c, s in st.items():
            L("C pat17477059 v%s c%s %s fee %.2f paid %.2f insbal %.2f patbal %.2f carrier %s" % (vid, c, s["cpt"], s["fee"], s["paid"], s["insbal"], s["patbal"], s["carrier"]))
            rec = {"vid": vid, "cid": c, "cpt": s["cpt"], "insbal": s["insbal"], "patbal": s["patbal"]}
            tot = round(s["insbal"] + s["patbal"], 2)
            if tot <= 0.005: rec["result"] = "no open balance - nothing"; out["C"].append(rec); continue
            if DRY: rec["result"] = "DRY would move back %.2f + WOBAD %.2f" % (s["patbal"], tot); out["C"].append(rec); continue
            if s["patbal"] > 0.005: m = move_to_ins.move(c); rec["move"] = str(m)[:100]; L("   move_to_ins -> %s" % str(m)[:100]); time.sleep(0.6)
            ok, msg = manual_post.post(c, "BCBS", 0.0, tot, "WOBAD", checknumber="ERA" + chkno("1052817"), depositdate=dd("1052817"), note="Self-pay no-pay bad debt - Florida Blue PR-177 not eligible on the 7/2026 HCA stay (William 9/14/2026 instruction) run " + S)
            rec["result"] = (ok, str(msg)[:160]); L("   WOBAD %.2f -> %s %s" % (s["insbal"], ok, str(msg)[:120])); out["C"].append(rec); time.sleep(0.8)
# ---------------- D: pat17477777 v19454919 CO-45 + PR-1 ----------------
if "D" in PARTS:
    st = live("17477777", "19454919")
    for c, s in st.items():
        co45 = pr1 = 0.0
        for r in lines:
            if r["check"] == "1052818" and r["visit"] == "19454919" and r["cpt"] == s["cpt"]:
                for part in r["carcamts"].split(";"):
                    k, v = part.split("="); co45 += float(v) if k == "CO45" else 0; pr1 += float(v) if k.startswith("PR") else 0
        L("D pat17477777 v19454919 c%s %s fee %.2f insbal %.2f patbal %.2f CO45 %.2f PR %.2f" % (c, s["cpt"], s["fee"], s["insbal"], s["patbal"], co45, pr1))
        rec = {"cid": c, "co45": co45, "pr": pr1, "insbal": s["insbal"], "patbal": s["patbal"]}
        if s["insbal"] < co45 - 0.005 or co45 <= 0: rec["result"] = "balance/CO45 mismatch - nothing"; out["D"].append(rec); continue
        if DRY: rec["result"] = "DRY would WOINS %.2f (PR %.2f stays)" % (co45, pr1); out["D"].append(rec); continue
        ok, msg = manual_post.post(c, "BCBS", 0.0, co45, "WOINS", checknumber=chkno("1052818"), depositdate=dd("1052818"), note=NOTE % chkno("1052818")); rec["result"] = (ok, str(msg)[:160]); L("   WOINS %.2f -> %s %s" % (co45, ok, str(msg)[:120]))
        time.sleep(0.8); rec["after"] = live("17477777", "19454919").get(c, {}); out["D"].append(rec)
json.dump(out, open("registers/era_fb_fix_%s%s.json" % (S, "_dry" if DRY else ""), "w"), indent=1, default=str)
L("DONE A %d B %d C %d D %d" % (len(out["A"]), len(out["B"]), len(out["C"]), len(out["D"])))
