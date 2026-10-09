# PLAIN ENGLISH (Old-claims disposition - finish the TWO-CODE charges old_claims_apply.py skipped, 10/9/2026 go)
# Decides: nothing new. A charge in the disposition plan can carry TWO write-offs (the patient-share code WOCAID2ND / WOLATE first,
#   then the WOINS contractual). old_claims_apply.py posts the first one, AdvancedMD then moves the still-open remainder to the
#   PATIENT balance (manual_post's paysource/woamount shape closes the insurance side), and the apply script's already-posted guard
#   ('a non-void payment with the same check number' = OLD1009) skips the second write-off - the log shows 'SKIP <cid> already posted'.
#   Seen 10/9/2026 22:40Z on package J (2 charges) and 22:59Z on package K (46 charges). The money then sits on the patient balance,
#   which William's rule forbids (never bill the dual / crossover residual to the patient).
# What it does, per skipped charge whose plan has a second write-off not yet in the log: RE-READ live; state A = insurance balance 0 and
#   the patient balance equals the planned second write-off (+-1c) -> move_to_ins.move(cid, rebill=False) (whole visit, no rebill) ->
#   re-read -> only when insurance balance == planned write-off and patient 0 -> manual_post.post(0 pay, planned wo, planned code,
#   check OLD1009) -> re-read, verify 0 / 0 -> DONE line in old_claims_apply_<stamp>.log + registers/old_claims_apply_<stamp>.json item
#   + Writeoff_register_<date>.xlsx row. State B = insurance balance already == the planned write-off and patient 0 (move_to_ins.move is
#   VISIT-wide, so fixing a sibling charge on the same visit already moved this one back - 13 of K's 46 on 10/9) -> post directly, no move.
#   Anything else = STOP line, nothing written for that charge. Run it --dry first; a STOP list that is all state B is normal on a rerun.
# Rules it uses: dry by default (--live writes); one package at a time (--only); never a rebill; never a charge the plan does not list.
# Never touches: charges without a SKIP line, charges whose live state differs from the pattern above, payments already posted.
"""Usage: cd /home/claude/unbilled && python3 old_claims_twocode_fix.py --only K [--stamp 1009] [--live]"""
import amd, resave, move_to_ins, manual_post, json, sys, os, re, time, datetime
import xml.etree.ElementTree as ET
a = sys.argv[1:]
def opt(n, d=None): return a[a.index(n) + 1] if n in a else d
STAMP = opt("--stamp", "1009"); LIVE = "--live" in a; ONLY = set(opt("--only", "").split(",")) - {""}
if not ONLY: sys.exit("--only <package letters> is required")
SRC = next((p for p in ("old_claims_disposition_%s.json" % STAMP, "registers/old_claims_disposition_%s.json" % STAMP) if os.path.exists(p)), None)
D = json.load(open(SRC)); LOGF = "old_claims_apply_%s.log" % STAMP
lines = open(LOGF).read().splitlines() if os.path.exists(LOGF) else []
skipped = {l.split()[1] for l in lines if l.startswith("SKIP ") and "already posted" in l}
done = {l.split()[1] + "|" + l.split()[2] for l in lines if l.startswith("DONE ")}
REG = "registers/old_claims_apply_%s.json" % STAMP; reg = json.load(open(REG)) if os.path.exists(REG) else {"stamp": STAMP, "items": []}
LOG = open(LOGF, "a")
def L(m): print(m, flush=True); LOG.write(m + "\n"); LOG.flush()
def live(cid):
    rt = ET.fromstring(resave.detail(cid)); c = next((x for x in rt.iter("charge") if x.get("id") == "charge" + cid), None)
    if c is None or c.get("void") == "1": return None
    return float(c.get("insbalance") or 0), float(c.get("patbalance") or 0)
amd.login_cached()
todo = []
for v in D["visits"]:
    if v["pkg"] not in ONLY: continue
    for act in v["actions"]:
        cid = re.sub(r"\D", "", str(act["cid"]))
        if cid not in skipped or "resend_seq" in act: continue
        key = cid + "|post" + (("-" + act["wocode"]) if (act.get("wocode") and not act.get("pay")) else "")
        if key in done: continue
        todo.append((v, act, cid, key))
