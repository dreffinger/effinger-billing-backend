#!/usr/bin/env python3
# PLAIN ENGLISH (board input of 10/22-23/2026 - the three HCA facesheets William pasted + the StudentResources carrier he added)
# Decides: nothing new. For each chart William answered on the Insurance Refresh Board tonight it adds the plan(s) from the
#   facesheet (no group numbers), runs AMD's free 271 on each new plan, sets the patient's default order, writes the HCA
#   admission date (10/12/2026) + onhcfa=1 + the visit insurance order with a FULL-visit echo (void trap), and releases the
#   visits from Unbilled. A plan whose 271 answers INACTIVE holds the chart (William's turn). Levin: the UNI20 plan carrying the
#   StudentResources id is moved to the new UNI98 carrier in place and the 2/26/2026 99223 is re-sent as an original.
#   python3 board_act_1023.py            # dry: show the plan
#   python3 board_act_1023.py --live     # do it, register -> registers/board_act_1023.json
import amd, add_ins, ins_update, resave, payreasons, elig_amd, freq1_visit, json, re, sys, time, datetime
import xml.etree.ElementTree as ET

LIVE = "--live" in sys.argv
STAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
ADMIT = "10/12/2026"
CHARTS = [tuple(x) for x in json.load(open("board_act_1023_input.json"))["charts"]]   # chart ids + plans from the facesheets - local file, never committed (PHI)
REG = {"run": STAMP, "live": LIVE, "charts": [], "levin": {}}


def L(m):
    print(m, flush=True)


def plans(pid):
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}))
    root = ET.fromstring(r.encode("latin-1", "ignore"))
    pat = root.find(".//patient")
    pl = []
    for p in root.iter("insplan"):
        pl.append({k: p.get(k) for k in ("id", "sequence", "carrier", "subscribernum", "begindate", "enddate")})
    return pat, pl


def unbilled_visits():
    """(pid -> [(vid, cid, dos, cpt)]) from the live Unbilled list."""
    out = {}
    for r in payreasons.unbilled_rows(all_rows=True):
        if "Insurance order is missing" not in (r.get("errors") or ""):
            continue
        out.setdefault(r["pid"], []).append(r)
    return out


def set_admit(vid, cpt, admit):
    ext = ('<extins txtChargeCode="%s" hospitalizationfrom="%s" patsignature="1" emergency="0" epsdt="0" payprov="1" '
           'employment="0" autoaccident="0" otheraccident="0" pregnant="0" outsidelab="0"/>') % (cpt, admit)
    return amd.post(amd.msg("updextrainsinfo", "chargeentry", {"visitid": vid, "nocookie": "1"}, ext))


