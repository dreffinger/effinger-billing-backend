#!/usr/bin/env python3
# PLAIN ENGLISH (diagnosis-list and modifier edits William ordered on the Insurance Refresh Board 11/25/2026, applied by a full-visit echo save)
# Decides: nothing. Three kinds of edit, each a FULL-VISIT echo (recode._save = every live charge echoed with resave.CHG_FIELDS - omitting a
#   charge voids it - so the visit keeps every line); after the save the charge is read back and the register records before / after.
#   remove  <chargeid> <ICD code>        take that one code out of the charge's diagnosis list (every charge of the visit that carries it)
#   keep    <chargeid> <ICD code>        keep ONLY that code on every charge of the visit (William 11/25: 'delete all except i10')
#   nomod   <chargeid> <mcode id>        take that one modifier off THIS charge only (e.g. mcode7 = modifier 25 on a 99489 add-on)
#   Orders this run: NASMYTH chart 17478413 v19461189 'that is wrong change to i10' - O24.419 off both lines (I10 already first);
#   ORWELL chart 44953 four 99233s 'delete all except i10 and resubmit'; HUMANA 99489 modifier 25 off three add-on lines ('yes try that').
# Rules it uses: a code / modifier that is not on the charge = nothing to do (said, not faulted); the diagnosis list is never left empty;
#   a 99487 line beside a 99489 is echoed unchanged. Rebills are NOT done here (the resend rule differs per card: freq7 with the ICN for an
#   adjudicated Humana claim, the inspector re-look for a never-billed visit).
# Never touches: fees, places of service, other visits, balances. Usage: python3 dx_mod_edit_1125.py <kind> <chargeid> <code|mcode> [...] [--live]
import amd, resave, recode, re, sys, json, os
LIVE = "--live" in sys.argv; STAMP = "2026-11-25T0721Z"
args = [a for a in sys.argv[1:] if not a.startswith("--")]
jobs = [tuple(args[i:i + 3]) for i in range(0, len(args) - 2, 3)]
amd.login_cached(); REG = "registers/dx_mod_edit_%s.json" % STAMP
reg = json.load(open(REG)) if os.path.exists(REG) else []
def dmap(cid):
    x = resave.detail(cid); return dict(re.findall(r'<diagcode id="(dcode\d+)"[^>]*?\bcode="([^"]*)"', x))
for kind, cid, what in jobs:
    m = dmap(cid); inv = {v: k for k, v in m.items()}
    vis, pat, allc = resave.visit_charges(cid)
    before = {c.get("id"): {"dx": [m.get(d, d) for d in (c.get("diagcodes") or "").split()], "mod": c.get("modcodes")} for c in allc}
    print("%s %s %s | before %s" % (kind, cid, what, before))
    def edit(a):
        d = (a.get("diagcodes") or "").split()
        if kind == "remove":
            tgt = inv.get(what)
            if tgt and tgt in d and len(d) > 1: a["diagcodes"] = " ".join(x for x in d if x != tgt); return True
            return False
        if kind == "keep":
            tgt = inv.get(what)
            if tgt and tgt in d and d != [tgt]: a["diagcodes"] = tgt; return True
            return False
        if kind == "nomod":
            if a.get("id") != "charge" + str(cid): return False
            mods = (a.get("modcodes") or "").split()
            if what in mods: a["modcodes"] = " ".join(x for x in mods if x != what); return True
            return False
        return False
    rec = {"kind": kind, "cid": cid, "what": what, "visit": vis.get("id"), "before": before, "live": LIVE}
    if not LIVE:
        would = [c.get("id") for c in allc if edit(dict(c.attrib))]
        rec["would_change"] = would; print("  DRY - would change", would)
    else:
        c2, msg = recode._save(cid, edit); rec["save"] = msg; print("  SAVE:", msg)
        if c2 is not None:
            m2 = dmap(cid); rec["after"] = {c.get("id"): {"dx": [m2.get(d, d) for d in (c.get("diagcodes") or "").split()], "mod": c.get("modcodes")} for c in c2}
            print("  after", rec["after"])
    reg.append(rec)
json.dump(reg, open(REG, "w"), indent=1)
