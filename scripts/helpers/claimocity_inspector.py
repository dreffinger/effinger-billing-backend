# PLAIN ENGLISH (Claimocity feed ingest (generic; born as the [DOB] backlog import) - step 6, Claim Inspector pass on the imported visits).
# Decides, per visit the inspector flagged (the standing rules of the billing-easy-task skill):
#   117065068 Hospitalization From Date empty -> admission = the feed's PV1 admit date, else the visit's own 99223 DOS, else the
#              most recent 99223 within 45 days on the chart (gettxhistory); updextrainsinfo per CPT, then full-echo resave to reinspect.
#   Pattern 4531 (99309 at the hospital location) -> the HCA SNF unit: facility fac67 (HCA REHAB), charge POS 31, resave.
#              (11/10/2026: never for a CCM visit - CCM at the hospital location is a wrong building and is held for William.)
#   Pattern 20389 / primary-position dx (sequela, external cause, Z secondary-only, 'code first' manifestation) -> William's
#              9/14 cascade (dx_primary_fix.plan): delete the code, else move it behind the condition code, else I10 first; full-echo
#              dx save; the visit is re-listed and the leftover advisories bypassed with fresh ids.
#   Pattern 11256 unspecified laterality -> bypass + laterality_flag_log.md (billing-only, William alerted in the report).
#   Advisories (68065080 add-on, 35790, 7011, 3429, 33799, 35777, 4426, 4310, 4311, 20657, 23400, 4564, 28158) -> bypass.
# THE NO-CHARGE QUALITY LINE (1123F, William 11/10/2026 - practices/ehpa/rules.md): on a visit that carries it, an edit whose words name the
#   line (its code, pcode65441, its charge number, or a zero amount of a charge) is NEVER bypassed, whatever its pattern. William's decision
#   (11/10/2026: "choose whether AdvancedMD should take the no-charge 1123F line off a held visit automatically or leave the visit held for
#   you ... just deal with it"): THIS STEP TAKES THE LINE OFF BY ITSELF, so that a reporting line never holds a visit. A visit that would be
#   held (errors remain after the fixes and bypasses) and carries a live quality line - before the line is proven (the import register's
#   quality_gate.confirmed) for ANY such hold, after proof only when the remaining edits name the line: void that ONE charge
#   (void_tx.void_charge), re-save the visit so AdvancedMD inspects it again, list the batch again. Recorded under "quality_removed"
#   ({visit, pid, charge, fee, why, void_ok, released, at}); the import reads it (one refusal when the visit then went through). A void that
#   fails = nothing else is tried, the visit is held with its line ("quality": true). A visit still listed after the line is gone is held
#   for its own reason, as before. Held rows say "quality": true when the visit still carries the line, "names_line": true when the words name it.
#   Each entry also says "resave_ok" (written false BEFORE the re-save, so an error leaves it false) and, when the visit is still listed and the
#   re-save failed or the remaining words still name a line that came off, "still_named": true - AdvancedMD did not inspect the visit again; the
#   import then adds no new line in that run, and this step re-saves the visit again in every run until it is free (one re-save of the visit should release it).
# THE RETRY PASS (11/12/2026; William 11/11/2026: "dont stop this dont let it stop make sure this suceeds" - the code never switches itself off, and
#   a real claim never waits because of it): a visit stuck held with its no-charge line (the void failed, the re-save after it failed, or the visit
#   is still listed for the edit about the line) is tried again in every run of this step - the visits the import register's gates list under
#   "stuck", and the ones this start could not free - until it is free; each such entry says "retry_of".
#   every run tries the void and the re-save again for a visit stuck with its no-charge line.
#   The pass also looks at the visits of EARLIER batches whose line is not decided yet (the gates'
#   "open_lines"): when the claim check holds such a visit for a data error and no step ever looked at it, the line comes off here, a run late. The
#   pass decides, per visit: no longer listed = free, nothing is voided or saved; listed with advisories only = they are bypassed, nothing is
#   voided; the visit's own charge reads billed = a claim that was sent is never changed; else the line is voided (when it is still live), the
#   visit re-saved and listed again. A listing AdvancedMD did not answer shows nothing: it frees nobody. A second start of the step under one
#   stamp keeps what the first start recorded about no-charge lines.
# November 12, 2026 - fix round 1 (the lead's decisions K10 and K11): (a) THE ROUTINE'S OWN VOID IS NEVER LOST - the register is written to disk
#   after the entries are recorded and BEFORE the first void, in take_line_off and in the retry pass (and after each visit, as before): a cut right
#   after the void leaves the entry saying void_ok false, the import reads the visit as stuck, and the retry pass finds the line void already and
#   re-saves the visit. (b) A VISIT OF A FAULT RUN (AdvancedMD answered a fault but kept the visit, the call that carried the 1123F line ended in an
#   error, or the run was cut while it was out) is listed by the import under "stuck" with "fault": true, its line's charge number perhaps unknown:
#   the retry pass looks at it in every run (retry_fault) - not listed = free; listed with a data error (before the proof any, after the proof only
#   words that name the line) = its live 1123F line is found on THAT visit by its own procedure and amount (fault_lines) and taken off by the retry
#   sequence, with the M0004 line beside it; none found = it stays for a person, and no new line meanwhile. No other charge of the visit is touched.
# THE OPTION CODE M0004 (William 11/10/2026: "use it"; it rides once per clinician with the 1123F line, after proof): the same for its no-charge
#   line - an edit that names M0004 / pcode692183 is never bypassed, and the step takes BOTH no-charge lines off when the edits name neither or
#   both, and also when they name 1123F alone (the 1123F line never leaves the M0004 line behind: M0004 rides only with 1123F; that M0004 entry
#   says "with": "1123F" and starts nothing for M0004); only the M0004 line when they name M0004 alone (claimocity_import.names_lines: words
#   about a zero amount name the line whose code is not named). Each line is known by its OWN procedure in its own detail (1123F pcode65441,
#   M0004 pcode692183, at most one cent) - never a visit's own charge, also when the import recorded the two the other way round. One
#   "quality_removed" entry PER line, with its "code"; held rows say "mvp": true while the visit still carries the M0004 line and "names_mvp":
#   true when the words name it.
# Only visits this import created are touched (registers/feed_import_1028.json) - and, by the retry pass alone, the visits of earlier batches that
#   the import register's gates name: on those nothing but a no-charge line is ever voided. Writes registers/feed_inspector_1028.json.
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import amd, resave, txh, dx_primary_fix, void_tx, re, json, sys, time, datetime, collections
import xml.etree.ElementTree as ET
REG = json.load(open(("registers/feed_import_%s.json" % STAMP)))
MINE = {c["visit"].replace("vst", ""): c for c in REG["created"]}
DX = json.load(open(DXCACHE)); DCODE2ICD = {v: k for k, v in DX.items()}
ADVISORY = ("68065080", "35790", "7011", "3429", "33799", "35777", "4426", "4310", "4311", "20657", "23400", "4564", "28158", "27261", "20657")
HOSP = {"99221", "99222", "99223", "99231", "99232", "99233", "99238", "99239"}
OUT = {"fixed": [], "bypassed": [], "held": [], "laterality": [], "quality_removed": []}
QUALITY_CODE = "1123F"; QUALITY_PCODE = "pcode65441"                  # the import's quality line (claimocity_import.py QUALITY_CODE / QUALITY_PCODE)
MVP_CODE = "M0004"; MVP_PCODE = "pcode692183"                         # the import's option-code line (claimocity_import.py MVP_CODE / MVP_PCODE)
QUALITY_PROVEN = isinstance(REG.get("quality_gate"), dict) and REG["quality_gate"].get("confirmed") is True      # what the import of this batch wrote: before proof ANY hold takes the line off
def names_line(words, charge=""):
    """The import's own test (claimocity_import.names_line): the words of an edit name the quality line when they name its code, AdvancedMD's
    id for it, its own charge number, or a zero amount ("zero" or "$0" together with "charge" or "amount")."""
    w = str(words or ""); low = w.lower(); n = re.sub(r"\D", "", str(charge or ""))
    if QUALITY_CODE.lower() in low or QUALITY_PCODE in low: return True
    if n and re.search(r"(?<!\d)%s(?!\d)" % n, w): return True
    return bool(re.search(r"zero|\$0", low)) and bool(re.search(r"charge|amount", low))
