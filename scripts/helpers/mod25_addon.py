# PLAIN ENGLISH (modifier 25 on the CCM add-on, written 10/1/2026 run 2026-10-01T0110Z): William's CCM gate - the add-on 99489 (and 99497
#   with 99223/99306) carries modifier 25 = mcode7 (NEVER the literal "25" = mcode25, which is modifier 78); 99487 never carries 25.
# Decides: adds mcode7 to ONE named charge of a visit through the full-visit echo (recode._save - every live charge of the visit is
#   re-sent, so nothing is voided), refuses when the charge is a 99487 (pcode492676) or already carries mcode7, and reads the detail
#   back. --live writes; without it the helper only reports what it would change.
# Never touches: other charges' modifiers, diagnosis codes, dates, plans, payments, balances.
#   python3 mod25_addon.py <chargeid> [--live]
import amd, resave, recode, re, json, sys, os, datetime
cid = sys.argv[1].replace("charge", ""); LIVE = "--live" in sys.argv
amd.login_cached()
x = resave.detail(cid)
m = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x); a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) if m else {}
mods = (a.get("modcodes") or "").split()
print("charge", cid, "proccode", a.get("proccode"), "modcodes", mods, "visit", re.search(r'<visit [^>]*id="([^"]*)"', x).group(1) if re.search(r'<visit [^>]*id="([^"]*)"', x) else "?")
if a.get("proccode") == "pcode492676": print("REFUSED: 99487 never carries modifier 25"); sys.exit(2)
if "mcode7" in mods: print("already carries mcode7 - nothing to do"); sys.exit(0)
if not LIVE: print("DRY: would add mcode7 to charge", cid); sys.exit(0)
def _e(ch):
    if ch.get("id") == "charge" + cid:
        ms = (ch.get("modcodes") or "").split()
        if "mcode7" not in ms: ms.append("mcode7"); ch["modcodes"] = " ".join(ms); return True
    return False
c2, msg = recode._save(cid, _e)
x2 = resave.detail(cid); m2 = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x2)
after = (dict(re.findall(r'(\w+)="([^"]*)"', m2.group(0))).get("modcodes") or "") if m2 else "?"
print(msg, "| modcodes after:", after)
os.makedirs("registers", exist_ok=True)
regf = "registers/mod25_addon.json"; reg = json.load(open(regf)) if os.path.exists(regf) else []
reg.append({"when": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), "chargeid": cid, "result": msg, "modcodes_after": after}); json.dump(reg, open(regf, "w"), indent=1)
