# PLAIN ENGLISH (Full-visit resave)
# Decides: How to save a visit back to AMD safely: fetch the whole visit, echo every charge, then reinspect and approve.
# Rules it uses: Never save a visit from one charge's detail - AMD voids the charges you leave out. Cleans 01/01/1900 dates out of the claim fields.
#   11/10/2026: set_insorder reads the visit's insurance-order LIST (not only the attribute), never saves a visit already billed (except for the two
#   re-route helpers, which pass allow_billed=True), and puts back an admission date the save wiped (the import's own call, per hospital code) - or
#   says "admission date lost on save".
#   11/11/2026 (round 8, the echo guard): set_insorder never sends a save when the visit's charges could not all be read. This helper finds a
#   visit's charges in the chart's transaction history, page by page (visit_charges). A history page that FAILS brings no charge row, and that
#   used to be taken for "no more charges": the list of live charges came back short or EMPTY without a word - and a full-visit save that leaves
#   a live charge out VOIDS it (9/3/2026). Not known to have happened; closed before the 84 never-billed feed visits are saved. visit_charges
#   still returns exactly what it returned before, to every caller, and raises nothing new; beside its answer it now records in READ_NOTE why
#   the charges may not all have been read (a failed history page, a history longer than the 700 rows it reads, a live charge missing from its
#   own detail). set_insorder answers "visit <id>: nothing sent - ..." - for a dry run too - when that note is not empty, when no live charge
#   was read, or when the charge it was asked for is not among the live charges read. feed_order_sweep.py does the same before its own save
#   and its own clinician move.
#   A KNOWN, OLDER GAP, left open on purpose in this round: every OTHER helper that calls visit_charges (move_to_ins.move, freq1_visit.run,
#   recode, the insurance check's own save in claimocity_verify.py, the inspector step, the hand helpers) does not look at that note yet and
#   still saves what it read. The list of those helpers (written 11/11/2026) is the proposal for a later hardening.
# Never touches: Balances or insurance order on its own; callers pass those in.
# ---
"""Resave + reinspect + approve a visit, echoing detail attrs (proven pattern 8/29)."""
import amd, re, sys
import xml.etree.ElementTree as ET

def detail(chargeid):
    return amd.post(amd.msg('getchargedetaildataicd10','demographics',{'chargeid':str(chargeid),'nocookie':'1'}))

CHG_FIELDS = ["respparty","begindate","enddate","diagcodes","modcodes","aging","billins",
              "proccode","cobcode","pos","tos","units","netfee","fee","allowed",
              "patportion","insportion","patbalance","insbalance","finclasscode","lineitemnote"]

def _extins_xml(vis, hospfrom):
    """Echo the visit's full extins attr set, overriding hospitalizationfrom only."""
    base = {"id": "", "hospitalizationto": "", "unabletoworkfrom": "", "unabletoworkto": "",
            "datesimilarsymptom": "", "dateofinjury": "", "otheraccident": "0", "emergency": "0",
            "employment": "0", "outsidelab": "0", "payprov": "1", "patsignature": "1", "epsdt": "0",
            "accidentstate": "", "autoaccident": "0", "datelastseen": "", "resubmissioncode": "",
            "origrefnum": ""}
    e = vis.find("extins")
    if e is not None:
        for k, v in e.attrib.items():
            base[k] = v
    base["hospitalizationfrom"] = hospfrom
    return "<extins %s/>" % " ".join('%s="%s"' % (k, v) for k, v in base.items())

