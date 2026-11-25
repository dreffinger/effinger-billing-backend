# PLAIN ENGLISH (modifier 25 on the CCM add-on, written 10/1/2026 run 2026-10-01T0110Z): William's CCM gate - the add-on 99489 (and 99497
#   with 99223/99306) carries modifier 25 = mcode7 (NEVER the literal "25" = mcode25, which is modifier 78); 99487 never carries 25.
#   EXCEPT FOR HUMANA (William 11/25/2026, asked "Should I stop putting 25 on 99489 for Humana and re-send the ones still inside the
#   filing limit?": "yes try that"): the 99489 add-on of a visit whose claim goes to Humana FIRST carries NO modifier 25 - Humana answered
#   CO-4 on 24 such lines with the modifier in 2026 and on none of its 43 lines without it. The feed import leaves the modifier off when
#   it enters the charge (claimocity_import.py NO_MOD25); this helper is the tool of the standing gate and follows the SAME rule: it never
#   puts the modifier on such a line. Until 11/25/2026 it added mcode7 to any 99489 it was given - the gate put back what the import had
#   just left off, and Humana would have denied the line again.
# Decides: adds mcode7 to ONE named charge of a visit through the full-visit echo (recode._save - every live charge of the visit is
#   re-sent, so nothing is voided), refuses when the charge is a 99487 (pcode492676) or already carries mcode7, and reads the detail
#   back. --live writes; without it the helper only reports what it would change.
#   THE HUMANA RULE, HOW IT IS READ:
#   (1) Which code and which carriers: the import's own two lines - HUMANA = {...} and NO_MOD25 = {...} - read from the copy of
#       claimocity_import.py that lies beside this helper. ONE place holds the rule, so the gate and the import cannot disagree. The
#       built-in copy below is only what is used when that file is not there (a self-test holds the two equal).
#   (2) Which carrier the claim goes to first: the first row of the visit's own insurance-order LIST in the charge's detail
#       (visit/insuranceorderlist/insuranceorder, by ordinal - a claim is built from that list). The carrier is the one that row names;
#       when the row names none, it is the carrier of the chart's plan at that row's sequence. A visit that shows NO list: the chart's
#       OWN billing order answers - the first plan of the patient's insurance order, exactly what the import reads when it enters the
#       charge. The visit's insorder attribute is never read: it says "1" also on a visit that was entered for a chart without an
#       order, and that "1" is a stand-in, not a plan. The chart is read ONCE, and only when it is needed (getdemographic).
#   (3) Nothing shows the first carrier (no list and no billing order on the chart, an answer that cannot be read): the charge is
#       handled exactly as before 11/25/2026. The rule never leaves a modifier off on a guess.
#   WHAT IT SAYS for such a charge - without --live and with it, nothing is sent:
#       "NO MODIFIER 25 - HUMANA: ..." and exit 0: the line passes the gate as it is. Nothing is added and nothing is to be flagged.
#       "MODIFIER 25 STANDS ON A HUMANA ADD-ON: ..." and exit 3: the 99489 already carries the modifier while its claim goes to Humana
#       first. This helper adds the modifier and takes none off - that line is for William before the visit is approved.
# Never touches: other charges' modifiers, diagnosis codes, dates, plans, payments, balances. A charge of the Humana rule is never saved.
#   python3 mod25_addon.py <chargeid> [--live]
#   Exit 0 = added, or nothing to do; 2 = refused (a 99487, or no charge id given); 3 = modifier 25 stands on a Humana add-on.
import amd, resave, recode, re, json, sys, os, datetime
import xml.etree.ElementTree as ET
RULE_FILE = "claimocity_import.py"                               # the import helper: its lines HUMANA = {...} and NO_MOD25 = {...} ARE the rule (William 11/25/2026)
NO_MOD25_BUILT_IN = {"99489": ("car6285", "car302851")}          # used ONLY when that file cannot be read here: HUM01 HUMANA and HUMMA1 HUMANA GOLD PLUS HMO MA PLAN (practices/ehpa/carriers.json)
CPT_BY_ID = {"pcode492676": "99487", "pcode492677": "99489"}     # AdvancedMD's ids of the two care-management codes (claimocity_import.py PCODE) - for a charge detail that names no code text
MOD25 = "mcode7"                                                 # modifier 25 as AdvancedMD stores it (never "mcode25": that one is modifier 78)

def no_mod25_rule(folder=None):
    """{code: {carrier ids}} - the codes that carry NO modifier 25 when the claim goes to one of those carriers first. Read from the import
    helper's own lines in `folder` (this helper's own folder when none is given): NO_MOD25 = {"99489": HUMANA} names the code and the
    list, HUMANA = {"car...", ...} holds the carriers. Whatever cannot be read there - no file, no such line, an empty list - gives the
    built-in copy. Never raises."""
    try:
        src = open(os.path.join(folder or os.path.dirname(os.path.abspath(__file__)), RULE_FILE), encoding="utf-8", errors="replace").read()
        m = re.search(r"(?m)^NO_MOD25 = \{([^}\n]*)\}", src); got = {}
        for code, name in (re.findall(r'"(\d{4}[0-9A-Z])"\s*:\s*([A-Z][A-Z0-9_]*)', m.group(1)) if m else []):
            lst = re.search(r"(?m)^%s = \{([^}\n]*)\}" % re.escape(name), src)
            cars = set(re.findall(r'"(car\d+)"', lst.group(1))) if lst else set()
            if cars: got[code] = cars
        if got: return got
    except Exception: pass
    return {code: set(cars) for code, cars in NO_MOD25_BUILT_IN.items()}
def car(x):
    """A carrier id the way the rule holds it - car<digits>, also for an id an answer gives as bare digits; "" for anything else."""
    s = str(x or "").strip()
    return ("car" + s) if re.fullmatch(r"\d{1,9}", s) else s if re.fullmatch(r"car\d{1,9}", s) else ""
