# PLAIN ENGLISH (Claim Inspector pass, 3 PM ET 9/13/2026 run - ehpa cloud, prompt v5 step 2; generalizes insp_0912e_fix.py)
# Decides: for ONE inspector batch (arg 1), clears the holds by William's standing rules:
#   - "Hospitalization From Date empty" = admission date: the visit's own 99223 DOS, else the most recent 99223 on/before the
#     DOS within 45 days (gettxhistory); written with updextrainsinfo hospitalizationfrom ONLY (never hospitalizationto), then a
#     full-visit resave (resave.visit_charges echo) with onhcfa=1. No anchor -> HELD and reported, never guessed.
#   - Pattern 20389 (sequela / external-cause / requires-primary code listed first): move that code behind the condition code;
#     pat17472546's S81.801S-only visits of the 9/3/2026 stay get M86.9 (dcode1034545415) in front (William 9/6).
#   - Pattern 11256 (unspecified laterality): bypass + log to laterality_flag_log.md.
#   - Advisory patterns (35790, 3429/7011/35777/33799, 20657, 27261, 4310, 4311, 4426, 4564, 28158): bypass.
#   Edits/resaves change every error id, so the script re-lists the batch and bypasses with the FRESH ids in a second pass.
# Never touches: missing-data errors (never bypassed), voided or paid charges (echo skips them), hospitalizationto.
"""Usage: python3 insp_0913_fix.py <batchid> [--dry]"""
import amd, resave, recode, txh, re, sys, time, datetime, json
import xml.etree.ElementTree as ET
BATCH = sys.argv[1]; dry = "--dry" in sys.argv
amd.login_cached()
LOG = open("insp_0913_fix.log", "a"); LAT = open("laterality_flag_log.md", "a")
STAMP = time.strftime("%m/%d %H:%M", time.gmtime())
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
ADVISORY = {"35790", "3429", "7011", "35777", "33799", "20657", "27261", "4310", "4311", "4426", "4564", "28158", "11256", "20389"}

def list_batch():
    t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": BATCH, "nocookie": "1"}), timeout=120)
    root = ET.fromstring(t); out = []
    for v in root.iter("visit"):
        chs = [dict(c.attrib) for c in v.iter("charge")]
        errs = []
        for e in v.iter("error"):
            name = e.get("name") or ""; m = re.search(r"Pattern (\d+)", name)
            errs.append({"id": e.get("id"), "pat": m.group(1) if m else ("HOSPFROM" if "Hospitalization From" in name else "OTHER"), "name": name})
        out.append({"vid": v.get("id"), "pid": v.get("patientid"), "name": v.get("patientname"), "carrier": v.get("carriercode"), "chs": chs, "errs": errs})
    return out

def admit_for(pid, dos):
    d = datetime.datetime.strptime(dos, "%m/%d/%Y").date(); best = None
    for c in txh.fetch(pid).iter("charge"):
        if c.get("void") == "1" or c.get("proccode") != "99223" or not c.get("dos"): continue
        cd = datetime.datetime.strptime(c.get("dos").strip(), "%m/%d/%Y").date()
        if cd <= d and (d - cd).days <= 45 and (best is None or cd > best): best = cd
    return best.strftime("%m/%d/%Y") if best else None

def set_date(vid, code, admit):
    ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" '
           'employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit))
    r = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": "vst%s" % vid, "nocookie": "1"}, ext))
    return "Fault" not in r

def resave_onhcfa(cid, edit=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""; changed = 0
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        if edit and edit(a): changed += 1
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"; va["onhcfa"] = "1"
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry",
                         {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
                          "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                         "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, v) for k, v in va.items()), chg)))
    time.sleep(0.8)
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:250])
    v2, p2, c2 = resave.visit_charges(cid)
    return "ok (%d edited; %d live, was %d)" % (changed, len(c2), len(allc))

def dcodes_of(cid):
    x = resave.detail(cid); return dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', x))

def bypass(vid, errids):
    r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"},
                         '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in errids))))
    return "Fault" not in r

