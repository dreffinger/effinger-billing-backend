# PLAIN ENGLISH (Primary-diagnosis denial fix: "the diagnosis code cannot be billed in the primary position")
# Decides: For a visit whose FIRST diagnosis is a code a payer will not accept as principal (a manifestation /
#   "code first" code such as F01.5x vascular dementia or F02.8x dementia in other diseases, an external-cause code,
#   a sequela code, or a secondary-only Z code), what William's 9/14/2026 rule says to do, in this order:
#     1. DELETE the bad code if that works (another acceptable code is left to be primary and the claim keeps
#        enough diagnoses - CCM 99487/99489/99490/99491/99439/99437/G0511 needs at least two);
#     2. otherwise MOVE it out of the primary slot (to the end) so an acceptable code leads;
#     3. otherwise ADD I10 (essential hypertension, dcode1034543883) in front of it;
#   then RESUBMIT as an original claim (freq 1 + rebill).
# Rules it uses: full-visit resave (every live charge echoed - the void trap), never a visit with a real payment
#   posted, verify the saved diagnosis list before rebilling, one register line per visit.
# Never touches: the chart's problem list, carrier masters, charges outside the visits it is given.
# ---
"""Usage:
  python3 dx_primary_fix.py plan F01.50 F31.9 G47.00 G30.9 [--cpt 99487]      # show the decision only
  python3 dx_primary_fix.py <patientid> [--bad F01.50] [--visits v1,v2] [--dry]  # fix every OPEN visit of the patient
      --bad CODE   only visits whose primary dx is CODE (default: any never-primary code)
      --visits     restrict to these visit ids (comma separated)
      --dry        show the plan per visit, save nothing
Library: plan(codes, cpt) -> (action, new_codes); fix_visit(pid, vid, cid, seq, dry) -> result string.
"""
import amd, resave, txh, freq1_visit, era_post, json, re, sys, time, datetime, os
import xml.etree.ElementTree as ET

I10_DCODE = "dcode1034543883"          # I10 ESSENTIAL (PRIMARY) HYPERTENSION (the paid 2023-24 claims of pat44953)
CCM_CPTS = {"99487", "99489", "99490", "99491", "99439", "99437", "G0511", "99424", "99425", "99426", "99427"}
REGISTER = "registers/dx_primary_register.json"
LOG = open("dx_primary_fix.log", "a")
def L(m): print(m, flush=True); LOG.write("%s %s\n" % (datetime.datetime.utcnow().strftime("%m-%d %H:%M:%S"), m)); LOG.flush()

# Codes payers reject in the principal position (ICD-10-CM manifestation / "code first" codes, external causes,
# sequela 7th character, secondary-only Z codes).  Prefix match on the code without the dot.
_NEVER_PREFIX = (
    "F015", "F01A", "F01B", "F01C",          # vascular dementia - "code first" (Humana ZY3 on pat44953, 9/14/2026)
    "F028", "F02A", "F02B", "F02C",          # dementia in other diseases classified elsewhere (F03.9x is fine)
    "F54",                                    # psychological factors in diseases classified elsewhere
    "D630", "D631", "D638", "D77", "E35",     # anemia / blood / endocrine disorders in diseases classified elsewhere
    "G02", "G05", "G07", "G13", "G32", "G53", "G55", "G59", "G63", "G737", "G94", "G99",
    "H22", "H28", "H32", "H36", "H42", "H62", "H67", "H82",
    "I32", "I39", "I43", "I52", "I68", "I79", "J17", "J910", "J99", "K23", "K77", "K87", "K93",
    "L14", "L45", "L54", "L62", "L86", "L99", "M01", "M146", "M148", "M360", "M361", "M362", "M363", "M364", "M368",
    "M49", "M63", "M68", "M73", "M82", "M90", "N08", "N16", "N22", "N29", "N33", "N37", "N51", "N74", "N77",
    "P75",
    "R652",                                   # R65.20/R65.21 severe sepsis - "code first" underlying infection (inspector Pattern 20389 on pat17476020, 9/22/2026)
)
_Z_SECONDARY_ONLY = ("Z16", "Z17", "Z18", "Z19", "Z22", "Z55", "Z56", "Z57", "Z58", "Z59", "Z60", "Z62", "Z63", "Z64", "Z65",
                     "Z66", "Z67", "Z68", "Z77", "Z78", "Z79", "Z80", "Z81", "Z82", "Z83", "Z84", "Z85", "Z86", "Z87", "Z88",
                     "Z89", "Z90", "Z91", "Z92", "Z93", "Z94", "Z95", "Z96", "Z97", "Z98", "Z99")

