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
#      11/10/2026 (round 7): the save is skipped only when the visit's insurance-order LIST (what a claim is built from) AND its insorder attribute
#      already equal the order - a visit entered while its chart had no plan reads "1" over an EMPTY list and never billed (84 visits, $18,802). Every
#      live charge is echoed, a visit already billed is never saved, the admission date is read before and after and put back. A visit whose order is
#      not confirmed HOLDS the chart in words that say what its list shows (NO CLAIM CAN BE MADE / still bills to its old order / already billed).
#      HOLD is a label in this report only: AdvancedMD still bills a visit that has an insurance order - every hold line says so. The admission date
#      is judged per hospital code; one a save lost and could not put back is remembered and keeps the visit held until it reads back; after such a
#      save (or a lost charge) the chart's other visits are not saved (William looks first).
#      Where the two rules meet: the sentence for a no-charge line that could not be read names the visit's own LIST as the old order and keeps its
#      own ending (it says itself that the claim goes out); a visit whose list is EMPTY gets the NO CLAIM words and not that sentence.
#   5. no ACTIVE plan at all -> Stedi insurance discovery -> add a found ACTIVE MEDICAL plan (never Part D / PDP) + order; else HOLD.
#      11/10/2026 (round 7): the look-up is dated to the chart's latest date of service and its plan is added only when the answer is a medical plan
#      (never dental, vision, life or a stand-alone drug plan - payer name, carrier name and every plan text of the answer; a Medicare Advantage plan
#      with drug coverage IS medical, the 11/10 clarification) shown active on every date of service;
#      otherwise nothing is added and the answer's words go to William. When every free check of a chart with plans errored, nothing is bought:
#      "free check down - not checked tonight".
#   6. the feed's IN1 payers are mapped and reported next to the chart (the 271 decides, the feed only informs).
# Writes feed_verify_1028.json (+ registers copy). AMD writes: visit insorder resaves; addinsurance only from discovery; updextrainsinfo only to put
# back an admission date a resave wiped (11/10/2026). Never: a save on a billed visit, a rebill, a void (except the no-charge line left out above).
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
def fast_set_insorder(v, order, removed=None, info=None):
    """Visit insorder by full echo of the visit's charges: one getchargedetaildataicd10 per register charge, resave.visit_charges for every
    live charge of the visit, one updvisitwithcharges force=1. -> (ok, msg)
    THE INSURANCE-ORDER LIST (11/10/2026, round 7): a visit entered while its chart had no plan reads insorder "1" over an EMPTY list, and a
    claim is built from the list - such a visit never billed (84 visits, $18,802). So: the save is skipped ONLY when the attribute AND the
    list (order_list) equal the order; EVERY live charge of the visit is echoed (a sibling the register does not list would be voided);
    a visit already billed (bill date, insurance bill or payment on a live charge) is never saved ("already billed - not saved"); a visit
    whose import row predates this change (no "open_plans_at_entry") and whose list is EMPTY is not saved here either - such a visit is
    saved only by feed_order_sweep.py, with the owner's approved file in place. After the save the attribute, the list, every echoed charge (still
    live, nothing new) and the admission date of each hospital code (each from its charge's own detail) are read back; a wiped or changed
    admission date is written back with the import's own call and read again (still wrong: not ok, "admission date lost on save"). An error
    after the save was sent is not raised: the visit is read again, a lost admission date written back, and the answer is not ok ("error after
    the save was sent: ..."). A visit whose row carries "admit_lost_before" (an earlier run of this batch lost its date) is not confirmed until
    that date reads back. The message carries the list before and after. `info` (a dict the caller passes) receives sent, accepted,
    list_before, list_now (None = not read), billed, old_row, admit_lost ({code: date still lost}), dropped, added.
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
    inf = info if isinstance(info, dict) else {}
    inf.update(sent=False, accepted=False, list_before=None, list_now=None, billed=[], old_row=False, admit_lost={}, dropped=[], added=[])
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
    if vis is not None: inf["list_before"] = inf["list_now"] = order_list(vis)
    if vis is None or not charges or len(charges) != len(v["charges"]) - qgone:
        return False, "detail read mismatch (%d of %d charges live%s)" % (len(charges), len(v["charges"]), ("; the no-charge line %s could not be read in three tries" % ", ".join(unread)) if unread else "")
    before = order_list(vis); att = (vis.get("insorder") or "").replace(" ", "")
    want = v.get("admit_lost_before")      # an earlier run of this batch lost this visit's admission date on its save: it stays held until the date reads back
    if isinstance(want, dict) and want:
        nowa = admit_codes(charges) if [k for k in want if k != "visit"] else {}
        if "visit" in want: nowa["visit"] = admit_of(vis)
        still = {k: x for k, x in want.items() if x and nowa.get(k) != x}
        if still:
            inf["admit_lost"] = still
            return False, "admission date lost on an earlier save of this batch (was %s, now %s) - nothing sent until it reads back; insorder %s, list [%s]" % (
                " / ".join(sorted(set(still.values()))), " / ".join(sorted(set(nowa.get(k) or "none" for k in still))), att, before)
    if att == order and before == order: return True, "already %s, list [%s] - nothing sent" % (order, before)      # decided from the register's own reads (no extra call)
    reg_ids = [c.get("id") for c in charges]
    vis, pat, charges = resave.visit_charges(re.sub(r"\D", "", reg_ids[0]))      # 11/10/2026 (round 7): a save echoes EVERY live charge of the visit, not only the register's
    live_ids = [c.get("id") for c in charges]
    if vis is None or [x for x in reg_ids if x not in live_ids]:
        return False, "detail read mismatch (register charge(s) %s not among the visit's %d live charges)" % (",".join(x for x in reg_ids if x not in live_ids) or "?", len(charges))
    before = order_list(vis); inf["list_before"] = inf["list_now"] = before; att = (vis.get("insorder") or "").replace(" ", "")
    if att == order and before == order: return True, "already %s, list [%s] - nothing sent" % (order, before)
    billed = billed_reasons(charges)
    if billed:
        inf["billed"] = billed
        return False, "already billed - not saved (%s on a live charge; insorder %s, list [%s], asked %s)" % (", ".join(billed), att, before, order)
    if not before and "open_plans_at_entry" not in v:
        inf["old_row"] = True
        return False, "list [] - not saved here: entered before this change (its import row has no open_plans_at_entry); such a visit is saved only by feed_order_sweep.py --resave, with the owner's approved file in place (his approved visits, or his standing word)"
    adm0 = admit_codes(charges); vadm0 = "" if adm0 else admit_of(vis); extra = [x for x in live_ids if x not in reg_ids]      # the admission date of each hospital code, each from its charge's own detail
    def after_error(why):      # the save may have landed: read the visit again, put a lost admission date back, say what it reads now (never raised)
        try:
            v3, p3, c3 = resave.visit_charges(re.sub(r"\D", "", reg_ids[0]))
            ids3 = [c.get("id") for c in c3]; inf["list_now"] = order_list(v3); inf["dropped"] = [x for x in live_ids if x not in ids3]
            adm3, still3 = admit_back((v3 if v3 is not None else vis).get("id"), c3, adm0, vadm0)
            if still3: inf["admit_lost"] = still3
            return False, "error after the save was sent: %s - read again: insorder %s, list [%s] -> [%s], %d of %d echoed charges live%s - NOT AS ASKED" % (
                why, v3.get("insorder") if v3 is not None else "?", before, inf["list_now"], len(live_ids) - len(inf["dropped"]), len(live_ids), ("; " + adm3[2:]) if adm3 else "")
        except Exception as e2:
            inf["list_now"] = None
            return False, "error after the save was sent: %s, and the visit could not be read again (%s) - look at it in AdvancedMD before anything else is sent" % (why, type(e2).__name__)
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
    inf["sent"] = True; took = ""; out = []
    try: r = echo(charges)
    except Exception as e: return after_error("the answer to the save never came back (%s: %s)" % (type(e).__name__, str(e)[:80]))
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
        try: r2 = echo(rest)      # ONCE more, without the no-charge line(s)
        except Exception as e: return after_error("the answer to the second save (without the no-charge line) never came back (%s: %s)" % (type(e).__name__, str(e)[:80]))
        if "Fault" in r2:
            if [c.get("proccode") for c in out] == ["pcode65441"]: return False, "resave FAULT %s (sent once more without the quality line %s: a fault again - the line is not the cause)" % (re.sub(r"\s+", " ", r[:120]), out[0].get("id"))
            return False, "resave FAULT %s (sent once more without the no-charge line(s) %s: a fault again - the lines are not the cause)" % (re.sub(r"\s+", " ", r[:120]), ", ".join("%s %s" % (kind[c.get("proccode")], c.get("id")) for c in out))
        charges = rest; took = re.sub(r"\s+", " ", r[:140])
    inf["accepted"] = True
    try:
        v2, p2, c2 = resave.visit_charges(re.sub(r"\D", "", charges[0].get("id")))      # read back through a charge that is live: every live charge, the attribute, the LIST
        got = (v2.get("insorder") or "").replace(" ", "") if v2 is not None else ""; after = order_list(v2); inf["list_now"] = after
        echoed = [c.get("id") for c in charges]; now = [c.get("id") for c in c2]
        dropped = [x for x in echoed if x not in now]; added = [x for x in now if x not in echoed]
        adm, still = admit_back((v2 if v2 is not None else vis).get("id"), c2, adm0, vadm0)      # a wiped or changed admission date (per hospital code): written back with the import's own call, then read again
    except Exception as e: return after_error("the read-back after the save failed (%s: %s)" % (type(e).__name__, str(e)[:80]))
    adm = ("; " + adm[2:]) if adm else ""; inf["dropped"], inf["added"] = dropped, added
    if still: inf["admit_lost"] = still
    ok = got == order and after == order and not dropped and not added and not inf["admit_lost"]
    tail = ", list [%s] -> [%s], %d of %d echoed charges live%s%s%s%s%s" % (before, after, len(echoed) - len(dropped), len(echoed),
        (" (also echoed, not in the register: %s)" % ",".join(extra)) if extra else "", ("; no longer live: " + ",".join(dropped)) if dropped else "",
        ("; new: " + ",".join(added)) if added else "", adm, "" if ok else " - NOT AS ASKED")
    if took:      # was each line really voided by the echo without it? One read of its own detail
        res = []
        for c in out:
            x = c.get("id"); code = "M0004" if c.get("proccode") == "pcode692183" else "1123F"
            qv = [y for y in ET.fromstring(resave.detail(re.sub(r"\D", "", x))).iter("charge") if y.get("id") == x]
            gone = bool(qv) and qv[0].get("void") == "1"; res.append((code, x, gone))
            if ok and gone and isinstance(removed, list):
                removed.append(dict({"visit": v.get("visit"), "pid": v.get("pid"), "charge": x, "code": code, "fee": v.get("mvp_fee" if code == "M0004" else "quality_fee"), "why": took, "void_ok": True, "released": True, "at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).replace(tzinfo=None).isoformat()},
                                    **({"with": "1123F"} if code == "M0004" and mwith else {})))
        if [k for k, _x, _g in res] == ["1123F"]: return ok, "insorder %s -> %s (the echo with the quality line %s was refused; sent once more without it: the line is %s)%s" % (vis.get("insorder"), got, res[0][1], "void" if res[0][2] else "still live", tail)
        return ok, "insorder %s -> %s (the echo with the no-charge line(s) was refused; sent once more without %s)%s" % (vis.get("insorder"), got, ", ".join("%s %s: %s" % (k, x, "void" if g else "still live") for k, x, g in res), tail)
    return ok, "insorder %s -> %s%s" % (vis.get("insorder"), got, tail)
def order_list(vis):
    """The visit's insurance-order LIST as AdvancedMD built it (11/10/2026): the plan sequences of visit/insuranceorderlist/insuranceorder in
    ordinal order, joined like the insorder attribute ("1", "4,2"); "" when the list is empty. A claim is built from this list - the attribute
    can read "1" over an empty list. (The same function is in resave.py; the self-test checks the two agree.)"""
    rows = vis.findall("insuranceorderlist/insuranceorder") if vis is not None else []
    def ordinal(o):
        try: return int(o.get("ordinal") or 0)
        except ValueError: return 0
    return ",".join((o.get("sequence") or "").strip() for o in sorted(rows, key=ordinal))
def billed_reasons(charges):
    """Why a visit counts as already billed, read from its live charges' own detail: a bill date, an insurance bill (insbilled 1 or an insbill
    row) or a payment that is not void (any amount). [] = never billed. (The same function is in resave.py.)"""
    why = []
    for c in charges:
        if (c.get("datebilled") or "").strip() and "bill date" not in why: why.append("bill date")
        if (c.get("insbilled") == "1" or c.find(".//insbill") is not None) and "insurance bill" not in why: why.append("insurance bill")
        if any(p.get("void") != "1" for p in c.iter("payment")) and "payment" not in why: why.append("payment")
    return why
HOSP_CODES = {"99221", "99222", "99223", "99231", "99232", "99233", "99238", "99239"}      # the codes the import writes the admission date for (claimocity_import.HOSP)
def admit_of(vis):
    """The visit's admission date (extins hospitalizationfrom, "MM/DD/YYYY"), "" when there is none."""
    e = vis.find("extins") if vis is not None else None
    return ((e.get("hospitalizationfrom") if e is not None else "") or "").strip()