def chart_plans(pid):
    """(the chart's OWN billing order - the patient's insorder, "" when it has none -, {plan sequence: carrier id} of its plans, an open plan
    before an ended one): the proven read of elig_amd.plans (getdemographic)."""
    r = amd.post(amd.msg("getdemographic", "demographics", {"patientid": "pat" + re.sub(r"\D", "", str(pid)), "nocookie": "1"}))
    p = re.search(r"<patient [^>]*>", r); order = (dict(re.findall(r'(\w+)="([^"]*)"', p.group(0))).get("insorder") or "") if p else ""
    out = {}
    for a in sorted((dict(re.findall(r'(\w+)="([^"]*)"', t)) for t in re.findall(r"<insplan ([^>]*)>", r)), key=lambda a: bool((a.get("enddate") or "").strip())):
        if (a.get("sequence") or "").strip() and car(a.get("carrier")): out.setdefault(a["sequence"].strip(), car(a.get("carrier")))
    return order.replace(" ", ""), out
def first_carrier(detail_text):
    """The carrier the visit's claim goes to FIRST - "" when nothing shows it. (a) The first row of the visit's insurance-order list by
    ordinal (resave.order_list's reading), as the charge's own detail shows it: the carrier that row names, else the carrier of the
    chart's plan at that row's sequence. (b) A visit that shows no list: the first plan of the chart's OWN billing order - what the
    import reads when it enters the charge. The visit's insorder attribute is never read (it says "1" also where that is only a
    stand-in). Never raises: an answer that cannot be read shows nothing."""
    try:
        d = ET.fromstring(detail_text); v = d.find(".//visit"); p = d.find(".//patient"); pid = re.sub(r"\D", "", (p.get("id") or "") if p is not None else "")
        def ordinal(o):
            try: return int(o.get("ordinal") or 0)
            except ValueError: return 0
        rows = sorted(v.findall("insuranceorderlist/insuranceorder"), key=ordinal) if v is not None else []
        if rows and car(rows[0].get("carrier")): return car(rows[0].get("carrier"))
        if not pid: return ""
        order, plans = chart_plans(pid)
        seq = (rows[0].get("sequence") or "").strip() if rows else order.split(",")[0]
        return plans.get(seq, "") if seq else ""
    except Exception: return ""
def code_of(detail_text, proccode):
    """The procedure code of a charge: what the detail's own procedure list names for its id, else the two ids this helper knows."""
    try: named = {x.get("id"): (x.get("code") or "").strip() for x in ET.fromstring(detail_text).findall(".//proccodelist/proccode") if x.get("id")}.get(proccode, "")
    except Exception: named = ""
    return named or CPT_BY_ID.get(proccode or "", "")
def main(argv):
    if not argv or not re.sub(r"\D", "", argv[0]): print("REFUSED: no charge id given - python3 mod25_addon.py <chargeid> [--live]"); return 2
    cid = argv[0].replace("charge", ""); LIVE = "--live" in argv
    amd.login_cached()
    x = resave.detail(cid)
    m = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x); a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(0))) if m else {}
    mods = (a.get("modcodes") or "").split(); vm = re.search(r'<visit [^>]*id="([^"]*)"', x); visit = vm.group(1) if vm else "?"
    print("charge", cid, "proccode", a.get("proccode"), "modcodes", mods, "visit", visit)
    if a.get("proccode") == "pcode492676": print("REFUSED: 99487 never carries modifier 25"); return 2
    # William 11/25/2026 ("yes try that"): no modifier 25 on the add-on of a claim that goes to Humana first - the import's own rule, read from its file
    cpt = code_of(x, a.get("proccode")); cars = no_mod25_rule().get(cpt) or set(); first = first_carrier(x) if cars else ""
    if first and first in cars:
        if MOD25 in mods:
            print("MODIFIER 25 STANDS ON A HUMANA ADD-ON: charge %s (%s) carries %s and the claim of visit %s goes to Humana first (%s) - William 11/25/2026: no modifier 25 on the %s add-on for Humana. This helper adds the modifier and takes none off: nothing was changed - for William before the visit is approved"
                  % (cid, cpt, MOD25, visit, first, cpt)); return 3
        print("NO MODIFIER 25 - HUMANA: charge %s is a %s add-on and the claim of visit %s goes to Humana first (%s) - William 11/25/2026 ('yes try that'): this line carries NO modifier 25. It passes the CCM gate as it is: nothing added, nothing sent, nothing to flag"
              % (cid, cpt, visit, first)); return 0
    if MOD25 in mods: print("already carries mcode7 - nothing to do"); return 0
    if not LIVE: print("DRY: would add mcode7 to charge", cid); return 0
    def _e(ch):
        if ch.get("id") == "charge" + cid:
            ms = (ch.get("modcodes") or "").split()
            if MOD25 not in ms: ms.append(MOD25); ch["modcodes"] = " ".join(ms); return True
        return False
    c2, msg = recode._save(cid, _e)
    x2 = resave.detail(cid); m2 = re.search(r'<charge [^>]*id="charge%s"[^>]*>' % cid, x2)
    after = (dict(re.findall(r'(\w+)="([^"]*)"', m2.group(0))).get("modcodes") or "") if m2 else "?"
    print(msg, "| modcodes after:", after)
    os.makedirs("registers", exist_ok=True)
    regf = "registers/mod25_addon.json"; reg = json.load(open(regf)) if os.path.exists(regf) else []
    reg.append({"when": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%MZ"), "chargeid": cid, "result": msg, "modcodes_after": after}); json.dump(reg, open(regf, "w"), indent=1)
    return 0
if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