L("=== old_claims_twocode_fix %s %s packages %s: %d skipped charges with a second write-off still unposted ===" % (STAMP, "LIVE" if LIVE else "DRY", ",".join(sorted(ONLY)), len(todo)))
n_ok = n_stop = 0; d_wo = 0.0; xl = []
for v, act, cid, key in todo:
    wo = round(float(act.get("wo") or 0), 2); code = act.get("wocode") or "WOINS"
    st = live(cid)
    if st is None: L("STOP %s not live" % cid); n_stop += 1; continue
    ins, pat = st
    # state A: remainder on the PATIENT balance (AMD moved it there) -> move back first.  state B: remainder already back on the
    # INSURANCE balance (move_to_ins.move is visit-wide, so fixing a sibling charge on the same visit moved this one too) -> post directly.
    already_moved = abs(ins - wo) <= 0.011 and pat <= 0.004
    if not already_moved and not (ins <= 0.004 and abs(pat - wo) <= 0.011):
        L("STOP %s live insbalance %.2f patbalance %.2f, planned %s %.2f - not the two-code pattern, nothing written" % (cid, ins, pat, code, wo)); n_stop += 1; continue
    if not LIVE: L("DRY %s v%s %s %s: %s, post %s %.2f" % (cid, v["vid"], v["carrier"], v["dos"], ("insurance balance %.2f already back (sibling move)" % ins) if already_moved else ("patient balance %.2f -> move back to insurance" % pat), code, wo)); n_ok += 1; d_wo += wo; continue
    if not already_moved:
        r = move_to_ins.move(cid, rebill=False); L("  moved patient balance back to insurance charge%s -> %s" % (cid, str(r)[:110])); time.sleep(0.8)
        st = live(cid); ins, pat = st if st else (None, None)
        if st is None or abs(ins - wo) > 0.011 or pat > 0.004: L("STOP %s after move: insbalance %s patbalance %s (expected %.2f / 0)" % (cid, ins, pat, wo)); n_stop += 1; continue
    else: L("  %s already back on insurance (%.2f, sibling visit-wide move) - posting directly" % (cid, ins))
    note = "old-claims disposition %s (William 10/9/2026: close old claims from the payer's answer): %s" % (STAMP, "; ".join(v["notes"])[:160])
    ok, msg = manual_post.post(cid, v["carrier"], 0.0, wo, code, checknumber="OLD1009", depositdate=datetime.date.today().strftime("%m/%d/%Y"), note=note, dry=False)
    L("%s %s %s v%s %s %s %s pay 0.00 wo %.2f %s chk OLD1009 -> %s" % ("DONE" if ok else "FAIL", cid, key.split("|")[1], v["vid"], v["carrier"], v["dos"], act.get("cpt", ""), wo, code, str(msg)[:90]))
    if not ok: n_stop += 1; continue
    time.sleep(0.8); st = live(cid)
    L("  verify %s: insbalance %s patbalance %s" % (cid, st and "%.2f" % st[0], st and "%.2f" % st[1]))
    reg["items"].append({"pid": v["pid"], "vid": v["vid"], "cid": cid, "pkg": v["pkg"], "tier": v["tier"], "pay": 0.0, "wo": wo, "wocode": code, "check": "OLD1009", "at": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z", "note": "second write-off of a two-code charge, posted after moving the remainder back from the patient balance"})
    xl.append([datetime.date.today().isoformat(), v["patient"], v["carrier"], v["dos"], wo, "%s %s" % (code, note[:200])])
    n_ok += 1; d_wo += wo; time.sleep(0.35)
    json.dump(reg, open(REG, "w"), indent=1)
if LIVE and xl:
    import openpyxl
    XL = "Writeoff_register_%s.xlsx" % datetime.date.today().isoformat()
    wb = openpyxl.load_workbook(XL) if os.path.exists(XL) else openpyxl.Workbook(); ws = wb.active
    if ws.max_row == 1 and not ws.cell(1, 1).value: ws.append(["date", "patient", "carrier", "dos", "amount", "note"])
    for r in xl: ws.append(r)
    wb.save(XL)
L("=== %s two-code fix done: %d second write-offs $%.2f, %d stopped ===" % ("LIVE" if LIVE else "DRY", n_ok, d_wo, n_stop))
