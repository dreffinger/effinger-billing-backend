# PLAIN ENGLISH (Claimocity backlog import, William 10/28/2026 02:23 ET: "enter all of these encounters into advanced md
#   and bill them out, i dont care if we get duplicates later" - Gregg's pickup paused).
# Decides: for every DFT^P03 message in the 10/16-10/27 SFTP files whose patient has an AMD chart, creates the visit with
#   its charges (updvisitwithnewcharges on a NEW visit: id=""), diagnosis list, admission date on hospital stays, modifier
#   25 on 99497 / 99489 as the practice's existing charges carry it, facility/POS/profile copied from how the feed's own
#   earlier visits look in AMD. Charges enter Charge Review (approval=1, inspector on) like any feed charge.
# Dedupe: a feed line whose patient already has a live (non-void) charge with the same CPT + DOS is skipped.
# Never touches: insurance plans (the cascade/precheck step verifies them afterwards), existing visits, patients without a chart.
# Usage: python3 feed_import_1028.py --dry | --one <feed pid> | --all [--limit N]
import os as _os
STAMP = _os.environ.get("FEED_STAMP", "1028")            # batch stamp: every feed_*_<STAMP>.* file and register belongs to one ingest run
HL7_DIR = _os.environ.get("FEED_HL7_DIR", "/tmp/claude-0/-home-claude/b8abe0d4-8133-5488-ad3a-bd2fb16f50f8/scratchpad/hl7/claimocity_oct")
DXCACHE = _os.environ.get("FEED_DX_CACHE", "dx_cache_feed.json")   # ICD-10 -> dcode map shared by every run (null = not in AMD's table)
CHART_PREFIX = _os.environ.get("FEED_CHART_PREFIX", "F" + STAMP)   # chart-number series for charts this run creates
import amd, resave, txh, re, json, sys, time, datetime, collections
import xml.etree.ElementTree as ET
PARSED = json.load(open(("feed_parsed_%s.json" % STAMP)))
MATCH = json.load(open(("feed_match_%s.json" % STAMP)))
DX = json.load(open(DXCACHE))
REG = ("registers/feed_import_%s.json" % STAMP)
PCODE = {"99487": "pcode492676", "99489": "pcode492677", "99223": "pcode65084", "99232": "pcode65089", "99233": "pcode65090",
         "99239": "pcode65095", "99497": "pcode492667", "99498": "pcode492668", "99306": "pcode65116", "99308": "pcode65118",
         "99309": "pcode65119", "99316": "pcode65122", "99344": "pcode601053"}
FEE = {"99223": "310.00", "99232": "111.00", "99233": "160.00", "99239": "163.00", "99306": "256.00", "99308": "107.00", "99309": "141.00",
       "99487": "206.00", "99489": "109.00", "99497": "133.00", "99344": "300.00", "99316": "207.00", "99498": "115.00"}
PROFILE = {"1225327380": "prof13", "1235128869": "prof15"}          # Effinger DO / Garland-G ARNP
FAC = {"HCA Florida Capital Hospital": ("fac29", "21"), "BRYNWOOD OPERATIONS LLC": ("fac34", "31"), "Aspire of Tallahassee": ("fac32", "31"),
       "Centre Pointe Health And Rehab Center": ("fac33", "31"), "Westminster Oaks-Bertrand Health Center": ("fac58", "31"),
       "Oakes Southwood": ("fac1350", "31"), "Azalea Gardens ALF": ("fac37", "13"), "Tapestry Senior Living Lakeshore": ("fac55", "13"),
       "Opal Hermitage Boulevard ALF": ("fac53", "13"), "Capital Square at Tallahassee": ("fac54", "13"), "Canterfield of Tallahassee ALF": ("fac38", "13"),
       "Sodalis Senior Living ALF": ("fac65", "13"), "Allegro Senior Living ALF": ("fac57", "13")}
HOSP = {"99221", "99222", "99223", "99231", "99232", "99233", "99238", "99239"}
MOD25 = {"99497", "99489"}
def mdy(yyyymmdd):
    return "%s/%s/%s" % (yyyymmdd[4:6], yyyymmdd[6:8], yyyymmdd[0:4])