def full_resave(cid, order, admit):
    """Full-visit echo (every live charge), visit insorder=order, onhcfa=1, extins hospitalizationfrom=admit."""
    vis, pat, allc = resave.visit_charges(re.sub(r"\D", "", str(cid)))
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None:
                a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib)
    va["insorder"] = order; va["onhcfa"] = "1"; va["force"] = "1"
    for k in list(va):
        if va[k] is None: del va[k]
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    body = amd.msg("updvisitwithcharges", "chargeentry",
                   {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
                    "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
                   "<visit %s><chargelist>%s</chargelist>%s</visit>" % (vs, chg, resave._extins_xml(vis, admit)))
    return amd.post(body), len(allc)


def check_visit(cid):
    x = resave.detail(cid); root = ET.fromstring(x); vis = root.find(".//visit"); e = vis.find("extins")
    charges = [c for c in vis.findall(".//charge")]
    return {"insorder": vis.get("insorder"), "onhcfa": vis.get("onhcfa"), "hf": e.get("hospitalizationfrom") if e is not None else None,
            "void": [c.get("void") for c in charges]}


def work_chart(pid, adds, unb):
    rec = {"pid": pid, "adds": [], "elig": [], "visits": []}
    pat, pl = plans(pid)
    L("== chart %s %s: %d existing plan(s): %s" % (pid, pat.get("name"), len(pl), [(p["carrier"], p["subscribernum"], p["sequence"], p["enddate"]) for p in pl]))
    seqs = []
    hold = None
    for car, code, member, begin, fincl in adds:
        have = [p for p in pl if p["carrier"] == car and p["subscribernum"] == member]
        if have:
            L("   plan %s %s already on the chart (ins %s seq %s) - not added again" % (code, member, have[0]["id"], have[0]["sequence"]))
            insid, seq = have[0]["id"], have[0]["sequence"]
        elif not LIVE:
            L("   dry: would add %s (%s) member %s begin %s finclass %s" % (code, car, member, begin, fincl)); insid, seq = "insDRY", "?"
        else:
            insid, seq = add_ins.add(pid, car, member, begin, "1", fincl)
            L("   add_ins %s %s -> %s seq %s" % (code, member, insid, seq))
            if not insid:
                rec["adds"].append({"code": code, "member": member, "error": seq}); hold = "add_ins failed: %s" % seq; continue
            time.sleep(0.5)
        rec["adds"].append({"code": code, "member": member, "insid": insid, "seq": seq})
        seqs.append(str(seq))
        if LIVE and insid.startswith("ins"):
            try:
                s = elig_amd.run_plan(pid, insid.replace("ins", ""), True)
                line = elig_amd.one_line(s); rec["elig"].append({"code": code, "insid": insid, "status": s.get("status"), "line": line})
                L("   AMD 271 %s -> %s" % (code, line[:220]))
                if (s.get("status") or "").upper().startswith("INACTIVE") and code != "TRI05":
                    hold = "%s 271 INACTIVE" % code
            except Exception as e:
                rec["elig"].append({"code": code, "insid": insid, "error": str(e)[:200]}); L("   AMD 271 %s failed: %s" % (code, str(e)[:120]))
    order = ",".join(seqs)
    rec["order"] = order
    if hold:
        rec["hold"] = hold; L("   HOLD - %s; nothing released" % hold); return rec
    if LIVE:
        okp, mp = ins_update.update(pid, rec["adds"][0]["insid"], sequence=order)
        rec["patient_order"] = (okp, mp); L("   patient order %s -> %s %s" % (order, okp, mp[:160]))
    rows = unb.get(pid, [])
    L("   Unbilled rows: %s" % [(r["visitid"], (r.get("charges") or [{}])[0].get("id"), (r.get("charges") or [{}])[0].get("dos"), (r.get("charges") or [{}])[0].get("chgcode")) for r in rows])
    for r in rows:
        ch = (r.get("charges") or [{}])[0]
        vid = str(r["visitid"]); cid = str(ch.get("id") or ""); cpt = ch.get("chgcode") or ""
        v = {"vid": vid, "cid": cid, "dos": (ch.get("dos") or "").strip(), "cpt": cpt, "fee": ch.get("fee")}
        if not LIVE:
            v["plan"] = "dry: admit %s, insorder %s, onhcfa 1, release" % (ADMIT, order); rec["visits"].append(v); L("   %s" % v); continue
        ra = set_admit(vid, cpt, ADMIT); v["updextrainsinfo"] = "ok" if "Fault" not in ra else re.sub(r"\s+", " ", ra[:200])
        rr, n = full_resave(cid, order, ADMIT); v["resave"] = ("ok (%d charge(s) echoed)" % n) if "Fault" not in rr else re.sub(r"\s+", " ", rr[:300])
        time.sleep(0.5)
        st = check_visit(cid); v["after"] = st
        ok = st["insorder"] == order and st["onhcfa"] == "1" and (st["hf"] or "").startswith(ADMIT[:5]) and "1" not in (st["void"] or [])
        v["release"] = payreasons.release_visit(vid) if ok else "held: verify failed %s" % st
        rec["visits"].append(v); L("   visit %s -> %s | %s | release %s" % (vid, v["resave"], st, v["release"]))
        time.sleep(0.4)
    return rec


def work_levin(unused=None):
    pid = "17475632"; rec = {"pid": pid}
    r = amd.post(amd.msg("lookupcarrier", "lookup", {"code": "%UNI98%", "nocookie": "1"}))
    cars = re.findall(r'<carrier id="(car\d+)" code="([^"]*)" name="([^"]*)" cpid="([^"]*)"', r)
    L("== Levin: lookupcarrier %%UNI98%% -> %s" % (cars[:3] if cars else re.sub(r"\s+", " ", r[:300])))
    rec["lookupcarrier"] = cars[:3] if cars else re.sub(r"\s+", " ", r[:300])
    car = None
    for c in cars:
        if isinstance(c, tuple) and c[1].upper().startswith("UNI98"): car = c[0]
    pat, pl = plans(pid)
    L("   plans: %s" % [(p["id"], p["sequence"], p["carrier"], p["subscribernum"], p["enddate"]) for p in pl])
    rec["plans_before"] = pl
    target = [p for p in pl if p["subscribernum"] == json.load(open("board_act_1023_input.json"))["levin"]["member"]]
    if not car or not target:
        rec["hold"] = "carrier or plan not found (car=%s, plan=%s)" % (car, bool(target)); L("   HOLD %s" % rec["hold"]); return rec
    plan = target[0]
    if plan["carrier"] == car:
        L("   plan %s already on %s" % (plan["id"], car))
    elif LIVE:
        ok, m = ins_update.update(pid, plan["id"], carrier=car)
        rec["carrier_move"] = (ok, m); L("   ins_update carrier -> %s: %s %s" % (car, ok, m[:200]))
        if not ok: rec["hold"] = "carrier move failed"; return rec
    else:
        L("   dry: would move plan %s (seq %s) from %s to %s" % (plan["id"], plan["sequence"], plan["carrier"], car))
    # the 2/26/2026 99223
    body = amd.msg("gettxhistory", "demographics", {"patientid": pid, "filterhistory": "0", "pagenumber": "1", "typefilter": "0", "sortbypayment": "false", "groupbyvisit": "0", "sortdescending": "1", "visitid": "0", "profileid": "", "getmemo": "false", "nocookie": "1"})
    th = ET.fromstring(amd.post(body, timeout=120).encode("latin-1", "ignore"))
    hits = [(c.get("visit"), c.get("id"), c.get("dos"), c.get("proccode"), c.get("fee"), c.get("carrier"), c.get("billdate")) for c in th.iter("charge")
            if (c.get("dos") or "").startswith(json.load(open("board_act_1023_input.json"))["levin"]["dos"]) and c.get("void") != "1"]
    L("   2/26/2026 charges: %s" % hits); rec["charges"] = hits
    if LIVE and hits and "hold" not in rec:
        vid, cid = hits[0][0], hits[0][1]
        res = freq1_visit.run(re.sub(r"\D", "", vid), re.sub(r"\D", "", cid), plan["sequence"])
        rec["freq1"] = str(res)[:300]; L("   freq1_visit.run -> %s" % str(res)[:200])
    return rec


if __name__ == "__main__":
    amd.login_cached()
    unb = unbilled_visits()
    for pid, adds in CHARTS:
        try:
            REG["charts"].append(work_chart(pid, adds, unb))
        except Exception as e:
            REG["charts"].append({"pid": pid, "error": str(e)[:300]}); L("   ERROR %s: %s" % (pid, str(e)[:200]))
    try:
        REG["levin"] = work_levin()
    except Exception as e:
        REG["levin"] = {"error": str(e)[:300]}; L("   Levin ERROR %s" % str(e)[:200])
    if LIVE:
        json.dump(REG, open("registers/board_act_1023_%s.json" % STAMP, "w"), indent=1)
    print(json.dumps(REG, indent=1)[:6000])
