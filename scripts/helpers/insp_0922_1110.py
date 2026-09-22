# PLAIN ENGLISH (Claim Inspector pass, 7am ET 9/22/2026 run 2026-09-22T1110Z): 93 visits on 67 batches. 82 of them are
#   charts the 9/22 chat session wrote off this morning (registers/writeoffs_posted_2026-09-22.json - every balance read back
#   at $0): the write-off posting re-inspected them and they surfaced with ADVISORY patterns only (20657 timely, 33799 MUE,
#   3429/7011 CCM frequency, 11256 unspecified laterality) plus one Pattern 20389 (R65.21 severe sepsis leading the dx list,
#   pat17476020 v19439282). The other 11 are pat17472874's April-2026 stay (Hospitalization From Date empty) held for
#   William's admission date - untouched.
# Decides, per visit: (1) PRIMARY-DX cascade on the 20389 visit - dx_primary_fix.plan (R65.2x added to never_primary this
#   run) applied with a plain full-visit resave (save_visit_dx: every live charge echoed by id, NO rebill - the visit is
#   written off, nothing goes to a payer); (2) HOLD anything that carries a data error (hospitalization date); (3) re-list
#   every batch and bypass ONLY advisory patterns with FRESH error ids; Pattern 11256 bypassed + logged to
#   laterality_flag_log.md; a 20389 that survives its dx fix is LEFT and reported, never bypassed.
# Deceased guard: no claim leaves this pass (every bypassed visit is at $0), so no date-of-death lookup is needed.
# Never touches: payments, write-offs, visits outside the inspector list, hospitalizationto, insurance plans, rebills.
"""Usage: python3 insp_0922_1110.py [--dry]"""
import amd, resave, dx_primary_fix, re, time, json, sys, datetime
import xml.etree.ElementTree as ET
DRY = "--dry" in sys.argv
STAMP = "2026-09-22T1110Z"
ADV = ("The Source of Payment you have chosen is not typical", "Pattern 23400", "Pattern 4426", "Pattern 4310", "Pattern 4311", "Pattern 35790", "Pattern 7011", "Pattern 3429", "Pattern 35777", "Pattern 33799", "Pattern 20657", "Pattern 27261")
amd.login_cached()
scan = json.load(open("scan_0912/summary_before.json"))
visits = [v for b in scan["inspector"].values() for v in b]
wotxt = json.dumps(json.load(open("registers/writeoffs_posted_2026-09-22.json")))
wov = set(re.findall(r'"?visit(?:id)?"?\s*:\s*"?(\d{5,9})', wotxt))
out = {"stamp": STAMP, "dry": DRY, "dxfix": [], "held": [], "bypassed": [], "left": []}
def L(m): print(m, flush=True)
# (1) primary-dx cascade on Pattern 20389 visits
for v in visits:
    if not any(e[1].startswith("Pattern 20389") for e in v["errs"]): continue
    vid, pid, cid0 = v["vid"], v["pid"], v["chgs"][0][0]
    rec = {"vid": vid, "pid": pid, "steps": []}
    def S(m): L("v%s pat%s %s" % (vid, pid, m)); rec["steps"].append(m)
    vis, pat, allc, m = dx_primary_fix.visit_dx(cid0)
    inv = {code: d for d, code in m.items()}; inv.setdefault("I10", dx_primary_fix.I10_DCODE)
    new = {}
    for c in allc:
        det = resave.detail(c.get("id").replace("charge", ""))
        pm = dict(re.findall(r'<proccode id="(pcode\d+)"[^>]*?\bcode="([^"]*)"', det))
        cpt = pm.get(c.get("proccode"), c.get("proccode"))
        dcodes = (c.get("diagcodes") or "").split(); codes = [m.get(d, d) for d in dcodes]
        act, newcodes = dx_primary_fix.plan(codes, cpt)
        S("%s %s dx %s -> plan %s %s (insbal %s, in write-off register %s)" % (c.get("id"), cpt, codes, act, newcodes, c.get("insbalance"), vid in wov))
        if act != "ok": new[c.get("id")] = [inv[x] for x in newcodes]
    if new:
        try:
            r = dx_primary_fix.save_visit_dx(cid0, new, dry=DRY); S("save_visit_dx -> %s" % str(r)[:300])
            v2, p2, c2 = resave.visit_charges(cid0); S("readback live=%d/%d dx=%s" % (len(c2), len(allc), [(x.get("id"), x.get("diagcodes")) for x in c2]))
            out["dxfix"].append(rec)
        except Exception as e:
            S("save_visit_dx FAILED %s" % e); out["held"].append(rec)
    else: out["held"].append(rec)