def resave(anychargeid, batchid, hospfrom=None, extra_charge_xml=""):
    x = detail(anychargeid)
    root = ET.fromstring(x)
    pat = root.find(".//patient")
    vis = root.find(".//visit")
    charges = vis.findall(".//charge")
    chg_xml = ""
    for c in charges:
        attrs = {"id": c.get("id")}
        for f in CHG_FIELDS:
            v = c.get(f)
            if v is not None: attrs[f] = v
        a = " ".join('%s="%s"' % (k, v) for k, v in attrs.items())
        chg_xml += "<charge %s/>" % a
    vattrs = {"id": vis.get("id"), "date": vis.get("date"), "profile": vis.get("profile"),
              "insorder": vis.get("insorder"), "refplan": vis.get("refplan"),
              "facility": vis.get("facility"), "force": "1"}
    va = " ".join('%s="%s"' % (k, v) for k, v in vattrs.items() if v is not None)
    body = amd.msg("updvisitwithnewcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"),
         "approval": "1", "inspectorenabled": "1", "batchid": str(batchid),
         "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        '<visit %s><chargelist>%s%s</chargelist>%s</visit>' % (
            va, chg_xml, extra_charge_xml,
            _extins_xml(vis, hospfrom) if hospfrom else ""))
    return amd.post(body)

if __name__ == "__main__":
    hf = sys.argv[3] if len(sys.argv) > 3 else None
    print(resave(sys.argv[1], sys.argv[2], hf)[:3000])

READ_NOTE = ""      # 11/11/2026 (round 8): beside visit_charges's answer - why the visit's live charges may NOT all have been read; "" = nothing to say
def _fault_text(root):
    """The words of a Fault in a parsed AdvancedMD answer, on one line, at most 120 characters; None when the answer carries no Fault.
    The test is an ELEMENT named Fault anywhere in the answer - never the letters "Fault" in the answer's text: a name, a memo or a
    building's name can hold those letters in a perfectly good answer (the test `"Fault" in answer` would call that answer failed), and the
    empty <Error /> that every good answer carries is not a fault either."""
    f = next((e for e in root.iter() if e.tag == "Fault" or (isinstance(e.tag, str) and e.tag.endswith("}Fault"))), None)
    if f is None: return None
    return (" ".join(" ".join(f.itertext()).split()) or "no words in it")[:120]

