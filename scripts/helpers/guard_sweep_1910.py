# PLAIN ENGLISH (deceased-guard sweep, 3pm ET 9/23/2026 run 2026-09-23T1910Z): the Claimocity feed was still loading batch 127783 while
#   insp_0923_1910.py ran, so its bypass loop cleared advisory rows on visits that arrived AFTER the guard pass (v19455714+), and the
#   --bypass-only re-run did not carry the guard's held list, so v19455625 (pat17473477, DOS 9/20 after a 9/15 date of death) was bypassed
#   too. This sweep runs deceased_guard.check on every one of those visits; a BLOCKED visit gets a full-visit resave (no field changes,
#   force=1, inspectorenabled=1) so the inspector re-runs and the advisory comes back with a fresh id - the visit is back on hold and
#   will not leave on the next claim run. Register registers/guard_sweep_2026-09-23T1910Z.json + registers/insp_2026-09-23T1910Z_blocked.json.
# Never touches: diagnoses, modifiers, payments, insurance; nothing is bypassed here.
import amd, resave, txh, era_post, deceased_guard, re, json, time, sys, datetime
DRY = "--dry" in sys.argv
STAMP = "2026-09-23T1910Z"
amd.login_cached(); batch = era_post.batch()
def d(s): return datetime.datetime.strptime(s.strip()[:10], "%m/%d/%Y").date()
UNGUARDED = [("19455625", "17473477"), ("19455714", "17473347"), ("19455716", "12232248"), ("19455718", "17472741"), ("19455721", "17473343"),
    ("19455730", "48207"), ("19455733", "20407"), ("19455735", "17473669"), ("19455736", "17469645"), ("19455737", "17477134"), ("19455742", "17472553"),
    ("19455746", "20514"), ("19455747", "21020"), ("19455748", "23832"), ("19455749", "23617"), ("19455750", "17472397"), ("19455754", "23161"),
    ("19455756", "24208"), ("19455757", "17474614"), ("19455758", "17477496"), ("19455762", "17469466"), ("19455763", "17472556"), ("19455784", "17477830"),
    ("19455789", "17477829"), ("19455800", "17475198"), ("19455801", "17476681"), ("19455802", "25266"), ("19455807", "46048"), ("19455808", "17470875"),
    ("19455812", "17472285"), ("19455819", "22758"), ("19455820", "12182947"), ("19455829", "23204")]
def full_resave(cid):
    vis, pat, allc = resave.visit_charges(cid); chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, v) for k, v in a.items())
    va = dict(vis.attrib); va["force"] = "1"
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    r = amd.post(amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "batchid": str(batch), "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg)))
    time.sleep(0.8); v2, p2, c2 = resave.visit_charges(cid)
    ok = "Fault" not in r
    return ok, ("FAULT " + re.sub(r"\s+", " ", r[:200])) if not ok else "resaved live=%d/%d" % (len(c2), len(allc))
out = {"stamp": STAMP, "checked": [], "blocked": [], "errors": []}
blocked_vids = set()
for vid, pid in UNGUARDED:
    try:
        root = txh.fetch_visit(pid, vid)
        chs = [c for c in root.iter("charge") if c.get("void") != "1" and not (c.get("fee") or "").startswith("-")]
        if not chs: out["errors"].append((vid, pid, "no live charges in tx history")); print(vid, pid, "no live charges"); continue
        dos = d(chs[0].get("dos")); cid = re.sub(r"\D", "", chs[0].get("id") or "")
        blocked = False; why = ""
        for c in chs:
            b, w = deceased_guard.check(pid, dos.isoformat(), c.get("carrier") or "", c.get("proccode") or "", allow_lookup=not DRY)
            if b: blocked, why = True, w; break
        rec = {"vid": vid, "pid": pid, "dos": dos.isoformat(), "cpts": [c.get("proccode") for c in chs], "blocked": blocked, "why": why}
        out["checked"].append(rec); print(vid, pid, dos, rec["cpts"], "BLOCKED " + why if blocked else "clear", flush=True)
        if blocked:
            blocked_vids.add(vid)
            if DRY: rec["action"] = "DRY: would resave to re-inspect"
            else:
                ok, msg = full_resave(cid); rec["action"] = msg; print("   ", msg, flush=True)
            out["blocked"].append(rec)
        time.sleep(0.3)
    except Exception as e:
        out["errors"].append((vid, pid, str(e)[:200])); print(vid, pid, "ERROR", str(e)[:200], flush=True)
json.dump(out, open("registers/guard_sweep_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
if not DRY:
    prev = set(json.load(open("registers/insp_%s_blocked.json" % STAMP))) if __import__("os").path.exists("registers/insp_%s_blocked.json" % STAMP) else set()
    json.dump(sorted(prev | blocked_vids | {"19455625", "19455691"}), open("registers/insp_%s_blocked.json" % STAMP, "w"))
print("DONE: checked %d, blocked %d, errors %d" % (len(out["checked"]), len(out["blocked"]), len(out["errors"])))