def names_lines(words, qcharge="", mcharge=""):
    """The import's own test (claimocity_import.names_lines), for a visit that carries the 1123F line AND the M0004 line: (the words name the 1123F
    line, the words name the M0004 line). A line is named by its code, AdvancedMD's id for it or its own charge number; words about a zero amount
    name the line whose code is not named - both lines when neither is named by its code."""
    w = str(words or ""); low = w.lower()
    def named(code, pcode, charge):
        n = re.sub(r"\D", "", str(charge or ""))
        return code.lower() in low or pcode in low or bool(n and re.search(r"(?<!\d)%s(?!\d)" % n, w))
    q = named(QUALITY_CODE, QUALITY_PCODE, qcharge); m = named(MVP_CODE, MVP_PCODE, mcharge)
    zero = bool(re.search(r"zero|\$0", low)) and bool(re.search(r"charge|amount", low))
    return (q or (zero and not m)), (m or (zero and not q))
def split_errors(errors, qline, mline=""):
    """(advisories this step bypasses, the rest). On a visit that carries the quality line an edit whose words name the line is never bypassed - nor,
    on a visit that carries the M0004 line, an edit whose words name that line."""
    named = (lambda t: any(names_lines(t, qline, mline))) if mline else (lambda t: bool(qline) and names_line(t, qline))
    adv = [e for e in errors if (pattern(e) in ADVISORY or pattern(e) == "11256") and not named(e["text"])]
    return adv, [e for e in errors if e not in adv]
def line_live(c, code, charge):
    """Is that no-charge line of the visit still there? ONE read of the line's own charge detail before anything is voided -> ('live', charge digits)
    when it is live, shows the line's own procedure (1123F: pcode65441, M0004: pcode692183) and carries at most one cent (never a visit's own charge);
    ('gone', why) when it is void already; ('unsure', why) when that cannot be shown - then nothing is voided."""
    pc = MVP_PCODE if code == MVP_CODE else QUALITY_PCODE; qc = re.sub(r"\D", "", str(charge or ""))
    if not qc: return "gone", "no %s charge is recorded" % ("M0004" if code == MVP_CODE else "quality")
    try:
        for ch in ET.fromstring(resave.detail(qc)).iter("charge"):
            if re.sub(r"\D", "", ch.get("id") or "") != qc: continue
            if ch.get("void") == "1": return "gone", "the %s line is void already" % ("M0004" if code == MVP_CODE else "quality")
            if ch.get("proccode") != pc: return "unsure", "charge %s shows procedure %s, not %s - not voided" % (qc, ch.get("proccode") or "none", pc)
            try: small = float(ch.get("fee") or "0") <= 0.01
            except Exception: small = False
            if not small: return "unsure", "charge %s carries %s, more than one cent - not voided" % (qc, ch.get("fee"))
            return "live", qc
        return "unsure", "charge %s is not in AdvancedMD's answer - not voided" % qc
    except Exception as e: return "unsure", "charge %s could not be read (%s) - not voided" % (qc, type(e).__name__)
def quality_live(c):
    """Is the visit's quality line still there? (line_live for the 1123F line: its own procedure pcode65441, at most one cent)"""
    return line_live(c, QUALITY_CODE, c.get("quality_charge"))
def no_charge_lines(c):
    """[(code, recorded charge)] of the visit's no-charge lines, known by their OWN procedure: when the import recorded the 1123F line and the M0004
    line the other way round (its answer named no procedures), the detail of each recorded charge says which is which. One read of each."""
    rec = [x for x in (c.get("quality_charge") if c.get("quality_codes") else "", c.get("mvp_charge") if c.get("mvp_codes") else "") if x]
    if len(rec) < 2: return ([(QUALITY_CODE, rec[0])] if c.get("quality_codes") and c.get("quality_charge") else [(MVP_CODE, rec[0])]) if rec else []
    pcs = {}
    for x in rec:
        try: pcs[x] = next((ch.get("proccode") for ch in ET.fromstring(resave.detail(re.sub(r"\D", "", x))).iter("charge") if re.sub(r"\D", "", ch.get("id") or "") == re.sub(r"\D", "", x)), None)
        except Exception: pcs[x] = None
    if pcs.get(rec[0]) == MVP_PCODE and pcs.get(rec[1]) == QUALITY_PCODE: return [(QUALITY_CODE, rec[1]), (MVP_CODE, rec[0])]
    return [(QUALITY_CODE, rec[0]), (MVP_CODE, rec[1])]
def held(vid, c, why, quality=False, names=False, mvp=False, mnames=False):
    row = {"visit": vid, "pid": c["pid"], "why": why}
    if quality: row["quality"] = True          # the visit still carries the quality line
    if names: row["names_line"] = True         # the words name the line
    if mvp: row["mvp"] = True                  # the visit still carries the M0004 line
    if mnames: row["names_mvp"] = True         # the words name the M0004 line
    OUT["held"].append(row)
def write_register():
    """The step's register on disk as it stands now. November 12, 2026 - fix round 1 (decision K10): written after each visit as always, and ALSO right
    after the entries are recorded and BEFORE the first void, in take_line_off and in the retry pass - the routine's own void is never lost. A cut right
    after the void then leaves that entry on disk saying void_ok false: the import reads the visit as stuck (no new line), and the retry pass finds the
    line void already and re-saves the visit. A write that fails raises: nothing is voided that is not on disk first."""
    with open("registers/feed_inspector_%s.json" % STAMP, "w") as f: json.dump(OUT, f, indent=1)