def never_primary(code):
    """True when ICD-10-CM / payers will not accept `code` as the principal (first-listed) diagnosis."""
    c = (code or "").upper().replace(".", "").strip()
    if not c: return False
    if c[0] in "VWXY" and c[1:2].isdigit(): return True          # external cause V00-Y99
    if c[0] in "ST" and len(c) == 7 and c[-1] == "S": return True  # sequela of injury: the sequela condition goes first
    if c.startswith(_Z_SECONDARY_ONLY): return True
    return c.startswith(_NEVER_PREFIX)

def plan(codes, cpt=None):
    """William's cascade on a list of ICD-10 codes (first = primary). Returns (action, new_codes).
    action: 'ok' (nothing to do), 'delete', 'move', 'add-i10'."""
    codes = [x for x in codes if x]
    if not codes or not never_primary(codes[0]): return "ok", codes
    bad = codes[0]; rest = codes[1:]
    rest_ok = [c for c in rest if not never_primary(c)]
    needs_two = (cpt or "").upper() in CCM_CPTS
    def lead_with_ok(lst):
        first = [c for c in lst if not never_primary(c)][0]
        return [first] + [c for c in lst if c != first]
    if rest_ok and (len(rest) >= 2 or not needs_two):
        return "delete", lead_with_ok(rest)                 # 1. delete the bad code - it works
    if rest_ok:
        return "move", lead_with_ok(rest) + [bad]           # 2. move it out of the primary slot
    return "add-i10", ["I10"] + codes                        # 3. put I10 in its place

def _dxmap(root):
    return {d.get("id"): (d.get("code") or "") for d in root.iter("diagcode") if d.get("id")}

def visit_dx(cid):
    """(vis, pat, [charge elems], {dcode: code}) for the visit owning charge cid."""
    vis, pat, allc = resave.visit_charges(cid)
    m = {}
    for c in allc:
        r = ET.fromstring(resave.detail(c.get("id").replace("charge", "")))
        m.update(_dxmap(r))
    return vis, pat, allc, m