# (2) data-error holds
for v in visits:
    if any(e[1].startswith("Hospitalization From Date") for e in v["errs"]):
        out["held"].append({"vid": v["vid"], "pid": v["pid"], "why": "Hospitalization From Date empty - no 99223 anchor within 45 days (board row on William's turn)"})
json.dump(out, open("registers/insp_%s%s.json" % (STAMP, "_dry" if DRY else ""), "w"), indent=1)
if DRY: L("DRY done"); sys.exit()
# (3) re-list every batch and bypass advisories with fresh ids
time.sleep(4)
for attempt in range(3):
    ib = amd.call('action="getclaiminspectorbatches" class="chargeentry" nocookie="1"'); bids = re.findall(r'<batch id="([^"]+)"', ib); L("batches after (attempt %d): %d" % (attempt, len(bids)))
    left = []; did = 0
    for bid in bids:
        t = amd.post(amd.msg("getclaiminspectorcharges", "chargeentry", {"batchid": bid, "nocookie": "1"}), timeout=120)
        for vm in re.finditer(r'<visit id="(\d+)"([^>]*)>(.*?)</visit>', t, re.S):
            vid = vm.group(1); pid = (re.search(r'patientid="(\d+)"', vm.group(2)) or re.search(r'patient="pat(\d+)"', vm.group(2)))
            pid = pid.group(1) if pid else "?"
            errs = re.findall(r'<error id="(\d+)"[^>]*>([^<]{0,90})', vm.group(3))
            if not errs: continue
            adv = [e[0] for e in errs if e[1].startswith(ADV)]
            lat = [e[0] for e in errs if e[1].startswith("Pattern 11256")]
            ids = adv + lat
            if ids and len(ids) == len(errs):
                if lat: open("laterality_flag_log.md", "a").write("- %s run %s: v%s pat%s Pattern 11256 unspecified laterality bypassed\n" % (datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%MZ"), STAMP, vid, pid))
                r = amd.post(amd.msg("bypassclaimedits", "chargeentry", {"nocookie": "1"}, '<visitlist><visit id="%s"><claimeditlist>%s</claimeditlist></visit></visitlist>' % (vid, "".join('<claimedit id="%s"/>' % e for e in ids))))
                ok = "Fault" not in r
                L("  bypass b%s v%s pat%s %s -> %s" % (bid, vid, pid, [e[1][:30] for e in errs], "ok" if ok else re.sub(r"\s+", " ", r[:160])))
                if ok: did += 1; out["bypassed"].append({"bid": bid, "vid": vid, "pid": pid, "errs": [e[1][:40] for e in errs], "zero_balance": vid in wov})
            else: left.append((bid, vid, pid, errs)); L("  LEFT b%s v%s pat%s %s" % (bid, vid, pid, errs))
        time.sleep(0.2)
    if not did: break
    time.sleep(4)
out["left"] = left
json.dump(out, open("registers/insp_%s.json" % STAMP, "w"), indent=1)
L("DONE: dxfix %d, held %d, bypassed %d, left after bypass %d" % (len(out["dxfix"]), len(out["held"]), len(out["bypassed"]), len(left)))
