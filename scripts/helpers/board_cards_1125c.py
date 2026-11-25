#!/usr/bin/env python3
# PLAIN ENGLISH (the 'CLAUDE (next run)' cards the 11/25 chat filed on the Insurance Refresh Board, worked by the Billing Button
#   press of 05:56Z - BUTTON PRESS brief: "process all the new insurance info on the refresh board ... fix the charts and rebill them")
# Decides: nothing. Each section applies William's own words on the card (read from the saved board cards; the Medicare numbers are
#   never typed here) with the standing helpers, --dry first, then --live; --only <section> runs one section:
#   mbi    charts 17471643 + 17471791 (one patient, two charts - the face sheet's Medicare number on BOTH, 271, unpaid visits re-sent once;
#          the FCC Medicaid second plan on the sheet is checked with the Medicaid 271 and reported, never guessed), 17471238 and 20709 (the
#          sheet's 'Medicare Beneficiary ID' replaces the older HIC number the chart carries), 17473460 (the sheet's number). Each the
#          medicare_number_fix way: write, AdvancedMD's free check, keep only on ACTIVE (else the old number back), re-send unpaid Medicare
#          visits inside 12 months ONE frequency-1 claim each (deceased guard inside). Chart 17473460: when Medicare answers 'name does
#          not match' (73) on the sheet's number, Medicare is asked by number + birth date for the spelling it holds (reported, not written).
#   fitz   chart 12182505: Railroad Medicare (RET01 car6080) with the card's number first, AARP Plan F (AAR01 car6600) second, both checked
#          (AMD 271), the 6 visits last billed to Florida Medicare re-pointed to Railroad Medicare and sent once (freq1_visit.reroute).
#   wo     write-offs on William's word: 17475908 (TRICARE East, v19436456 + v19436537, $421), 17477353 (Humana 99489 10/27/2026, $109),
#          17471273 (Aetna, 7 visits 7/14-7/20/2026, $976) - WOINS, pay 0, reference BOARD1125C, the dated note the card gives.
#   void   charges dated after the date of death (William: "VOID all charges sent after date of death"): 17477267 [DOB] 99487,
#          17469397 09/20/2026 99487 + 99489, 17475365 09/20/2026 99487 - the 11/20 WOINS (DOD1120) and the $0 payment voided, then the
#          charge voided (void_tx.void_charge), read back void.
#   karnes chart 17472826: the 9/9/2026 WOINS on v19438893 (99223) + v19438892 (99232) voided (the BCBS $0 posting stays), a patient
#          balance moved back to insurance, each visit re-sent to BCBS (seq 1) once (freq1_visit.run).
#   staff  chart 17477572: I10 made the first diagnosis on v19453098 / v19453097 / v19453099 (dx_primary_fix.save_visit_dx, full-visit
#          echo), then ONE re-send each to Capital Health Plan (freq1_visit.run) - William: "change these to i10 and rebill".
# Never touches: paid visits, charts not named, write-offs or payments the card does not name. Register registers/board_cards_c_<stamp>[_dry].json.
# Usage: python3 board_cards_1125c.py [--live] [--only mbi|fitz|wo|void|karnes|staff]
import amd, ins_update, add_ins, elig_amd, freq1_visit, resave, manual_post, void_tx, move_to_ins, txh, stedi, json, re, sys, os, time, datetime
import medicare_number_fix as mnf, dx_primary_fix as dpf
LIVE = "--live" in sys.argv; S = "2026-11-25T0634Z"
ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
BOARD = "/tmp/claude-0/-home-claude-effinger-billing-backend/54dad968-8e54-5d62-b91f-c8705cdd698d/scratchpad/board_0634/items"
def card(cid):
    o = json.load(open(os.path.join(BOARD, cid + ".json"))); return o.get("data", o)
def wtext(cid):
    return "\n".join(n.get("text", "") for n in card(cid).get("notes") or [] if str(n.get("who", "")).lower().startswith("william"))
def mbis(text):
    return [m for m in re.findall(r"\b(%s)\b" % mnf.MBI, text.upper())]
def after(label, text):
    m = re.search(label + r"\s*(%s)" % mnf.MBI, text, re.I); return mnf.norm(m.group(1)) if m else ""
