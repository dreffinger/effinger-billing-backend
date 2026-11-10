# PLAIN ENGLISH (Claimocity feed ingest (generic; born as the [DOB] backlog import) - step 5, the cascade insurance check William asked for:
#   "use the nightly cascade insurance look up stedi tools as well to verify correct insurances and all on the claims").
# Decides, per chart with imported visits, which plan the claims bill FIRST and whether the visits may be released:
#   1. deceased guard (cache with real dates + AMD 'deceased' flag + any 271 date of death) - a DOS after death HOLDS.
#   2. AMD's free 271 (checkEligibility) on every open chart plan -> ACTIVE / INACTIVE / REJECTED, other payers, QMB, hospice.
#   3. lead plan: traditional Medicare (FLO02) ACTIVE and CMS lists no Medicare Advantage replacement -> Medicare first;
#      CMS lists an MA/other primary -> that carrier's ACTIVE chart plan first (none -> HOLD); no Medicare -> the first ACTIVE
#      commercial/MA plan; only Medicaid/LTC plans -> the ACTIVE one (FCC answers AAA at eligibility but pays - REJECTED kept).
#      Secondary = one more open plan of another carrier (the Medicaid/LTC plan for a QMB/dual). Medicaid/LTC never leads over Medicare.
#   4. the visits' insorder is set to that order (full-visit echo, no rebill - nothing is billed yet); the chart default order is left.
#      A visit that carries the no-charge quality line 1123F and whose echo is refused is echoed ONCE more without that line, which voids it
#      (William 11/10/2026: a reporting line never holds a visit); the removal is recorded under "quality_removed" in the chart's entry.
#      With the option code's no-charge line M0004 beside it (once per clinician): the echo is sent once more without BOTH lines when the fault's
#      words name neither or both, or 1123F alone (M0004 never rides without 1123F); without only the M0004 line when they name M0004 alone; each
#      line is known by its own procedure; one entry per line. A no-charge line whose detail cannot be read in three tries: held, and the hold
#      says in plain words that the order was NOT set and the claim goes out under the old order unless William changes it.
#   5. no ACTIVE plan at all -> Stedi insurance discovery -> add a found ACTIVE MEDICAL plan (never Part D / PDP) + order; else HOLD.
#   6. the feed's IN1 payers are mapped and reported next to the chart (the 271 decides, the feed only informs).
# Writes feed_verify_1028.json (+ registers copy). AMD writes: visit insorder resaves; addinsurance only from discovery.
# Usage: python3 feed_verify_1028.py [--no-stedi] [--limit N] [--only patNNN,...]
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
# 11/9/2026 (1:39 PM ET run): discovery items whose plan/payer text says DENTAL / VISION / LIFE are skipped like Part D - a Cigna Dental HMO hit had insured chart 17478318 and its hospital claims bounced 'not eligible'.
import amd, elig_amd, stedi, add_ins, ins_update, resave, re, json, sys, os, time, collections
os.environ.setdefault("DECEASED_CACHE", "/home/claude/unbilled/deceased_cache_local.json")
import deceased_guard
REG = json.load(open(("registers/feed_import_%s.json" % STAMP)))
PARSED = {m["pid"]: m for m in json.load(open(("feed_parsed_%s.json" % STAMP)))}
CARRIERS = json.load(open("carriers_rich.json"))            # carN -> [code, name]
CODE2CAR = {v[0]: k for k, v in CARRIERS.items()}
PAYER_MAP = [
    (r"MEDICARE A\b|FCSO|MEDICARE PART A|MEDICARE B\b|TRADITIONAL MEDICARE|^MEDICARE$|^MCA-|^MCB", "FLO02"),
    (r"SUNSHINE", "SUN01"), (r"SIMPLY", "SIM01"), (r"WELLCARE", "WEL04"), (r"HUMANA", "HUM01"),
    (r"CAPITAL HEALTH", "CAP07"), (r"AMBETTER", "AMB03"), (r"FLORIDA COMMUNITY CARE|FCC\b", "FLO99"),
    (r"UNITED ?HEALTH|UHC|AARP MEDICARE ADV", "UNI20"), (r"AARP", "AAR01"), (r"AETNA", "AET07"),
    (r"CIGNA", "CIG09"), (r"FLORIDA BLUE|BCBS|BLUE CROSS|BC/BS", "BCBS"), (r"TRICARE FOR LIFE|TFL", "TRI05"),
    (r"TRICARE", "TRI00"), (r"CHAMPVA", "CHA03"), (r"VA COMMUNITY|VACCN|VETERAN", "VACCN"),
    (r"MEDICAID(?! MANAGED)|AHCA|FLORIDA MEDICAID|^MCD|-MCD\b", "MCAD"), (r"MOLINA", "MOL01"),
]
STEDI_NAME_MAP = [(r"HUMANA", "HUM01"), (r"UNITED ?HEALTH|UHC", "UNI20"), (r"AETNA", "AET07"), (r"CIGNA", "CIG09"),
                  (r"FLORIDA BLUE|BLUE CROSS|BCBS", "BCBS"), (r"SUNSHINE|CENTENE", "SUN01"), (r"WELLCARE", "WEL04"), (r"CAPITAL HEALTH", "CAP07"),
                  (r"SIMPLY", "SIM01"), (r"AMBETTER", "AMB03"), (r"FLORIDA COMMUNITY", "FLO99"), (r"^CMS$|MEDICARE", "FLO02"), (r"MEDICAI", "MCAD"),
                  (r"\bUMR\b", "UMR")]   # 11/9/2026: discovery named UMR (UHC TPA, car303242) and the verify step held for want of this line