def list_batch():
    r = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": "1", "nocookie": "1"}), timeout=180)
    root = ET.fromstring(r.encode("latin-1", "ignore")); out = {}
    for v in root.iter("visit"):
        vid = re.sub(r"\D", "", v.get("id") or "")
        if vid not in MINE: continue
        errs = []
        for e in v.iter("error"):
            errs.append({"id": e.get("id"), "number": e.get("number") or "", "text": (e.get("name") or e.get("text") or "")[:160]})
        out[vid] = {"pid": v.get("patientid"), "errors": errs}
    return out
def pattern(e):
    m = re.search(r"Pattern (\d+)", e["text"]); return m.group(1) if m else e["number"]
def bypass(vid, ids):
    r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % i for i in ids))))
    return "Fault" not in r
def set_hosp(vid, cpts, admit):
    ok = True
    for cpt in cpts:
        ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>') % (cpt, admit)
        r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst" + vid, "nocookie": "1"}, ext), timeout=120)
        ok = ok and ("Fault" not in r); time.sleep(0.3)
    return ok
def anchor_99223(pid, dos_mdy):
    dos = datetime.datetime.strptime(dos_mdy, "%m/%d/%Y").date(); best = None
    for c in txh.fetch(pid).iter("charge"):
        if c.get("void") == "1" or c.get("proccode") != "99223": continue
        try: d = datetime.datetime.strptime(c.get("dos"), "%m/%d/%Y").date()
        except Exception: continue
        if d <= dos and (dos - d).days <= 45 and (best is None or d > best): best = d
    return best.strftime("%m/%d/%Y") if best else None
def resave_visit(cid, hospfrom=None, facility=None, pos=None):
    """Full-echo resave (reinspect) with optional facility / POS override."""
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        if pos: a["pos"] = pos
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    if facility: va["facility"] = facility
    if hospfrom: va["onhcfa"] = "1"
    ext = resave._extins_xml(vis, hospfrom) if hospfrom else ""
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
                 "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                 "<visit %s><chargelist>%s</chargelist>%s</visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg, ext)), timeout=180)
    time.sleep(0.8)
    return "Fault" not in r, re.sub(r"\s+", " ", r[:200])
def advisories(vid, c, adv):
    """Bypass the advisories that remain (laterality logged first). -> notes for the step's log line."""
    for e in adv:
        if pattern(e) == "11256":
            OUT["laterality"].append({"visit": vid, "pid": c["pid"], "text": e["text"]})
            open("laterality_flag_log.md", "a").write("- %s vst%s %s: %s (bypassed, Claimocity import 10/28)\n" % (datetime.date.today(), vid, c["pid"], e["text"]))
    if not adv: return []
    ok = bypass(vid, [e["id"] for e in adv]); OUT["bypassed"].append({"visit": vid, "patterns": sorted({pattern(e) for e in adv})})
    return ["bypassed %d advisories%s" % (len(adv), "" if ok else " FAILED")]
def take_line_off(vid, c, own, words, named, which=None, mnamed=False):
    """William 11/10/2026: the routine takes the no-charge line(s) off a held visit by itself. which = [(code, charge)] of the lines to take off (the
    1123F line when not given; with the M0004 line: both, or only the M0004 line when the edits name M0004 alone). Each line's own detail is read first, and NOTHING is
    voided unless every line to take off shows itself live with its own procedure and at most one cent. Then ONE void per line (void_tx.void_charge,
    in order; the first that fails ends it - nothing else is tried), a re-save of the visit on its OWN first charge so AdvancedMD inspects it again,
    the batch listed again; then the visit is released or held for its own reason. One "quality_removed" entry per line records it. -> a note."""
    which = [(k, x) for k, x in (which or [(QUALITY_CODE, c.get("quality_charge"))]) if x]; one = [k for k, _ in which] == [QUALITY_CODE] and not (c.get("mvp_codes") and c.get("mvp_charge"))
    carries = {QUALITY_CODE: bool(c.get("quality_codes") and c.get("quality_charge")), MVP_CODE: bool(c.get("mvp_codes") and c.get("mvp_charge"))}; gone = set()
    def hold(w, n1, n2): held(vid, c, w, quality=carries[QUALITY_CODE] and QUALITY_CODE not in gone, names=n1, mvp=carries[MVP_CODE] and MVP_CODE not in gone, mnames=n2)
    live = {}
    for k, x in which:
        live[k] = line_live(c, k, x)
        if live[k][0] == "gone": gone.add(k)
    todo = [(k, x) for k, x in which if k not in gone]
    if not todo: hold(words, named, mnamed); return "HELD: %s (its %s not live any more)" % (words[:60], "quality line is" if one else "no-charge lines are")
    at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(); entries = []
    for k, x in todo:
        entry = {"visit": vid, "pid": c["pid"], "charge": x, "code": k, "fee": c.get("mvp_fee" if k == MVP_CODE else "quality_fee"), "why": words[:140], "void_ok": False, "released": False, "at": at}
        if k == MVP_CODE and named and not mnamed: entry["with"] = QUALITY_CODE      # taken off only because the 1123F line comes off (M0004 never rides without it, 8.2): not M0004's fault
        OUT["quality_removed"].append(entry); entries.append((k, entry))      # recorded at once: even if a later call raises, the import knows what was tried
    bad = [(k, live[k][1]) for k, _ in todo if live[k][0] == "unsure"]
    if bad:
        for k, entry in entries: entry["note"] = live[k][1] if live[k][0] == "unsure" else "not tried: another no-charge line of the visit could not be shown live"
        hold(words, named, mnamed); return "HELD with its quality line: %s" % bad[0][1] if one else "HELD with its no-charge lines: %s" % bad[0][1]
    write_register()      # K10 (November 12, 2026 - fix round 1): what is about to be tried is ON DISK before the first void - a cut after the void leaves void_ok false = the visit is stuck, and the retry pass re-saves it
    for k, entry in entries:
        ok, msg = void_tx.void_charge(c["pid"], live[k][1])
        if not ok:
            entry["note"] = "the void failed: %s" % re.sub(r"\s+", " ", str(msg))[:120]
            for k2, e2 in entries:
                if e2 is not entry and not e2["void_ok"]: e2["note"] = "not tried: the void of the %s line failed" % k
            hold(words, named, mnamed); return "HELD with its quality line: the void failed" if one else "HELD with its %s line: the void failed" % k
        entry["void_ok"] = True; gone.add(k)
    for _k, entry in entries: entry["resave_ok"] = False      # written BEFORE the re-save: an error in the re-save or in the listing leaves it False (confirm review NH2-2)
    ok2, r = resave_visit(own); time.sleep(1.0)
    if not ok2:
        for _k, entry in entries: entry["note"] = "the re-save after the void failed: %s" % r[:100]
    again = list_batch().get(vid)
    rq = c.get("quality_charge") if carries[QUALITY_CODE] and QUALITY_CODE not in gone else ""; rm = c.get("mvp_charge") if carries[MVP_CODE] and MVP_CODE not in gone else ""
    adv, data = split_errors(again["errors"], rq, rm) if again else ([], [])
    notes = advisories(vid, c, adv)
    # still listed for the edit about a line that came off (the re-save failed, or the remaining words still name that line): AdvancedMD did not
    # inspect the visit again - that is NOT the visit's own reason; the import adds no new line while that is so, and this step tries again in every run (NH2-2)
    _still = bool(data) and (not ok2 or any(names_lines(e["text"], c.get("quality_charge") or "", c.get("mvp_charge") or "")[0 if k_ == QUALITY_CODE else 1] for e in data for k_, _x in todo))
    for _k, entry in entries:
        entry["released"] = not data; entry["resave_ok"] = bool(ok2)
        if _still: entry["still_named"] = True
    if data:
        if one: held(vid, c, "; ".join(e["text"][:80] for e in data), names=any(names_line(e["text"], c.get("quality_charge")) for e in data))
        else: hold("; ".join(e["text"][:80] for e in data), bool(rq) and any(names_lines(e["text"], rq, rm)[0] for e in data), bool(rm) and any(names_lines(e["text"], rq, rm)[1] for e in data))
    if one: return "quality line %s taken off (void), visit re-saved: %s%s" % (c.get("quality_charge"), "released" if not data else "still held for its own reason", ("; " + "; ".join(notes)) if notes else "")
    return "no-charge line(s) %s taken off (void), visit re-saved: %s%s" % (", ".join("%s %s" % (k, x) for k, x in todo), "released" if not data else "still held for its own reason", ("; " + "; ".join(notes)) if notes else "")