# facility per feed message (MSH-4) and provider NPI per message (PV1-7) re-read from the raw files
import glob
FACOF = {}; NPIOF = {}; ADMIT = {}
for f in glob.glob((HL7_DIR + "/*.hl7")):
    raw = open(f, errors="replace").read().replace("\r", "\n")
    for b in re.split(r"(?m)^(?=MSH\|)", raw):
        if not b.startswith("MSH|"): continue
        msh = b.split("\n")[0].split("|"); fac = msh[3].split("^")[-1]; pid = None
        for line in b.split("\n"):
            s = line.split("|")
            if s[0] == "PID": pid = s[3]; FACOF[pid] = fac
            if s[0] == "PV1" and pid:
                NPIOF[pid] = s[7].split("^")[0] if len(s) > 7 else ""
                ADMIT[pid] = s[44] if len(s) > 44 else ""
_ctx = {}
def chart_ctx(pid):
    """episode, respparty, refplan, insorder, live {(cpt,dos)} from the chart's own history/detail."""
    if pid in _ctx: return _ctx[pid]
    num = re.sub(r"\D", "", pid)
    root = txh.fetch(num)
    live = set(); sample = None; newest = ""
    for c in root.iter("charge"):
        a = c.attrib
        if a.get("void") == "1" or (a.get("fee") or "").startswith("-"): continue
        live.add((a.get("proccode"), a.get("dos")))
        if (a.get("dos") or "") > newest or sample is None:
            newest = a.get("dos") or ""; sample = a.get("id")
    ctx = {"live": live, "episode": "", "resp": "", "refplan": "", "insorder": ""}
    r = amd.post('<ppmdmsg action="getdemographic" class="demographics" msgtime="%s" patientid="%s" nocookie="1"/>' % (amd._msgtime(), pid))
    p = re.search(r'<patient [^>]*>', r); a = dict(re.findall(r'(\w+)="([^"]*)"', p.group(0))) if p else {}
    ctx["resp"] = a.get("respparty", ""); ctx["insorder"] = a.get("insorder", "") or "1"; ctx["deceased"] = a.get("deceased", "")
    pl = re.findall(r'<insplan id="(ins\d+)" carrier="(car\d+)" begindate="([^"]*)" enddate="([^"]*)"[^>]*sequence="(\d+)"', r)
    ctx["plans"] = pl
    if sample:
        d = ET.fromstring(resave.detail(re.sub(r"\D", "", sample)))
        v = d.find(".//visit")
        if v is not None:
            ctx["episode"] = v.get("episode", ""); ctx["refplan"] = v.get("refplan", "")
            if not ctx["resp"]:
                ch = [e for e in d.iter("charge")]
                if ch: ctx["resp"] = ch[0].get("respparty", "")
    _ctx[pid] = ctx
    return ctx
# One face-to-face E/M per patient per day: a charge already on the chart for the same DOS from the same visit family IS this encounter,
# whatever level or new/established code it ended up with (the Claim Inspector swaps a second new-patient code to 99349; coders change
# levels). 10/30/2026: two 9/2 home visits were entered twice because the feed said 99344 and the chart carried 99349.
EM_FAMILY = [set("99341 99342 99344 99345 99347 99348 99349 99350".split()),            # home / ALF visits
             set("99221 99222 99223 99231 99232 99233 99238 99239 99234 99235 99236".split()),   # hospital
             set("99304 99305 99306 99307 99308 99309 99310 99315 99316".split()),      # SNF / NF
             set("99202 99203 99204 99205 99212 99213 99214 99215".split())]            # office
# (CCM 99487 + its add-on 99489 and ACP 99497/99498 legitimately share a DOS - those stay on the exact code + DOS rule)
def same_encounter(cpt, dos, live):
    fam = next((f for f in EM_FAMILY if cpt in f), None)
    if not fam: return False
    return any(lc in fam and ld == dos for lc, ld in live)