def admit_codes(charges):
    """The admission date of each hospital procedure code of the visit: {CPT: "MM/DD/YYYY" or ""} for every live charge whose code is a hospital
    code, each read from that charge's OWN detail (the practice writes the date once per hospital code, so a visit of 99497 + 99223 is judged by
    its 99223, whichever charge comes first). {} = no hospital code. (The same function is in resave.py.)"""
    import xml.etree.ElementTree as ET
    out = {}
    for c in charges:
        d = ET.fromstring(resave.detail(re.sub(r"\D", "", c.get("id") or "")))
        cpt = {x.get("id"): x.get("code") for x in d.findall(".//proccodelist/proccode") if x.get("id")}.get(c.get("proccode"), "")
        if cpt in HOSP_CODES and not out.get(cpt): out[cpt] = admit_of(d.find(".//visit"))
    return out
def restore_admit(visitid, charges, admit):
    """Write the admission date back after a save wiped or changed it - the import's proven call, unchanged (claimocity_import.py, the lines that
    write hospitalizationfrom): updextrainsinfo per hospital procedure code. admit = one date for every hospital code of the visit's live charges
    (each charge's code read from its own detail), or {CPT: date} = only those codes, each with its own date. Returns (codes written, faults).
    (The same function is in resave.py.)"""
    import xml.etree.ElementTree as ET
    if isinstance(admit, dict): todo = [(k, x) for k, x in sorted(admit.items()) if x]
    else:
        todo = []
        for c in charges:
            pm = {x.get("id"): x.get("code") for x in ET.fromstring(resave.detail(re.sub(r"\D", "", c.get("id") or ""))).findall(".//proccodelist/proccode") if x.get("id")}
            cpt = pm.get(c.get("proccode"), "")
            if cpt in HOSP_CODES and cpt not in [k for k, _d in todo]: todo.append((cpt, admit))
    bad = []
    for cpt, admit in todo:
        ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" '
               'autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>') % (cpt, admit)
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst" + re.sub(r"\D", "", str(visitid)), "nocookie": "1"}, ext), timeout=120)
        if "Fault" in r or 'hospitalizationfrom="%s"' % admit not in r: bad.append(cpt)
    return [k for k, _d in todo], bad