# ---- THE RETRY PASS (11/12/2026; William 11/11/2026: "dont stop this dont let it stop make sure this suceeds") ------------------------------------
# The quality code never switches itself off any more, so a visit that is stuck held with its no-charge line must come free by the routine: this
# pass runs after the step's normal pass, in every run of the step. It tries again (a) the visits the import register's gates list under "stuck"
# (quality_gate for the 1123F line, mvp_gate for the M0004 line - written minutes earlier by the import of the same run), (b) the visits this very
# start - or an earlier start under the same stamp - could not free (its own entries that say stuck), and it looks at (c) the visits of EARLIER
# batches whose line is not decided yet (the gates' "open_lines"): a visit the claim check holds while no step ever looked at it.
def listing(also=()):
    """The Claim Inspector batch as list_batch reads it, for the retry pass: (True, {visit: {pid, errors}}) of my visits and of the visits in `also` -
    or (False, {}) when AdvancedMD did not answer the listing (a fault, success="0", an answer that cannot be read). list_batch turns a fault
    into an empty list, which reads as "no visit is listed"; this pass must never call a visit free on that: a listing that failed shows nothing."""
    try:
        r = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": "1", "nocookie": "1"}), timeout=180)
        if "Fault" in r or 'success="0"' in r: return False, {}
        out = {}
        for v in ET.fromstring(r.encode("latin-1", "ignore")).iter("visit"):
            vid = re.sub(r"\D", "", v.get("id") or "")
            if vid in MINE or vid in also: out[vid] = {"pid": v.get("patientid"), "errors": [{"id": e.get("id"), "number": e.get("number") or "", "text": (e.get("name") or e.get("text") or "")[:160]} for e in v.iter("error")]}
        return True, out
    except Exception: return False, {}
def own_billed(own):
    """Was the visit's own first charge billed? ONE read of its detail, read as the import reads a charge (a billed date is listed): True / False -
    or None when that cannot be shown. A claim that was sent is never changed: the retry pass neither voids nor saves on a visit that reads billed,
    nor on one whose own charge cannot be read."""
    cid = re.sub(r"\D", "", str(own or ""))
    if not cid: return None
    try:
        for ch in ET.fromstring(resave.detail(cid)).iter("charge"):
            if re.sub(r"\D", "", ch.get("id") or "") != cid: continue
            return bool([b for b in ch.findall("insbilllist/insbill") if b.get("billeddate")] or (ch.get("insbilled") == "1" and (ch.get("datebilled") or "").strip()))
        return None
    except Exception: return None
def stuck_says(e):
    """Does a "quality_removed" entry say that the visit is stuck held with that line? The void failed - or the line came off and the visit is still
    listed for the edit about it (the import's own test). An entry that says "listed": false says free."""
    if e.get("listed") is False: return False
    return e.get("void_ok") is not True or (e.get("released") is not True and (e.get("still_named") is True or e.get("resave_ok") is False))