def build(msg, ctx):
    fid = msg["pid"]; fac, pos = FAC.get(FACOF.get(fid, ""), ("", "31"))
    prof = PROFILE.get(NPIOF.get(fid, ""), "prof13")
    lines = []
    for c in msg["FT1"]:
        cpt = c["cpt"]
        if cpt not in PCODE: return None, "unknown CPT %s" % cpt
        if (cpt, mdy(c["dos"][:8])) in ctx["live"]: continue        # dedupe: same code, same DOS
        if same_encounter(cpt, mdy(c["dos"][:8]), ctx["live"]): continue   # dedupe: same E/M family, same DOS (10/30: 99344 vs the inspector's 99349)
        lines.append(c)
    if not lines: return None, "all lines already in AMD"
    dos = mdy(lines[0]["dos"][:8])
    chg = ""
    cpts = [c["cpt"] for c in lines]
    missing_dx = set()
    for c in lines:
        dcodes = []
        for code in c["dx"].split("^"):
            if DX.get(code): dcodes.append(DX[code])
            elif code: missing_dx.add(code)
        if not dcodes: return None, "no usable dx for %s" % c["cpt"]
        mod = "mcode7" if c["cpt"] in MOD25 and len(cpts) > 1 else ""
        fee = FEE[c["cpt"]]; d = mdy(c["dos"][:8])
        dcodes = dcodes[:12]
        chg += ('<charge id="" respparty="%s" begindate="%s" enddate="%s" diagcodes="%s" modcodes="%s" aging="%s" billins="1" proccode="%s" cobcode="" pos="%s" tos="01" '
                'units="%s" netfee="0" fee="%s" allowed="%s" patportion="0.00" insportion="%s" patbalance="0.00" insbalance="%s" finclasscode="MC" lineitemnote="">'
                '<diagcodelist>%s</diagcodelist></charge>') % (ctx["resp"], d, d, " ".join(dcodes), mod, d, PCODE[c["cpt"]], pos, c["units"] or "1", fee, fee, fee, fee,
                "".join('<diagcode id="%s"/>' % re.sub(r"\D", "", x) for x in dcodes))
    ext = ""
    if any(c in HOSP for c in cpts) and ADMIT.get(fid):
        ext = '<extins hospitalizationfrom="%s"/>' % mdy(ADMIT[fid][:8])
    onh = "1" if ext else "0"
    # two-step create (proven 10/28/2026 on pat17476917 vst19458732): addvisit <appt> makes the empty visit, then
    # updvisitwithnewcharges on that visit id adds the charges. VISIT_ID is substituted by the caller.
    vis = ('<visit id="%%VISIT%%" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" acceptassign="1" forcepaper="0" force="1">'
           '<chargelist>%s</chargelist>%s</visit>') % (dos, prof, fac, ctx["refplan"], ctx["insorder"], onh, chg, ext)
    body = amd.msg("updvisitwithnewcharges", "chargeentry",
                   {"patientid": ctx["pid"], "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1",
                    "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, vis)
    appt = ('<appt id="" patient="%s" episode="%s" date="%s" profile="%s" facility="%s" refplan="%s" insorder="%s" onhcfa="%s" '
            'acceptassign="1" forcepaper="0" isappt="0" note="" billingnote="" referenceid=""/>') % (ctx["pid"], ctx["episode"], dos, prof, fac, ctx["refplan"], ctx["insorder"], onh)
    create = amd.msg("addvisit", "chargeentry", {"patientid": ctx["pid"], "episodeid": ctx["episode"], "approval": "1", "inspectorenabled": "1",
                     "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, appt)
    return (create, body), {"dos": dos, "cpts": cpts, "fac": fac, "pos": pos, "prof": prof, "admit": ADMIT.get(fid, ""), "missing_dx": sorted(missing_dx)}
def main():
    a = sys.argv[1:]; dry = "--dry" in a; one = a[a.index("--one") + 1] if "--one" in a else None
    limit = int(a[a.index("--limit") + 1]) if "--limit" in a else 10 ** 9
    amd.login_cached()
    reg = json.load(open(REG)) if __import__("os").path.exists(REG) else {"created": [], "skipped": [], "failed": []}
    # a feed id is the PATIENT (PID-3), not the message: dedupe on (patient, DOS, CPT set) - the live-charge check is the backstop.
    # EVERY earlier batch register counts (a visit re-dated after its import, e.g. the CCI 24078 re-dates, no longer matches the feed DOS
    # in AMD, so the live check alone would create it again - 10/29/2026 dry run).
    import glob as _glob
    done = set()
    for rf in _glob.glob("registers/feed_import_*.json"):
        if rf.endswith("_decisions.json"): continue
        try: prior = json.load(open(rf))
        except Exception: continue
        done |= {(r["feed_id"], r["dos"], tuple(sorted(r["cpts"]))) for r in prior.get("created", []) if r.get("feed_id")}
        done |= {(r["feed_id"], r["dos_feed"], tuple(sorted(r["cpts"]))) for r in prior.get("created", []) if r.get("feed_id") and r.get("dos_feed")}   # re-dated visits keep their feed DOS here
        if rf == REG: done |= {(r["feed_id"], None, None) for r in prior.get("skipped", [])}
    # deceased guard before any write: a DOS after the cached date of death is never entered (William's standing rule)
    _dc = {}
    for _p in [__import__("os").environ.get("DECEASED_CACHE", ""), "deceased_cache_local.json", "registers/deceased_cache.json"]:
        if _p and __import__("os").path.exists(_p):
            try: _dc = json.load(open(_p)); break
            except Exception: pass
    def _dod(pid):
        v = _dc.get(re.sub(r"\D", "", pid)) or {}
        d = v.get("dod") or ""
        return d if re.match(r"\d{4}-\d{2}-\d{2}$", d) else None
    n = 0; stats = collections.Counter()
    for msg in PARSED:
        fid = msg["pid"]
        if one and fid != one: continue
        mkey = (fid, mdy(msg["FT1"][0]["dos"][:8]), tuple(sorted(c["cpt"] for c in msg["FT1"])))
        if mkey in done or (fid, None, None) in done: stats["already created"] += 1; continue
        k = msg["name"].upper().strip() + "|" + msg["dob"][:8]; pid = MATCH.get(k, {}).get("resolved")
        if not pid: stats["no chart"] += 1; continue
        if n >= limit: break
        try:
            dod = _dod(pid)
            if dod and any(c["dos"][:8] > dod.replace("-", "") for c in msg["FT1"]):
                stats["DOS after date of death - not entered"] += 1; reg["skipped"].append({"feed_id": fid, "pid": pid, "why": "DOS after date of death %s (deceased cache) - never billed" % dod}); json.dump(reg, open(REG, "w"), indent=1); continue
            ctx = chart_ctx(pid); ctx["pid"] = pid
            if ctx.get("deceased"):
                stats["deceased chart - held"] += 1; reg["skipped"].append({"feed_id": fid, "pid": pid, "why": "deceased flag on chart - William"}); continue
            body, info = build(msg, ctx)
            if body is None:
                stats["skip: " + info] += 1; reg["skipped"].append({"feed_id": fid, "pid": pid, "why": info}); continue
            n += 1
            if dry:
                print("DRY", pid, info); stats["dry"] += 1; continue
            create, body = body
            r0 = amd.post(create, timeout=120)
            vm = re.search(r'<visit id="(vst\d+)"', r0)
            if not vm:
                stats["FAULT create"] += 1; reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "err": "addvisit: " + re.sub(r"\s+", " ", r0[:500])})
                print("FAULT addvisit", pid, info["dos"], re.sub(r"\s+", " ", r0[:200])); json.dump(reg, open(REG, "w"), indent=1); continue
            r = amd.post(body.replace("%VISIT%", vm.group(1)), timeout=180)
            if "Fault" in r or 'success="0"' in r:
                stats["FAULT"] += 1; reg["failed"].append({"feed_id": fid, "pid": pid, "info": info, "empty_visit": vm.group(1), "err": re.sub(r"\s+", " ", r[:600])})
                print("FAULT", pid, info["dos"], info["cpts"], re.sub(r"\s+", " ", r[:300]))
            else:
                vid = re.search(r'<visit id="(vst\d+)"', r); cids = re.findall(r'<charge id="(charge\d+)"', r)
                fees = re.findall(r'<charge [^>]* fee="([^"]*)"', r)
                if info["admit"] and any(c in HOSP for c in info["cpts"]):
                    # the extins child is ignored on create - write the admission date with the proven updextrainsinfo shape
                    for cpt in info["cpts"]:
                        if cpt in HOSP:
                            ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" employment="0" '
                                   'autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>') % (cpt, mdy(info["admit"][:8]))
                            re_ = amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": vm.group(1), "nocookie": "1"}, ext), timeout=120)
                            info["admit_written"] = "Fault" not in re_ and 'hospitalizationfrom="%s"' % mdy(info["admit"][:8]) in re_
                reg["created"].append({"feed_id": fid, "pid": pid, "visit": vid.group(1) if vid else "", "charges": cids, "fees": fees, "at": datetime.datetime.utcnow().isoformat(), **info})
                for cpt in info["cpts"]: ctx["live"].add((cpt, info["dos"]))
                stats["created"] += 1; stats["charge lines"] += len(cids)
                print("OK", pid, info["dos"], info["cpts"], vid.group(1) if vid else "?", cids, fees)
            json.dump(reg, open(REG, "w"), indent=1)
            time.sleep(0.6)
        except Exception as e:
            stats["error"] += 1; reg["failed"].append({"feed_id": fid, "pid": pid, "err": str(e)[:400]}); print("ERR", pid, str(e)[:200])
            json.dump(reg, open(REG, "w"), indent=1)
        if n % 25 == 0 and n: print("progress", n, dict(stats))
    print("DONE", dict(stats))
if __name__ == "__main__": main()