def visit_charges(chargeid):
    """ALL live charges of the visit that owns `chargeid` (getchargedetaildataicd10 returns only ONE charge, and a
    resave that omits a sibling VOIDS it — learned the hard way 9/3/2026).  Returns (visit_elem, patient_elem,
    [charge_elem...]) with each charge element taken from its own detail call.
    11/11/2026 (round 8): the answer, the calls and what is raised are exactly as before - for every caller. Beside the answer, READ_NOTE
    (set to "" at the start of every call) holds the FIRST reason why the visit's live charges may not all have been read:
      a. a history page (gettxhistory) came back with a Fault: it brings no charge row, so until now it was taken for "no more charges";
      b. page 7, the last page this helper reads, was still full: the chart's history is longer than the 700 charge rows read (the longest
         history on any chart had 400 charge rows on 11/11/2026);
      c. a charge the history lists as live on this visit is not in its own detail answer (until now it was dropped without a word).
    The note names the call and the page or the charge first, then the visit and the chart, and the fault's own words last. Only set_insorder
    (below) and feed_order_sweep.py read it; every other caller still gets a short list without a word - a known, older gap. A caller that
    puts a function of its own in this one's place (the self-tests do) keeps working: whoever reads the note sets it to "" itself before it
    calls."""
    global READ_NOTE
    READ_NOTE = ""
    import xml.etree.ElementTree as ET, re
    x = detail(chargeid); root = ET.fromstring(x)
    vis = root.find(".//visit"); pat = root.find(".//patient")
    vid = re.sub(r"\D", "", vis.get("id")); pid = re.sub(r"\D", "", pat.get("id"))
    # gettxhistory is paginated (100 charges/page): page until no new charges, or an old visit on a high-volume patient
    # is invisible and a resave/move would report "charge not live" (found 9/11/2026 on the insurances cleaning task).
    ids = []; seen = set()
    for page in range(1, 8):
        body = amd.msg('gettxhistory', 'demographics', {'patientid': pid, 'filterhistory': '0', 'pagenumber': str(page), 'typefilter': '0', 'sortbypayment': 'false', 'groupbyvisit': '0', 'sortdescending': '1', 'visitid': '0', 'profileid': '', 'getmemo': 'false', 'nocookie': '1'})
        th = ET.fromstring(amd.post(body, timeout=120))
        flt = _fault_text(th)      # a. (11/11/2026) a page that failed is NOTED - the loop itself goes on exactly as before (a page with no charge row ends it)
        if flt is not None and not READ_NOTE: READ_NOTE = "gettxhistory page %d for visit %s of chart %s answered a Fault, so the chart's charges were not all listed: %s" % (page, vis.get("id"), pat.get("id"), flt)
        new = 0
        for c in th.iter("charge"):
            if c.get("id") in seen: continue
            seen.add(c.get("id")); new += 1
            if c.get("visit") == vid and c.get("void") != "1" and not (c.get("fee") or "").startswith("-"): ids.append(c.get("id"))
        if new == 0 or new < 100: break
    else:      # b. (11/11/2026) the loop ran out of pages: page 7 was still full, so the history goes on beyond what was read
        if not READ_NOTE: READ_NOTE = "gettxhistory page 7 for visit %s of chart %s was still full: the chart's history is longer than the 700 charge rows this helper reads" % (vis.get("id"), pat.get("id"))
    charges = []
    for cid in ids:
        r = ET.fromstring(detail(cid))
        c = [e for e in r.iter("charge") if e.get("id") == "charge" + cid]
        if c and c[0].get("void") != "1": charges.append(c[0])
        elif not c and not READ_NOTE:      # c. (11/11/2026) the history lists it as live on this visit, its own detail answer does not hold it: left out as before, and NOTED
            flt = _fault_text(r); READ_NOTE = "getchargedetaildataicd10 of charge %s for visit %s of chart %s did not return that charge, which the history lists as live%s" % (cid, vis.get("id"), pat.get("id"), (": " + flt) if flt else "")
    return vis, pat, charges

DATE_ATTRS = {"hospitalizationfrom", "hospitalizationto", "unabletoworkfrom", "unabletoworkto", "datesimilarsymptom", "dateofinjury", "datelastseen", "datelmp", "dateofsymptom"}
def clean_extins(attrs):
    """NEVER send an empty/space date attribute on updextrainsinfo: AMD stores it as 01/01/1900 and the claim rejects.
    Omit blank or 1900 date attrs (omission clears them).  Learned 9/4/2026 on Tillotson."""
    return {k: v for k, v in attrs.items() if not (k in DATE_ATTRS and (not str(v).strip() or "1900" in str(v)))}


# 11/10/2026 (round 7): a feed visit entered while its chart had NO plan keeps insorder "1" but AdvancedMD builds NO insurance-order LIST for
# it - and a claim is built from the list. Such a visit never bills and shows on no work list (84 visits, $18,802 on 11/10/2026). The
# attribute alone proves nothing: these helpers read the list, the bill state and the admission date from the charge detail.
def order_list(vis):
    """The visit's insurance-order LIST as AdvancedMD built it: the plan sequences of visit/insuranceorderlist/insuranceorder in ordinal
    order, joined like the insorder attribute ("1", "4,2"); "" when the list is empty. (The same function is in claimocity_verify.py.)"""
    rows = vis.findall("insuranceorderlist/insuranceorder") if vis is not None else []
    def ordinal(o):
        try: return int(o.get("ordinal") or 0)
        except ValueError: return 0
    return ",".join((o.get("sequence") or "").strip() for o in sorted(rows, key=ordinal))

