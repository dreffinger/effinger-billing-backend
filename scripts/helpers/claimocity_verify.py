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
#      11/25/2026 (William: "correct every one that comes to the correct date of birth and insurance and fix them ... where we know the correct dob but claimocity sends
#      the wrong one or the 01011900 default date"): the paid look-up is asked with the CHART's own name and birth date - taken from the chart answer this step already
#      holds, no extra call - whenever the chart's birth date is a real one; else with the feed's, as before; never a mix of the two. Until that day it was asked with the
#      FEED's name and birth date, so a visit on a chart whose birth date had been corrected from a face sheet was looked up under the wrong date, missed, and was held
#      "no active plan: discovery found nothing". The chart's record says which one was asked ("lookup_asked", and behind the hold's own words whenever the two dates are
#      not the same) - by the kind of slip, never with a name or a date. See lookup_who.
#      11/25/2026, the review of that change (a chart whose birth date was FAR from the feed's - a chart the patient map sends the patient to with no check, it may be
#      another person's - was looked up, insured and its visit released as the chart's own person; a look-up with no real birth date at all was bought by name alone and
#      its answer added): the paid look-up is bought only for a chart that is KNOWN to be the feed's patient, and only with a real birth date to ask with. Known = the
#      chart carries this patient's Claimocity id (its additional number); or the two real birth dates are the same and at least one of the two names is; or the feed's
#      name is the chart's (the owner's full-name rule) and the dates are not far apart (a slip, or one side has none). Anything else: NOTHING is bought and NOTHING is
#      added on this step's own word - the chart is held "same person? ..." for William (record key same_person = its visits; worded so that the hand step
#      claimocity_fixholds.py adds nothing either). No real birth date on either side: nothing is bought - held "no active plan: no paid look-up was bought - ... (face
#      sheet needed)" (record key no_birth_date). William's answer for a run: --same-person <charts>. Another first name under the same date is not held; it is SAID, like
#      every other difference, on the "discovery: added" line the digest prints. A chart that could not be read is asked as before, and the words say it could not be
#      read - never that it has no birth date. See lookup_hold.
#      11/25/2026, the SECOND review of this part (each finding was reproduced before it was changed):
#      (a) KNOWN ALSO MEANS PROVEN BY A NUMBER. The hold fired on a chart the identity rule itself had matched by a Social Security or member number while the two birth
#      dates were far apart - William's own case ("we know the correct dob but claimocity sends the wrong one") - so he was asked about a chart the rule had proof for.
#      Now the numbers are weighed the rule's own way (feed_identity.evidence - the file beside this helper): the chart's Social Security number and its plans'
#      subscriber numbers, from the chart answer this step already holds, against PID-19 and the member number of each IN1 row in the feed's RAW files (FEED_HL7_DIR,
#      else hl7/<stamp>/). The parsed message carries neither number; they are read into memory only, never written, never printed. The same nine-digit Social Security
#      number, or a member number in common, frees the chart as its Claimocity id does - where the chart's name is a name candidate of the feed's (the same last name,
#      the first three letters of the first name: the rule's rule 4 goes no further) and, for a member number since round 2 of this review (below), only where the two
#      birth dates agree. Under any other name a number in common frees nobody - a member number can be a
#      whole family's - and the hold says it is there. The last four alone free nobody; two DIFFERENT Social Security numbers free nobody whatever else is in common,
#      and are said. A plan the feed's OWN steps put on the chart - the intake, this step's look-up, the hand step: the registers say which - is never weighed: its
#      number came from the feed itself and proves nothing about whose chart it is. Without feed_identity.py beside this helper, or without the raw files, no number
#      proves anything and the hold stands as it did. See identity_rule, feed_numbers, feed_added_plans, number_proof.
#      (b) EVERY MESSAGE OF A CLAIMOCITY ID IS JUDGED - until then only the last one parsed, so a patient sent once with the chart's own birth date and once with a
#      wrong one was held, or not, by the order of the two messages. The patient is the chart's when ANY of its messages says so. Where the batch carries two
#      DIFFERENT real birth dates for one id and the chart carries none of its own, nobody knows which of the two to ask with: "no birth date" - face sheet
#      needed, nothing bought. See lookup_judge.
#      (c) THE FEED PATIENTS OF ONE CHART ARE COMPARED WITH EACH OTHER. Two feed patients of one name whose real birth dates are far apart both fit a same-name chart
#      that carries NO birth date; this step bought one look-up with the first one's date, added that plan and released both visits. On a chart with no birth date of
#      its own such a pair is held "same person? ..." - nothing bought, nothing added. See lookup_apart.
#      (d) THE RECORD SAYS WHO IS IN DOUBT: same_person = the visits of the feed patients in doubt (until then every visit of the chart), same_person_ids = their
#      Claimocity ids, and the hold names both. A visit released on William's word says so also when the chart's own person is listed first.
#      (e) A PLAN ADVANCEDMD REFUSES IS NOT "ADDED": the line reads "discovery: the <carrier> plan the look-up found was NOT added - AdvancedMD refused it", it is not
#      counted under plans added, and AdvancedMD's own answer - it can name a member number or a patient - stays in this workspace's record under "discovery", which
#      the digest step never copies.
#      (f) WILLIAM'S STANDING WORD IS READ STRICTLY AND NEVER DROPPED WITHOUT A WORD (registers/feed_same_person.json): a key counts only when it is exactly one chart,
#      approved_by only in his own form (William, the day, alone or with (board) or (chat) behind it); an id in another case or with a blank beside it is still his
#      id, two ids in one text are two ids, a chart named twice keeps both lists - and ONE printed line, which begins SAME PERSON FILE:, names every entry that does
#      not count. See same_person_yes, same_person_gaps, said_yes.
#      11/25/2026, ROUND 2 of that review (what the independent checkers of its fixes found; each was reproduced before it was changed):
#      A MEMBER NUMBER PROVES THE CHART ONLY WITH BIRTH DATES THAT AGREE. A family shares member numbers, and the identity rule's rule 4 puts a relative's visit on
#      the chart that carries the number - a husband's chart for his wife (her first name begins with his), a father's for his son of the same name. The 'same
#      person?' hold was the one place William was asked; with (a) it no longer fired: a look-up was bought about the CHART's person, his plan was added and her
#      visit was released on his chart. Now a member number in common proves the chart only where BOTH sides carry a real birth date and the two are the same or a
#      slip apart (the identity rule's own slips: one digit, two digits swapped, month and day swapped, one day apart). With the dates far apart, or a date missing
#      on either side, it proves nothing: the hold stays, SAYS that a plan of the chart carries a member number Claimocity sent, and William is asked - once per
#      chart, his yes is kept in his standing file. The nine-digit Social Security number, the Claimocity id on the chart and his word free a chart as before.
#      Where several feed patients of one chart are in doubt the hold's words are the first one's; what the numbers say about each further one is said behind
#      that one's visits ("Claimocity id <id> (<visits>; a plan of the chart carries a member number Claimocity sent)"). See lookup_hold.
#      THE RECORD SAYS WHICH 'NO BIRTH DATE' IT IS - record key no_birth_date_case, a fixed word: "neither side" (neither Claimocity nor the chart carries a real
#      birth date) or "two dates" (Claimocity sent two different real birth dates for a patient of the chart and the chart carries none of its own - (b) above).
#      The digest's line for the record key no_birth_date said 'neither Claimocity nor the chart carries a real birth date' of both; of the second that was untrue,
#      and it has a line of its own now. On a chart with a patient of each kind the record, the hold and lookup_asked say "two dates".
#      11/26/2026, ROUND 3 (identity rule 2026-11-26.5 - a relative is not the patient; reproduced by the round-2 checker, and here, before it was changed):
#      A NAME THAT IS ALIKE BUT NOT THE SAME IS HELD LIKE ANY OTHER NAME. 'The feed's name is the chart's' meant a full-name candidate of the identity rule, and that
#      was also a first name that only BEGINS with the chart's (four letters or more) and the chart's name with another suffix: a wife under a first name that begins
#      with her husband's, a son of his father's name with JR. With a birth date missing on one side - the year-1900 placeholder - or a slip between the two, such a
#      relative was asked about under the CHART's person without a hold: a look-up bought about him, his plan added, her visit released on his chart. Now the same name
#      is the same first word and no other suffix (the suffix: JR, SR, II, III, IV or V as the last word of the last name or as any word after the first word of the
#      first name - since round 4 a lone V right behind the first word is a middle initial); a middle initial or a second first name does not matter. A name that is only alike is held 'same person?' - the hold says "... and the names are
#      alike but not the same", never 'the names differ' of a father and his son of one first name - and the words about whom was asked say "the names are alike but
#      not the same" in the place of 'the first names differ'. With the same real birth date such a name is asked as before (a name candidate with the same date);
#      the Claimocity id on the chart, the Social Security number, a member number with birth dates that agree, and William's word free it as they free any other
#      chart. William's own case - the chart's very own name sent with the placeholder - is asked about without a question, as before. See _name_kind, lookup_hold.
#      11/26/2026, ROUND 4 (identity rule 2026-11-26.6 - the identity check's two medium findings on round 3):
#      THE WHOLE FIRST NAME IS COMPARED AND A LONE V BEHIND THE FIRST NAME IS A MIDDLE INITIAL. lookup_who was handed the first WORD of the feed's first name only,
#      so the same name with JR (or another suffix) behind the first name on both sides read '... the names are alike but not the same' in lookup_asked and in the
#      line 'discovery: added ...', and a suffix on the feed's side only read as nothing: it is handed the whole first name now, compares the names with it, and asks
#      with its first word. And a lone V right behind the first word of the first name (MARY V) is a middle initial, not the suffix V - MARY and MARY V are the same
#      name, never held 'same person? ... alike but not the same' for it (V stays a suffix behind the last name and behind a middle name or initial: ROBERT A V).
#      See _name_kind, lookup_who.
#   6. the feed's IN1 payers are mapped and reported next to the chart (the 271 decides, the feed only informs).
# Writes feed_verify_1028.json (+ registers copy). AMD writes: visit insorder resaves; addinsurance only from discovery; updextrainsinfo only to put
# back an admission date a resave wiped (11/10/2026). Never: a save on a billed visit, a rebill, a void (except the no-charge line left out above).
# Usage: python3 feed_verify_1028.py [--no-stedi] [--limit N] [--only patNNN,...] [--same-person patNNN,...]
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
# 11/9/2026 (1:39 PM ET run): discovery items whose plan/payer text says DENTAL / VISION / LIFE are skipped like Part D - a Cigna Dental HMO hit had insured chart 17478318 and its hospital claims bounced 'not eligible'.
import amd, elig_amd, stedi, add_ins, ins_update, resave, re, json, sys, os, time, collections
# (11/25/2026, the second verification of the death check: this step no longer names a cache file of its own - deceased_cache_local.json. The guard keeps ONE cache,
# the workspace's registers/deceased_cache.json, and carries every day the old file holds into it: what the feed learns, the check before approvals knows.)
import deceased_guard
REG = json.load(open(("registers/feed_import_%s.json" % STAMP)))
PARSED = {m["pid"]: m for m in json.load(open(("feed_parsed_%s.json" % STAMP)))}
CARRIERS = json.load(open("carriers_rich.json"))            # carN -> [code, name]
CODE2CAR = {v[0]: k for k, v in CARRIERS.items()}
MSGS = collections.defaultdict(list)      # 11/25/2026 (the second review): EVERY parsed message of a Claimocity id, in the file's order - PARSED keeps only the last one, and 'same person?' was judged by that one alone
for _m in json.load(open(("feed_parsed_%s.json" % STAMP))): MSGS[_m["pid"]].append(_m)
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
    charge or the admission date -> save_problem. A visit that carries the quality / M0004 line keeps the words the import starts probing on
    (the visit itself is for a person; 11/12/2026: the code never switches itself off) ("insorder not applied on <visit> (the visit carries ...)") in front."""
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
# ---- William 11/25/2026 ("correct every one that comes to the correct date of birth and insurance and fix them figure our how to do this for other charts that have the
# same mistake where we know the correct dob but claimocity sends the wrong one or the 01011900 default date") - WHOM THE PAID LOOK-UP IS ASKED ABOUT ---------------------
# The feed sends some patients with a WRONG birth date (an old one ten days off, a year twenty years off) or with the year-1900 placeholder, although the chart their visits
# sit on holds the right one - corrected from a face sheet. This step asked Stedi's insurance discovery with the FEED's name and birth date - a look-up under a date the
# chart itself no longer carries: it found nothing, nothing was added, and the chart was held "no active plan: discovery found nothing". After the match the chart is the
# patient: lookup_who takes the name and the birth date from the chart answer main() already holds (elig_amd.plans gives the patient's own attributes with the plans - no
# extra call) and falls back to the feed's only when the chart's birth date is not a real one. What it says goes into registers and reports, so its words carry no name and
# no date.
# WHEN IT IS NOT ASKED (11/25/2026, the review of the first version of this change - two findings, each reproduced by a second reviewer). "After the match the chart is the
# patient" is not always true: a Claimocity id the patient map knows goes to its chart with no check, and the old resolve rule put a patient on the single same-name chart
# whatever its birth date. For such a chart - another person's - the first version asked the look-up about the CHART's person, added that person's plan and released the
# FEED patient's visit as a clean claim (before, the feed patient's own plan landed on it: a name and date mismatch a payer can refuse). And with no real birth date on
# either side the look-up was bought with a name and the placeholder, and its answer added. So lookup_hold judges first, and main() buys nothing and adds nothing when it
# holds: 'same_person' - nobody knows that the chart is the feed's patient (two real dates FAR apart; or the date differs or is missing AND the name is not the chart's;
# or only the date is the same and both names are others) and the chart's answer does not show the patient's Claimocity id; 'no_birth_date' - no real birth date on
# either side. The hold for 'same_person' carries none of the phrases the hand step claimocity_fixholds.py acts on ("no active plan", "discovery found [") - that step
# would put the FEED patient's plans on a chart that may be another person's; the hold for 'no_birth_date' starts "no active plan" like every chart that waits for a
# face sheet. William's answer is given to a run as --same-person <charts>; a chart that carries the Claimocity id needs none. Only a chart whose answer shows a patient
# is judged: one that could not be read (no name and no birth-date attribute in the answer) is asked as before, and lookup_who says it could not be read. (The older
# self-test tools/selftest/test_feed_order.py answers such a chart, with a feed message that has no date either, and expects the look-up bought - no real chart answers so.)
# _real_dob, _slip and _name_kind are the owner's rule as scripts/helpers/feed_identity.py states it (real_dob, slip, name_kind) - private copies here; the same text
# stands in feed_in1_intake.py (and _real_dob, _slip in claimocity_import.py), and tools/selftest/test_pos_rule.py checks that they read the same. They are NOT drop-in
# equal to that module: _slip answers in this helper's own shorter words ("one digit", "two digits swapped" - there "one digit differs", "two neighbouring digits
# swapped") and answers "far" where slip answers ""; _real_dob answers False for a today that is no date (real_dob raises) and for a date with blanks around it (real_dob
# strips them; nothing here hands one over). The words are in registers and in the digest's own list, so point these at the module only through that word map.
# _dob8, _name_kind, _same_id, lookup_hold and lookup_who stand, the same text, in feed_in1_intake.py (its Florida Medicaid check).
# SINCE THE SECOND REVIEW (11/25/2026 - the header's (a) to (f) say what was found): a chart is ALSO known to be the feed's patient when a NUMBER proves it - the same
# nine-digit Social Security number on both sides, or a member number of the feed's insurance rows on one of the chart's plans (number_proof: the identity rule's own
# reading, taken from feed_identity.py beside this helper by identity_rule; the feed's numbers come from the raw files by feed_numbers, into memory only) and the chart's
# name is a name candidate of the feed's, as the rule's rule 4 asks. The last four alone free nobody, a number under another name frees nobody (the hold says it is
# there), a plan the feed's own steps added is never weighed (feed_added_plans), and two different Social Security numbers free nobody whatever else is in common. A
# feed patient is judged with EVERY message of its Claimocity id (lookup_judge), and on a chart that carries no birth date of its own the feed patients are compared
# with each other (lookup_apart). William's standing word is asked through said_yes; what does not count in his file is named by same_person_gaps. All of these - with
# _show_id, _yes_entries and same_person_yes - stand, the same text, in feed_in1_intake.py, and tools/selftest/test_pos_rule.py holds the two copies together letter
# for letter.
# SINCE ROUND 2 OF THAT REVIEW (11/25/2026): a MEMBER number in common is such a proof only where both sides carry a real birth date and the two are the same or a slip
# apart (_slip) - a family shares member numbers, and the chart that carries the number may be the husband's or the father's. With the dates far apart, or a date
# missing on either side, the hold stands and its words say the number is there (lookup_hold). The Social Security number is weighed as before.
def _real_dob(d8, today8):
    """True when d8 is a REAL birth date (the owner's rule): 8 digits, a real calendar date, the year 1901 or later, not after today8 and not more than 120 years before
    it. Anything else - empty, the year-1900 placeholder, zeros, a day that does not exist - is NO BIRTH DATE. (The rule of real_dob in feed_identity.py.)"""
    d8 = str(d8 if d8 is not None else ""); today8 = str(today8 if today8 is not None else "")
    if not re.fullmatch(r"[0-9]{8}", d8) or not re.fullmatch(r"[0-9]{8}", today8) or d8[:4] < "1901": return False
    try: __import__("datetime").date(int(d8[:4]), int(d8[4:6]), int(d8[6:8]))
    except ValueError: return False
    return "%04d%s" % (int(today8[:4]) - 120, today8[4:]) <= d8 <= today8
def _slip(a8, b8):
    """How two REAL birth dates differ (the owner's rule) - the kind of slip, the first that fits: "one digit" (one digit differs), "two digits swapped" (two neighbouring
    digits swapped), "month and day swapped" (MMDD read as DDMM), "one day apart"; anything else is "far". "" when the two are the same date. (The rule of slip in
    feed_identity.py, in this helper's own shorter words; there far is the empty answer.)"""
    a8, b8 = str(a8), str(b8)
    if a8 == b8: return ""
    if len(a8) != 8 or len(b8) != 8: return "far"
    diff = [i for i in range(8) if a8[i] != b8[i]]
    if len(diff) == 1: return "one digit"
    if len(diff) == 2 and diff[1] == diff[0] + 1 and a8[diff[0]] == b8[diff[1]] and a8[diff[1]] == b8[diff[0]]: return "two digits swapped"
    if a8[:4] == b8[:4] and a8[4:6] == b8[6:8] and a8[6:8] == b8[4:6]: return "month and day swapped"
    try:
        day = __import__("datetime").date
        if abs((day(int(a8[:4]), int(a8[4:6]), int(a8[6:8])) - day(int(b8[:4]), int(b8[4:6]), int(b8[6:8]))).days) == 1: return "one day apart"
    except ValueError: pass
    return "far"
def _dob8(s):
    """A birth date as AdvancedMD writes it (MM/DD/YYYY, with or without leading zeros or a time behind it), as the feed writes it (YYYYMMDD, or longer with a time) or
    with dashes (YYYY-MM-DD) -> the 8 digits YYYYMMDD; "" for anything that cannot be read that way. It reads the shape only: whether the date is a REAL one is _real_dob's."""
    s = str(s if s is not None else "").strip(); m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)
    if m: return "%s%02d%02d" % (m.group(3), int(m.group(1)), int(m.group(2)))
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m: return "".join(m.groups())
    x = re.sub(r"\D", "", s)
    return x[:8] if len(x) >= 8 else ""
def _name_kind(feed_last, feed_first, chart_last, chart_first, alike=False):
    """What a chart's name is to the feed's (the owner's rule for names, identity rule 2026-11-26.5): "full" - the SAME name: the same last name, the same first WORD of the
    first name (a middle initial or a second first name behind it does not matter) and the same suffix, or none; "name" - the same last name and the first names share their
    first three letters; "surname" - the same last name under another first name (or none); "" - another last name, or none. Last names are compared in upper case, letters
    only, without a trailing suffix word (JR, SR, II, III, IV, V); an accent is not a difference. The suffix of a name is one of those six words as the last word of the last
    name or as any word after the first word of the first name - but a lone V right behind the first word of the first name is a middle initial, not the suffix V (identity
    rule 2026-11-26.6: MARY V is MARY with an initial; V stays a suffix behind the last name and behind a middle name or initial). A name that is ALIKE BUT NOT THE SAME - the first word of one first name only begins the other's, or the two
    are one word and the suffixes differ (also when only one side carries one) - is "name" (until that version it was "full": a wife under a first name that begins with her
    husband's, a son of his father's name with JR); asked for it (alike=True) such a name is "alike", so that a hold can say what is true of it. (The rule of name_kind in
    feed_identity.py.)"""
    ud = __import__("unicodedata"); up = lambda s: "".join(c for c in ud.normalize("NFKD", str(s if s is not None else "")) if not ud.combining(c)).upper()
    sfx = ("JR", "SR", "II", "III", "IV", "V"); words = lambda s: re.findall(r"[A-Z]+", up(s))
    def key(s):
        w = words(s)
        return "".join(w[:-1] if len(w) > 1 and w[-1] in sfx else w)
    def suffix(last, first):      # the suffix words a name carries: the last word of the last name, any word after the first word of the first name - a lone V right behind the first word is a middle initial (identity rule .6)
        fw = [re.sub(r"[^A-Z]", "", x) for x in up(first).split()[1:]]; fw = fw[1:] if fw[:1] == ["V"] else fw
        return {w for w in (words(last)[-1:] if len(words(last)) > 1 else []) + fw if w in sfx}
    k = key(feed_last)
    if not k or k != key(chart_last): return ""
    a, b = re.sub(r"[^A-Z]", "", up(feed_first)), re.sub(r"[^A-Z]", "", up(chart_first))
    if not a or not b or a[:3] != b[:3]: return "surname"
    wa, wb = (re.sub(r"[^A-Z]", "", (up(x).split() or [""])[0]) for x in (feed_first, chart_first))
    if wa and wb and wa == wb and suffix(feed_last, feed_first) == suffix(chart_last, chart_first): return "full"
    return "alike" if alike and wa and wb and (wa.startswith(wb) or wb.startswith(wa)) else "name"
def _same_id(a, b):
    """True when a chart's additional number is this patient's Claimocity id: equal as upper-case letters and digits, and eight characters or more (the feed step and the
    old integration write the id there; an empty or short value is never one). (The evidence 'mrn' of feed_identity.py.)"""
    x, y = (re.sub(r"[^A-Z0-9]", "", str(v if v is not None else "").upper()) for v in (a, b))
    return len(x) >= 8 and x == y
def _show_id(i):
    """A Claimocity id as a printed line or a register may show it: its 24 hex characters - or fixed words in its place, because an id of another shape could be anything
    a sender typed. (show_id of feed_identity.py.)"""
    s = str(i if i is not None else "")
    return s if re.fullmatch(r"[0-9A-Fa-f]{24}", s) else "(an id that is not 24 hex characters)"
def identity_rule():
    """The identity rule's own module - feed_identity.py in the folder THIS helper stands in (the driver and the runbook copy the two together) - loaded for its reading
    of the numbers only (evidence, in1_member). None when the file is not there, is another file of that name or cannot be loaded: then no number proves anything and
    every hold stands as it did. Nothing is added to the loaded modules. It never raises."""
    try:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feed_identity.py")
        if not os.path.isfile(p): return None
        iu = __import__("importlib.util").util; sp = iu.spec_from_file_location("feed_identity_beside", p); m = iu.module_from_spec(sp); sp.loader.exec_module(m)
        return m if all(callable(getattr(m, n, None)) for n in ("evidence", "in1_member")) else None
    except Exception: return None
def feed_numbers(folder, fi):
    """The feed's own Social Security and member numbers, by Claimocity id, from the RAW feed files of a folder (every file in it and under it; or the one file named):
    {id: {"ssn": [PID-19 as it was sent], "members": [the member number of each IN1 row - IN1-49, else IN1-36: fi.in1_member, the identity rule's reading]}}. The
    parsed feed message (feed_parsed_<stamp>.json) carries NEITHER number - the parse step leaves PID-19 out on purpose and keeps only the payer NAMES of the IN1 rows -
    so they are read here the way claimocity_match.py reads them: into memory only, never written, never printed. An id stands under PID-3 as it was sent and under its
    first component. fi = the identity rule's module (identity_rule); {} without it or without the folder, and a file that cannot be read is passed over: then no number
    proves anything. It never raises."""
    out = {}
    try:
        if fi is None or not folder or not os.path.exists(str(folder)): return out
        paths = [str(folder)] if os.path.isfile(str(folder)) else [os.path.join(d, f) for d, _s, fs in sorted(os.walk(str(folder))) for f in sorted(fs)]
    except Exception: return out
    for p in paths:
        try:
            cur = ()
            for line in open(p, errors="replace").read().replace("\r", "\n").split("\n"):
                s = line.split("|"); t = s[0].strip()
                if t == "MSH": cur = ()      # a message without a PID line never takes the numbers of the message before it
                elif t == "PID":
                    cur = tuple(k for k in dict.fromkeys((s[3], s[3].split("^")[0].strip()) if len(s) > 3 else ()) if k)
                    for k in cur:
                        e = out.setdefault(k, {"ssn": [], "members": []})
                        if len(s) > 19 and s[19].strip() and s[19] not in e["ssn"]: e["ssn"].append(s[19])
                elif t == "IN1" and cur:
                    n = fi.in1_member(s)
                    for k in cur:
                        if n and n not in out[k]["members"]: out[k]["members"].append(n)
        except Exception: continue
    return out
def feed_added_plans(folder="registers"):
    """The plans the feed's OWN steps put on each chart - {chart number: {plan ids}} - or None when nobody can say. A plan of the chart is proof by member number only
    when its number did not come from the feed itself: the intake adds a plan with the feed's own insurance row, and until 11/25/2026 the paid look-up was asked with the
    feed's name and birth date - so on a chart the patient map sends a feed patient to, such a plan carries that feed patient's number whoever the chart belongs to,
    and proves nothing about the chart (on 11/25/2026 the repository's registers listed about a hundred such plans). Read from the registers every bootstrapped workspace holds:
    feed_in1_intake.json (the intake - "ins" of each entry "<chart>|<carrier>"), feed_verify_<stamp>.json in the workspace and in the registers folder (the paid
    look-up - "discovery: added <carrier> plan -> ins123 ..."), feed_fixholds_<stamp>.json (the hand step - "added <carrier> seq 1 (ins123) ..."). A plan made with a
    NEW chart is not listed: that chart carries its patient's Claimocity id. A register that is not there adds nothing; one that cannot be read means nobody can say
    which plans the feed added: None - and then no member number proves anything in this run (number_proof). It never raises."""
    out = {}
    try:
        files = [os.path.join(folder, x) for x in (sorted(os.listdir(folder)) if os.path.isdir(folder) else []) if x == "feed_in1_intake.json" or (x.startswith(("feed_verify_", "feed_fixholds_")) and x.endswith(".json"))]
        files += [x for x in sorted(os.listdir(".")) if x.startswith("feed_verify_") and x.endswith(".json")]
        for f in files:
            with open(f) as fh: d = json.load(fh)
            for k, v in d.items():
                m = re.fullmatch(r"(?:pat)?0*([0-9]+)(?:\|.*)?", str(k))
                if not m or not isinstance(v, dict): continue
                ids = [v.get("ins")] + [i for x in (v.get("fixes") if isinstance(v.get("fixes"), list) else []) for i in re.findall(r"^(?:discovery: added \S+ plan -> |added \S+ seq \S+ \()(ins[0-9]+)", str(x))]
                out.setdefault(m.group(1), set()).update(i for i in ids if isinstance(i, str) and re.fullmatch(r"ins[0-9]+", i))
    except Exception: return None
    return out
def number_proof(fi, nums, pa, plans, own=None):
    """What the NUMBERS say about a chart and a feed patient, in ONE fixed word - the identity rule's own reading (fi.evidence; fi = feed_identity.py beside this helper,
    None when it is not there): "ssn" - the feed and the chart carry the same nine-digit Social Security number; "member" - a member number of the feed's insurance rows
    is the subscriber number of one of the chart's plans, open or ended; "contra" - the two sides carry two DIFFERENT Social Security numbers: proof of two people,
    whatever else they have in common; "" - nothing: no number on one side, only the last four in common (the weakest evidence frees nobody here), or no module.
    nums = the feed's own numbers for this Claimocity id ({"ssn": [...], "members": [...]} - feed_numbers), pa = the chart's own patient attributes (its ssn), plans =
    the chart's plan rows (id, subscribernum), own = the plan ids the feed's own steps added to this chart (feed_added_plans): such a plan is never weighed - its
    number came from the feed itself; None = nobody can say which plans those are, and then NO member number is weighed (the Social Security number still is).
    It works on the numbers and gives back the word only. It never raises: what cannot be weighed proves nothing."""
    try:
        if fi is None or not isinstance(nums, dict) or not isinstance(pa, dict): return ""
        subs = [] if own is None else [p.get("subscribernum") for p in (plans or []) if isinstance(p, dict) and p.get("subscribernum") and p.get("id") not in own]
        ev, contra = fi.evidence({"ssn": nums.get("ssn"), "members": nums.get("members")}, {"ssn": pa.get("ssn"), "members": subs})
        return "contra" if contra else "ssn" if "ssn" in ev else "member" if "member" in ev else ""
    except Exception: return ""
def lookup_hold(pa, first, last, dob8, fid="", today8=None, sure=False, proof="", apart=False):
    """Why a paid look-up of a chart is NOT asked - (key, words) - or ("", words) when it is asked (lookup_who says with what). pa = the chart's own patient attributes
    (name "LAST,FIRST ...", dob MM/DD/YYYY, additionalmrn when the answer carries it); first, last, dob8 = what the feed carries (first = the whole first name or its
    first word); fid = the patient's Claimocity id; sure = William's word that the chart is this patient; proof = what the NUMBERS say (number_proof: "ssn", "member",
    "contra" or ""); apart = another feed patient with a visit on this chart carries a birth date far from this one's (lookup_apart). The rule (11/25/2026, the review):
      "same_person" - nobody knows that the chart is the feed's patient: the two real birth dates are FAR apart; or they are a slip apart, or one side (or each) has no
          real one, AND the feed's name is not the chart's ("full" by _name_kind); or only the birth date is the same and BOTH names are others; or - the second review -
          the patient fits the chart by the name alone and stands apart from another feed patient of it. Not held when the chart carries the patient's Claimocity id
          (_same_id), when a number proves it, or on William's word - the second value then says which ("" when there was nothing to doubt). A number proves it the
          way the identity rule's rule 4 does (the second review: William was asked about a chart the rule itself had matched by the number): proof "ssn" or "member"
          AND a chart whose name is a name candidate of the feed's - the same last name and the first three letters of the first name ("name" or "full" by
          _name_kind). Under any other name a number in common frees nobody (a member number can be a whole family's) - the hold says it is there, for William.
          A MEMBER number proves it only with birth dates that AGREE (round 2 of that review: a husband's chart was freed for his wife and a father's for his son
          of the same name - a family shares member numbers): BOTH sides carry a real birth date and the two are the same or a slip apart. With the dates far
          apart, or a date missing on either side, it proves nothing: the hold stands and says the number is there. The Social Security number proves as before.
          Two DIFFERENT Social Security numbers (proof "contra") free nobody and are said behind the words, held or asked.
          Identity rule 2026-11-26.5 (a relative is not the patient): 'the chart's name' is the SAME name only - the same first word, no other suffix. A name that is
          ALIKE BUT NOT THE SAME (a first name that begins with the chart's, the chart's name with JR) is held like any other name, and the words say what is true of
          it: "... and the names are alike but not the same" - until then such a relative was asked about under the chart's person whenever a birth date was missing
          on one side or the two were a slip apart.
      "no_birth_date" - the chart is the patient, but neither side carries a real birth date: there is nothing to ask with (face sheet needed).
    A chart answer that shows no patient at all (neither a name nor a birth-date attribute - a read that failed) is not judged: ("", ""), the look-up is asked as before.
    The words are fixed - no name, no date, no number. It never raises: a comparison that cannot be made is held ("same_person")."""
    try:
        today8 = today8 or __import__("datetime").date.today().strftime("%Y%m%d"); a = pa if isinstance(pa, dict) else {}
        if "name" not in a and "dob" not in a: return "", ""
        cl, _, cf = __import__("html").unescape(str(a.get("name") or "")).partition(",")
        c8 = _dob8(a.get("dob")); f8 = _dob8(dob8); cr = _real_dob(c8, today8); fr = _real_dob(f8, today8); kind = _name_kind(last, first, cl, cf, alike=True)
        names = " and the names are alike but not the same" if kind == "alike" else " and the names differ"      # (identity rule .5) what is true of the two names: a father and his son of one first name do not 'differ' by it
        if cr and fr and c8 == f8: why = "" if (kind or _name_kind("X", first, "X", cf) == "full") else "only the birth date is the same - both names differ"
        elif cr and fr and _slip(f8, c8) == "far": why = "Claimocity's birth date and this chart's are far apart"
        elif kind == "full": why = ""
        else: why = ("Claimocity's birth date is a slip from this chart's" if cr and fr else "one side carries no birth date" if cr or fr else "no birth date on either side") + names
        if apart and not why: why = "another Claimocity patient on this chart carries a birth date far from this one's and the chart carries none"
        known = _same_id(a.get("additionalmrn"), fid)
        proven = kind in ("name", "alike", "full") and (proof == "ssn" or (proof == "member" and cr and fr and _slip(f8, c8) != "far"))      # (round 2) a member number: only where both birth dates are real and the same or a slip apart
        num = "the chart and Claimocity carry the same Social Security number" if proof == "ssn" else "a plan of the chart carries a member number Claimocity sent" if proof == "member" else ""
        two = "the chart and Claimocity carry two different Social Security numbers" if proof == "contra" else ""
        if why and not (known or proven or sure): return "same_person", "same person? %s, and the chart's answer does not show this patient's Claimocity id%s" % (why, ("; " + (num or two)) if (num or two) else "")
        if not (cr or fr): return "no_birth_date", "neither Claimocity nor the chart carries a real birth date to ask with (face sheet needed)"
        how = "" if not why else "the chart carries this patient's Claimocity id" if known else num if proven else "William's word: same person"
        return "", "; ".join(x for x in (how, two) if x)
    except Exception:
        return "same_person", "same person? the chart's name and birth date could not be compared with Claimocity's"
def lookup_judge(pa, msgs, fid="", today8=None, sure=False, proof="", apart=False):
    """lookup_hold for ONE feed patient, asked with EVERY message a batch carries for its Claimocity id - (key, words, the message to ask with). msgs = [(first name, last
    name, birth date YYYYMMDD), ...]. 11/25/2026, the second review: one message was kept per id - the last one parsed - so a patient sent once with the chart's own birth
    date and once with a wrong one was held, or not, by the ORDER of the two messages. Now the patient is the chart's when ANY of its messages says so (the identity
    rule's way: a real date of the batch that is the chart's is enough); it is held 'same person?' only when NO message fits the chart, and 'no birth date' only when
    none of them can be asked with. Where the batch carries a real birth date for the id, that date stands for every message of it - again the rule's way: a message
    sent with the placeholder, or with no date, never counts as 'no birth date' beside a real one. The message to ask with is chosen by what it carries, never by its
    place in the file: the chart's own birth date before another real date, then by date and name; None when the patient is held 'same person?'. Two DIFFERENT real
    birth dates under one id are said behind the words; when the chart carries no real date of its own nobody knows which of the two to ask with - 'no birth date'
    (face sheet needed), as the identity rule writes a new chart with neither of them. apart = lookup_apart found this patient apart from another feed patient of the
    chart: handed on to lookup_hold for every message. It never raises: what cannot be judged is held ('same_person')."""
    try:
        today8 = today8 or __import__("datetime").date.today().strftime("%Y%m%d"); a = pa if isinstance(pa, dict) else {}
        ms = sorted({tuple(str(x if x is not None else "") for x in (f, l, d)) for f, l, d in msgs}) or [("", "", "")]
        c8 = _dob8(a.get("dob")); real = sorted({_dob8(m[2]) for m in ms if _real_dob(_dob8(m[2]), today8)})
        if real: ms = sorted({(m[0], m[1], d) for m in ms for d in real})
        res = sorted(((lookup_hold(a, m[0], m[1], m[2], fid, today8, sure, proof, apart), m) for m in ms), key=lambda r: (0 if real and r[1][2] == c8 else 1, r[1]))
        ok = [r for r in res if not r[0][0]]; none = [r for r in res if r[0][0] == "no_birth_date"]
        if ok and len(real) > 1 and ("name" in a or "dob" in a) and not _real_dob(c8, today8):
            return "no_birth_date", "Claimocity sent two different birth dates for this patient and the chart carries none of its own - nobody knows which to ask with (face sheet needed)", ok[0][1]
        if ok: return "", "; ".join(x for x in (ok[0][0][1], "Claimocity sent two different birth dates for this patient" if len(real) > 1 else "") if x), ok[0][1]
        if none: return none[0][0][0], none[0][0][1], none[0][1]
        return res[0][0][0], res[0][0][1], None
    except Exception:
        return "same_person", "same person? the chart's name and birth date could not be compared with Claimocity's", None
def lookup_apart(pa, pats, today8=None):
    """The feed patients of ONE chart compared with EACH OTHER -> the positions in pats that stand APART from another one. pats = the messages of each feed patient with
    a visit on the chart, [[(first name, last name, birth date YYYYMMDD), ...], ...]. 11/25/2026, the second review: two feed patients of one name whose real birth
    dates are far apart were both put on the one same-name chart that carries NO birth date - each fits such a chart by the name alone - and the insurance check bought
    ONE look-up with the first one's date, added that plan and released both visits. Apart is a patient who carries a real birth date beside another feed patient of
    the chart whose real birth date is FAR from it - neither the same nor a slip. Only a chart that shows a patient and carries NO real birth date of its own is looked
    at: where the chart has one, lookup_hold has judged every patient against it. What it means is lookup_hold's (its apart): a patient who stands apart and is tied to
    the chart by no more than the name is held 'same person?'; one the chart is tied to - its Claimocity id, the same Social Security number, William's word - is
    asked, and the words say which (a member number ties nobody to a chart that carries no birth date: round 2 of that review). So two such patients are both held,
    and one beside a patient the chart is tied to is held alone. It never raises: when the comparison cannot be made every patient stands apart."""
    try:
        today8 = today8 or __import__("datetime").date.today().strftime("%Y%m%d"); a = pa if isinstance(pa, dict) else {}
        if ("name" not in a and "dob" not in a) or _real_dob(_dob8(a.get("dob")), today8): return set()
        real = [sorted({_dob8(m[2]) for m in ms if _real_dob(_dob8(m[2]), today8)}) for ms in pats]
        far = lambda x, y: bool(x) and bool(y) and not any(_slip(p, q) != "far" for p in x for q in y)
        return {n for n in range(len(pats)) if any(far(real[n], real[m]) for m in range(len(pats)) if m != n)}
    except Exception:
        return set(range(len(pats))) if isinstance(pats, (list, tuple)) else set()
def _yes_entries(pairs):
    """The entries of William's standing file read STRICTLY -> ([(chart number, {"feed_ids": [ids]}) for every entry that counts], [(its chart as "pat<number>" - "" when
    the key is not one chart, why it does not count or not in full)]). pairs = the file's (key, value) pairs as they stand in it: a chart named twice comes twice, and
    both entries count. 11/25/2026, the review of the standing word: a key was squeezed to its digits ("pat1, pat2" counted for chart 12), any text in approved_by was his
    yes (also one that says no), and an id in another case, with a blank beside it or sharing its text with a second id was dropped without a word. Now an entry counts
    when its key is exactly ONE chart (pat123 or 123, in any case, blanks around it), approved_by is his word in its own form - William, the day as MM/DD/YYYY, alone or
    with (board) or (chat) behind it: never a name, a card id or a no - and feed_ids is a list that names at least one Claimocity id. An id is read as upper-case
    letters and digits, so the same id in another case or with a blank beside it is that id, and two ids in one text are two ids. The whys are fixed words: nothing of
    the file is copied into them. It never raises: an entry that cannot be read does not count."""
    good, bad = [], []
    for k, v in pairs:
        num = ""; why = ""
        try:
            m = re.fullmatch(r"\s*(?:pat)?\s*0*([0-9]+)\s*", k, re.I) if isinstance(k, str) else None; num = m.group(1) if m else ""
            e = dict(v[1]) if isinstance(v, tuple) else None
            if not num: why = "its key is not one chart"
            elif e is None: why = "it is no entry with feed_ids and approved_by"
            elif not (isinstance(e.get("approved_by"), str) and re.fullmatch(r"William\s+(0?[1-9]|1[0-2])/(0?[1-9]|[12][0-9]|3[01])/20[0-9]{2}(\s+\((board|chat)\))?", e["approved_by"].strip(), re.I)):
                why = "approved_by is not his word in the form William MM/DD/YYYY - alone or with (board) or (chat) behind it"
            elif not isinstance(e.get("feed_ids"), list): why = "feed_ids is not a list"
            else:
                ids = [x.upper() for i in e["feed_ids"] if isinstance(i, str) for x in re.findall(r"[A-Za-z0-9]+", i)]
                if not ids: why = "feed_ids names no Claimocity id"
                else:
                    good.append((num, {"feed_ids": ids}))
                    if any(not isinstance(i, str) or not re.search(r"[A-Za-z0-9]", i) for i in e["feed_ids"]): why = "one of its feed_ids is no Claimocity id - the others count"
        except Exception: why = why or "it could not be read"
        if why: bad.append((("pat" + num) if num else "", why))
    return good, bad
def same_person_gaps(path="registers/feed_same_person.json"):
    """What in William's standing file does NOT count -> (ONE line to print, or ""; {chart number: why} for the entries whose key is one chart). 11/25/2026, the review of
    the standing word: an entry the readers did not take was dropped without a word - his kept yes was silently not kept, and the next batch asked him again. The line
    begins SAME PERSON FILE: and says TOP OF THE REPORT; it names a chart only as pat<number> and gives each why in fixed words (_yes_entries) - a key that is not one
    chart is counted, never printed: it could be anything a person typed. A file that is not there gives no line; one that cannot be read is said by same_person_yes.
    It never raises."""
    try:
        if not os.path.exists(path): return "", {}
        with open(path) as fh: d = json.load(fh, object_pairs_hook=lambda p: ("object", p))
        bad = _yes_entries(d[1])[1] if isinstance(d, tuple) else []
    except Exception: return "", {}
    if not bad: return "", {}
    named = ["%s (%s)" % (c, w) for c, w in bad if c]; odd = sum(1 for c, _w in bad if not c)
    said = "; ".join(named[:20] + (["%d more" % (len(named) - 20)] if len(named) > 20 else []) + (["%d with a key that is not one chart" % odd] if odd else []))
    return ("SAME PERSON FILE: %d entr%s of %s do%s not count, or not in full - TOP OF THE REPORT - William's word is NOT kept there and such a chart is asked about again: %s. An entry reads "
            "{\"pat<chart>\": {\"feed_ids\": [\"<one Claimocity id in each pair of quotes>\"], \"approved_by\": \"William MM/DD/YYYY (board)\"}}; for a chart that is already in the file the new id is "
            "added to its list - on main, on his word." % (len(bad), "y" if len(bad) == 1 else "ies", path, "es" if len(bad) == 1 else "", said)), {c[3:]: w for c, w in bad if c}
def said_yes(yes, chart, fid):
    """True when William's standing word (yes = what same_person_yes read) names this chart AND this Claimocity id: the chart by its number, with or without "pat" in
    front; the id as upper-case letters and digits, the way _yes_entries reads the file's. It never raises: what cannot be asked is no yes."""
    try: return re.sub(r"[^A-Z0-9]", "", str(fid if fid is not None else "").upper()) in yes.get(re.sub(r"\D", "", str(chart)).lstrip("0") or "0", ())
    except Exception: return False
def same_person_yes(path="registers/feed_same_person.json"):
    """William's STANDING word that a chart is a feed patient (11/25/2026): {"pat123": {"feed_ids": [the Claimocity ids his yes is about], "approved_by": his word and its
    date}}. The file's home is the repository (practices/ehpa/registers/); it is written only on his word, and the ingest copies it into the workspace. His yes counts for
    that chart AND that Claimocity id only. -> ({chart number: {Claimocity ids}}, a line to print or ""). The entries are read strictly (_yes_entries, since the review of
    the standing word): one that does not count frees nobody and is named by same_person_gaps - never dropped without a word; a chart the file names twice keeps both
    lists. A file that cannot be read counts for nobody and is said here. Whether his word names a chart and an id is asked with said_yes. It never raises."""
    try:
        if not os.path.exists(path): return {}, ""
        with open(path) as fh: d = json.load(fh, object_pairs_hook=lambda p: ("object", p))
        if not isinstance(d, tuple): raise ValueError("no JSON object")
    except Exception as e:
        return {}, "SAME PERSON FILE: %s could not be read (%s) - nobody's standing word counts in this run; a chart held 'same person?' stays held" % (path, type(e).__name__)
    out = {}
    for num, v in _yes_entries(d[1])[0]:
        if num and isinstance(v.get("feed_ids"), list):
            ids = {i for i in v["feed_ids"] if isinstance(i, str) and i}
            if ids: out.setdefault(num, set()).update(ids)
    return out, ""
def death_check_line(g):
    """The run's date-of-death checks in ONE printed line (11/25/2026, William: "is stedi able to do that for free?"): asked free at AdvancedMD, answered free,
    went to the vendor - the deceased guard's own COUNTS (g = the loaded guard module, or None) - and how many checks ended UNVERIFIED (the guard's own LOG lines:
    nobody answered, the charge went on), with ' - TOP OF THE REPORT' when there is one. "" when there is nothing to say: no guard loaded, nothing asked and nothing
    unverified. (The second verification of that day: the line said 'vendor bought' for checks the vendor refused or never answered - the count is the guard's CHECKS
    that went to the vendor; stedi_usage.py has the requests and the dollars - and nothing on the feed's path said that a chart stayed unverified.) Counts only -
    never a chart, a name or a date. It never raises."""
    try:
        c = getattr(g, "COUNTS", None); lg = getattr(g, "LOG", None)
        u = sum(1 for x in lg if isinstance(x, str) and "UNVERIFIED" in x) if isinstance(lg, list) else 0
        tail = ("; date of death UNVERIFIED x%d - TOP OF THE REPORT" % u) if u else ""
        try: fa, fn, pa = [int(c.get(k) or 0) for k in ("free asked", "free answered", "paid asked")] if isinstance(c, dict) else [None] * 3
        except (TypeError, ValueError): fa = fn = pa = None
        if fa is None: return ("DEATH CHECK: checks not counted by this guard" + tail) if u else ""
        if not (fa or pa or u): return ""
        return "DEATH CHECK: AdvancedMD free asked x%d, answered x%d; went to the vendor x%d%s%s" % (fa, fn, pa, "; free check off after 3 failures in a row" if getattr(g, "free_down", lambda: False)() else "", tail)
    except Exception: return ""
def lookup_who(pa, first, last, dob8, today8=None, what="look-up"):
    """Whom a paid look-up of a chart is asked about: (first name, last name, birth date YYYYMMDD, words). pa = the chart's own patient attributes as AdvancedMD's
    getdemographic answer gives them (name "LAST,FIRST ...", dob MM/DD/YYYY) - the answer the caller already holds, so this costs no call. first, last, dob8 = what the
    feed carries - first the WHOLE first name (identity rule 2026-11-26.6, the identity check's finding B1: the callers handed over its first word only, and the same name
    with JR behind the first name on both sides read 'alike but not the same'); the names are compared with it, and the feed's name is asked with its first word. When
    the chart's birth date is a REAL one (_real_dob) and its name can be read, the answer is the CHART's first name (its first word), last name and birth date; else it
    is the feed's values as they were passed, the first name cut to its first word - never a mix of the two. words = which one was asked and how the other differs, in fixed
    words that carry no name and no date (a slip is named by its kind; another first name under the same last name, or another last name, is said behind them - 11/25/2026,
    the review; a name that is alike but not the same as the chart's says so, in the place of 'the first names differ' - identity rule 2026-11-26.5); they begin with `what` ("look-up", "Medicaid") and go into registers and reports. A chart answer that shows no patient at all (a read that failed) leaves
    the feed's values and says the chart could not be read - never that it has no birth date. Whether the look-up is asked at all is lookup_hold's.
    It never raises: whatever cannot be compared leaves the feed's values, and the words say so."""
    fw = (str(first).strip().split() or [""])[0] if first is not None else first      # (identity rule .6) the feed's name is asked with the first word of its first name
    try:
        today8 = today8 or __import__("datetime").date.today().strftime("%Y%m%d"); a = pa if isinstance(pa, dict) else {}
        if "name" not in a and "dob" not in a: return fw, last, dob8, "%s asked with what Claimocity sent; the chart's name and birth date could not be read" % what
        cl, _, cn = __import__("html").unescape(str(a.get("name") or "")).partition(","); cl = cl.strip(); cf = cn.strip().split(" ")[0]
        c8 = _dob8(a.get("dob")); f8 = _dob8(dob8); fr = _real_dob(f8, today8)
        kind = _name_kind(last, first, cl, cn, alike=True) if (cl and cf) else "full"
        names = "" if kind == "full" else "; the names are alike but not the same" if kind == "alike" else "; the first names differ" if kind else "; the last names differ"
        if _real_dob(c8, today8):
            if not (cl and cf): return fw, last, dob8, "%s asked with Claimocity's name and birth date; the chart's name could not be read" % what
            return cf, cl, c8, "%s asked with the chart's birth date; %s%s" % (what, ("Claimocity's is the same" if f8 == c8 else "Claimocity's differs: " + _slip(f8, c8)) if fr else "no birth date from Claimocity", names)
        return fw, last, dob8, ("%s asked with Claimocity's birth date; the chart has no birth date of its own" if fr else "%s asked with what Claimocity sent; no birth date on either side") % what + names
    except Exception:
        return fw, last, dob8, "%s asked with what Claimocity sent; the chart's name and birth date could not be compared" % what
def main():
    a = sys.argv[1:]; use_stedi = "--no-stedi" not in a; limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 10 ** 9
    only = set(a[a.index("--only") + 1].split(",")) if "--only" in a else None
    same = ({re.sub(r"\D", "", x) for x in a[a.index("--same-person") + 1].split(",")} - {""}) if "--same-person" in a else set()      # 11/25/2026 (review): William's word for THIS run - these charts (patNNN or NNN) are their feed patients (lookup_hold's sure)
    same_yes, _syl = same_person_yes()      # ... and his STANDING word: registers/feed_same_person.json (this chart AND this Claimocity id)
    if _syl: print(_syl)
    _syg, _syb = same_person_gaps()      # 11/25/2026 (the second review): what in his file does NOT count is said in ONE line here, and on the hold of a chart it names - never dropped without a word
    if _syg: print(_syg)
    # 11/25/2026 (the second review, KNOWN ALSO MEANS PROVEN BY A NUMBER in the header): the identity rule's own reading of the numbers, from feed_identity.py beside this
    # helper, and the feed's own numbers by Claimocity id from the batch's RAW files - the folder the driver names (FEED_HL7_DIR), else where it keeps a batch's files
    # (hl7/<stamp>/). In memory only. No module or no files: no number proves anything, and a chart held 'same person?' stays held. OWN = the plans the feed's own
    # steps put on each chart (the registers say which): their numbers came from the feed itself and are never weighed.
    FI = identity_rule(); NUMS = feed_numbers(os.environ["FEED_HL7_DIR"] if os.path.isdir(os.environ.get("FEED_HL7_DIR") or "") else os.path.join("hl7", STAMP), FI); OWN = feed_added_plans()
    if OWN is None: print("PLAN ORIGIN: a feed register here could not be read, so nobody can say which plans the feed itself added - no member number proves anything in this run (a Social Security number still does); a chart held 'same person?' stays held")
    def who3(m):      # one parsed message as lookup_judge takes it: (the whole first name, the last name, the birth date as 8 digits)
        _l, _, _f = str(m.get("name") or "").partition(","); return _f.strip(), _l.strip(), str(m.get("dob") or "")[:8]
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
            # 11/25/2026 (the review, WHEN IT IS NOT ASKED above; the second review, the header's (a) to (d)): before anything is bought, every feed patient whose visits
            # sit on this chart - one per Claimocity id, in visit order, with EVERY message the batch carries for that id - is judged against the chart's own name, birth
            # date, Claimocity id and numbers (pa and plans, read at the top of this chart's check); on a chart with no birth date of its own the feed patients are also
            # compared with each other. One patient nobody knows to be the chart's holds the chart (its visits are released together): nothing is bought and nothing is
            # added on this step's own word, and the record names who is in doubt - their visits (same_person) and their Claimocity ids (same_person_ids). Else the
            # look-up is asked for the first patient there is a real birth date to ask with; none at all: held for William's face sheet, nothing bought.
            _lkm = None; _lkn = ""; _lko = []
            if lead is None and not rec["hold"] and use_stedi:
                _fids = list(dict.fromkeys(v["feed_id"] for v in visits))
                _own = None if OWN is None else OWN.get(num.lstrip("0") or "0", set())
                _pats = [(_f, [who3(_m) for _m in (MSGS.get(_f) or [{}])], num in same or said_yes(same_yes, num, _f), number_proof(FI, NUMS.get(_f), pa, plans, _own)) for _f in _fids]
                _lka = lookup_apart(pa, [_ms for _f, _ms, _s, _p in _pats]); _lkj = [lookup_judge(pa, _ms, _f, sure=_s, proof=_p, apart=_n in _lka) for _n, (_f, _ms, _s, _p) in enumerate(_pats)]
                _dbt = [_n for _n, _j in enumerate(_lkj) if _j[0] == "same_person"]
                if _dbt:      # same_person: the visits and the Claimocity ids IN DOUBT (an id is written only in its own shape), for ONE line at the top of the digest; the hold names both
                    # (round 2 of the second review) The hold's words are those of the FIRST patient in doubt. What the NUMBERS say about a further one - a member number in
                    # common that proves nothing, the same Social Security number under another name, two different ones: the fixed words lookup_hold puts behind its own -
                    # is said behind that patient's visits, so that the hold says it for EVERY patient in doubt (until then only when that patient was listed first)
                    _dv = [(_fids[_n], [v["visit"] for v in visits if v["feed_id"] == _fids[_n]], _lkj[_n][1].partition("does not show this patient's Claimocity id; ")[2] if _n != _dbt[0] else "") for _n in _dbt]
                    rec["lookup_asked"] = "look-up not asked: " + _lkj[_dbt[0]][1]; rec["same_person"] = [x for _f, _vs, _nm in _dv for x in _vs]; rec["same_person_ids"] = [_show_id(_f) for _f, _vs, _nm in _dv]
                    _gap = _syb.get(num.lstrip("0") or "0")      # his standing file names this chart in an entry that does not count: said where William reads the hold
                    rec["hold"].append("%s - in doubt: %s%s%s - for William: no paid look-up was bought and no plan was added on this step's own word" % (
                        _lkj[_dbt[0]][1], "; ".join("Claimocity id %s (%s%s)" % (_show_id(_f), " ".join(_vs), ("; " + _nm) if _nm else "") for _f, _vs, _nm in _dv[:3]), (" and %d more" % (len(_dv) - 3)) if len(_dv) > 3 else "",
                        (" - his standing file has an entry for this chart that does not count: %s" % _gap) if _gap else ""))
                elif any(not _j[0] for _j in _lkj):
                    _n0 = next(_n for _n, _j in enumerate(_lkj) if not _j[0]); _lkn = _lkj[_n0][1]; _lkm = _lkj[_n0][2]
                    _lko = list(dict.fromkeys(_j[1] for _n, _j in enumerate(_lkj) if _n != _n0 and not _j[0] and _j[1]))      # what let ANOTHER feed patient of this chart be asked (his word, a number, the id): said too
                else:      # no_birth_date: the chart's visits, for ONE line at the top of the digest - and (round 2 of the second review) WHICH case it is, in a fixed
                    # word: "two dates" when Claimocity sent two different real birth dates for a feed patient of this chart, which carries none of its own - then the
                    # hold says so too, whichever of the chart's feed patients is listed first; else "neither side". The digest has a true sentence for each (until
                    # then it said 'neither Claimocity nor the chart carries a real birth date' of both)
                    _two = [_j[1] for _j in _lkj if _j[1].startswith("Claimocity sent two different birth dates")]; _nbw = (_two or [_lkj[0][1]])[0]
                    rec["lookup_asked"] = "look-up not asked: " + _nbw; rec["no_birth_date"] = list(rec["visits"]); rec["no_birth_date_case"] = "two dates" if _two else "neither side"
                    rec["hold"].append("no active plan: no paid look-up was bought - %s" % _nbw)
            if lead is None and not rec["hold"]:
                if use_stedi:
                    _mf, _ml, _md = _lkm if _lkm is not None else who3(PARSED.get(visits[0]["feed_id"], {}))
                    first = _mf or ""; last = _ml      # (identity rule .6, finding B1) the WHOLE first name: lookup_who compares the names with it and cuts the first word itself for the name it asks with
                    # 11/25/2026 (William, WHOM THE PAID LOOK-UP IS ASKED ABOUT above): the chart's own name and birth date - pa, read at the top of this chart's
                    # check - when its birth date is a real one, else the feed's exactly as before. The record says which (lookup_asked); a hold says it too, behind
                    # its own words, whenever the two dates are not the same (the digest and the hand step still find "no active plan" at the hold's start).
                    # 11/25/2026 (review): the same words stand behind "discovery: added ..." - the line the digest prints - and they also say another first or last
                    # name, the Claimocity id on the chart, a number in common, or William's word, where one of those let the look-up be asked. 11/25/2026 (the second
                    # review): they say it for EVERY feed patient of the chart - until then a visit released on his word said nothing when the chart's own person was
                    # listed first
                    first, last, dob8, asked = lookup_who(pa, first, last, _md); asked += ("; " + _lkn) if _lkn else ""
                    asked += "".join("; another Claimocity patient with a visit on this chart: " + _w for _w in _lko); rec["lookup_asked"] = asked
                    _how = "" if asked.endswith("is the same") else " - " + asked
                    try:
                        # 11/10/2026 (round 7, 4.7): the look-up is dated to the chart's latest date of service (the captured shape with dateOfService), and a
                        # plan it alone found is added only when it is a MEDICAL plan the answer shows active on EVERY date of service of the chart's visits
                        dos8 = sorted(x for x in (ymd(v["dos"]) for v in visits) if x)
                        raw = stedi.disc(first, last, dob8, "FL", dos=dos8[-1] if dos8 else None)
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
                                # 11/25/2026 (the second review): add_ins answers (the new plan's id, its sequence) - or (None, AdvancedMD's own words) when AdvancedMD
                                # refuses the plan. Until then the refusal was written as "discovery: added ... -> None seq <AdvancedMD's words>", counted as a plan
                                # added, and those words - they can name a member number or a patient - went into the register for the repository and into the
                                # digest. Now "added" is said, and counted, only for a plan id AdvancedMD gave; a refusal is said in fixed words and its own words
                                # stay in this workspace's record under "discovery", which the digest step never copies.
                                insid, seq = add_ins.add(num, CODE2CAR[code], it["member"])
                                if isinstance(insid, str) and re.fullmatch(r"ins[0-9]+", insid) and re.fullmatch(r"[0-9]+", str(seq)):
                                    rec["fixes"].append("discovery: added %s plan -> %s seq %s%s" % (code, insid, seq, _how)); stats["plans added"] += 1
                                    ok, m2 = ins_update._set_order(num, {p["id"]: p for p in elig_amd.plans(num)[1]}, insid, str(seq)); rec["fixes"].append("chart order -> %s: %s" % (seq, m2[:100]))
                                    lead = {"id": insid, "sequence": str(seq)}; code_of[insid] = code; reason = "Stedi discovery %s ACTIVE" % code; status[insid] = "ACTIVE"
                                else:
                                    rec["fixes"].append("discovery: the %s plan the look-up found was NOT added - AdvancedMD refused it%s" % (code, _how)); stats["plans not added"] += 1
                                    if isinstance(rec.get("discovery"), dict): rec["discovery"]["add_refused"] = {"code": code, "answer": str(seq)[:300]}
                                break
                        if lead is None and refused:      # worded without "discovery found [": the hand step claimocity_fixholds.py would buy the look-up again and add it
                            rec["hold"].append("no active plan: the look-up's answer was not added - for William: %s%s" % ("; ".join(refused)[:700], _how))
                        elif lead is None: rec["hold"].append("no active plan: discovery found %s%s" % ([(i.get("payer"), i.get("status")) for i in ds.get("items") or []] or "nothing", _how))
                    except Exception as e:
                        rec["hold"].append("no active plan; discovery error %s%s" % (str(e)[:120], _how))
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
                    # looks for ("insorder not applied on <visit>" with the line named) - the words the import starts probing on (the visit itself is for a person;
                    # 11/12/2026: the code never switches itself off - it puts one line a run on the first eligible visit until one is billed)
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
    _dl = death_check_line(deceased_guard)      # what this step itself asked about a patient who has passed away - free at AdvancedMD or bought (its own process, its own counts; added 11/25/2026)
    if _dl: print(_dl)
    print("DONE", dict(stats))
if __name__ == "__main__": main()