LTC = {"FLO99", "MCAD", "SUN01", "SIM01"}
FAMILY = {"UNI20": "UHC", "UHCMA": "UHC", "AAR01": "UHC", "UMR": "UHC", "CIPSC": "UHC", "HUM01": "HUM", "HUMMA": "HUM", "CIG09": "CIG", "CIG13": "CIG",
          "AET07": "AET", "AET12": "AET", "BCBS": "BCBS", "FLO01": "BCBS", "WEL04": "WEL", "WEL07": "WEL"}          # Medicaid / LTC plans never lead over active Medicare
MA_WORDS = r"HUMANA|UNITED|UHC|AARP|WELLCARE|AETNA|CIGNA|CAPITAL HEALTH|FLORIDA BLUE|BLUE|DEVOTED|SIMPLY|CAREPLUS|FREEDOM|OPTIMUM|SUNSHINE|AMBETTER|EMPHESYS|OPTUM"
def map_payer(name, table):
    for pat, code in table:
        if re.search(pat, (name or "").upper()): return code
    return None
def ma_replacement(s):
    """From a Medicare (FLO02) 271 summary: the name of a Medicare Advantage / other-primary payer CMS reports, else None."""
    for o in s.get("other_payers") or []:
        if o.get("code") in ("R", "U") and (o.get("type") or "") != "OT":
            names = " ".join((e.get("name") or "") for e in o.get("entities") or [])
            ids = " ".join((e.get("id") or "") for e in o.get("entities") or [])
            if re.search(r"\bS\d{4}\b", ids): continue                      # S-contract = Part D, never a medical payer
            if re.search(MA_WORDS, names.upper()) and not re.search(r"PRESCRIPTION|PDP|PART D|RX", (names + " " + (o.get("plan") or "")).upper()):
                return names.strip()
    return None
def mma_plan(s):
    """From a Florida Medicaid (MCAD) 271 summary: the SMMC MMA (comprehensive) plan's carrier code, else None (= FFS)."""
    for o in s.get("other_payers") or []:
        if "MMA" in str(o.get("plan") or "").upper():
            names = " ".join((e.get("name") or "") for e in o.get("entities") or [])
            return map_payer(names, STEDI_NAME_MAP) or "?" + names[:30]
    return None