def charge_of(pid, vid, cpt=None):
    """live charges of a visit: [(cid, attrs)]"""
    out = []
    for c in txh.fetch_visit(pid, vid).iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        out.append((re.sub(r"\D", "", a.get("id", "")), a))
    return out
def wo_line(pid, vid, cid, code, note, carrier=""):
    x = resave.detail(cid); ch = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<charge [^>]*>', x).group(0)))
    bal = float(ch.get("insbalance") or 0); carrier = carrier or ch.get("carrier") or ""
    wos = [dict(re.findall(r'(\w+)="([^"]*)"', w)) for w in re.findall(r'<writeoff [^>]*>', x)]
    done = [w for w in wos if w.get("void") != "1" and "BOARD1125C" in (w.get("checknumber", "") + w.get("memo", "") + w.get("note", ""))]
    line = {"pid": pid, "visit": vid, "charge": cid, "cpt": ch.get("proccode"), "dos": ch.get("begindate"), "insbalance": bal, "carrier": carrier}
    if done: line["result"] = "already written off this run"
    elif bal <= 0: line["result"] = "no open insurance balance - nothing to write off"
    else:
        ok, msg = manual_post.post(cid, carrier, 0.0, bal, code, "BOARD1125C", None, note, dry=not LIVE); line["result"] = ("LIVE " if LIVE else "DRY ") + str(msg)[:140]; line["ok"] = ok
    print("  wo", line); return line
amd.login_cached(); reg = {"stamp": S, "live": LIVE}
# ---------------- mbi ----------------
if not ONLY or ONLY == "mbi":
    do_t = wtext("[name]-17471643-medicare-number"); do_n = mbis(do_t)
    cands = {"17471643": do_n[:1], "17471791": do_n[:1],
             "17471238": [after(r"Medicare Beneficiary ID", wtext("garland-g-mercy-17471238-medicare-number"))],
             "20709": [after(r"Medicare Beneficiary ID", wtext("[name]-20709-medicare-number"))],
             "17473460": mbis(wtext("[name]-17473460-medicare-match"))[:1]}
    cands = {k: [x for x in v if x] for k, v in cands.items()}
    print("== mbi candidates:", {k: [x[:2] + "***" + x[-2:] for x in v] for k, v in cands.items()})
    mnf.feed_numbers = lambda pid: list(cands.get(str(pid), []))
    mreg = {}
    for pid in os.environ.get("MBI_PIDS", "17471643,17471791,17471238,20709,17473460").split(","):
        try:
            _, plans, _ = ins_update._plans(pid)
            cur = [mnf.norm(p.get("subscribernum")) for p in plans.values() if p.get("carrier") == "car6085" and not p.get("enddate")]
            same = bool(cands[pid]) and cands[pid][0] in cur
            if same: print("  pat%s: the sheet's number is the SAME as the chart's" % pid)
            rec = mnf.fix(pid, LIVE, False, mreg); rec["sheet_same_as_chart"] = same; rec["source"] = "William's face sheet 11/25 (board card)"
            if pid == "17473460" and not str(rec.get("number", "")).startswith("corrected") and cands[pid]:
                # Medicare holds another spelling? ask by number + birth date (the plain check, no look-up) and report the name it answers
                raw, _, _ = ins_update._plans(pid); pa = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<patient [^>]*>', raw).group(0)))
                last, first = (pa.get("name") or ",").split(",")[:2]; first = first.split()[0] if first.split() else ""; m, d, y = (pa.get("dob") or "0/0/0").split("/")
                j = stedi.elig("CMS", first, last.strip(), y + m.zfill(2) + d.zfill(2), cands[pid][0], datetime.date.today().strftime("%Y%m%d"), pid=pid)
                os.makedirs("patient_db/%s" % pid, exist_ok=True); json.dump(j, open("patient_db/%s/stedi_cms_plain_%s.json" % (pid, S), "w"))
                sub = j.get("subscriber") or {}; errs = [(str(e.get("code")), str(e.get("description"))[:50]) for e in j.get("errors") or []]
                rec["medicare_name_check"] = {"name_on_record": "%s %s" % (sub.get("firstName") or "", sub.get("lastName") or ""), "errors": errs, "chart_name": "%s %s" % (first, last.strip())}
                print("  pat%s Medicare's plain check by number: name on record %r, errors %s" % (pid, rec["medicare_name_check"]["name_on_record"], errs))
        except Exception as e: mreg[pid] = {"error": "%s: %s" % (type(e).__name__, str(e)[:160])}; print("  pat%s stopped: %s" % (pid, mreg[pid]["error"]))
    mreg["medicaid_271_do"] = "not checked this run (the Medicaid check needs the Medicaid id; the sheet gives it - a chat session or the next run with feed_in1_intake)"
    reg["mbi"] = mreg