def admit_back(visitid, charges, before, vbefore=""):
    """After a save: is every admission date of `before` ({CPT: date}, admit_codes) still there? A date that is gone or changed is written back
    with the import's call (restore_admit) and read again. vbefore = the one visit-level date of a visit with no hospital code (it cannot be
    written back - said). Returns (words for the message, {CPT: date still lost} - empty when all is well). (The same function is in resave.py.)"""
    import xml.etree.ElementTree as ET
    if before:
        now = admit_codes(charges); lost = {k: x for k, x in before.items() if x and now.get(k) != x}
        if not lost: return "", {}
        codes, bad = restore_admit(visitid, charges, lost); now = admit_codes(charges); still = {k: x for k, x in lost.items() if now.get(k) != x}
        was = " / ".join(sorted(set(lost.values())))
    elif vbefore:
        now1 = admit_of(ET.fromstring(resave.detail(re.sub(r"\D", "", charges[0].get("id") or ""))).find(".//visit")) if charges else ""
        if now1 == vbefore: return "", {}
        codes, bad = restore_admit(visitid, charges, vbefore)
        now1 = admit_of(ET.fromstring(resave.detail(re.sub(r"\D", "", charges[0].get("id") or ""))).find(".//visit")) if charges else ""
        now = {"visit": now1}; lost = {"visit": vbefore}; still = {} if now1 == vbefore else dict(lost); was = vbefore
    else: return "", {}
    if not still: return ", admission date %s was lost on save and written back (%s)" % (was, ",".join(codes)), {}
    return ", admission date lost on save (was %s, now %s; written back for %s%s)" % (" / ".join(sorted(set(still.values()))), " / ".join(sorted(set(now.get(k) or "none" for k in still))),
        ",".join(codes) or "no hospital code", (", refused for " + ",".join(bad)) if bad else ""), still
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
# 11/10/2026 (round 7, 4.7 and 4.8) - a plan only the paid look-up (Stedi insurance discovery) found. The 11/9 skip read ONE benefit row's plan text and
# the payer name: the Cigna dental plan of chart 17478318 was added by the 11/5 run, before that skip existed, and its hospital claims bounced. Now
# the payer name, the practice's carrier name it maps to and the plan text of EVERY benefit row of the answer are read, and the answer must show the
# plan active on every date of service (its own plan dates).
# CLARIFICATION 11/10/2026 (~18:30Z): a Medicare Advantage plan WITH drug coverage ('Medicare Advantage Prescription Drug', MAPD, an HMO or PPO
# with Rx) is a MEDICAL plan and is added; only a STAND-ALONE drug plan (PDP, Part D only, 'Prescription Drug Plan' with no Advantage / HMO / PPO /
# medical word in the answer's own words) is skipped. Dental, vision and life plans are never medical (a 'Dental HMO' is still dental).
NOT_MEDICAL = r"DENTAL|VISION|\bLIFE\b|METLIFE|EYEMED|\bVSP\b"      # never a medical payer (METLIFE: a placeholder life/dental row, captured_calls, pat17478063)
DRUG_ONLY = r"PDP|PART D|PRESCRIPTION|PHARMACY|OPTUMRX|CAREMARK|EXPRESS SCRIPTS"      # a drug plan's words ...
MEDICAL_TOO = r"ADVANTAGE|\bMAPD\b|\bMA-PD\b|\bHMO\b|\bPPO\b|\bPFFS\b|SNP\b|MEDICAL"      # ... that do not count when the same words also name a medical plan (SNP: a special needs Advantage plan)
def not_medical(text, own=None):
    """The word that makes a plan NOT a medical payer, "" when it is one: a dental, vision or life word anywhere in `text`; a drug word in `text`
    only when no Advantage / MAPD / HMO / PPO / medical word is in the answer's own words (`own`, default `text`) - a Medicare Advantage plan with
    drug coverage is medical, a stand-alone drug plan is not (11/10/2026). TRICARE FOR LIFE is medical."""
    t = str(text or "").upper().replace("TRICARE FOR LIFE", "TRICARE"); o = t if own is None else str(own or "").upper()
    m = re.search(NOT_MEDICAL, t) or (re.search(DRUG_ONLY, t) if not re.search(MEDICAL_TOO, o) else None)
    return m.group(0) if m else ""