def retry_visits():
    """{visit number: what the pass needs} - 'kind' ("stuck": tried again until free; "open": only looked at), 'c' (the visit's row: this batch's own,
    or one built from the gate's items for a visit of an earlier batch), 'own' (the visit's own first charge), 'act' ({code: charge} of the lines the
    gates or the entries name), 'since' (the register that first recorded the visit - every entry of the pass says it as "retry_of") and 'why'."""
    num = lambda x: re.sub(r"\D", "", str(x or "")); out = {}
    def add(vid, kind, code, charge, fee, own, pid, other, since, why):
        t = out.setdefault(vid, {"kind": kind, "own": own, "pid": pid, "act": {}, "all": {}, "fee": {}, "since": since, "why": why})
        if kind == "stuck" and t["kind"] != "stuck": t.update(kind="stuck", since=since, why=why, act={})      # stuck wins: the visit is tried until it is free
        if kind == t["kind"]: t["act"][code] = charge
        t["all"][code] = charge; t["fee"][code] = fee; t["own"] = t["own"] or own
        if other: t["all"].setdefault(MVP_CODE if code == QUALITY_CODE else QUALITY_CODE, other)      # the visit's other no-charge line as its row recorded it
    for gk in ("quality_gate", "mvp_gate"):
        g = REG.get(gk) if isinstance(REG.get(gk), dict) else {}
        for kind, key in (("stuck", "stuck"), ("open", "open_lines")):
            for it in (g.get(key) if isinstance(g.get(key), list) else []):
                # K11 (November 12, 2026 - fix round 1): a visit of a fault run is listed under "stuck" of the quality_gate with what the import knows - its line's charge number may be unknown
                flt = isinstance(it, dict) and it.get("fault") is True and kind == "stuck" and gk == "quality_gate" and bool(num(it.get("visit"))) and isinstance(it.get("chart"), str)
                if not flt and (not isinstance(it, dict) or not num(it.get("visit")) or not num(it.get("charge")) or not isinstance(it.get("chart"), str)): continue      # an odd item is passed over
                vid = num(it.get("visit")); own = it.get("own") if isinstance(it.get("own"), str) else ""
                if kind == "open" and (vid in MINE or not num(own)): continue      # this batch's own visits are the normal pass's; an item without its own first charge is passed over
                add(vid, kind, MVP_CODE if str(it.get("code") or "").upper() == MVP_CODE else QUALITY_CODE, it["charge"] if isinstance(it.get("charge"), str) else "", it.get("fee"), own, it["chart"],
                    it.get("with") if isinstance(it.get("with"), str) else "", str(it.get("since") or it.get("register") or ""), str(it.get("why") or ""))
                if flt: out[vid].update(fault=True, dos=str(it.get("dos") or ""))
    newest = {}
    for e in OUT["quality_removed"]:      # this start's entries, and an earlier start's under the same stamp: the newest per line decides
        if isinstance(e, dict) and num(e.get("visit")) and num(e.get("charge")): newest[(num(e.get("visit")), str(e.get("code") or QUALITY_CODE).upper())] = e
    for (vid, code), e in newest.items():
        if vid in out and out[vid]["kind"] == "stuck" and not stuck_says(e): out[vid]["act"].pop(code, None)      # a newer entry of this stamp already says that line is free
        if not stuck_says(e) or vid not in MINE: continue
        c = MINE[vid]; q = c.get("quality_charge") if (c.get("quality_codes") and c.get("quality_charge")) else ""; mv = c.get("mvp_charge") if (c.get("mvp_codes") and c.get("mvp_charge")) else ""
        add(vid, "stuck", MVP_CODE if code == MVP_CODE else QUALITY_CODE, e["charge"], e.get("fee"), next((x for x in c["charges"] if x not in (q, mv)), ""), c["pid"],
            (q if code == MVP_CODE else mv) or "", str(e.get("retry_of") or "feed_inspector_%s.json" % STAMP), str(e.get("why") or ""))
    for vid, t in list(out.items()):
        if not t["act"]: del out[vid]; continue
        a = t["all"]
        t["c"] = MINE[vid] if vid in MINE else {"visit": "vst" + vid, "pid": t["pid"], "cpts": [], "charges": [x for x in (t["own"], a.get(QUALITY_CODE), a.get(MVP_CODE)) if x],
                                               "quality_codes": [QUALITY_CODE] if a.get(QUALITY_CODE) else [], "quality_charge": a.get(QUALITY_CODE, ""), "quality_fee": t["fee"].get(QUALITY_CODE),
                                               "mvp_codes": [MVP_CODE] if a.get(MVP_CODE) else [], "mvp_charge": a.get(MVP_CODE, ""), "mvp_fee": t["fee"].get(MVP_CODE)}
    return out
def retry_one(vid, t, info):
    """ONE visit of the retry pass. info = how the Claim Inspector lists it now (None = not listed). This is take_line_off's own sequence with these
    differences: a line that is void already does not end it (the visit is re-saved and listed again), every entry says "retry_of", a listing that
    failed frees nobody, and nothing is voided or saved on a visit that is free or was billed. -> a note for the step's log line."""
    c = t["c"]; stuck = t["kind"] == "stuck"; q = c.get("quality_charge") if (c.get("quality_codes") and c.get("quality_charge")) else ""; mv = c.get("mvp_charge") if (c.get("mvp_codes") and c.get("mvp_charge")) else ""
    at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat(); entries = []
    def entry(code, charge, **kw):
        e = dict({"visit": vid, "pid": c["pid"], "charge": charge, "code": code, "fee": c.get("mvp_fee" if code == MVP_CODE else "quality_fee"), "why": str(kw.pop("why", t["why"]))[:140], "void_ok": False, "released": False, "at": at,
                  "retry_of": t["since"]}, **dict(t.get("mark") or {}, **kw))      # mark: {"fault": true} for a visit of a fault run (retry_fault, K11) - the import finds it by its visit
        OUT["quality_removed"].append(e); entries.append((code, e)); return e      # recorded at once: even if a later call raises, the import knows what was tried
    def free(note):      # the visit is free: one entry per line the gates named, nothing voided or saved ("void_ok" = that line reads void)
        for code, charge in sorted(t["act"].items(), key=lambda kv: kv[0] != QUALITY_CODE): entry(code, charge, void_ok=line_live(c, code, charge)[0] == "gone", released=True, listed=False, note=note)
        return "free: " + note
    if info is None: return free("the visit is no longer listed by the Claim Inspector - nothing done") if stuck else "not listed - nothing done"
    adv, data = split_errors(info["errors"], q, mv)
    if not data:      # listed with advisories only: the hold is gone - they are bypassed as the step always does, nothing is voided
        if not stuck: return "advisories only - nothing done"
        notes = advisories(vid, c, adv)
        if any("FAILED" in n for n in notes): return "advisories only, but the bypass was not accepted - nothing recorded, the next run tries again"
        return free("only advisories remained - bypassed, nothing voided")
    words = "; ".join(e["text"][:80] for e in data)
    if q and mv: nq = any(names_lines(e["text"], q, mv)[0] for e in data); nm = any(names_lines(e["text"], q, mv)[1] for e in data)
    else: nq = bool(q) and any(names_line(e["text"], q) for e in data); nm = bool(mv) and any(names_lines(e["text"], "", mv)[1] for e in data)
    if not stuck and QUALITY_PROVEN and not (nq or nm): return "held for words that name no no-charge line - left alone (after proof)"      # the normal pass's own test
    billed = own_billed(t["own"])
    if billed is None: return "the visit's own charge could not be read - nothing done, the next run tries again"
    if billed: return free("the visit was billed - nothing done") if stuck else "the visit was billed - nothing done"
    if q and mv:      # both no-charge lines: told apart by their OWN procedure first (the import may have recorded them the other way round), as in the normal pass
        _nl = dict(no_charge_lines(c)); q = _nl.get(QUALITY_CODE, ""); mv = _nl.get(MVP_CODE, ""); c = dict(c, quality_charge=q, mvp_charge=mv)
        if stuck and set(t["act"].values()) <= {q, mv}: t = dict(t, act={k: x for k, x in ((QUALITY_CODE, q), (MVP_CODE, mv)) if k in t["act"]})
    # which lines come off: a stuck visit - the lines that are stuck, and the M0004 line with the 1123F line (M0004 never rides without it); a visit that
    # was only looked at - the normal pass's rule (both when the edits name neither or both or 1123F alone, only the M0004 line when they name M0004 alone)
    take_q = bool(q) and ((QUALITY_CODE in t["act"]) if stuck else (nq or not nm))
    which = [(k, x) for k, x in ((QUALITY_CODE, q), (MVP_CODE, mv)) if x and ((k == QUALITY_CODE and take_q) or (k == MVP_CODE and (take_q or not stuck or MVP_CODE in t["act"])))]
    carries = {QUALITY_CODE: bool(q), MVP_CODE: bool(mv)}; gone = set()
    def hold(w, n1, n2):      # ONE held row a visit: the row this start's normal pass wrote for it gives way to what the pass finds now (the digest lists and counts the held rows)
        OUT["held"][:] = [r_ for r_ in OUT["held"] if not (isinstance(r_, dict) and r_.get("visit") == vid)]
        held(vid, c, w, quality=carries[QUALITY_CODE] and QUALITY_CODE not in gone, names=n1, mvp=carries[MVP_CODE] and MVP_CODE not in gone, mnames=n2)
    live = {k: line_live(c, k, x) for k, x in which}
    for k, x in which:
        e = entry(k, x, why=words)
        if k == MVP_CODE and take_q and ((MVP_CODE not in t["act"]) if stuck else (nq and not nm)): e["with"] = QUALITY_CODE      # it comes off only because the 1123F line comes off (M0004 never rides without it): not M0004's fault
        if live[k][0] == "gone": e["void_ok"] = True; gone.add(k)      # void already: nothing to void - go on to the re-save
    bad = [(k, live[k][1]) for k, _ in which if live[k][0] == "unsure"]
    if bad:      # a line that cannot be shown to be the no-charge line: nothing is voided, nothing else is tried for this visit
        for k, e in entries:
            if not e["void_ok"]: e["note"] = live[k][1] if live[k][0] == "unsure" else "not tried: another no-charge line of the visit could not be shown live"
        hold(words, nq, nm); return "HELD with its no-charge line: %s" % bad[0][1]
    for _k, e in entries: e["resave_ok"] = False      # written BEFORE the void and the re-save: an error in the re-save or in the listing leaves it False - and on disk a line already void waits for its re-save ("still listed")
    write_register()      # K10 (November 12, 2026 - fix round 1): what is about to be tried is ON DISK before the first void - a cut after the void leaves void_ok false = the visit stays stuck, and the next retry re-saves it
    for k, e in entries:
        if e["void_ok"]: continue
        ok, msg = void_tx.void_charge(c["pid"], live[k][1])
        if not ok:      # the void failed again: nothing else is tried; the next run tries again
            e["note"] = "the void failed: %s" % re.sub(r"\s+", " ", str(msg))[:120]
            for _k2, e2 in entries:
                if e2 is not e and not e2["void_ok"]: e2["note"] = "not tried: the void of the %s line failed" % k
            hold(words, nq, nm); return "HELD with its %s line: the void failed again" % k
        e["void_ok"] = True; gone.add(k)
    ok2, r = resave_visit(re.sub(r"\D", "", t["own"])); time.sleep(1.0)
    if not ok2:
        for _k, e in entries: e["note"] = "the re-save after the void failed: %s" % r[:100]
    ok3, again = listing({vid})
    if not ok3:      # the listing after the re-save failed: the visit is not shown free - the next run lists it again
        for _k, e in entries: e.update(resave_ok=bool(ok2), released=False, still_named=True, note="the listing after the re-save failed")
        return "line(s) off, visit re-saved, but the listing after it failed - the next run lists it again"
    now = again.get(vid); rq = q if QUALITY_CODE not in gone else ""; rm = mv if MVP_CODE not in gone else ""
    adv2, data2 = split_errors(now["errors"], rq, rm) if now else ([], [])
    notes = advisories(vid, c, adv2)
    _still = bool(data2) and (not ok2 or any(names_lines(e["text"], q or "", mv or "")[0 if k_ == QUALITY_CODE else 1] for e in data2 for k_, _x in which))
    for _k, e in entries:
        e["released"] = not data2; e["resave_ok"] = bool(ok2)
        if _still: e["still_named"] = True
    if data2: hold("; ".join(e["text"][:80] for e in data2), bool(rq) and any(names_lines(e["text"], rq, rm)[0] for e in data2), bool(rm) and any(names_lines(e["text"], rq, rm)[1] for e in data2))
    return "no-charge line(s) %s off, visit re-saved: %s%s" % (", ".join("%s %s" % (k, x) for k, x in which), "released" if not data2 else "still listed", ("; " + "; ".join(notes)) if notes else "")