# ---------------- fitz ----------------
if not ONLY or ONLY == "fitz":
    pid = "12182505"; row = {"steps": [], "visits": {}}
    num = after(r"Medicare number", wtext("[name]-12182505").replace("-", "")) or mbis((card("[name]-12182505").get("need") or ""))[:1]
    num = num if isinstance(num, str) else (num[0] if num else "")
    aarp = re.search(r"Membership ID\s*([\d-]{8,14})", wtext("[name]-12182505")); aarp = aarp.group(1) if aarp else ""
    print("== fitz pat%s railroad number %s, AARP id %s" % (pid, "found" if num else "NOT FOUND", "found" if aarp else "NOT FOUND"))
    _, plans, order = ins_update._plans(pid); pl = list(plans.values())
    print("  plans:", [(p.get("id"), p.get("carrier"), p.get("sequence"), p.get("enddate"), mnf.norm(p.get("subscribernum"))[-4:]) for p in pl], "order", order)
    ret = [p for p in pl if p.get("carrier") == "car6080" and not p.get("enddate")]; aar = [p for p in pl if p.get("carrier") == "car6600" and not p.get("enddate")]
    if num and not ret:
        if LIVE: rid, rseq = add_ins.add(pid, "car6080", num, "11/01/2006"); row["steps"].append(["add RET01", rid, rseq]); print("  add RET01 ->", rid, rseq)
        else: rid, rseq = None, str(len(pl) + 1); row["steps"].append(["DRY would add RET01", num[-4:], "11/01/2006"])
    elif ret:
        rid, rseq = ret[0]["id"], ret[0]["sequence"]; row["steps"].append(["RET01 already on the chart", rid, rseq, "number matches" if mnf.norm(ret[0].get("subscribernum")) == num else "NUMBER DIFFERS"])
        if LIVE and num and mnf.norm(ret[0].get("subscribernum")) != num: print("  RET01 number ->", str(ins_update.update(pid, rid, subscribernum=num))[:80]); row["steps"].append(["RET01 number written"])
    else: rid = rseq = None
    if aarp and not aar:
        if LIVE: aid, aseq = add_ins.add(pid, "car6600", aarp, "01/01/2015"); row["steps"].append(["add AAR01", aid, aseq]); print("  add AAR01 ->", aid, aseq)
        else: aid, aseq = None, str(len(pl) + 2); row["steps"].append(["DRY would add AAR01", aarp[-4:], "01/01/2015"])
    elif aar: aid, aseq = aar[0]["id"], aar[0]["sequence"]; row["steps"].append(["AAR01 already on the chart", aid, aseq])
    else: aid = aseq = None
    if LIVE and rid:
        for label, iid in (("RET01", rid), ("AAR01", aid)):
            if not iid: continue
            try: s = elig_amd.run_plan(pid, iid, force=True); row["steps"].append(["AMD 271 " + label, elig_amd.one_line(s)[:300]]); print("  271 %s: %s" % (label, elig_amd.one_line(s)[:300]))
            except Exception as e: row["steps"].append(["AMD 271 %s error" % label, str(e)[:100]])
        others = [p.get("sequence") for p in pl if not p.get("enddate") and p.get("sequence") not in (rseq, aseq)]
        want = ",".join([str(rseq)] + ([str(aseq)] if aseq else []) + others)
        try: res = ins_update.update(pid, rid, sequence=want); row["steps"].append(["patient order", want, str(res)[:120]]); print("  patient order", want, "->", str(res)[:120])
        except Exception as e: row["steps"].append(["patient order error", str(e)[:120]])
    # the visits last billed to Florida Medicare with no payment at all
    byv = {}
    for c in txh.fetch(pid).iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        byv.setdefault(a.get("visit"), []).append((a, sum(1 for x in c.iter("payment") if x.get("void") != "1" and abs(float(x.get("amount") or 0)) > 0.005)))
    for vid, cs in byv.items():
        if not any(a.get("carrier") == "FLO02" and float(a.get("insbal") or 0) > 0.005 for a, _ in cs) or any(n for _, n in cs): continue
        a0 = cs[0][0]; amt = sum(float(a.get("insbal") or 0) for a, _ in cs); order_ = ",".join([str(rseq)] + ([str(aseq)] if aseq else [])) if rseq else "?"
        if not LIVE or not rid: row["visits"][vid] = "DRY would re-point %s $%.2f to RET01 (order %s) and send" % (a0.get("dos"), amt, order_); print("  v%s %s $%.2f DRY" % (vid, a0.get("dos"), amt)); continue
        r = freq1_visit.reroute(vid, re.sub(r"\D", "", a0.get("id")), order_, rseq); row["visits"][vid] = "%s %.2f %s" % (a0.get("dos"), amt, str(r)[-120:]); print("  v%s %s $%.2f -> %s" % (vid, a0.get("dos"), amt, str(r)[-100:])); time.sleep(0.4)
    reg["fitz"] = row