def ymd(dos):
    """A date of service as YYYYMMDD ("11/10/2026" or "2026-11-10" -> "20261110"); "" when it cannot be read."""
    m = re.match(r"\s*(\d{1,2})/(\d{1,2})/(\d{4})", str(dos or ""))
    if m: return "%s%02d%02d" % (m.group(3), int(m.group(1)), int(m.group(2)))
    x = re.sub(r"\D", "", str(dos or ""))
    return x[:8] if len(x) >= 8 and x[:2] in ("19", "20") else ""
def disc_window(it, raw):
    """(begin, end) YYYYMMDD of a look-up item's plan as its answer gives them (planDateInformation, else a benefit row's benefitsDateInformation
    'plan' range); "" where the answer gives none."""
    def d8(x):
        x = re.sub(r"\D", "", str(x or "")); return x[:8] if len(x) >= 8 else ""
    begin = end = ""
    for d in [it.get("dates")] + [b.get("benefitsDateInformation") for b in (raw.get("benefitsInformation") or []) if isinstance(b, dict)]:
        if not isinstance(d, dict): continue
        begin = begin or next((d8(d.get(k)) for k in ("planBegin", "eligibilityBegin", "policyEffective", "periodStart") if d8(d.get(k))), "")
        end = end or next((d8(d.get(k)) for k in ("planEnd", "eligibilityEnd", "policyExpiration", "periodEnd") if d8(d.get(k))), "")
        a_, sep, z_ = str(d.get("plan") or "").partition("-")
        begin = begin or d8(a_); end = end or (d8(z_) if sep else "")
    return begin, end
