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
# Only visits this import created are touched (registers/feed_import_1028.json). Writes registers/feed_inspector_1028.json.
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import amd, resave, txh, dx_primary_fix, re, json, sys, time, datetime, collections
import xml.etree.ElementTree as ET
REG = json.load(open(("registers/feed_import_%s.json" % STAMP)))
MINE = {c["visit"].replace("vst", ""): c for c in REG["created"]}
DX = json.load(open(DXCACHE)); DCODE2ICD = {v: k for k, v in DX.items()}
ADVISORY = ("68065080", "35790", "7011", "3429", "33799", "35777", "4426", "4310", "4311", "20657", "23400", "4564", "28158", "27261", "20657")
HOSP = {"99221", "99222", "99223", "99231", "99232", "99233", "99238", "99239"}
OUT = {"fixed": [], "bypassed": [], "held": [], "laterality": []}
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
def main():
    amd.login_cached()
    batch = list_batch(); print("inspector: %d of my visits flagged" % len(batch))
    for vid, info in batch.items():
        c = MINE[vid]; cid = re.sub(r"\D", "", c["charges"][0]); pats = {pattern(e) for e in info["errors"]}
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
                    OUT["held"].append({"visit": vid, "pid": c["pid"], "why": "no admission anchor (no PV1 admit, no 99223 within 45 days)"}); print("HOLD", vid, "no admit anchor"); continue
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
            # 5. re-list and bypass the advisories that remain
            time.sleep(1.0)
            again = list_batch().get(vid)
            if again:
                adv = [e for e in again["errors"] if pattern(e) in ADVISORY or pattern(e) == "11256"]
                data = [e for e in again["errors"] if e not in adv]
                for e in adv:
                    if pattern(e) == "11256":
                        OUT["laterality"].append({"visit": vid, "pid": c["pid"], "text": e["text"]})
                        open("laterality_flag_log.md", "a").write("- %s vst%s %s: %s (bypassed, Claimocity import 10/28)\n" % (datetime.date.today(), vid, c["pid"], e["text"]))
                if adv:
                    ok = bypass(vid, [e["id"] for e in adv]); note.append("bypassed %d advisories%s" % (len(adv), "" if ok else " FAILED"))
                    OUT["bypassed"].append({"visit": vid, "patterns": sorted({pattern(e) for e in adv})})
                if data:
                    OUT["held"].append({"visit": vid, "pid": c["pid"], "why": "; ".join(e["text"][:80] for e in data)}); note.append("HELD: " + "; ".join(pattern(e) for e in data))
            OUT["fixed"].append({"visit": vid, "pid": c["pid"], "patterns": sorted(pats), "note": note})
            print("DONE", vid, sorted(pats), "|", "; ".join(note)[:200])
        except Exception as e:
            OUT["held"].append({"visit": vid, "pid": c["pid"], "why": "error %s" % str(e)[:160]}); print("ERR", vid, str(e)[:160])
        json.dump(OUT, open(("registers/feed_inspector_%s.json" % STAMP), "w"), indent=1)
    left = list_batch(); print("inspector after: %d of my visits still listed" % len(left), collections.Counter(pattern(e) for v in left.values() for e in v["errors"]))
if __name__ == "__main__": main()