# ---- pass 1: data fixes ----
V = list_batch(); L("=== %s batch %s pass 1: %d visits (dry=%s) ===" % (STAMP, BATCH, len(V), dry))
held = []; anchors = {}
for v in V:
    vid, pid, pt = v["vid"], v["pid"], v["name"]; pats = {e["pat"]: e["id"] for e in v["errs"]}
    ch = v["chs"]; cid = ch[0]["id"]; dos = ch[0]["dos"].strip(); codes = [c["chgcode"] for c in ch]
    try:
        did_resave = False
        if "HOSPFROM" in pats:
            admit = dos if "99223" in codes else admit_for(pid, dos); anchors[vid] = admit
            if not admit:
                L("HOLD  %-24s v%s %s %s: no 99223 within 45 days - admission unknown" % (pt, vid, dos, "+".join(codes))); held.append((pt, pid, vid, dos, codes)); continue
            if dry: L("DRY   %-24s v%s %s %s -> admit %s" % (pt, vid, dos, "+".join(codes), admit))
            else:
                ok = set_date(vid, codes[0], admit)
                msg = resave_onhcfa(cid); did_resave = True
                L("ADMIT %-24s v%s %s %s -> %s extins=%s resave=%s" % (pt, vid, dos, "+".join(codes), admit, ok, msg))
        if "20389" in pats:
            m = dcodes_of(cid); byc = {c: i for i, c in m.items()}
            cur = [m.get(x, x) for x in (re.search(r'diagcodes="([^"]*)"', resave.detail(cid)) or [None, ""])[1].split()]
            if "S81.801S" in byc and "M86.9" not in byc and pid == "17472546" and anchors.get(vid) == "09/03/2026":
                fn = lambda a: (a.__setitem__("diagcodes", " ".join(["dcode1034545415"] + [x for x in (a.get("diagcodes") or "").split() if x != "dcode1034545415"])) or True)
                what = "M86.9 in front of S81.801S (William 9/6, same 9/3 stay)"
            else:
                def fn(a, mm=m):
                    d = (a.get("diagcodes") or "").split()
                    n = sorted(d, key=lambda x: 1 if re.match(r"([STVWXY]\d|Z16)", mm.get(x, "")) else 0)
                    if n != d: a["diagcodes"] = " ".join(n); return True
                    return False
                what = "external-cause/sequela/Z16 code moved behind the condition"
            if dry: L("DRY   %-24s v%s %s dx %s -> %s" % (pt, vid, dos, cur, what))
            else:
                msg = resave_onhcfa(cid, fn); did_resave = True
                L("DX    %-24s v%s %s dx %s -> %s -> %s" % (pt, vid, dos, cur, what, msg))
        if "11256" in pats:
            code = (re.search(r"code\(s\) ([\w ]+?)(?:\.\.\.| defines|$)", [e["name"] for e in v["errs"] if e["pat"] == "11256"][0]) or [None, "?"])[1]
            L("LAT   %-24s v%s %s %s: unspecified %s - bypass in pass 2, logged" % (pt, vid, dos, "+".join(codes), code))
            if not dry: LAT.write("- %s %s (pat%s) %s visit %s %s: %s unspecified laterality/site - bypassed (no known correction); William to specify\n" % (STAMP, pt, pid, dos, vid, "+".join(codes), code))
    except Exception as ex: L("ERR   %-24s v%s: %s" % (pt, vid, str(ex)[:200]))
    time.sleep(0.4)
if dry: L("=== dry pass 1 done; held %d ===" % len(held)); sys.exit()

# ---- pass 2: re-list, bypass advisories with fresh ids ----
time.sleep(2); V2 = list_batch(); L("=== pass 2: %d visits still listed ===" % len(V2))
for v in V2:
    vid, pt = v["vid"], v["name"]; adv = [e["id"] for e in v["errs"] if e["pat"] in ADVISORY]; other = [e for e in v["errs"] if e["pat"] not in ADVISORY]
    if adv: L("BYPASS %-24s v%s %s -> %s" % (pt, vid, [(e["pat"]) for e in v["errs"] if e["pat"] in ADVISORY], bypass(vid, adv)))
    for e in other: L("LEFT  %-24s v%s %s %s" % (pt, vid, e["pat"], e["name"][:120]))
    time.sleep(0.3)
time.sleep(2); V3 = list_batch(); L("=== after: %d visits still listed in batch %s ===" % (len(V3), BATCH))
for v in V3: L("REMAIN %-24s v%s %s" % (v["name"], v["vid"], [(e["pat"], e["name"][:80]) for e in v["errs"]]))
b = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); L("BATCHES after: %s" % re.findall(r'<batch id="([^"]+)"', b))
json.dump({"held": held, "anchors": anchors, "remaining": V3}, open("insp_0913_result_%s.json" % BATCH, "w"), indent=1)
