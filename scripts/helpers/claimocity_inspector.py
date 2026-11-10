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
QUALITY_PROVEN = isinstance(REG.get("quality_gate"), dict) and REG["quality_gate"].get("confirmed") is True      # what the import of this batch wrote: before proof ANY hold takes the line off
def names_line(words, charge=""):
    """The import's own test (claimocity_import.names_line): the words of an edit name the quality line when they name its code, AdvancedMD's
    id for it, its own charge number, or a zero amount ("zero" or "$0" together with "charge" or "amount")."""
    w = str(words or ""); low = w.lower(); n = re.sub(r"\D", "", str(charge or ""))
    if QUALITY_CODE.lower() in low or QUALITY_PCODE in low: return True
    if n and re.search(r"(?<!\d)%s(?!\d)" % n, w): return True
    return bool(re.search(r"zero|\$0", low)) and bool(re.search(r"charge|amount", low))
def split_errors(errors, qline):
    """(advisories this step bypasses, the rest). On a visit that carries the quality line an edit whose words name the line is never bypassed."""
    adv = [e for e in errors if (pattern(e) in ADVISORY or pattern(e) == "11256") and not (qline and names_line(e["text"], qline))]
    return adv, [e for e in errors if e not in adv]
def quality_live(c):
    """Is the visit's quality line still there? ONE read of the line's own charge detail before anything is voided -> ('live', charge digits) when
    it is live, shows procedure pcode65441 and carries at most one cent (never a visit's own charge); ('gone', why) when it is void already;
    ('unsure', why) when that cannot be shown - then nothing is voided."""
    qc = re.sub(r"\D", "", str(c.get("quality_charge") or ""))
    if not qc: return "gone", "no quality charge is recorded"
    try:
        for ch in ET.fromstring(resave.detail(qc)).iter("charge"):
            if re.sub(r"\D", "", ch.get("id") or "") != qc: continue
            if ch.get("void") == "1": return "gone", "the quality line is void already"
            if ch.get("proccode") != QUALITY_PCODE: return "unsure", "charge %s shows procedure %s, not %s - not voided" % (qc, ch.get("proccode") or "none", QUALITY_PCODE)
            try: small = float(ch.get("fee") or "0") <= 0.01
            except Exception: small = False
            if not small: return "unsure", "charge %s carries %s, more than one cent - not voided" % (qc, ch.get("fee"))
            return "live", qc
        return "unsure", "charge %s is not in AdvancedMD's answer - not voided" % qc
    except Exception as e: return "unsure", "charge %s could not be read (%s) - not voided" % (qc, type(e).__name__)
def held(vid, c, why, quality=False, names=False):
    row = {"visit": vid, "pid": c["pid"], "why": why}
    if quality: row["quality"] = True          # the visit still carries the quality line
    if names: row["names_line"] = True         # the words name the line
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
def take_line_off(vid, c, own, words, named):
    """William 11/10/2026: the routine takes the no-charge quality line off a held visit by itself. ONE void of that charge (only after its own
    detail shows it live, pcode65441, at most one cent), a re-save of the visit on its OWN first charge so AdvancedMD inspects it again, the
    batch listed again; then the visit is released or held for its own reason. One "quality_removed" entry records it. -> a note."""
    st, qc = quality_live(c)
    if st == "gone": held(vid, c, words, names=named); return "HELD: %s (its quality line is not live any more)" % words[:60]
    entry = {"visit": vid, "pid": c["pid"], "charge": c.get("quality_charge"), "fee": c.get("quality_fee"), "why": words[:140], "void_ok": False, "released": False, "at": datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None).isoformat()}
    OUT["quality_removed"].append(entry)      # recorded at once: even if a later call raises, the import knows what was tried
    if st == "unsure": entry["note"] = qc; held(vid, c, words, quality=True, names=named); return "HELD with its quality line: %s" % qc
    ok, msg = void_tx.void_charge(c["pid"], qc)
    if not ok: entry["note"] = "the void failed: %s" % re.sub(r"\s+", " ", str(msg))[:120]; held(vid, c, words, quality=True, names=named); return "HELD with its quality line: the void failed"
    entry["void_ok"] = True
    ok2, r = resave_visit(own); time.sleep(1.0)
    if not ok2: entry["note"] = "the re-save after the void failed: %s" % r[:100]
    again = list_batch().get(vid)
    adv, data = split_errors(again["errors"], "") if again else ([], [])
    notes = advisories(vid, c, adv); entry["released"] = not data
    if data: held(vid, c, "; ".join(e["text"][:80] for e in data), names=any(names_line(e["text"], c.get("quality_charge")) for e in data))
    return "quality line %s taken off (void), visit re-saved: %s%s" % (c.get("quality_charge"), "released" if not data else "still held for its own reason", ("; " + "; ".join(notes)) if notes else "")
def main():
    amd.login_cached()
    batch = list_batch(); print("inspector: %d of my visits flagged" % len(batch))
    for vid, info in batch.items():
        c = MINE[vid]; pats = {pattern(e) for e in info["errors"]}
        qline = c.get("quality_charge") if (c.get("quality_codes") and c.get("quality_charge")) else ""      # the visit carries the no-charge quality line
        cid = re.sub(r"\D", "", next((x for x in c["charges"] if x != qline), c["charges"][0]))              # the visit's own first charge (never the quality line)
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
                    held(vid, c, "no admission anchor (no PV1 admit, no 99223 within 45 days)", quality=bool(qline)); print("HOLD", vid, "no admit anchor"); continue
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
                adv, data = split_errors(again["errors"], qline)
                note.extend(advisories(vid, c, adv))
                if data:
                    words = "; ".join(e["text"][:80] for e in data); named = bool(qline) and any(names_line(e["text"], qline) for e in data)
                    if qline and (not QUALITY_PROVEN or named): note.append(take_line_off(vid, c, cid, words, named))      # William 11/10/2026: the routine takes the line off by itself
                    else: held(vid, c, words, quality=bool(qline), names=named); note.append("HELD: " + "; ".join(pattern(e) for e in data))
            OUT["fixed"].append({"visit": vid, "pid": c["pid"], "patterns": sorted(pats), "note": note})
            print("DONE", vid, sorted(pats), "|", "; ".join(note)[:200])
        except Exception as e:
            held(vid, c, "error %s" % str(e)[:160], quality=bool(qline) and not any(x.get("visit") == vid and x.get("void_ok") for x in OUT["quality_removed"])); print("ERR", vid, str(e)[:160])
        json.dump(OUT, open(("registers/feed_inspector_%s.json" % STAMP), "w"), indent=1)
    left = list_batch(); print("inspector after: %d of my visits still listed" % len(left), collections.Counter(pattern(e) for v in left.values() for e in v["errors"]))
if __name__ == "__main__": main()
