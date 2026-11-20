# PLAIN ENGLISH (A chart whose Medicare number Medicare rejects: find the right one, fix it, re-send what was never paid)
# Decides: for one chart whose open Medicare plan AdvancedMD's free eligibility check REJECTS as an invalid number (reject code 72),
#   which number is right, and - when one is proven - writes it and re-sends the unpaid visits. Built 11/20/2026 after the review of
#   the feed's member numbers found chart 22075 with 22 visits unpaid for 14 months because its Medicare number had stopped being
#   valid, and a scan of every chart with money open at Medicare found 16 more like it. It is the standing cascade rule (d)
#   'MBI MISMATCH -> fix the chart's Medicare number in place and rebill', applied to every age of claim instead of the last 3 days.
# Where the right number comes from, cheapest first: (1) the Medicare block of the facility's feed (free; patient_db/adt/*.json
#   written by adt_ingest.py) when it has the Medicare shape and differs from the chart; (2) Medicare's own look-up by name, birth
#   date and state through Stedi (the look-up price; with the SSN when the chart holds one). A candidate is PROVEN only when, written
#   on the chart, AdvancedMD's free check answers ACTIVE (or Medicare knows the number and gives a date of death: then only visits up to that date go out) - otherwise the old number is put back and the chart is listed for a person.
# What is re-sent: every visit open at Medicare that carries no payment on any line (a $0 denial posting is not a payment), whose own
#   insurance order starts with the Medicare plan, and that is not older than 12 months; ONE frequency-1 original claim each
#   (freq1_visit.run; the deceased-patient guard is inside the rebill). Older visits are listed, never sent and never written off
#   here (William decides: on 11/20/2026 he had four such visits of chart 22075 sent, under the timely-filing watch).
# Never touches: paid visits, secondary balances, other plans, the insurance order, a chart whose number Medicare accepts.
# Usage: python3 medicare_number_fix.py <pid> [<pid> ...] [--live] [--no-lookup]     Register: registers/medicare_number_fix.json
import amd, ins_update, elig_amd, freq1_visit, resave, txh, stedi, json, re, sys, os, time, datetime, collections, glob
LIVE = "--live" in sys.argv; LOOKUP = "--no-lookup" not in sys.argv
MBI = r"[1-9][AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y][AC-HJKMNP-RT-Y0-9]\d[AC-HJKMNP-RT-Y]{2}\d{2}"
norm = lambda s: re.sub(r"[^A-Z0-9]", "", (s or "").upper())
def feed_numbers(pid):
    """Medicare-shaped numbers the feed carried for this chart (newest file last)."""
    try: pmap = json.load(open("registers/claimocity_patient_map.json"))
    except Exception: return []
    fids = {k for k, v in pmap.items() if re.sub(r"\D", "", v) == str(pid)}; out = []
    for f in sorted(glob.glob("patient_db/adt/*.json")):
        try: recs = json.load(open(f))
        except Exception: continue
        for r in recs:
            if r["patient"].get("id") in fids:
                for b in r["insurance"]:
                    n = norm(b.get("member"))
                    if re.fullmatch(MBI, n) and re.search(r"MEDICARE|FCSO|FIRST COAST|^MCA|^MCB", (b.get("name") or "").upper()) and n not in out: out.append(n)
    return out