# ---- A VISIT OF A FAULT RUN (November 12, 2026 - fix round 1, decision K11) ----------------------------------------------------------------------------
# AdvancedMD answered a fault but kept the visit, the call that carried the 1123F line ended in an error, or the run was cut while that call was out:
# that visit is for a person and its patient gets no line again this year (as before), AND the import lists it under "stuck" (with "fault": true and
# what it knows - the visit, the chart, the amount, the date; the line's charge number may be unknown), so no real claim waits for it: no new line while
# the Claim Inspector holds it, and this pass looks at it in every run until it is free. Never any other charge of the visit than its no-charge lines.
def fault_lines(vid, t):
    """The no-charge lines of a visit of a fault run. The 1123F line: the charge an earlier look found (it may be void by now), else ONE read of the chart's
    history for a live 1123F line of at most one cent on the line's date (on this visit, when the history names visits). Each candidate's OWN detail must
    show procedure pcode65441, at most one cent, and THIS visit - the visit the feed import itself created (its failed row names it); a line that is
    being looked for must be live. Then the visit's live charges (resave.visit_charges): its own first charge, and a live M0004 line of at most one cent
    (it comes off with the 1123F line - M0004 never rides without it). -> ("found", {code: charge}, own) | ("none", why, "") | ("unsure", why, "")."""
    known = re.sub(r"\D", "", str(t["act"].get(QUALITY_CODE) or "")); cands = [known] if known else []
    if not known:
        try: hist = txh.fetch(re.sub(r"\D", "", t["pid"]))
        except Exception as e: return "unsure", "the chart's history could not be read (%s)" % type(e).__name__, ""
        for ch in hist.iter("charge"):
            a = ch.attrib
            if str(a.get("proccode") or "").upper() != QUALITY_CODE or a.get("void") == "1" or (a.get("fee") or "").startswith("-"): continue
            if a.get("visit") and re.sub(r"\D", "", a.get("visit")) != vid: continue      # the history names the visit: it must be this one
            if t.get("dos") and a.get("dos") and a.get("dos") != t["dos"]: continue
            try: small = float(a.get("fee") or "0") <= 0.01
            except Exception: small = False
            if small and re.sub(r"\D", "", a.get("id") or ""): cands.append(re.sub(r"\D", "", a.get("id")))
    good = []
    for cid in dict.fromkeys(cands):
        try: root = ET.fromstring(resave.detail(cid))
        except Exception as e: return "unsure", "charge %s could not be read (%s)" % (cid, type(e).__name__), ""
        vis = root.find(".//visit"); ch = next((x for x in root.iter("charge") if re.sub(r"\D", "", x.get("id") or "") == cid), None)
        if ch is None or vis is None or re.sub(r"\D", "", vis.get("id") or "") != vid or ch.get("proccode") != QUALITY_PCODE: continue
        try: small = float(ch.get("fee") or "0") <= 0.01
        except Exception: small = False
        if small and (known or ch.get("void") != "1"): good.append(cid)
    if not good: return "none", ("charge %s is not shown as that visit's 1123F line" % known) if known else "no live 1123F line of at most one cent on that visit in the chart's history", ""
    if len(good) > 1: return "none", "%d live 1123F lines on that visit (%s) - not told apart" % (len(good), ", ".join(good)), ""
    try: _v, _p, allc = resave.visit_charges(good[0])
    except Exception as e: return "unsure", "the visit's charges could not be read (%s)" % type(e).__name__, ""
    own = next((re.sub(r"\D", "", x.get("id") or "") for x in allc if x.get("proccode") not in (QUALITY_PCODE, MVP_PCODE) and re.sub(r"\D", "", x.get("id") or "")), "")
    if not own: return "none", "the visit shows no live charge of its own", ""
    def tiny(x):
        try: return float(x.get("fee") or "0") <= 0.01
        except Exception: return False
    mv = [re.sub(r"\D", "", x.get("id") or "") for x in allc if x.get("proccode") == MVP_PCODE and x.get("void") != "1" and tiny(x)]
    return "found", dict({QUALITY_CODE: "charge" + good[0]}, **({MVP_CODE: "charge" + mv[0]} if len(mv) == 1 else {})), "charge" + own
