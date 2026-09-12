# 9/11 3pm ET - work the inspector: admit dates, dx fixes, CCM mod-25, then bypass advisories with fresh ids
import amd, resave, recode, re, json, time, datetime, collections
import xml.etree.ElementTree as ET
amd.login_cached()
LOG = open("insp_work_0911.log", "a")
def L(m): print(m, flush=True); LOG.write(str(m)+"\n"); LOG.flush()
def d(s): return datetime.datetime.strptime(s.strip()[:10], "%m/%d/%Y").date()

BYPASSABLE = {"20657","3429","7011","35777","33799","35790","24078","23400","15775",
              "4531","4310","4311","4426","4564","28158","27261","11256","2776"}
LATLOG = open("laterality_flag_log.md", "a")

def listbatch(bid):
    return amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid}))

def parse(t):
    root = ET.fromstring(t)
    out = []
    for v in root.iter("visit"):
        errs = [(e.get("id"), re.sub(r"\s+"," ", (e.text or "") + "".join((c.text or "") for c in e.iter()))[:200], e.get("number") or "")
                for e in v.iter("error")]
        chgs = [(c.get("id"), c.get("proccode")) for c in v.iter("charge")]
        out.append({"vid": v.get("id"), "pid": v.get("patientid") or "", "name": v.get("patientname") or "",
                    "status": v.get("claimstatus") or "", "errs": errs, "chgs": chgs})
    return out

def pattern_of(txt):
    m = re.search(r"Pattern (\d+)", txt)
    return m.group(1) if m else ("ADMIT" if "Hospitalization From Date" in txt else "OTHER")