def live_state(pid, vid):
    out = []
    for c in txh.fetch(pid).iter("charge"):
        if c.get("visit") != str(vid) or c.get("void") == "1": continue
        pays = [p for p in c.iter("payment") if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
        wos = [w for w in c.iter("writeoff") if w.get("void") != "1" and float(w.get("amount") or 0) != 0]
        out.append({"cid": c.get("id"), "pays": len(pays), "wos": len(wos), "insbal": float(c.get("insbal") or 0),
                    "patbal": float(c.get("patbal") or 0), "cpt": c.get("proccode"), "dos": c.get("dos")})
    return out

def save_visit_dx(cid, new_dcodes_by_charge, dry=False):
    """Full-visit resave with an explicit dcode list per charge id ({'charge123': ['dcode..', ...]})."""
    vis, pat, allc = resave.visit_charges(cid)
    chg = ""; edited = 0
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            if c.get(f) is not None: a[f] = c.get(f)
        child = ""
        new = new_dcodes_by_charge.get(c.get("id"))
        if new is not None and new != (c.get("diagcodes") or "").split():
            a["diagcodes"] = " ".join(new); edited += 1
            child = "<diagcodelist>%s</diagcodelist>" % "".join('<diagcode id="%s"/>' % re.sub(r"\D", "", x) for x in new)
        chg += "<charge %s>%s</charge>" % (" ".join('%s="%s"' % (k, v) for k, v in a.items()), child)
    va = dict(vis.attrib); va["force"] = "1"
    vs = " ".join('%s="%s"' % (k, v) for k, v in va.items())
    if dry: return "DRY save: %d charges, %d edited" % (len(allc), edited), None
    body = amd.msg("updvisitwithcharges", "chargeentry",
        {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1",
         "batchid": str(era_post.batch()), "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"},
        "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg))
    r = amd.post(body); time.sleep(0.8)
    if "Fault" in r: return "FAULT " + re.sub(r"\s+", " ", r[:220]), None
    v2, p2, c2 = resave.visit_charges(cid)
    det = {x.get("id"): (x.get("proccode"), (x.get("diagcodes") or "").split(), x.get("insbalance")) for x in c2}
    return "saved: %d live charges (was %d)" % (len(c2), len(allc)), det

def fix_visit(pid, vid, cid, seq="1", dry=False, bad=None):
    """Apply the cascade to one visit and rebill it as an original claim. Returns a result string."""
    st = live_state(pid, vid)
    if not st: return "SKIP v%s: no live charges" % vid
    if any(s["pays"] for s in st): return "SKIP-PAID v%s: a payment is posted - never rebill a paid visit" % vid
    vis, pat, allc, m = visit_dx(cid)
    inv = {v: k for k, v in m.items()}          # code -> dcode
    inv.setdefault("I10", I10_DCODE)
    plans = {}; actions = set()
    for c in allc:
        dcodes = (c.get("diagcodes") or "").split()
        codes = [m.get(d, d) for d in dcodes]
        if bad and (not codes or codes[0].upper() != bad.upper()):
            return "SKIP v%s: primary dx is %s, not %s" % (vid, codes[:1], bad)
        cpt_code = None
        for pc in ET.fromstring(resave.detail(c.get("id").replace("charge", ""))).iter("proccode"):
            if pc.get("id") == c.get("proccode"): cpt_code = pc.get("code")
        act, new = plan(codes, cpt_code)
        actions.add(act)
        if act != "ok": plans[c.get("id")] = [inv[x] for x in new]
        L("  %s %s dx %s -> %s (%s)" % (c.get("id"), cpt_code, codes, new, act))
    if not plans: return "OK v%s: primary dx already acceptable" % vid
    r, det = save_visit_dx(cid, plans, dry=dry)
    L("  " + r)
    if dry: return "DRY v%s %s" % (vid, "/".join(sorted(actions)))
    if r.startswith("FAULT"): return r
    for chid, newd in plans.items():
        if det.get(chid, (None, None))[1] != newd: return "VERIFY-FAILED v%s %s saved %s wanted %s" % (vid, chid, det.get(chid), newd)
    r2 = freq1_visit.run(str(vid), str(cid).replace("charge", ""), seq); L("  " + r2); time.sleep(0.4)
    os.makedirs("registers", exist_ok=True)
    reg = json.load(open(REGISTER)) if os.path.exists(REGISTER) else []
    reg.append({"pid": str(pid), "vid": str(vid), "cid": str(cid), "action": "/".join(sorted(actions)),
                "dx_after": [m.get(d, d) if d != I10_DCODE else "I10" for d in list(plans.values())[0]],
                "rebill": r2, "when": datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"})
    json.dump(reg, open(REGISTER, "w"), indent=1)
    return "%s v%s %s -> %s" % ("/".join(sorted(actions)).upper(), vid, list(plans.values())[0], r2)

if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "plan":
        cpt = a[a.index("--cpt") + 1] if "--cpt" in a else None
        codes = [x for x in a[1:] if not x.startswith("--") and x != cpt]
        print(plan(codes, cpt)); sys.exit()
    pid = a[0]; dry = "--dry" in a
    bad = a[a.index("--bad") + 1] if "--bad" in a else None
    only = set(a[a.index("--visits") + 1].split(",")) if "--visits" in a else None
    amd.login_cached()
    root = txh.fetch(pid)
    visits = {}
    for c in root.iter("charge"):
        if c.get("void") == "1" or float(c.get("insbal") or 0) <= 0: continue
        if only and c.get("visit") not in only: continue
        visits.setdefault(c.get("visit"), c.get("id"))
    L("=== DX PRIMARY FIX pat%s dry=%s visits=%d bad=%s ===" % (pid, dry, len(visits), bad))
    for vid, cid in sorted(visits.items()):
        vis, pat, allc = resave.visit_charges(cid)
        seq = (vis.get("insorder") or "1").split(",")[0]
        try: L("%s: %s" % (vid, fix_visit(pid, vid, cid, seq, dry=dry, bad=bad)))
        except Exception as e: L("%s: ERROR %s" % (vid, str(e)[:200]))
        time.sleep(0.5)
    L("=== done ===")
