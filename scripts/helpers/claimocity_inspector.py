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
# THE OPTION CODE M0004 (William 11/10/2026: "use it"; it rides once per clinician with the 1123F line, after proof): the same for its no-charge
#   line - an edit that names M0004 / pcode692183 is never bypassed, and the step takes BOTH no-charge lines off when the edits name neither or
#   both, only the one that is named when they name one (claimocity_import.names_lines: words about a zero amount name the line whose code is not
#   named). Each line is known by its OWN procedure in its own detail (1123F pcode65441, M0004 pcode692183, at most one cent) - never a visit's own
#   charge, also when the import recorded the two the other way round. One "quality_removed" entry PER line, with its "code"; held rows say
#   "mvp": true while the visit still carries the M0004 line and "names_mvp": true when the words name it.
# Only visits this import created are touched (registers/feed_import_1028.json). Writes registers/feed_inspector_1028.json.
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
    1123F line when not given; with the M0004 line: both, or only the one the edits name). Each line's own detail is read first, and NOTHING is
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
        OUT["quality_removed"].append(entry); entries.append((k, entry))      # recorded at once: even if a later call raises, the import knows what was tried
    bad = [(k, live[k][1]) for k, _ in todo if live[k][0] == "unsure"]
    if bad:
        for k, entry in entries: entry["note"] = live[k][1] if live[k][0] == "unsure" else "not tried: another no-charge line of the visit could not be shown live"
        hold(words, named, mnamed); return "HELD with its quality line: %s" % bad[0][1] if one else "HELD with its no-charge lines: %s" % bad[0][1]
    for k, entry in entries:
        ok, msg = void_tx.void_charge(c["pid"], live[k][1])
        if not ok:
            entry["note"] = "the void failed: %s" % re.sub(r"\s+", " ", str(msg))[:120]
            for k2, e2 in entries:
                if e2 is not entry and not e2["void_ok"]: e2["note"] = "not tried: the void of the %s line failed" % k
            hold(words, named, mnamed); return "HELD with its quality line: the void failed" if one else "HELD with its %s line: the void failed" % k
        entry["void_ok"] = True; gone.add(k)
    ok2, r = resave_visit(own); time.sleep(1.0)
    if not ok2:
        for _k, entry in entries: entry["note"] = "the re-save after the void failed: %s" % r[:100]
    again = list_batch().get(vid)
    rq = c.get("quality_charge") if carries[QUALITY_CODE] and QUALITY_CODE not in gone else ""; rm = c.get("mvp_charge") if carries[MVP_CODE] and MVP_CODE not in gone else ""
    adv, data = split_errors(again["errors"], rq, rm) if again else ([], [])
    notes = advisories(vid, c, adv)
    for _k, entry in entries: entry["released"] = not data
    if data:
        if one: held(vid, c, "; ".join(e["text"][:80] for e in data), names=any(names_line(e["text"], c.get("quality_charge")) for e in data))
        else: hold("; ".join(e["text"][:80] for e in data), bool(rq) and any(names_lines(e["text"], rq, rm)[0] for e in data), bool(rm) and any(names_lines(e["text"], rq, rm)[1] for e in data))
    if one: return "quality line %s taken off (void), visit re-saved: %s%s" % (c.get("quality_charge"), "released" if not data else "still held for its own reason", ("; " + "; ".join(notes)) if notes else "")
    return "no-charge line(s) %s taken off (void), visit re-saved: %s%s" % (", ".join("%s %s" % (k, x) for k, x in todo), "released" if not data else "still held for its own reason", ("; " + "; ".join(notes)) if notes else "")
def main():
    amd.login_cached()
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
                if data and mline:      # 11.6: both no-charge lines come off when the edits name neither or both, only the named one when they name one
                    words = "; ".join(e["text"][:80] for e in data)
                    nq = bool(qline) and any(names_lines(e["text"], qline, mline)[0] for e in data); nm = any(names_lines(e["text"], qline, mline)[1] for e in data)
                    if not QUALITY_PROVEN or nq or nm:
                        which = [(k, x) for k, x in ((QUALITY_CODE, qline), (MVP_CODE, mline)) if x and (nq == nm or (k == QUALITY_CODE) == nq)]
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
    left = list_batch(); print("inspector after: %d of my visits still listed" % len(left), collections.Counter(pattern(e) for v in left.values() for e in v["errors"]))
if __name__ == "__main__": main()