def disc_refusal(it, raw, code, dos8):
    """Why a look-up item that answered ACTIVE with a member id may NOT be added as a plan, "" when it may: a dental, vision, life or stand-alone
    drug plan (the payer name, the carrier name it maps to, or any benefit row's plan text says so - TRICARE FOR LIFE is medical, and so is a
    Medicare Advantage plan with drug coverage: its answer names Advantage, MAPD, an HMO or a PPO); a plan the answer does not show active on
    every date of service in dos8 (its plan begins after the earliest one, ends before the latest one, or the answer gives no begin date while
    the visits fall on more than one date - the look-up itself is dated to the latest)."""
    own = [it.get("payer") or "", it.get("plan") or ""] + [str(b.get("planCoverage") or "") for b in (raw.get("benefitsInformation") or []) if isinstance(b, dict)]
    words = own + [(CARRIERS.get(CODE2CAR.get(code)) or ["", ""])[1] if code else ""]      # the practice's carrier name counts for dental / vision / life / drug words, never as a medical word
    m = not_medical(" | ".join(str(w) for w in words), " | ".join(str(w) for w in own))
    if m: return "the answer or the carrier name says %s: a dental, vision, life or stand-alone drug plan is never a medical payer" % m.lower()
    if not dos8: return "no date of service could be read, so the answer cannot show the plan active on it"
    begin, end = disc_window(it, raw)      # the plan's own dates are compared, never written down: a placeholder row can carry the patient's birth date there
    late = [d for d in dos8 if begin and d < begin]; early = [d for d in dos8 if end and d > end]
    if late: return "not active on %s - the plan begins after it" % ", ".join(sorted(set(mdy8(d) for d in late)))
    if early: return "not active on %s - the plan ends before it" % ", ".join(sorted(set(mdy8(d) for d in early)))
    if not begin and len(set(dos8)) > 1: return "the answer gives no plan begin date, so it does not show the plan active on %s" % ", ".join(sorted(set(mdy8(d) for d in dos8[:-1] if d != dos8[-1])))
    return ""
def mdy8(d):
    """YYYYMMDD -> MM/DD/YYYY for the words William reads (dates of service only)."""
    return "%s/%s/%s" % (d[4:6], d[6:8], d[:4]) if len(d or "") == 8 else (d or "")
def disc_words(it, raw):
    """The look-up answer's own words for William: payer, plan text and status - no member id, no name, and no plan dates (a placeholder row can
    carry the patient's birth date as its plan dates)."""
    begin, end = disc_window(it, raw)
    return "%s '%s' %s (%s)" % (it.get("payer") or "?", it.get("plan") or "", it.get("status") or "?", "plan dates given" if (begin or end) else "no plan dates")
# 11/10/2026 (round 7, 4.4 and 4.6): HOLD is a label in this report, not a state in AdvancedMD - claimocity_inspector.py never reads it and 56 HELD
# visits on charts with a plan billed anyway. Every hold line says so, except a line that says NO CLAIM CAN BE MADE and every line of a chart held
# with NO plan whose visits were all entered with no plan (an EMPTY insurance order: there AdvancedMD makes no claim at all, and saying it "will still
# bill" would be false).
HELD = "HELD in this report only - AdvancedMD will still bill this visit to its insurance order at the next claim run unless someone stops it"
NO_CLAIM_END = "HELD in this report only - AdvancedMD makes no claim for this visit until it is saved again with its plan in place"
OLD_ORDER = "the claim goes out under the old order"      # the sentence for a no-charge line that could not be read (quality code, confirm review NH2-3) says it itself
def held(line, noclaim=False):
    """A hold line with the words of 4.6 at its end (once); a NO CLAIM CAN BE MADE line keeps its own ending; noclaim (a chart with no plan whose
    visits all have an empty insurance order) ends with the NO CLAIM words. The sentence for a no-charge line that could not be read keeps its own
    ending too: "the claim goes out under the old order ... unless William changes it" says the same thing in its own words."""
    return line if (HELD in line or NO_CLAIM_END in line or OLD_ORDER in line) else "%s - %s" % (line, NO_CLAIM_END if noclaim else HELD)