def retry_fault(vid, t, info):
    """ONE visit of a fault run (K11). info = how the Claim Inspector lists it now (None = not listed). Not listed = free. Listed with advisories only =
    they are bypassed as the step always does, free. Listed with a data error - before the proof any, after the proof only words that name a no-charge
    line - its no-charge lines are found (fault_lines) and taken off by the retry sequence (retry_one: the line read live first, the void, the re-save on
    the visit's own first charge, the listing; a visit that reads billed is never changed). No such line found = it stays listed for a person, and no
    new line meanwhile. Every entry says "fault": true (the import finds the visit by its number) and "retry_of". -> a note for the step's log line."""
    at = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()
    def entry(**kw):
        e = dict({"visit": vid, "pid": t["pid"], "charge": re.sub(r"\D", "", str(t["act"].get(QUALITY_CODE) or "")) and str(t["act"].get(QUALITY_CODE)), "code": QUALITY_CODE, "fee": t["fee"].get(QUALITY_CODE),
                  "why": t["why"][:140], "void_ok": False, "released": False, "at": at, "retry_of": t["since"], "fault": True}, **kw)
        OUT["quality_removed"].append(e); return e
    if info is None: entry(released=True, listed=False, note="the visit is no longer listed by the Claim Inspector - nothing done"); return "free: not listed"
    named = lambda e: any(names_lines(e["text"], t["act"].get(QUALITY_CODE) or ""))      # the code, its id, the charge number when known, or a zero amount
    adv = [e for e in info["errors"] if (pattern(e) in ADVISORY or pattern(e) == "11256") and not named(e)]; data = [e for e in info["errors"] if e not in adv]
    if not data:      # advisories only: the hold is gone - bypassed as always, nothing voided
        notes = advisories(vid, {"pid": t["pid"]}, adv)
        if any("FAILED" in n for n in notes): return "advisories only, but the bypass was not accepted - nothing recorded, the next run tries again"
        entry(released=True, listed=False, note="only advisories remained - bypassed, nothing voided"); return "free: only advisories remained"
    words = "; ".join(e["text"][:80] for e in data)
    if QUALITY_PROVEN and not any(named(e) for e in data):      # after the proof only words that name a no-charge line take it off (the normal pass's own test): this hold is the visit's own - a person looks
        entry(why=words, note="held after the proof for words that name no no-charge line - left alone; a person looks at that visit"); return "held after the proof for words that name no line - for a person"
    st, found, own = fault_lines(vid, t)
    if st == "unsure": return "%s - nothing done, the next run tries again" % found
    if st == "none": entry(why=words, note="%s - nothing voided; a person looks at that visit" % found); return "for a person: %s" % found
    q = found[QUALITY_CODE]; mv = found.get(MVP_CODE, ""); fee = t["fee"].get(QUALITY_CODE)
    c = {"visit": "vst" + vid, "pid": t["pid"], "cpts": [], "charges": [x for x in (own, q, mv) if x], "quality_codes": [QUALITY_CODE], "quality_charge": q, "quality_fee": fee,
         "mvp_codes": [MVP_CODE] if mv else [], "mvp_charge": mv, "mvp_fee": fee if mv else None}
    return retry_one(vid, dict(t, c=c, own=own, act={QUALITY_CODE: q}, all=dict(found), mark={"fault": True}), info)
def retry_pass():
    """The retry pass over retry_visits(), with ONE listing of the Claim Inspector batch for all of them. A listing AdvancedMD did not answer shows
    nothing: no entry is written and every visit stays as it was. An error while one visit is tried is caught - what was recorded for it stays -
    and the pass goes on with the next visit."""
    todo = retry_visits()
    if not todo: return
    ok, now = listing(set(todo))
    if not ok: print("inspector retry: the Claim Inspector listing was not answered - %d visit(s) not looked at; the next run tries again" % len(todo)); return
    for vid, t in todo.items():
        try: print("RETRY", vid, t["kind"] + (" (a fault run)" if t.get("fault") else ""), "|", (retry_fault if t.get("fault") else retry_one)(vid, t, now.get(vid))[:200])
        except Exception as e: print("ERR retry", vid, str(e)[:160])