def billed_reasons(charges):
    """Why a visit counts as already billed, read from its live charges' own detail: a bill date, an insurance bill (insbilled 1 or an insbill
    row) or a payment that is not void (any amount). [] = never billed. A billed visit is never saved by the order helpers (11/10/2026)."""
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
    """The admission date of each hospital procedure code of the visit (11/10/2026, round 7): {CPT: "MM/DD/YYYY" or ""} for every live charge
    whose code is a hospital code, each read from that charge's OWN detail (its code from the detail's procedure list, the date from that
    detail's extins). The practice writes the date once per hospital code (updextrainsinfo per CPT), so a visit of 99497 + 99223 is judged by
    its 99223, whichever of the two charges comes first. {} = no hospital code."""
    out = {}
    for c in charges:
        d = ET.fromstring(detail(re.sub(r"\D", "", c.get("id") or "")))
        cpt = {x.get("id"): x.get("code") for x in d.findall(".//proccodelist/proccode") if x.get("id")}.get(c.get("proccode"), "")
        if cpt in HOSP_CODES and not out.get(cpt): out[cpt] = admit_of(d.find(".//visit"))
    return out

def restore_admit(visitid, charges, admit):
    """Write the admission date back after a save wiped or changed it - the import's proven call, unchanged (claimocity_import.py, the lines
    that write hospitalizationfrom): updextrainsinfo per hospital procedure code. admit = one date for every hospital code of the visit's live
    charges (each charge's code read from its own detail), or {CPT: date} = only those codes, each with its own date. Returns (codes written,
    faults)."""
    if isinstance(admit, dict): todo = [(k, v) for k, v in sorted(admit.items()) if v]
    else:
        todo = []
        for c in charges:
            pm = {x.get("id"): x.get("code") for x in ET.fromstring(detail(re.sub(r"\D", "", c.get("id") or ""))).findall(".//proccodelist/proccode") if x.get("id")}
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
    with the import's call (restore_admit) and read again. vbefore = the one visit-level date of a visit with no hospital code (as before
    11/10/2026: it cannot be written back - said). Returns (words for the message, {CPT: date still lost} - empty when all is well)."""
    if before:
        now = admit_codes(charges); lost = {k: v for k, v in before.items() if v and now.get(k) != v}
        if not lost: return "", {}
        codes, bad = restore_admit(visitid, charges, lost); now = admit_codes(charges); still = {k: v for k, v in lost.items() if now.get(k) != v}
        was = " / ".join(sorted(set(lost.values())))
    elif vbefore:
        now1 = admit_of(ET.fromstring(detail(re.sub(r"\D", "", charges[0].get("id") or ""))).find(".//visit")) if charges else ""
        if now1 == vbefore: return "", {}
        codes, bad = restore_admit(visitid, charges, vbefore)
        now1 = admit_of(ET.fromstring(detail(re.sub(r"\D", "", charges[0].get("id") or ""))).find(".//visit")) if charges else ""
        now = {"visit": now1}; lost = {"visit": vbefore}; still = {} if now1 == vbefore else dict(lost); was = vbefore
    else: return "", {}
    if not still: return ", admission date %s was lost on save and written back (%s)" % (was, ",".join(codes)), {}
    return ", admission date lost on save (was %s, now %s; written back for %s%s)" % (" / ".join(sorted(set(still.values()))), " / ".join(sorted(set(now.get(k) or "none" for k in still))),
        ",".join(codes) or "no hospital code", (", refused for " + ",".join(bad)) if bad else ""), still

def set_insorder(chargeid, order, dry=False, allow_billed=False):
    """Visit insurance order by a FULL-VISIT echo - NO rebill (William 10/6/2026: one frequency-1 rebill per visit; the
    rebill is freq1_visit.run's job, never move_to_ins's). Echoes every live charge with CHG_FIELDS (omitting one voids
    it), force=1 and the new insorder. Returns (ok, message): ok is False on a Fault or when the re-read does not show the
    order - the caller must not rebill.
    11/10/2026 (round 7) - what it decides now:
      - skipped ONLY when the insorder attribute AND the visit's insurance-order LIST both equal the order (an attribute "1" over an empty
        list was skipped before, and such a visit never billed);
      - never saves a visit that is already billed (a bill date, an insurance bill or a payment on any live charge): "already billed - not
        saved" - EXCEPT for the two helpers whose job is to re-route an ALREADY-BILLED visit after a wrong-payer denial: freq1_visit.reroute
        (William 10/6/2026; run nightly by the insurance cascade and the billing button) and the MSP Unbilled fix (unbilled_msp_1109_0639.py)
        pass allow_billed=True and keep their own checks (the specification's correction of 11/10/2026). Every other caller - the insurance
        check, feed_order_sweep.py, the hand helpers - keeps the guard;
      - for every caller: echoes every live charge of the visit (visit_charges) and after the save reads back the attribute, the list, every
        echoed charge still live and nothing new, and the admission date of each hospital code (admit_codes - each from its charge's own
        detail): a wiped or changed admission date is written back with the import's proven call and read again; still wrong -> not ok,
        "admission date lost on save". An error after the save was sent (no answer) is not raised: the visit is read again, a lost admission
        date is written back, and the answer is not ok, with what the visit reads now. The message carries the list before and after.
    11/11/2026 (round 8, the echo guard) - NOTHING IS SENT WHEN THE VISIT'S CHARGES COULD NOT ALL BE READ. The save sends the whole visit
    back, and a live charge left out of it is voided - so the list of live charges must be complete. After the first read, and after the
    "already as asked - resave skipped" answer (unchanged: it is decided from the asked charge's own detail, and nothing is sent on that
    path, so a visit already right is still "skipped", note or no note), the answer is (False, "visit <id>: nothing sent - ...") - before
    the billed guard, for a dry run too, with nothing more read and nothing sent - when:
      - visit_charges left a note (READ_NOTE: a history page failed, the history is longer than the pages read, or a live charge is
        missing from its own detail);
      - or no live charge was read (a save with an empty charge list would void every charge of the visit);
      - or the charge it was asked for is not among the live charges read (the digits of the ids are compared; move_to_ins.move already
        has this guard: "charge not live on visit").
    That message never begins with the word "resave": feed_order_sweep.py reads an answer that begins "resave " as "a save went out". It
    is an answer, never an error: the caller leaves the visit as it is and reads it again later.
    After the save, a read-back that could not read all the visit's charges proves nothing: the visit is read again ("the read-back after
    the save could not read all the visit's charges ... - read again: ..."), and the answer is not ok; when that read is incomplete too:
    "... the visit could not be read again ... - look at it in AdvancedMD before anything else is sent" - the same as a read-back that fails.
    Never touches: balances, plans, the chart's default order, the charges' codes, places of service or amounts (echoed as read)."""
    import time
    global READ_NOTE
    order = str(order).replace(" ", "")
    READ_NOTE = ""      # 11/11/2026: set here before every read of this function - a stand-in for visit_charges (the self-tests', or a helper's own) never touches the note
    vis, pat, allc = visit_charges(re.sub(r"\D", "", str(chargeid))); note = READ_NOTE
    before = order_list(vis)
    if (vis.get("insorder") or "").replace(" ", "") == order and before == order:
        return True, "visit %s insorder already %s, list [%s] - resave skipped" % (vis.get("id"), order, before)
    asked = re.sub(r"\D", "", str(chargeid)); got = [re.sub(r"\D", "", c.get("id") or "") for c in allc]      # 11/11/2026 (round 8): the echo guard - see the docstring
    if note or not allc or asked not in got:
        which = ("AdvancedMD did not return all of this visit's charges (%d live charge(s) read)" % len(allc) if note else "no live charge of this visit was read (0 read)" if not allc else
                 "charge %s, the one asked for, is not among the %d live charge(s) read (%s)" % (asked, len(allc), ",".join(got)))
        return False, "visit %s: nothing sent - %s. A full-visit save that leaves a live charge out voids that charge: read the visit again before anything is sent (insorder %s, list [%s], asked %s)%s" % (
            vis.get("id"), which, vis.get("insorder"), before, order, (" - " + note) if note else "")
    billed = billed_reasons(allc)
    if billed and not allow_billed:
        return False, "visit %s already billed - not saved (%s on a live charge; insorder %s, list [%s], asked %s): a billed visit is saved only by the re-route helpers after a wrong-payer denial (allow_billed) or on the owner's word" % (
            vis.get("id"), ", ".join(billed), vis.get("insorder"), before, order)
    adm0 = admit_codes(allc); vadm0 = "" if adm0 else admit_of(vis)      # before the save: the admission date of each hospital code (a visit with none: its one date)
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va["insorder"] = order
    if dry:
        return True, "DRY resave %s insorder %s -> %s, list [%s] (%d live charges echoed)" % (vis.get("id"), vis.get("insorder"), order, before, len(allc))
    sent = [c.get("id") for c in allc]
    def after_error(why):      # the save may have landed: read the visit again, put a lost admission date back, say what it reads now - never raise
        global READ_NOTE
        try:
            READ_NOTE = ""
            v3, p3, c3 = visit_charges(re.sub(r"\D", "", str(chargeid)))
            if READ_NOTE:      # 11/11/2026: this read is not complete either - the same last answer as a read that fails
                return False, "resave %s: %s, and the visit could not be read again (%s) - look at it in AdvancedMD before anything else is sent - NOT as asked" % (vis.get("id"), why, "not all of its charges came back: " + READ_NOTE)
            adm3, _still = admit_back(v3.get("id") or vis.get("id"), c3, adm0, vadm0)
            live3 = [c.get("id") for c in c3]
            return False, "resave %s: %s - read again: insorder %s, list [%s] -> [%s], %d live charges (was %d)%s%s - NOT as asked" % (vis.get("id"), why, v3.get("insorder"), before,
                order_list(v3), len(c3), len(allc), (", no longer live: " + ",".join(x for x in sent if x not in live3)) if [x for x in sent if x not in live3] else "", adm3)
        except Exception as e2:
            return False, "resave %s: %s, and the visit could not be read again (%s) - look at it in AdvancedMD before anything else is sent - NOT as asked" % (vis.get("id"), why, type(e2).__name__)
    try:
        r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1",
                     "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                     "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    except Exception as e:
        return after_error("the answer to the save never came back (%s: %s)" % (type(e).__name__, str(e)[:80]))
    time.sleep(0.8)
    if "Fault" in r:
        return False, "resave FAULT visit %s: %s" % (vis.get("id"), re.sub(r"\s+", " ", r[:400]))
    try:
        READ_NOTE = ""
        v2, p2, c2 = visit_charges(re.sub(r"\D", "", str(chargeid)))
        if READ_NOTE: return after_error("the read-back after the save could not read all the visit's charges (%s)" % READ_NOTE)      # 11/11/2026: an incomplete read-back proves nothing - read again, as after a read-back that fails
        after = order_list(v2); live = [c.get("id") for c in c2]
        gone = [x for x in sent if x not in live]; new = [x for x in live if x not in sent]
        adm, still = admit_back(v2.get("id") or vis.get("id"), c2, adm0, vadm0)      # a wiped or changed admission date: written back (the import's call) and read again
    except Exception as e:
        return after_error("the read-back after the save failed (%s: %s)" % (type(e).__name__, str(e)[:80]))
    ok = (v2.get("insorder") or "").replace(" ", "") == order and after == order and not gone and not new and not still
    return ok, "resave %s insorder %s -> %s, list [%s] -> [%s], %d live charges (was %d)%s%s%s%s" % (vis.get("id"), vis.get("insorder"), v2.get("insorder"),
        before, after, len(c2), len(allc), (", no longer live: " + ",".join(gone)) if gone else "", (", new: " + ",".join(new)) if new else "", adm, "" if ok else " - NOT as asked")
