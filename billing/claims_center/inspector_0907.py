# PLAIN ENGLISH (9/7 Claim Inspector pass)
# Decides: Clears the 50 inspector holds by William's standing rules: hospital admission date = the most recent 99223 within 45 days on/before the visit (written to Extra Info, claim forced to CMS-1500); CCM pairs get modifier 25 on the add-on 99489 (never on 99487) and the add-on advisory is bypassed; CCM duplicate/frequency advisories on distinct monthly dates are bypassed; Bell Jr's S81.801S-only visits get M86.9 in front (William 9/6: "bell can be m86.9"); a sequela code listed first is moved behind the condition code; Z51.11 (chemo encounter) is dropped from a nursing-home visit; unspecified-laterality codes are bypassed and logged for William.
# Rules it uses: full-visit echo (resave.CHG_FIELDS) via recode._save; updextrainsinfo for the admission date; bypassclaimedits only for advisories, never for missing data.
# Never touches: Paid visits, or visits not on inspector_0907.json. Anything without a 99223 anchor is HELD and reported.
# ---
import amd, resave, recode, txh, json, re, time, datetime, sys
amd.login_cached(); dry = "--dry" in sys.argv
V = json.load(open("inspector_0907.json")); LOG = open("inspector_0907.log", "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
def admit_for(pid, dos):
    d = datetime.datetime.strptime(dos, "%m/%d/%Y").date(); best = None
    for c in txh.fetch(pid).iter("charge"):
        if c.get("void") == "1" or c.get("proccode") != "99223" or not c.get("dos"): continue
        cd = datetime.datetime.strptime(c.get("dos"), "%m/%d/%Y").date()
        if cd <= d and (d - cd).days <= 45 and (best is None or cd > best): best = cd
    return best.strftime("%m/%d/%Y") if best else None
def set_date(vid, code, admit):
    ext = '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)
    return amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": vid, "nocookie": "1"}, ext))
def bypass(vid, errids):
    r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in errids))))
    return "Fault" not in r
def resave_visit(cid, visit_over=None):
    def e(a): return False
    c2, msg = recode._save(cid, e) if not visit_over else (None, "")
    if visit_over:   # need visit attr override: reimplement inline
        vis, pat, allc = resave.visit_charges(cid); chg = ""
        for c in allc:
            a = {"id": c.get("id")}
            for f in resave.CHG_FIELDS:
                if c.get(f) is not None: a[f] = c.get(f)
            chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
        va = dict(vis.attrib); va["force"] = "1"; va.update(visit_over)
        r = amd.post(amd.msg("updvisitwithcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
        return "Fault" not in r
    return c2 is not None
def dcodes_of(cid):
    x = resave.detail(cid); return dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', x))
def edit_dx(cid, fn):
    """fn(list_of_dcode_ids, id->code map) -> new list or None"""
    m = dcodes_of(cid)
    def e(a):
        d = (a.get("diagcodes") or "").split(); n = fn(d, m)
        if n and n != d: a["diagcodes"] = " ".join(n); return True
        return False
    c2, msg = recode._save(cid, e); return msg
LAT = open("laterality_flag_log.md", "a"); hold = []
for v in V:
    vid = v["visitid"]; pid = v["patientid"]; pt = v["patient"]; errs = v["errors"]
    pats = {(re.search(r"Pattern (\d+)", e[3]).group(1) if re.search(r"Pattern (\d+)", e[3]) else e[1]): e[0] for e in errs}
    ch = v["charges"]; cid = ch[0]["id"]; dos = ch[0]["dos"].strip(); codes = [c["chgcode"] for c in ch]
    try:
        if "117065068" in pats:
            admit = dos if "99223" in codes else admit_for(pid, dos)
            if not admit: L("HOLD %s %s: no 99223 within 45 days - admission date unknown" % (pt, dos)); hold.append((pt, dos, "no admission anchor")); continue
            if dry: L("DRY ADMIT %s %s -> %s" % (pt, dos, admit)); continue
            r = set_date(vid, codes[0], admit); ok = "Fault" not in r
            x = resave.detail(cid); on = re.search(r'onhcfa="([^"]*)"', x)
            ok = resave_visit(cid, {"onhcfa": "1"} if (on and on.group(1) != "1") else None) and ok
            L("ADMIT %-22s %s -> %s %s" % (pt, dos, admit, "OK" if ok else "FAULT"))
        if "20389" in pats:
            m = dcodes_of(cid); codesd = {c: i for i, c in m.items()}
            if "S81.801S" in codesd and "M86.9" not in codesd:
                msg = "DRY" if dry else edit_dx(cid, lambda d, mm: ["dcode1034545415"] + [x for x in d if x != "dcode1034545415"])
                L("DX %s %s: M86.9 added in front of S81.801S -> %s" % (pt, dos, msg))
            else:
                # move any 7th-character-S sequela / external-cause code behind the first non-S code
                msg = "DRY" if dry else edit_dx(cid, lambda d, mm: sorted(d, key=lambda x: 1 if re.match(r"[STVWXY]\d", mm.get(x, "")) else 0))
                L("DX %s %s: sequela/external code moved behind the condition -> %s" % (pt, dos, msg))
            if not dry: bypass(vid, [pats["20389"]])
        if "2776" in pats:
            msg = "DRY" if dry else edit_dx(cid, lambda d, mm: [x for x in d if mm.get(x) != "Z51.11"])
            L("DX %s %s: Z51.11 removed (chemo encounter cannot be a secondary dx on a facility visit) -> %s" % (pt, dos, msg)); LAT.write("- 9/7 %s %s visit %s: Z51.11 removed (Pattern 2776); William to confirm\n" % (pt, dos, vid))
        if "35790" in pats:
            add = [c for c in ch if c["chgcode"] == "99489" and "25" not in (c["modifiers"] or "")]
            if add and not dry:
                def e(a, aid=add[0]["id"]):
                    if a["id"] == "charge" + aid: a["modcodes"] = "25"; return True
                    return False
                c2, msg = recode._save(cid, e); L("MOD25 %s %s: 25 added to 99489 -> %s" % (pt, dos, msg))
            elif add: L("DRY MOD25 %s %s" % (pt, dos))
            if not dry: L("BYPASS %s %s add-on advisory -> %s" % (pt, dos, bypass(vid, [pats["35790"]])))
        freq = [pats[k] for k in ("3429", "7011", "35777", "33799") if k in pats]
        if freq and not dry: L("BYPASS %s %s CCM duplicate/frequency advisories (monthly CCM, distinct dates) -> %s" % (pt, dos, bypass(vid, freq)))
        if "11256" in pats:
            code = re.search(r"code\(s\) (\w+)", [e[3] for e in errs if "11256" in e[3]][0]).group(1)
            if not dry: L("BYPASS %s %s unspecified %s -> %s" % (pt, dos, code, bypass(vid, [pats["11256"]])))
            LAT.write("- 9/7 %s %s visit %s: %s unspecified laterality/site - bypassed (no known correction); William to specify\n" % (pt, dos, vid, code))
    except Exception as ex: L("ERR %s %s: %s" % (pt, dos, str(ex)[:120]))
    time.sleep(0.4)
L("=== done; held %d ===" % len(hold))