def bypass(vid, ids):
    r = amd.post(amd.msg("bypassclaimedits","chargeentry",{"nocookie":"1"},
        '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in ids))))
    return "Fault" not in r

def set_date(vid, code, admit):
    ext = '<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>' % (code, admit)
    return amd.post(amd.msg("updextrainsinfo","chargeentry",{"visitid": "vst"+vid if not str(vid).startswith("vst") else vid, "nocookie":"1"}, ext))

def resave_visit(cid, over=None, chg_over=None):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        if chg_over and c.get("id") in chg_over: a.update(chg_over[c.get("id")])
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, amd.esc(v)) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    if over: va.update(over)
    r = amd.post(amd.msg("updvisitwithcharges","chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode") or "", "approval":"1","inspectorenabled":"1","getfinancials":"-1","customclaimfieldsavailable":"1","nocookie":"1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (" ".join('%s="%s"' % (k, amd.esc(v)) for k, v in va.items()), chg)))
    time.sleep(0.7)
    return "Fault" not in r, r[:200]

HIST = {}
def history(pid):
    pid = re.sub(r"\D","",str(pid))
    if pid not in HIST:
        root = ET.fromstring(amd.post(amd.msg('gettxhistory','demographics',{'patientid':pid,'filterhistory':'0','pagenumber':'1','typefilter':'0','sortbypayment':'false','groupbyvisit':'0','sortdescending':'1','visitid':'0','profileid':'','getmemo':'false','nocookie':'1'}), timeout=120))
        HIST[pid] = [(d(c.get("dos")), c.get("proccode")) for c in root.iter("charge") if c.get("void") != "1" and c.get("dos")]
    return HIST[pid]

def admit_for(pid, dos):
    h = history(pid)
    adm = [x for x, p in h if p == "99223" and x <= dos and (dos - x).days <= 45]
    if adm: return max(adm)
    return None

stats = collections.Counter()
held = []

r = amd.call('action="getclaiminspectorbatches" class="chargeentry"')
bids = re.findall(r'<batch id="([^"]+)"', r)
L("=== insp_work_0911 %s: %d batches ===" % (time.ctime(), len(bids)))

for bid in bids:
    t = listbatch(bid)
    vs = parse(t)
    if not vs: time.sleep(0.2); continue
    dirty = False
    for v in vs:
        pats = [pattern_of(txt) for eid, txt, num in v["errs"]]
        # --- data fixes first ---
        if "ADMIT" in pats:
            cid = v["chgs"][0][0] if v["chgs"] else None
            if not cid: L("HOLD %s %s: admit error but no charge id" % (v["vid"], v["name"])); held.append((v["name"], v["vid"], "no charge id")); continue
            vis, pat, allc = resave.visit_charges(cid)
            pid = re.sub(r"\D","", pat.get("id"))
            dos = d(allc[0].get("begindate"))
            codes = sorted({c.get("proccode") for c in allc})
            if "99223" in codes:
                adm = dos
            else:
                adm = admit_for(pid, dos)
            if adm is None:
                L("HOLD %s %s %s: no 99223 anchor within 45d" % (v["vid"], v["name"], dos)); stats["hold-admit"] += 1
                held.append((v["name"], v["vid"], "no 99223 anchor within 45d of %s" % dos)); continue
            ds = adm.strftime("%m/%d/%Y")
            for code in codes:
                rr = set_date(v["vid"], code, ds)
                if "Fault" in rr: L("FAULT set_date %s %s: %s" % (v["vid"], code, rr[:150]))
            e = vis.find("extins"); onh = vis.get("onhcfa") or (e.get("onhcfa") if e is not None else "")
            over = {"onhcfa": "1"}
            ok, _ = resave_visit(cid, over)
            L("ADMIT %s %s dos %s admit %s resave ok=%s" % (v["vid"], v["name"], dos, ds, ok))
            stats["admit-fixed"] += 1; dirty = True
        if "20389" in pats:
            # sequela/external-cause first: reorder behind condition; S81801S-only -> M86.9 front (Winslow Jr rule)
            cid = v["chgs"][0][0] if v["chgs"] else None
            if not cid: held.append((v["name"], v["vid"], "20389 no charge id")); continue
            x = resave.detail(cid)
            dmap = dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', x))
            def fix(a):
                codes_ = (a.get("diagcodes") or "").split()
                if not codes_: return False
                bad = [dc for dc in codes_ if re.match(r"^[STVWXY]", dmap.get(dc, ""))]
                good = [dc for dc in codes_ if dc not in bad]
                if not bad or codes_[0] not in bad: return False
                if good:
                    a["diagcodes"] = " ".join(good + bad)
                else:
                    a["diagcodes"] = " ".join(["dcode1034545415"] + codes_)  # M86.9 in front
                return True
            c2, msg = recode._save(cid, fix)
            L("20389 %s %s dx fix: %s" % (v["vid"], v["name"], msg)); stats["dx-reordered"] += 1; dirty = True
        if "35790" in pats or "15775" in pats:
            # ensure mod 25 (mcode7) on the 99489 add-on, never on 99487
            for cid, pc in v["chgs"]:
                if pc == "99489":
                    x = resave.detail(cid)
                    if 'code="25"' not in x:
                        vis, pat, allc = resave.visit_charges(cid)
                        tgt = [c for c in allc if c.get("id") == cid or c.get("proccode") == "99489"]
                        for c in tgt:
                            mc = (c.get("modcodes") or "").split(",") if c.get("modcodes") else []
                            if "mcode7" not in mc:
                                mc.append("mcode7")
                                ok, _ = resave_visit(cid, None, {c.get("id"): {"modcodes": ",".join([m for m in mc if m])}})
                                L("MOD25 %s %s 99489 +mcode7 ok=%s" % (v["vid"], v["name"], ok)); stats["mod25-added"] += 1; dirty = True
                        break
        if "11256" in pats:
            for eid, txt, num in v["errs"]:
                if pattern_of(txt) == "11256":
                    LATLOG.write("- %s | %s | vid %s | %s\n" % (datetime.date.today(), v["name"], v["vid"], txt[:160])); LATLOG.flush()
            stats["laterality-logged"] += 1
    # --- re-list and bypass everything bypassable with FRESH ids ---
    t2 = listbatch(bid) if dirty else t
    for v in parse(t2):
        if v["status"] not in ("ERROR", "PENDING", ""): continue
        ids = [eid for eid, txt, num in v["errs"] if pattern_of(txt) in BYPASSABLE]
        other = [(pattern_of(txt), txt[:80]) for eid, txt, num in v["errs"] if pattern_of(txt) not in BYPASSABLE]
        if ids:
            ok = bypass(v["vid"], ids)
            stats["bypassed-visits"] += 1; stats["bypassed-errs"] += len(ids)
            if not ok: L("BYPASS FAULT %s %s" % (v["vid"], v["name"]))
        if other:
            L("LEFT %s %s: %s" % (v["vid"], v["name"], other))
    time.sleep(0.3)

L("stats: %s" % dict(stats))
L("held: %s" % held)
json.dump(held, open("insp_held_0911.json","w"))