def main():
    amd.login_cached()
    try:      # a second start of the step under one stamp keeps what the first start recorded about no-charge lines (11/12/2026: until then those entries were lost, and with them the import's knowledge of what the step had done)
        _prev = json.load(open("registers/feed_inspector_%s.json" % STAMP))
        OUT["quality_removed"][:0] = [e for e in (_prev.get("quality_removed") if isinstance(_prev, dict) and isinstance(_prev.get("quality_removed"), list) else []) if isinstance(e, dict)]
    except Exception: pass
    batch = list_batch(); print("inspector: %d of my visits flagged" % len(batch))
    for vid, info in batch.items():
        c = MINE[vid]; pats = {pattern(e) for e in info["errors"]}
        qline = c.get("quality_charge") if (c.get("quality_codes") and c.get("quality_charge")) else ""      # the visit carries the no-charge quality line
        mline = c.get("mvp_charge") if (c.get("mvp_codes") and c.get("mvp_charge")) else ""                # ... and the no-charge M0004 line (once per clinician, after proof)
        cid = re.sub(r"\D", "", next((x for x in c["charges"] if x not in (qline, mline)), c["charges"][0]))   # the visit's own first charge (never a no-charge line)
        note = []
        try:
            # 1. hospitalization date
            if "117065068" in pats:
                admit = c.get("admit") and "%s/%s/%s" % (c["admit"][4:6], c["admit"][6:8], c["admit"][:4])
                if c["cpts"] and "99223" in c["cpts"]: admit = admit or c["dos"]
                if not admit: admit = anchor_99223(re.sub(r"\D", "", c["pid"]), c["dos"])
                if admit and any(x in HOSP for x in c["cpts"]):
                    ok = set_hosp(vid, c["cpts"], admit); note.append("admit %s %s" % (admit, "written" if ok else "WRITE FAILED"))
                elif not any(x in HOSP for x in c["cpts"]):
                    note.append("non-hospital CPT at a hospital facility - see location fix")
                else:
                    held(vid, c, "no admission anchor (no PV1 admit, no 99223 within 45 days)", quality=bool(qline), mvp=bool(mline)); print("HOLD", vid, "no admit anchor"); continue
            # 2. location: SNF codes sent by HCA -> HCA REHAB unit
            fac = pos = None
            # 11/10/2026 (William's place-of-service rule): CCM at the hospital location is a wrong building, never an HCA REHAB stay -
            # it is not moved to fac67 / POS 31; the 4531 error stays and the visit is held for William like any other data error
            # 11/10/2026 (review): a visit the import itself flagged (pos_err - its building is in doubt) is never moved to HCA REHAB either; it is held
            if "4531" in pats and c.get("fac") == "fac29" and all(x not in HOSP for x in c["cpts"]) and not any(x in ("99487", "99489") for x in c["cpts"]) and not c.get("pos_err"):
                fac, pos = "fac67", "31"; note.append("facility fac29 -> fac67 (HCA REHAB), POS 31")
            # 3. dx cascade on primary-position problems
            dx_notes = []
            if "20389" in pats or any("primary" in e["text"].lower() and "position" in e["text"].lower() for e in info["errors"]):
                vis, pat, allc = resave.visit_charges(cid); new_by_charge = {}
                for ch in allc:
                    dcodes = (ch.get("diagcodes") or "").split(); codes = [DCODE2ICD.get(d, d) for d in dcodes]
                    action, newcodes = dx_primary_fix.plan(codes, ch.get("proccode"))
                    if action != "ok":
                        new_by_charge[ch.get("id")] = [DX.get(x, x) if x != "I10" else dx_primary_fix.I10_DCODE for x in newcodes]
                        dx_notes.append("%s: %s %s -> %s" % (ch.get("id"), action, codes[:3], newcodes[:3]))
                if new_by_charge:
                    msg, det = dx_primary_fix.save_visit_dx(cid, new_by_charge); dx_notes.append(msg)
            if dx_notes: note.extend(dx_notes)
            # 4. resave to reinspect when something changed (or a stale hospitalization error)
            if "117065068" in pats or fac or dx_notes:
                hosp = None
                if "117065068" in pats and any(x in HOSP for x in c["cpts"]):
                    hosp = (c.get("admit") and "%s/%s/%s" % (c["admit"][4:6], c["admit"][6:8], c["admit"][:4])) or (c["dos"] if "99223" in c["cpts"] else None) or anchor_99223(re.sub(r"\D", "", c["pid"]), c["dos"])
                ok, r = resave_visit(cid, hosp, fac, pos); note.append("resave %s" % ("ok" if ok else r[:120]))
            # 5. re-list and bypass the advisories that remain - never an edit that names the quality line (11/10/2026)
            time.sleep(1.0)
            again = list_batch().get(vid)
            if again:
                if mline:      # the visit carries the M0004 line too: the lines known by their own procedure (the import may have recorded them the other way round)
                    _nl = dict(no_charge_lines(c)); qline = _nl.get(QUALITY_CODE, ""); mline = _nl.get(MVP_CODE, "")
                    c = dict(c, quality_charge=qline, mvp_charge=mline)
                adv, data = split_errors(again["errors"], qline, mline)
                note.extend(advisories(vid, c, adv))
                if data and mline:      # 11.6: both no-charge lines come off when the edits name neither or both; only the M0004 line when they name M0004 alone. The 1123F
                    # line never leaves the M0004 line behind (8.2: M0004 rides only with 1123F; confirm review NH2-1): words that name 1123F take both off
                    words = "; ".join(e["text"][:80] for e in data)
                    nq = bool(qline) and any(names_lines(e["text"], qline, mline)[0] for e in data); nm = any(names_lines(e["text"], qline, mline)[1] for e in data)
                    if not QUALITY_PROVEN or nq or nm:
                        which = [(k, x) for k, x in ((QUALITY_CODE, qline), (MVP_CODE, mline)) if x and (nq or not nm or k == MVP_CODE)]
                        note.append(take_line_off(vid, c, cid, words, nq, which, nm))
                    else: held(vid, c, words, quality=bool(qline), mvp=True); note.append("HELD: " + "; ".join(pattern(e) for e in data))
                elif data:
                    words = "; ".join(e["text"][:80] for e in data); named = bool(qline) and any(names_line(e["text"], qline) for e in data)
                    if qline and (not QUALITY_PROVEN or named): note.append(take_line_off(vid, c, cid, words, named))      # William 11/10/2026: the routine takes the line off by itself
                    else: held(vid, c, words, quality=bool(qline), names=named); note.append("HELD: " + "; ".join(pattern(e) for e in data))
            OUT["fixed"].append({"visit": vid, "pid": c["pid"], "patterns": sorted(pats), "note": note})
            print("DONE", vid, sorted(pats), "|", "; ".join(note)[:200])
        except Exception as e:
            _off = lambda k: any(x.get("visit") == vid and x.get("void_ok") and (x.get("code") or QUALITY_CODE) == k for x in OUT["quality_removed"])      # a line already taken off in this step
            held(vid, c, "error %s" % str(e)[:160], quality=bool(qline) and not _off(QUALITY_CODE), mvp=bool(mline) and not _off(MVP_CODE)); print("ERR", vid, str(e)[:160])
        json.dump(OUT, open(("registers/feed_inspector_%s.json" % STAMP), "w"), indent=1)
    _n = (len(OUT["quality_removed"]), len(OUT["held"]))
    try: retry_pass()      # 11/12/2026: every run tries again the visits stuck held with their no-charge line (THE RETRY PASS above); it never stops the step
    except Exception as e: print("ERR retry pass", str(e)[:160])
    if (len(OUT["quality_removed"]), len(OUT["held"])) != _n:      # written after the pass whenever it recorded an entry or a held row - also in a run whose normal pass found no visit of the batch listed (such a run wrote no register until now)
        json.dump(OUT, open(("registers/feed_inspector_%s.json" % STAMP), "w"), indent=1)
    left = list_batch(); print("inspector after: %d of my visits still listed" % len(left), collections.Counter(pattern(e) for v in left.values() for e in v["errors"]))
if __name__ == "__main__": main()