def order_hold(visit, order, m, info, qtag=None):
    """(the hold line, the register list it goes in) for a visit whose insurance order was not confirmed - in words that say what the visit's
    insurance-order LIST shows (4.4): empty -> NO CLAIM CAN BE MADE (no_order_list); another order -> it still bills to that old order
    (order_differs); billed -> its order was not changed (order_differs); not read -> order_unread; the order is right but the save lost a
    charge or the admission date -> save_problem. A visit that carries the quality / M0004 line keeps the words the import switches the code
    off on ("insorder not applied on <visit> (the visit carries ...)") in front."""
    lst = info.get("list_now"); why = re.sub(r"\s+", " ", str(m or ""))[:220]; w_ = "" if qtag else " (%s)" % why      # a quality-line visit already carries the answer in front
    if info.get("billed"):
        words, key = held("%s already billed - its order was not changed (it bills to its insurance order %s)%s" % (visit, lst or "?", w_)), "order_differs"
    elif lst is None:
        words, key = held("the insurance order of %s could not be read%s" % (visit, w_)), "order_unread"
    elif lst == "":
        words, key = "NO CLAIM CAN BE MADE on %s: its insurance order is empty%s%s - %s" % (visit, w_, (" - the save was sent and AdvancedMD still built no list: look at the plan at "
                     "sequence %s before anything is sent again" % order.split(",")[0]) if info.get("accepted") else "", NO_CLAIM_END), "no_order_list"
    elif lst != order:
        words, key = held("%s still bills to its old insurance order %s%s" % (visit, lst, w_)), "order_differs"
    elif info.get("admit_lost") and not info.get("sent"):      # an earlier save of this batch lost the admission date: held until it reads back
        words, key = held("%s bills to insurance order %s, but its admission date was lost on an earlier save and still does not read back - a person writes it back (the import's call) before the claim run%s" % (visit, lst, w_)), "save_problem"
    else:
        words, key = held("%s bills to insurance order %s, but %s%s" % (visit, lst, "the save did not read back as asked" if info.get("sent") else "nothing was sent: the visit's charges do not read as the import entered them", w_)), ("save_problem" if info.get("sent") else "")
    return (("insorder not applied on %s%s - " % (visit, qtag(m))) if qtag else "") + words, key
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
        # 11/10/2026 (round 7): a chart an earlier run of THIS batch released (record version 3 or 4) is not checked again - the records are per
        # batch, and an old batch's stuck visits are saved only by feed_order_sweep.py --resave with the owner's approved file
        if not only and pid in prev and prev[pid].get("decision") == "RELEASE" and prev[pid].get("v") in (3, 4): continue
        if n >= limit: break
        n += 1
        num = re.sub(r"\D", "", pid)
        rec = {"v": 4, "visits": [v["visit"] for v in visits], "dos": sorted({v["dos"] for v in visits}), "cpts": sorted({c for v in visits for c in v["cpts"]}), "checks": [], "fixes": [], "hold": []}
        rec["admit_lost"] = dict((prev.get(pid) or {}).get("admit_lost") or {}) if (prev.get(pid) or {}).get("v") == 4 else {}      # kept until each date reads back
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
            answered = [p for p in openp if status.get(p["id"]) in ("ACTIVE", "INACTIVE", "REJECTED")]      # a free check the payer really answered
            if lead is None and not rec["hold"] and openp and not answered:
                # 11/10/2026 (round 7, 4.8): every free check of this chart errored (11/6: no free check answered and 23 charts went to the paid
                # look-up) - nothing is bought; the chart waits for a night when the free check answers
                rec["hold"].append("free check down - not checked tonight: none of this chart's %d free eligibility check(s) answered (%s), so no paid look-up was bought" % (
                    len(openp), ", ".join("%s %s" % (code_of[p["id"]], status.get(p["id"]) or "?") for p in openp)))
            if lead is None and not rec["hold"]:
                if use_stedi:
                    msg = PARSED.get(visits[0]["feed_id"], {})
                    last, _, first = msg.get("name", "").partition(","); first = first.strip().split(" ")[0] if first else ""; last = last.strip()
                    try:
                        # 11/10/2026 (round 7, 4.7): the look-up is dated to the chart's latest date of service (the captured shape with dateOfService), and a
                        # plan it alone found is added only when it is a MEDICAL plan the answer shows active on EVERY date of service of the chart's visits
                        dos8 = sorted(x for x in (ymd(v["dos"]) for v in visits) if x)
                        raw = stedi.disc(first, last, msg.get("dob", "")[:8], "FL", dos=dos8[-1] if dos8 else None)
                        ds = stedi.disc_summ(raw); rec["discovery"] = ds
                        raws = [x if isinstance(x, dict) else {} for x in ((raw.get("items") or []) if isinstance(raw, dict) else [])]
                        refused = []
                        for i_, it in enumerate(ds.get("items") or []):
                            if not (it.get("status") or "").upper().startswith("ACTIVE") or not it.get("member"): continue
                            code = map_payer(it.get("payer"), STEDI_NAME_MAP)
                            why = disc_refusal(it, raws[i_] if i_ < len(raws) else {}, code, dos8)      # 11/9/2026: a 'CIGNA Dental Health / Dental HMO' hit had insured chart 17478318
                            if why: refused.append("%s - %s" % (disc_words(it, raws[i_] if i_ < len(raws) else {}), why)); continue
                            if code and any(code_of[p["id"]] == code for p in plans):
                                rec["fixes"].append("discovery found %s but the chart already carries a %s plan (status %s) - not re-added" % (code, code, [status.get(p["id"]) for p in plans if code_of[p["id"]] == code])); continue
                            if code and code in CODE2CAR:
                                insid, seq = add_ins.add(num, CODE2CAR[code], it["member"])
                                rec["fixes"].append("discovery: added %s plan -> %s seq %s" % (code, insid, seq)); stats["plans added"] += 1
                                if insid and str(insid).startswith("ins"):
                                    ok, m2 = ins_update._set_order(num, {p["id"]: p for p in elig_amd.plans(num)[1]}, insid, str(seq)); rec["fixes"].append("chart order -> %s: %s" % (seq, m2[:100]))
                                    lead = {"id": insid, "sequence": str(seq)}; code_of[insid] = code; reason = "Stedi discovery %s ACTIVE" % code; status[insid] = "ACTIVE"
                                break
                        if lead is None and refused:      # worded without "discovery found [": the hand step claimocity_fixholds.py would buy the look-up again and add it
                            rec["hold"].append("no active plan: the look-up's answer was not added - for William: %s" % "; ".join(refused)[:700])
                        elif lead is None: rec["hold"].append("no active plan: discovery found %s" % ([(i.get("payer"), i.get("status")) for i in ds.get("items") or []] or "nothing"))
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
                # 4. apply to the visits - 11/10/2026 (round 7): EVERY visit goes through fast_set_insorder, which reads the visit's insurance-order
                # LIST and sends the save only when the list (or the attribute) is not the order. The old shortcut ("the import copied the chart's
                # default order, so nothing to resave") and the attribute-only check released visits whose list was empty: never billed, on no work list.
                # Only this version's 'applied' entries are trusted (an older entry trusted the attribute).
                old = prev.get(pid) or {}
                applied = (old.get("applied") or {}) if old.get("v") == 4 else {}; rec["applied"] = dict(applied)
                lost_before = (old.get("admit_lost") or {}) if old.get("v") == 4 else {}      # admission dates an earlier run of this batch lost on its save: held until they read back
                stop_chart = ""      # SAVE NOT AS ASKED on a visit of this chart (a charge or an admission date lost): its other visits are not saved - William looks first
                for v in visits:
                    if applied.get(v["visit"]) == order: continue
                    if stop_chart:
                        rec.setdefault("order_unread", []).append(v["visit"])
                        rec["hold"].append(held("the insurance order of %s was not read or saved: the save of %s on this chart did not read back as asked (a charge or the admission date was lost) - the rest of this chart waits for William" % (v["visit"], stop_chart))); continue
                    if lost_before.get(v["visit"]): v = dict(v, admit_lost_before=lost_before[v["visit"]])
                    cid = v["charges"][0] if v.get("charges") else None
                    if not cid:      # nothing to read: the order cannot be confirmed - the chart is held (it used to pass silently)
                        rec["fixes"].append("%s: no charge id recorded" % v["visit"]); rec.setdefault("order_unread", []).append(v["visit"])
                        rec["hold"].append(held("the insurance order of %s could not be read (the import register holds no charge id for it)" % v["visit"])); continue
                    # 11/10/2026: a visit that carries the no-charge quality line and whose order cannot be set says so in the words the import
                    # looks for ("insorder not applied on <visit>" with the line named) - the import then switches the code off until William looks
                    qtag = (lambda w: " (the visit carries the quality line %s: %s)" % (v.get("quality_charge"), w[:120])) if (v.get("quality_codes") and v.get("quality_charge")) else None
                    if v.get("mvp_codes") and v.get("mvp_charge"):      # the option code's line too: the same words, naming both lines
                        qtag = lambda w: " (the visit carries the quality line %s and the M0004 line %s: %s)" % (v.get("quality_charge") or "-", v.get("mvp_charge"), w[:120])
                    try:
                        removed = []; info = {}; ok, m = fast_set_insorder(v, order, removed, info)
                        rec["fixes"].append("%s insorder %s: %s" % (v["visit"], order, m))      # the whole answer (4.3): "already ..., list [..] - nothing sent" or "insorder A -> B, list [..] -> [..], ..."
                        if info.get("sent") and info.get("accepted"): rec.setdefault("saved", []).append(v["visit"])      # a save AdvancedMD accepted (the digest's "orders changed")
                        if removed and [e.get("code") for e in removed] == ["1123F"]: rec.setdefault("quality_removed", []).extend(removed); rec["fixes"].append("%s: the quality line %s was taken off - the echo with it was refused, the echo without it was accepted (William 11/10/2026: a reporting line never holds a visit)" % (v["visit"], v.get("quality_charge")))
                        elif removed: rec.setdefault("quality_removed", []).extend(removed); rec["fixes"].append("%s: the no-charge line(s) %s were taken off - the echo with them was refused, the echo without them was accepted (William 11/10/2026: a reporting line never holds a visit)" % (v["visit"], ", ".join("%s %s" % (e.get("code"), e.get("charge")) for e in removed)))
                        if ok: rec["applied"][v["visit"]] = order
                        else:      # HOLD - never RELEASE - in words that say what the visit's list shows (4.4)
                            line, key = order_hold(v["visit"], order, m, info, qtag); rec["hold"].append(line)
                            if key: rec.setdefault(key, []).append(v["visit"])
                            # first in the list, so the Holds line of the report shows it whole (confirm review NH2-3). Where it meets round 7: the old
                            # order a claim goes out under is the visit's own LIST when it was read (else the chart's order, as before); a visit whose
                            # list is EMPTY gets no such sentence - no claim goes out for it, and its hold line above says NO CLAIM CAN BE MADE
                            if qtag and "could not be read in three tries" in m and info.get("list_now") != "":
                                rec["hold"].insert(0, "the order of %s was NOT set because its no-charge quality line could not be read (three tries) - the claim goes out under the old order %s unless William changes it" % (v["visit"], info.get("list_now") or rec.get("insorder") or "?"))
                        if info.get("admit_lost"): rec["admit_lost"][v["visit"]] = info["admit_lost"]      # remembered: the next run of this batch holds it until the date reads back
                        elif ok: rec["admit_lost"].pop(v["visit"], None)
                        if info.get("sent") and (info.get("admit_lost") or info.get("dropped") or info.get("added")): stop_chart = v["visit"]
                    except Exception as e:      # what was read before the error stands; once the save may have landed, the list counts as not read
                        ie = dict(info); ie["list_now"] = None if ie.get("sent") else ie.get("list_now")
                        line, key = order_hold(v["visit"], order, "error %s" % str(e)[:100], ie, qtag); rec["hold"].append(line)
                        if key: rec.setdefault(key, []).append(v["visit"])
                        if ie.get("sent"): stop_chart = v["visit"]
                    time.sleep(0.4)
            if feed_codes and lead is not None and code_of[lead["id"]] not in feed_codes:
                rec["note"] = "feed IN1 says %s, chart bills %s first (%s)" % (feed_codes, code_of[lead["id"]], reason)
            if rec["hold"] and lead is None and not openp:      # 11/10/2026 (4.5): its visits were entered with insorder "1" and NO list - a plan alone does not build it
                rec["hold"].append("no open plan on this chart: each visit of this chart must be saved again after a plan is added (%s) - a visit entered with no plan has an empty insurance order until then" % " ".join(rec["visits"]))
            # a chart with no open plan whose visits were all entered with no plan (the chart never had one, or the import says so for each visit):
            # their insurance order is empty, so AdvancedMD makes NO claim - its hold lines end with those words, never "will still bill"
            noclaim = lead is None and not openp and (not plans or all(r_.get("open_plans_at_entry") == 0 or r_.get("chart_insorder") == "" for r_ in visits))
            rec["hold"] = [held(h, noclaim) for h in rec["hold"]]      # 11/10/2026 (4.6): every hold line says HOLD stops nothing in AdvancedMD
            rec["decision"] = "HOLD" if rec["hold"] else "RELEASE"
            stats[rec["decision"]] += 1
            print(rec["decision"], pid, rec.get("order"), rec.get("lead", {}).get("code"), "|", reason[:60], "| feed", feed_codes, "|", "; ".join(h.replace(" - " + HELD, "").replace(" - " + NO_CLAIM_END, "") for h in rec["hold"])[:140], "| HELD in this report only" if rec["hold"] else "")
        except Exception as e:
            rec["decision"] = "HOLD"; rec["hold"] = [held(h) for h in rec["hold"]] + [held("verify error %s" % str(e)[:160])]; stats["error"] += 1; print("ERR", pid, str(e)[:160])
        if not rec.get("admit_lost"): rec.pop("admit_lost", None)
        out[pid] = rec
        json.dump({k: v for k, v in out.items() if k not in prev or v is not prev.get(k)} if OUTF != ("feed_verify_%s.json" % STAMP) else out, open(OUTF, "w"), indent=1)
        if n % 25 == 0: print("progress", n, dict(stats))
    print("DONE", dict(stats))
if __name__ == "__main__": main()