def fast_set_insorder(v, order, removed=None):
    """Visit insorder by full echo of THIS import's charges (the register holds every charge id of the visit, so no
    gettxhistory paging): one getchargedetaildataicd10 per charge + one updvisitwithcharges force=1. -> (ok, msg)
    THE NO-CHARGE QUALITY LINE (William 11/10/2026: a reporting line never holds a visit - the routine takes it off by itself): when the full
    echo is answered with a fault and the visit carries a LIVE quality line (its own detail shows pcode65441 and at most one cent - never a
    visit's own charge), the echo is sent ONCE more without that line (a charge left out of a full echo is voided - that is the removal).
    Accepted, the order reads back right and the line reads void: the order is set and the removal is added to `removed` (a list the caller
    passes; its register's "quality_removed"). A fault again: held as before - the line was not the cause.
    THE OPTION CODE M0004 (11/10/2026): its no-charge line is treated the same way - a VOID M0004 line never holds the visit; on a fault the live
    no-charge lines (each known by its own procedure, pcode65441 / pcode692183, at most one cent) are left out of the second echo: both when the
    fault's words name neither or both (names_lines), and also when they name 1123F alone (the 1123F line never leaves the M0004 line behind:
    M0004 rides only with 1123F - that M0004 entry says "with": "1123F"); only the M0004 line when they name M0004 alone. One removal entry per
    line, with its "code". A no-charge line's own detail is read up to three times before it counts as unreadable (one time-out must not keep the
    visit's own order from being set); still unreadable = held as before, and the message names that line."""
    import xml.etree.ElementTree as ET
    charges = []; vis = pat = None; qgone = 0; qc = v.get("quality_charge") or "-"; mc = (v.get("mvp_charge") if v.get("mvp_codes") else "") or "-"; unread = []
    def _detail(cid):      # one charge detail - a no-charge line up to three times until its answer holds that charge (confirm review NH2-3)
        for _try in (1, 2, 3):
            try:
                d = ET.fromstring(resave.detail(re.sub(r"\D", "", cid)))
                if cid not in (qc, mc) or any(c.get("id") == cid for c in d.iter("charge")): return d
            except Exception:
                if cid not in (qc, mc): raise
            if _try < 3: __import__("time").sleep(1.0)
        return None
    for cid in v["charges"]:
        d = _detail(cid)
        if d is None: unread.append(cid); continue      # never echoed without it on that ground: a charge nobody has checked is never left out
        if vis is None: vis = d.find(".//visit"); pat = d.find(".//patient")
        for c in d.iter("charge"):
            if c.get("id") == cid and c.get("void") != "1": charges.append(c)
            elif c.get("id") == cid and cid in (qc, mc): qgone += 1      # 11/10/2026: a VOID no-charge line (1123F or M0004) has nothing to echo and never holds the visit
    if vis is None or not charges or len(charges) != len(v["charges"]) - qgone:
        return False, "detail read mismatch (%d of %d charges live%s)" % (len(charges), len(v["charges"]), ("; the no-charge line %s could not be read in three tries" % ", ".join(unread)) if unread else "")
    if (vis.get("insorder") or "").replace(" ", "") == order: return True, "already %s" % order
    def echo(chs):      # the full echo of the given charges with the new order
        chg = ""
        for c in chs:
            a = {"id": c.get("id")}
            for f in resave.CHG_FIELDS:
                if c.get(f) is not None: a[f] = c.get(f)
            chg += "<charge %s/>" % " ".join('%s="%s"' % (k, x) for k, x in a.items())
        va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = order
        return amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
                        "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, x) for k, x in va.items()), chg)), timeout=180)
    r = echo(charges); took = ""; out = []
    if "Fault" in r:
        def small(c):
            try: return float(c.get("fee") or "0") <= 0.01
            except Exception: return False
        kind = {"pcode65441": "1123F", "pcode692183": "M0004"}      # the no-charge lines, known by their OWN procedure (never a visit's own charge)
        nc = {kind[c.get("proccode")]: c for c in charges if c.get("id") in (qc, mc) and c.get("proccode") in kind and small(c)}; mwith = False
        if len(nc) == 2:      # both lines live: the fault's words decide - both when they name neither or both, and when they name 1123F alone (the 1123F
            # line never leaves the M0004 line behind: 8.2, confirm review NH2-1); only the M0004 line when they name M0004 alone
            nq, nm = names_lines(r, nc["1123F"].get("id"), nc["M0004"].get("id"))
            if nm and not nq: nc = {"M0004": nc["M0004"]}
            mwith = nq and not nm      # the M0004 line comes off only because the 1123F line does: not M0004's fault
        out = [nc[k] for k in ("1123F", "M0004") if k in nc]; rest = [c for c in charges if c not in out]
        if not (out and rest and (v.get("quality_codes") or v.get("mvp_codes"))): return False, "resave FAULT " + re.sub(r"\s+", " ", r[:200])
        r2 = echo(rest)      # ONCE more, without the no-charge line(s)
        if "Fault" in r2:
            if [c.get("proccode") for c in out] == ["pcode65441"]: return False, "resave FAULT %s (sent once more without the quality line %s: a fault again - the line is not the cause)" % (re.sub(r"\s+", " ", r[:120]), out[0].get("id"))
            return False, "resave FAULT %s (sent once more without the no-charge line(s) %s: a fault again - the lines are not the cause)" % (re.sub(r"\s+", " ", r[:120]), ", ".join("%s %s" % (kind[c.get("proccode")], c.get("id")) for c in out))
        charges = rest; took = re.sub(r"\s+", " ", r[:140])
    d2 = ET.fromstring(resave.detail(re.sub(r"\D", "", charges[0].get("id")))); v2 = d2.find(".//visit")      # read back through a charge that is live
    live = [c for c in d2.iter("charge") if c.get("void") != "1"]
    got = (v2.get("insorder") or "").replace(" ", "") if v2 is not None else ""
    ok = got == order and len(live) >= 1
    if took:      # was each line really voided by the echo without it? One read of its own detail
        res = []
        for c in out:
            x = c.get("id"); code = "M0004" if c.get("proccode") == "pcode692183" else "1123F"
            qv = [y for y in ET.fromstring(resave.detail(re.sub(r"\D", "", x))).iter("charge") if y.get("id") == x]
            gone = bool(qv) and qv[0].get("void") == "1"; res.append((code, x, gone))
            if ok and gone and isinstance(removed, list):
                removed.append(dict({"visit": v.get("visit"), "pid": v.get("pid"), "charge": x, "code": code, "fee": v.get("mvp_fee" if code == "M0004" else "quality_fee"), "why": took, "void_ok": True, "released": True, "at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None).isoformat()},
                                    **({"with": "1123F"} if code == "M0004" and mwith else {})))
        if [k for k, _x, _g in res] == ["1123F"]: return ok, "insorder %s -> %s (the echo with the quality line %s was refused; sent once more without it: the line is %s)" % (vis.get("insorder"), got, res[0][1], "void" if res[0][2] else "still live")
        return ok, "insorder %s -> %s (the echo with the no-charge line(s) was refused; sent once more without %s)" % (vis.get("insorder"), got, ", ".join("%s %s: %s" % (k, x, "void" if g else "still live") for k, x, g in res))
    return ok, "insorder %s -> %s" % (vis.get("insorder"), got)
def names_lines(words, qcharge="", mcharge=""):
    """The import's own test (claimocity_import.names_lines), for a visit that carries the 1123F line AND the M0004 line: (the words name the 1123F
    line, the words name the M0004 line). A line is named by its code, AdvancedMD's id for it or its own charge number; words about a zero amount
    name the line whose code is not named - both lines when neither is named by its code."""
    w = str(words or ""); low = w.lower()
    def named(code, pcode, charge):
        n = re.sub(r"\D", "", str(charge or ""))
        return code.lower() in low or pcode in low or bool(n and re.search(r"(?<!\d)%s(?!\d)" % n, w))
    q = named("1123F", "pcode65441", qcharge); m = named("M0004", "pcode692183", mcharge)
    zero = bool(re.search(r"zero|\$0", low)) and bool(re.search(r"charge|amount", low))
    return (q or (zero and not m)), (m or (zero and not q))
def main():
    a = sys.argv[1:]; use_stedi = "--no-stedi" not in a; limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 10 ** 9
    only = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None
    amd.login_cached()
    by_chart = collections.defaultdict(list)
    for r in REG["created"]: by_chart[r["pid"]].append(r)
    OUTF = os.environ.get("VERIFY_OUT", ("feed_verify_%s.json" % STAMP))
    prev = {}
    for f in [("feed_verify_%s.json" % STAMP)] + [x for x in os.listdir(".") if x.startswith(("feed_verify_%s_p" % STAMP)) and x.endswith(".json")]:
        if os.path.exists(f): prev.update(json.load(open(f)))
    out = dict(prev); stats = collections.Counter(); n = 0
    for pid, visits in by_chart.items():
        if only and pid not in only: continue
        if not only and pid in prev and prev[pid].get("decision") == "RELEASE" and prev[pid].get("v") == 3: continue
        if n >= limit: break
        n += 1
        num = re.sub(r"\D", "", pid)
        rec = {"v": 3, "visits": [v["visit"] for v in visits], "dos": sorted({v["dos"] for v in visits}), "cpts": sorted({c for v in visits for c in v["cpts"]}), "checks": [], "fixes": [], "hold": []}
        try:
            pa, plans = elig_amd.plans(num)
            rec["insorder"] = pa.get("insorder", ""); rec["deceased_flag"] = pa.get("deceased", "")
            openp = [p for p in plans if not p.get("enddate")]
            code_of = {p["id"]: CARRIERS.get(p.get("carrier"), [p.get("carrier")])[0] for p in plans}
            rec["plans"] = [{"id": p["id"], "car": code_of[p["id"]], "seq": p.get("sequence"), "end": p.get("enddate")} for p in plans]
            feed_codes = []
            for v in visits:
                for nm in PARSED.get(v["feed_id"], {}).get("IN1", []):
                    c = map_payer(nm, PAYER_MAP)
                    if c and c not in feed_codes: feed_codes.append(c)
            rec["feed_payers"] = feed_codes
            latest_dos = max(v["dos"] for v in visits)
            # 1. deceased
            blocked, why = deceased_guard.check(num, latest_dos, "FLO02" if any(code_of[p["id"]] == "FLO02" for p in openp) else None,
                                                 "99487" if "99487" in rec["cpts"] else None, allow_lookup=use_stedi)
            if pa.get("deceased"): rec["hold"].append("AMD chart flagged deceased %s" % pa.get("deceased"))
            if blocked: rec["hold"].append(why)
            # 2. 271 per open plan
            status = {}; summ = {}
            for p in openp:
                try:
                    s = elig_amd.run_plan(num, p["id"].replace("ins", "")); summ[p["id"]] = s
                    status[p["id"]] = (s.get("status") or "UNKNOWN").split()[0]
                    rec["checks"].append({"plan": p["id"], "car": code_of[p["id"]], "seq": p.get("sequence"), "result": elig_amd.one_line(s)[:300]})
                    if s.get("date_of_death"):
                        dod = s["date_of_death"]; dod_iso = "%s-%s-%s" % (dod[:4], dod[4:6], dod[6:8]) if re.match(r"\d{8}$", dod) else dod
                        deceased_guard.record(num, {"dateOfDeath": dod}, "amd-271")
                        after = [v["dos"] for v in visits if deceased_guard._iso(v["dos"]) > dod_iso]
                        if after: rec["hold"].append("271 reports date of death %s - visits dated after it: %s (never bill; void)" % (dod_iso, after))
                        else: rec["note_dod"] = "271 reports date of death %s; all imported visits are on/before it - billable" % dod_iso
                except Exception as e:
                    status[p["id"]] = "ERROR"; rec["checks"].append({"plan": p["id"], "car": code_of[p["id"]], "result": "271 error %s" % str(e)[:120]})
                time.sleep(0.3)
            # 3. choose the lead
            def active(p): return status.get(p["id"]) == "ACTIVE"
            med = [p for p in openp if code_of[p["id"]] == "FLO02"]
            med_active = next((p for p in med if active(p)), None)
            if med_active is None:
                for p in med:   # Medicare answers INACTIVE after a death; coverage was in force on DOS before the death date -> still the lead
                    sdod = (summ.get(p["id"]) or {}).get("date_of_death")
                    if sdod and all(deceased_guard._iso(v["dos"]) <= "%s-%s-%s" % (sdod[:4], sdod[4:6], sdod[6:8]) for v in visits):
                        med_active = p; rec["fixes"].append("Medicare INACTIVE after death %s; every imported DOS precedes it - Medicare leads" % sdod); break
            lead = None; reason = ""
            if med_active:
                ma = ma_replacement(summ[med_active["id"]])
                if ma:
                    ma_code = map_payer(ma, STEDI_NAME_MAP)
                    fam = FAMILY.get(ma_code, ma_code)
                    cand = sorted([p for p in openp if FAMILY.get(code_of[p["id"]], code_of[p["id"]]) == fam and active(p)], key=lambda p: int(p.get("sequence") or 99))
                    if cand: lead = cand[0]; reason = "CMS: %s is the Medicare Advantage/primary payer" % ma
                    else: rec["hold"].append("CMS reports MA/other primary '%s' (%s) but no ACTIVE %s plan on the chart" % (ma, ma_code, ma_code))
                else:
                    lead = med_active; reason = "traditional Medicare ACTIVE, no MA replacement on the CMS 271"
            if lead is None and not rec["hold"]:
                comm = [p for p in openp if active(p) and code_of[p["id"]] not in LTC and code_of[p["id"]] != "FLO02"]
                if comm: lead = sorted(comm, key=lambda p: int(p.get("sequence") or 99))[0]; reason = "%s ACTIVE (no traditional Medicare)" % code_of[lead["id"]]
            if lead is None and not rec["hold"]:
                ltc = [p for p in openp if code_of[p["id"]] in LTC and status.get(p["id"]) in ("ACTIVE", "REJECTED")]
                mcad = next((p for p in ltc if code_of[p["id"]] == "MCAD" and active(p)), None)
                mma = mma_plan(summ[mcad["id"]]) if mcad else None
                if mma and not mma.startswith("?"):
                    cand = [p for p in openp if code_of[p["id"]] == mma and status.get(p["id"]) in ("ACTIVE", "REJECTED")]
                    if cand: lead = cand[0]; reason = "Medicaid 271: SMMC MMA plan is %s - physician claims go to the MMA plan" % mma
                    else: rec["hold"].append("Medicaid 271 names SMMC MMA plan %s but the chart has no %s plan" % (mma, mma))
                elif mma: rec["hold"].append("Medicaid 271 names an SMMC MMA plan not mapped to a carrier: %s" % mma)
                elif ltc: lead = sorted(ltc, key=lambda p: int(p.get("sequence") or 99))[0]; reason = "Medicaid/LTC plan %s only (271 %s, no MMA plan)" % (code_of[lead["id"]], status[lead["id"]])
            # 5. discovery when nothing is active
            if lead is None and not rec["hold"]:
                if use_stedi:
                    msg = PARSED.get(visits[0]["feed_id"], {})
                    last, _, first = msg.get("name", "").partition(","); first = first.strip().split(" ")[0] if first else ""; last = last.strip()
                    try:
                        ds = stedi.disc_summ(stedi.disc(first, last, msg.get("dob", "")[:8], "FL")); rec["discovery"] = ds
                        for it in ds.get("items") or []:
                            txt = ((it.get("plan") or "") + " " + (it.get("payer") or "")).upper()
                            if re.search(r"PDP|PRESCRIPTION|PART D|DENTAL|VISION|\bLIFE\b", txt) or not (it.get("status") or "").upper().startswith("ACTIVE") or not it.get("member"): continue   # 11/9/2026: a 'CIGNA Dental Health / Dental HMO' hit insured chart 17478318 - dental, vision and life hits are never a medical payer
                            code = map_payer(it.get("payer"), STEDI_NAME_MAP)
                            if code and any(code_of[p["id"]] == code for p in plans):
                                rec["fixes"].append("discovery found %s but the chart already carries a %s plan (status %s) - not re-added" % (code, code, [status.get(p["id"]) for p in plans if code_of[p["id"]] == code])); continue
                            if code and code in CODE2CAR:
                                insid, seq = add_ins.add(num, CODE2CAR[code], it["member"])
                                rec["fixes"].append("discovery: added %s plan -> %s seq %s" % (code, insid, seq)); stats["plans added"] += 1
                                if insid and str(insid).startswith("ins"):
                                    ok, m2 = ins_update._set_order(num, {p["id"]: p for p in elig_amd.plans(num)[1]}, insid, str(seq)); rec["fixes"].append("chart order -> %s: %s" % (seq, m2[:100]))
                                    lead = {"id": insid, "sequence": str(seq)}; code_of[insid] = code; reason = "Stedi discovery %s ACTIVE" % code; status[insid] = "ACTIVE"
                                break
                        if lead is None: rec["hold"].append("no active plan: discovery found %s" % ([(i.get("payer"), i.get("status")) for i in ds.get("items") or []] or "nothing"))
                    except Exception as e:
                        rec["hold"].append("no active plan; discovery error %s" % str(e)[:120])
                else:
                    rec["hold"].append("no ACTIVE plan on the chart (Stedi off)")
            # order = lead + one secondary of another carrier (dual: the Medicaid/LTC plan; else the next open plan)
            order = None
            if lead is not None:
                sec = None
                others = [p for p in openp if p["id"] != lead["id"] and code_of[p["id"]] != code_of[lead["id"]] and status.get(p["id"]) in ("ACTIVE", "REJECTED")]
                ltc_sec = [p for p in others if code_of[p["id"]] in LTC or (code_of[p["id"]] == "HUM01" and re.match(r"\d{10}$", p.get("subscribernum") or ""))]
                qmb = bool(med_active and any((o.get("code") == "QM") or "QMB" in str(o.get("plan") or "").upper() for o in summ[med_active["id"]].get("other_payers") or []))
                if code_of[lead["id"]] == "FLO02" and ltc_sec: sec = sorted(ltc_sec, key=lambda p: int(p.get("sequence") or 99))[0]
                elif code_of[lead["id"]] not in LTC and code_of[lead["id"]] != "FLO02" and ltc_sec and med_active:
                    sec = sorted(ltc_sec, key=lambda p: int(p.get("sequence") or 99))[0]      # MA / D-SNP lead on a dual: Medicaid plan second
                elif code_of[lead["id"]] == "FLO02":
                    supp = [p for p in others if active(p) and code_of[p["id"]] not in LTC]
                    if supp: sec = sorted(supp, key=lambda p: int(p.get("sequence") or 99))[0]
                order = ",".join([lead["sequence"]] + ([sec["sequence"]] if sec else []))
                rec["lead"] = {"code": code_of[lead["id"]], "seq": lead["sequence"], "why": reason, "qmb": qmb}
                rec["order"] = order
                # 4. apply to the visits
                applied = (prev.get(pid) or {}).get("applied") or {}; rec["applied"] = dict(applied)
                # the import copied the chart's default order onto every visit: when that is already the target, nothing to resave
                same_as_default = (rec["insorder"] or "").replace(" ", "") == order
                for v in visits:
                    if applied.get(v["visit"]) == order: continue
                    if same_as_default: rec["applied"][v["visit"]] = order; continue
                    cid = v["charges"][0] if v.get("charges") else None
                    if not cid: rec["fixes"].append("%s: no charge id recorded" % v["visit"]); continue
                    # 11/10/2026: a visit that carries the no-charge quality line and whose order cannot be set says so in the words the import
                    # looks for ("insorder not applied on <visit>" with the line named) - the import then switches the code off until William looks
                    qtag = (lambda w: " (the visit carries the quality line %s: %s)" % (v.get("quality_charge"), w[:120])) if (v.get("quality_codes") and v.get("quality_charge")) else None
                    if v.get("mvp_codes") and v.get("mvp_charge"):      # the option code's line too: the same words, naming both lines
                        qtag = lambda w: " (the visit carries the quality line %s and the M0004 line %s: %s)" % (v.get("quality_charge") or "-", v.get("mvp_charge"), w[:120])
                    try:
                        removed = []; ok, m = fast_set_insorder(v, order, removed)
                        rec["fixes"].append("%s insorder %s: %s" % (v["visit"], order, "ok" if ok else m[:140]))
                        if removed and [e.get("code") for e in removed] == ["1123F"]: rec.setdefault("quality_removed", []).extend(removed); rec["fixes"].append("%s: the quality line %s was taken off - the echo with it was refused, the echo without it was accepted (William 11/10/2026: a reporting line never holds a visit)" % (v["visit"], v.get("quality_charge")))
                        elif removed: rec.setdefault("quality_removed", []).extend(removed); rec["fixes"].append("%s: the no-charge line(s) %s were taken off - the echo with them was refused, the echo without them was accepted (William 11/10/2026: a reporting line never holds a visit)" % (v["visit"], ", ".join("%s %s" % (e.get("code"), e.get("charge")) for e in removed)))
                        if ok: rec["applied"][v["visit"]] = order
                        else:
                            rec["hold"].append("insorder not applied on %s%s" % (v["visit"], qtag(m) if qtag else ""))
                            if qtag and "could not be read in three tries" in m:      # first in the list, so the Holds line of the report shows it whole (confirm review NH2-3)
                                rec["hold"].insert(0, "the order of %s was NOT set because its no-charge quality line could not be read (three tries) - the claim goes out under the old order %s unless William changes it" % (v["visit"], rec.get("insorder") or "?"))
                    except Exception as e:
                        rec["hold"].append(("insorder not applied on %s%s" % (v["visit"], qtag("error %s" % str(e)[:100]))) if qtag else "insorder error on %s: %s" % (v["visit"], str(e)[:100]))
                    time.sleep(0.4)
            if feed_codes and lead is not None and code_of[lead["id"]] not in feed_codes:
                rec["note"] = "feed IN1 says %s, chart bills %s first (%s)" % (feed_codes, code_of[lead["id"]], reason)
            rec["decision"] = "HOLD" if rec["hold"] else "RELEASE"
            stats[rec["decision"]] += 1
            print(rec["decision"], pid, rec.get("order"), rec.get("lead", {}).get("code"), "|", reason[:60], "| feed", feed_codes, "|", "; ".join(rec["hold"])[:140])
        except Exception as e:
            rec["decision"] = "HOLD"; rec["hold"].append("verify error %s" % str(e)[:160]); stats["error"] += 1; print("ERR", pid, str(e)[:160])
        out[pid] = rec
        json.dump({k: v for k, v in out.items() if k not in prev or v is not prev.get(k)} if OUTF != ("feed_verify_%s.json" % STAMP) else out, open(OUTF, "w"), indent=1)
        if n % 25 == 0: print("progress", n, dict(stats))
    print("DONE", dict(stats))
if __name__ == "__main__": main()