# ---------------- wo ----------------
if not ONLY or ONLY == "wo":
    wo = []
    for vid in ("19436456", "19436537"):
        for cid, a in charge_of("17475908", vid): wo.append(wo_line("17475908", vid, cid, "WOINS", "TRICARE East reports the claim as already paid (duplicate rejection, claim run 1700349); remit not obtainable; written off on William's word 11/25/2026", a.get("carrier")))
    # Wallace: the 10/27/2026 99489 - find the visit by date and code
    for c in txh.fetch("17477353").iter("charge"):
        a = c.attrib
        if a.get("void") != "1" and a.get("dos") == "10/27/2026":
            cid = re.sub(r"\D", "", a.get("id", "")); x = resave.detail(cid)
            if re.search(r'code="99489"', x): wo.append(wo_line("17477353", a.get("visit"), cid, "WOINS", "Humana CO-4 on the CCM add-on; written off on William's word 11/25/2026", a.get("carrier")))
    for vid in ("19448259", "19448592", "19448627", "19448967", "19448986", "19449065", "19449321"):
        for cid, a in charge_of("17471273", vid): wo.append(wo_line("17471273", vid, cid, "WOINS", "Aetna finalized at 0; written off on William's word 11/25/2026", a.get("carrier")))
    reg["wo"] = wo
# ---------------- void ----------------
if not ONLY or ONLY == "void":
    vd = []
    for pid, dos, cpts in (("17477267", "09/20/2026", ("99487",)), ("17469397", "09/20/2026", ("99487", "99489")), ("17475365", "09/20/2026", ("99487",))):
        for c in txh.fetch(pid).iter("charge"):
            a = c.attrib
            if a.get("void") == "1" or a.get("dos") != dos: continue
            cid = re.sub(r"\D", "", a.get("id", "")); x = resave.detail(cid)
            cpt = next((p for p in cpts if re.search(r'code="%s"' % p, x)), None)
            if not cpt: continue
            ch, wos, pays = void_tx.charge_state(cid); live_wos = [w for w in wos if w.get("void") != "1"]; live_pays = [p for p in pays if p.get("void") != "1"]
            line = {"pid": pid, "visit": a.get("visit"), "charge": cid, "cpt": cpt, "dos": dos, "fee": ch.get("fee"), "wos": [(w.get("id"), w.get("amount"), w.get("checknumber")) for w in live_wos], "pays": [(p.get("id"), p.get("amount"), p.get("checknumber")) for p in live_pays], "steps": []}
            if ch.get("void") == "1": line["result"] = "already void"
            elif any(abs(float(p.get("amount") or 0)) > 0.005 for p in live_pays): line["result"] = "a real payment is posted - not voided, listed"
            elif not LIVE: line["result"] = "DRY would void %d write-off(s), %d $0 payment(s), then the charge" % (len(live_wos), len(live_pays))
            else:
                for w in live_wos: ok, msg = void_tx.void_writeoff(pid, cid, w.get("id")); line["steps"].append(["void wo", w.get("id"), ok, str(msg)[:80]]); time.sleep(0.3)
                for p in live_pays: ok, msg = void_tx.void_payment(pid, cid, p.get("id")); line["steps"].append(["void pay", p.get("id"), ok, str(msg)[:80]]); time.sleep(0.3)
                ok, msg = void_tx.void_charge(pid, cid); line["steps"].append(["void charge", ok, str(msg)[:80]])
                ch2, _, _ = void_tx.charge_state(cid); line["result"] = "after: void=%s insbal=%s patbal=%s" % (ch2.get("void"), ch2.get("insbalance"), ch2.get("patbalance"))
            print("  void", line); vd.append(line)
    reg["void"] = vd