def fix(pid, live=False, lookup=True, reg=None):
    reg = reg if reg is not None else {}; rec = reg.setdefault(str(pid), {"visits": {}}); today = datetime.date.today()
    raw, plans, order = ins_update._plans(pid)
    mp = [p for p in plans.values() if p.get("carrier") == "car6085" and not p.get("enddate")]
    if not mp: print("pat%s: no open Medicare plan - nothing done" % pid); rec["number"] = "no open Medicare plan"; return rec
    p = mp[0]; insid = p["id"]; seq = p.get("sequence"); old = norm(p.get("subscribernum"))
    s = elig_amd.run_plan(pid, insid.replace("ins", ""), True); st = str(s.get("status") or ""); aaa = [str(a.get("RejectReasonCode")) for a in (s.get("aaa") or [])]
    print("\n== pat%s Medicare plan %s seq %s, chart order %s: AdvancedMD's check on the chart's number: %s %s" % (pid, insid, seq, order, st, aaa))
    if st.upper().startswith("ACTIVE"): rec["number"] = "chart's number is accepted - nothing to fix"; new = old
    elif not aaa and s.get("date_of_death") and str(rec.get("number", "")).startswith("corrected"): rec["dod"] = str(s.get("date_of_death")); new = old   # a corrected number of a patient who has died: visits up to the death date still go out
    elif "72" not in aaa: rec["number"] = "not an invalid-number answer (%s %s) - listed for the cascade" % (st[:20], aaa); print("  not reject 72 - nothing done here"); return rec
    else:
        cands = [n for n in feed_numbers(pid) if n != old]; src = ["the facility's feed"] * len(cands)
        if not cands and lookup:
            pa = dict(re.findall(r'(\w+)="([^"]*)"', re.search(r'<patient [^>]*>', raw).group(0)))
            last, first = (pa.get("name") or ",").split(",")[:2]; first = first.split()[0] if first.split() else ""; last = re.sub(r"\s+(JR|SR|II|III|IV)$", "", last.strip())
            m, d, y = (pa.get("dob") or "0/0/0").split("/"); ssn = re.sub(r"\D", "", pa.get("ssn") or "")
            try:
                j = stedi.mbi(first, last, y + m.zfill(2) + d.zfill(2), "FL", today.strftime("%Y%m%d"), ssn if len(ssn) == 9 else None, pid=pid)
                os.makedirs("patient_db/%s" % pid, exist_ok=True); json.dump(j, open("patient_db/%s/stedi_mbi_lookup_%s.json" % (pid, today.strftime("%Y%m%d")), "w"))
                n = norm((j.get("subscriber") or {}).get("memberId")); errs = [str(e.get("code")) for e in j.get("errors") or []]
                print("  Medicare look-up by name and birth date%s: %s" % (" and SSN" if len(ssn) == 9 else "", "found a number%s" % (" - the SAME as the chart's" if n == old else "") if re.fullmatch(MBI, n) else "nothing (%s)" % (errs or "no number")))
                if re.fullmatch(MBI, n) and n != old: cands.append(n); src.append("Medicare's look-up")
                adv = sorted({e.get("entityName") or "" for b_ in j.get("benefitsInformation") or [] if b_.get("code") == "U" and re.search(r"HMO|PPO|POS|RISK|ADVANTAGE", (b_.get("insuranceType") or "").upper()) for e in b_.get("benefitsRelatedEntities") or []})
                if adv: rec["advantage"] = adv[0][:50]
            except Exception as e: print("  Medicare look-up failed (%s)" % type(e).__name__)
        if not cands: rec["number"] = "no other number found (feed, look-up) - listed for a person"; print("  no candidate number - listed"); return rec
        if not live: print("  DRY would try the number from %s on the chart and check it" % src[0]); new = None
        else:
            new = None
            for n, where in zip(cands, src):
                print("  writing the number from %s ->" % where, str(ins_update.update(pid, insid, subscribernum=n))[:60]); time.sleep(0.5)
                s2 = elig_amd.run_plan(pid, insid.replace("ins", ""), True); st2 = str(s2.get("status") or "")
                print("  AdvancedMD's check on it: %s (Part A %s, Part B %s)" % (st2, s2.get("partA"), s2.get("partB")))
                if st2.upper().startswith("ACTIVE"):
                    new = n; rec["number"] = "corrected from %s; AdvancedMD 271 ACTIVE" % where
                    hm = [" ".join(str(e.get("name") or "") for e in o.get("entities") or []) for o in (s2.get("other_payers") or []) if str(o.get("type") or "").upper() in ("HN", "HM")]
                    if hm and not rec.get("advantage"): rec["advantage"] = hm[0][:50]
                    break
                if not (s2.get("aaa") or []) and s2.get("date_of_death"):          # Medicare KNOWS the number; it reads inactive today only because the patient died (chart 21839, [DOB])
                    new = n; rec["dod"] = str(s2.get("date_of_death")); rec["number"] = "corrected from %s; Medicare knows the number, patient died %s" % (where, rec["dod"]); break
                print("  not ACTIVE - old number put back:", str(ins_update.update(pid, insid, subscribernum=p.get("subscribernum")))[:200])
            if not new: rec["number"] = "candidate number(s) not accepted - old number kept; listed for a person"; return rec
            _, _pl, o2 = ins_update._plans(pid)
            if (o2 or "") != (order or ""): print("  chart order %r -> %r after the edit" % (order, o2))
    byv = collections.OrderedDict()
    for c in txh.fetch(pid).iter("charge"):
        a = c.attrib
        if a.get("void") == "1": continue
        byv.setdefault(a.get("visit"), []).append((a, sum(1 for x in c.iter("payment") if x.get("void") != "1" and abs(float(x.get("amount") or 0)) > 0.005)))
    for vid, cs in byv.items():
        if not any(a.get("carrier") == "FLO02" and float(a.get("insbal") or 0) > 0.005 for a, _ in cs) or any(n for _, n in cs): continue
        a0 = cs[0][0]; m, d, y = a0.get("dos").split("/"); age = (today - datetime.date(int(y), int(m), int(d))).days; amt = sum(float(a.get("insbal") or 0) for a, _ in cs)
        if rec["number"].startswith("chart's number is accepted"): continue          # nothing was wrong with the number: the cascade's other rules own these visits
        if rec.get("advantage"): rec["visits"][vid] = "not sent - Medicare names an Advantage plan (%s): the cascade re-points it (%s, %.2f)" % (rec["advantage"], a0.get("dos"), amt); print("  v%s %s $%.2f: Medicare names an Advantage plan (%s) - not sent to Medicare, listed for the cascade" % (vid, a0.get("dos"), amt, rec["advantage"])); continue
        if rec.get("dod") and "%s%s%s" % (y, m.zfill(2), d.zfill(2)) > rec["dod"]: rec["visits"][vid] = "dated after the date of death - never sent (%s, %.2f)" % (a0.get("dos"), amt); print("  v%s %s $%.2f: dated after the date of death - not sent, listed for the write-off rule" % (vid, a0.get("dos"), amt)); continue
        if age > 365: rec["visits"][vid] = "older than 12 months - not sent, not written off (%s, %.2f)" % (a0.get("dos"), amt); print("  v%s %s $%.2f: older than 12 months - listed for William" % (vid, a0.get("dos"), amt)); continue
        if "204" in str(rec["visits"].get(vid, "")): continue
        if not live: print("  v%s %s $%.2f: DRY would re-send to Medicare once the number is proven" % (vid, a0.get("dos"), amt)); continue
        vis, pat, allc = resave.visit_charges(a0.get("id")); vorder = (vis.get("insorder") or "").replace(" ", "")
        if vorder.split(",")[0] != str(seq): rec["visits"][vid] = "visit order %s does not start with Medicare - not sent (%s, %.2f)" % (vorder, a0.get("dos"), amt); print("  v%s %s $%.2f: visit order %s does not start with Medicare - not sent" % (vid, a0.get("dos"), amt, vorder)); continue
        res = freq1_visit.run(vid, a0.get("id"), seq); rec["visits"][vid] = "%s %.2f %s" % (a0.get("dos"), amt, res[-40:]); print("  v%s %s $%.2f: %s" % (vid, a0.get("dos"), amt, res[-60:])); time.sleep(0.4)
    return rec
if __name__ == "__main__":
    amd.login_cached(); f = "registers/medicare_number_fix.json"; reg = json.load(open(f)) if os.path.exists(f) else {}
    for pid in [a for a in sys.argv[1:] if not a.startswith("--")]:
        try: fix(pid, LIVE, LOOKUP, reg)
        except Exception as e: print("pat%s: stopped - %s: %s" % (pid, type(e).__name__, str(e)[:120]))
        if LIVE: json.dump(reg, open(f, "w"), indent=1)
    sent = [(p, v) for p, r in reg.items() for v, t in r["visits"].items() if "204" in t]
    print("\nRESULT Medicare number fix: charts %d | numbers corrected %d | visits re-sent %d $%.2f | visits older than 12 months listed %d | charts listed for a person %d" % (
        len(reg), sum(1 for r in reg.values() if str(r.get("number", "")).startswith("corrected")), len(sent), sum(float(reg[p]["visits"][v].split()[1]) for p, v in sent),
        sum(1 for r in reg.values() for t in r["visits"].values() if t.startswith("older")), sum(1 for r in reg.values() if "listed" in str(r.get("number", "")))))