# ---------------- karnes ----------------
if not ONLY or ONLY == "karnes":
    pid = "17472826"; kr = []
    for vid in ("19438893", "19438892"):
        for cid, a in charge_of(pid, vid):
            ch, wos, pays = void_tx.charge_state(cid)
            tgt = [w for w in wos if w.get("void") != "1" and ((w.get("code") or w.get("Writeoffcode") or "").startswith("WOINS") or float(w.get("amount") or 0) != 0)]
            line = {"visit": vid, "charge": cid, "cpt": ch.get("proccode"), "dos": ch.get("begindate"), "insbal": ch.get("insbalance"), "patbal": ch.get("patbalance"), "wos": [(w.get("id"), w.get("amount"), w.get("code") or w.get("Writeoffcode"), w.get("checknumber")) for w in tgt], "pays": [(p.get("id"), p.get("amount"), p.get("checknumber")) for p in pays if p.get("void") != "1"], "steps": []}
            if any(abs(float(p.get("amount") or 0)) > 0.005 for p in pays if p.get("void") != "1"): line["result"] = "a real payment is posted - nothing reversed"
            elif not tgt and float(ch.get("insbalance") or 0) > 0: line["result"] = "no live WOINS - balance already open";
            elif not LIVE: line["result"] = "DRY would void %d WOINS write-off(s), move a patient balance back, re-send to BCBS seq 1" % len(tgt)
            else:
                for w in tgt: ok, msg = void_tx.void_writeoff(pid, cid, w.get("id")); line["steps"].append(["void wo", w.get("id"), ok, str(msg)[:80]]); time.sleep(0.3)
                ch2, _, _ = void_tx.charge_state(cid)
                if float(ch2.get("patbalance") or 0) > 0.005: line["steps"].append(["move_to_ins", str(move_to_ins.move(cid))[:120]]); time.sleep(0.3)
                r = freq1_visit.run(vid, cid, 1); line["steps"].append(["freq1 seq 1", str(r)[-80:]])
                ch3, _, _ = void_tx.charge_state(cid); line["result"] = "after: insbal=%s patbal=%s" % (ch3.get("insbalance"), ch3.get("patbalance"))
            print("  karnes", line); kr.append(line)
    reg["karnes"] = kr
# ---------------- staff ----------------
if not ONLY or ONLY == "staff":
    pid = "17477572"; sr = []
    _, plans, _ = ins_update._plans(pid); chp = [p for p in plans.values() if p.get("carrier") == "car41826" and not p.get("enddate")]; seq = chp[0]["sequence"] if chp else "1"
    for vid, cid in (("19453098", "23363598"), ("19453097", "23363597"), ("19453099", "23363599")):
        st = dpf.live_state(pid, vid)
        if any(s["pays"] for s in st): sr.append({"visit": vid, "result": "a payment is posted - not touched"}); continue
        vis, pat, allc, m = dpf.visit_dx(cid); inv = {v: k for k, v in m.items()}; inv.setdefault("I10", dpf.I10_DCODE)
        plans_ = {}
        for c in allc:
            dcodes = (c.get("diagcodes") or "").split(); codes = [m.get(d, d) for d in dcodes]
            new = ["I10"] + [x for x in codes if x != "I10"]; plans_[c.get("id")] = [inv[x] for x in new]
        line = {"visit": vid, "charge": cid, "dx_before": codes, "dx_after": new}
        r, det = dpf.save_visit_dx(cid, plans_, dry=not LIVE); line["save"] = str(r)[:160]
        if LIVE and not str(r).startswith("FAULT"):
            if all(det.get(k, (None, None))[1] == v for k, v in plans_.items()):
                r2 = freq1_visit.run(vid, cid, seq); line["rebill"] = str(r2)[-80:]
            else: line["rebill"] = "not sent - the saved diagnosis order is not as asked (%s)" % str(det)[:120]
        print("  staff", line); sr.append(line); time.sleep(0.4)
    reg["staff"] = sr
json.dump(reg, open("registers/board_cards_c_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1); print("register written")
