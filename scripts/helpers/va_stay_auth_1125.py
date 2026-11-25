# PLAIN ENGLISH (VA CCN authorization numbers William pasted on two board cards, 11/25/2026 - one referral plan per hospital stay)
# Decides: nothing. William's HCA facesheet pastes carry the Optum VA CCN authorization of a stay:
#   card-17478013          VA-AUTH-REDACTED (sheet effective 10/21/2026): the 11 visits of 10/21-10/31/2026 (v19458908 ... v19459750).
#     The 10/05-10/12 visits belong to the earlier admission, whose own number is still needed - they are NOT touched.
#   card-17475970 VA-AUTH-REDACTED (sheet effective 11/04/2026): the 10 visits of 11/09-11/18/2026 (v19461041 ... v19461858).
# The rule (advancedmd-api-reference, 9/8/2026): one referral plan per stay, else every claim prints the last-written auth. So, per chart:
#   (1) addreferralplan (class chargeentry, blank plan ismain=0) -> a NEW rplan id; (2) per visit a FULL-visit echo resave
#   (updvisitwithnewcharges, every live charge echoed with resave.CHG_FIELDS - the void trap) with visit attrs refplan=<new plan>,
#   preauth=<auth>, insorder=<the VA plan's sequence> and force=1; (3) read the visit back (refplan and preauth as sent);
#   (4) ONE frequency-1 reset + ONE chargerebill to the VA sequence (freq1_visit.run) - the deceased guard runs inside it.
# Known side effect (the skill's CAUTION): the resave also writes the preauth onto the visit's PREVIOUS plan - this helper reads every
#   referral plan before and after and prints what changed, so the card can say so.
# --dry = reads only. Register registers/va_stay_auth_2026-11-25T0435Z[_dry].json. Never touches: other visits, balances, codes.
# Usage: python3 va_stay_auth_1125.py [--live] [--only <pid>]
import amd, resave, freq1_visit, re, json, sys, time
import xml.etree.ElementTree as ET
LIVE = "--live" in sys.argv; S = "2026-11-25T0435Z"
ONLY = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
STAYS = [
    ("card-17478013", "17478013", "VA-AUTH-REDACTED", "1", [("19458908", "23371147"), ("19459085", "23371470"), ("19459129", "23371524"), ("19459117", "23371510"), ("19459151", "23371558"), ("19459576", "23372121"), ("19459559", "23372104"), ("19459599", "23372145"), ("19459750", "23372354"), ("19459730", "23372334"), ("19459723", "23372327")]),
    ("card-17475970", "17475970", "VA-AUTH-REDACTED", "1", [("19460346", "23373017"), ("19460344", "23373014"), ("19460401", "23373083"), ("19460532", "23373238"), ("19460684", "23373502"), ("19461085", "23373905"), ("19461064", "23373884"), ("19461041", "23373861"), ("19461136", "23373968"), ("19461269", "23374158"), ("19461242", "23374131"), ("19461295", "23374214"), ("19461449", "23374345"), ("19461629", "23374548"), ("19461858", "23374887")]),
]
amd.login_cached()
def refplans(pid, full=False):
    t = amd.post(amd.msg("getdemographic", "demographics", {"patientid": pid, "nocookie": "1"}), timeout=120)
    pl = [dict(re.findall(r'(\w+)="([^"]*)"', x)) for x in re.findall(r'<refplan [^>]*/?>', t)]
    if full: return pl
    return {a.get("id"): (a.get("ismain"), a.get("preauth")) for a in pl}
def new_plan(pid):
    """11/25: the 9/8 shape alone get-or-returns the main plan on some charts (9/19-9/20 probes); the 9/22 shape that worked on every
    chart (fix_referring_provider.py) carries the MAIN plan's facility - tried first; if the main plan comes back, the 9/22 ismain="1" shape
    (creates a new main plan, demotes the old one - captured 9/22) is the second and last try."""
    main = [p for p in refplans(pid, full=True) if p.get("ismain") == "1"]; fac = main[0].get("facility", "") if main else ""; rp = main[0].get("refprov", "rprov13") if main else "rprov13"
    before = set(refplans(pid))
    for ismain in ("0", "1"):
        r = amd.post(amd.msg("addreferralplan", "chargeentry", {"nocookie": "1"}, '<refplan id="" patient="pat%s" ismain="%s" status="stat1" preauthreq="0" sequence="%s" refprov="%s" type="I" reason="SELF-REFERRAL" preauth="" begindate="" enddate="" maxvisits="0" usedvisits="0" maxamount="" usedamount="0" proccode="" diagcodes="" facility="%s"/>' % (pid, ismain, "2" if ismain == "0" else "1", rp or "rprov13", fac)))
        m = re.search(r'id="(rplan\d+)"', r); got = m.group(1) if m else None
        print("  addreferralplan ismain=%s facility=%s -> %s" % (ismain, fac, got))
        if got and got not in before: return got, ismain
    return None, None
def resave_visit(cid, rplan, auth, order):
    x = resave.detail(cid); root = ET.fromstring(x)
    pat = root.find(".//patient"); vis = root.find(".//visit")
    _, _, allc = resave.visit_charges(cid)
    chg = ""
    for c in allc:
        a = {"id": c.get("id")}
        for f in resave.CHG_FIELDS:
            v = c.get(f)
            if v is not None: a[f] = v
        chg += "<charge %s/>" % " ".join('%s="%s"' % (k, amd.esc(v)) for k, v in a.items())
    va = dict(vis.attrib); va["refplan"] = rplan; va["preauth"] = auth; va["insorder"] = order; va["force"] = "1"
    vs = " ".join('%s="%s"' % (k, amd.esc(v)) for k, v in va.items())
    body = amd.msg("updvisitwithnewcharges", "chargeentry", {"patientid": pat.get("id"), "episodeid": vis.get("episode"), "approval": "1", "inspectorenabled": "1", "getfinancials": "-1", "customclaimfieldsavailable": "1", "nocookie": "1"}, "<visit %s><chargelist>%s</chargelist></visit>" % (vs, chg))
    r = amd.post(body); time.sleep(0.8)
    x2 = resave.detail(cid); v2 = ET.fromstring(x2).find(".//visit")
    live_after = len(resave.visit_charges(cid)[2])   # 11/25 fix: detail() returns ONE charge; count the visit
    return ("Fault" not in r), v2.get("refplan"), v2.get("preauth"), v2.get("insorder"), len(allc), live_after, (re.search(r"<description>([^<]*)", r).group(1)[:160] if "Fault" in r else "")
reg = []
for card, pid, auth, seq, visits in STAYS:
    if ONLY and pid != ONLY: continue
    before = refplans(pid); row = {"card": card, "pid": pid, "auth": auth, "seq": seq, "plans_before": before, "visits": {}}
    print("=== %s pat%s plans before: %s" % (card, pid, before))
    for vid, cid in visits:
        v, _, allc = resave.visit_charges(cid)
        print("  v%s refplan=%s preauth=%s insorder=%s charges=%d" % (vid, v.get("refplan"), v.get("preauth"), v.get("insorder"), len(allc)))
    if not LIVE:
        print("  DRY - would addreferralplan, resave %d visits with the new plan + %s + insorder %s, then freq1 rebill seq %s each" % (len(visits), auth, seq, seq)); reg.append(row); continue
    # 11/25/2026, learned this run: addreferralplan get-or-returns the chart's plan keyed by (patient, refprov) - every shape with the
    # main plan's refprov (rprov13) returned the main plan; only a different refprov inserts (a blank rprov14 plan was created on
    # pat17478013 proving it, rplan18462897 - unused: the referring provider on the claim must stay Effinger). So the auth is written on
    # the plan each visit already points to (the main plan) - the stays that share that plan print this number from now on (said on the card).
    new = resave.visit_charges(visits[0][1])[0].get("refplan"); row["plan_written"] = new   # the plan the visits already point to
    if "--plan" in sys.argv: new = sys.argv[sys.argv.index("--plan") + 1]; row["plan_written"] = new   # 11/25 cowling: back onto the Effinger plan rplan18462365
    if not new or new not in before: print("  visit plan unknown - stop"); row["error"] = "visit refplan not on the chart"; reg.append(row); continue
    for vid, cid in visits:
        ok, rp, pa, io, n_sent, n_after, err = resave_visit(cid, new, auth, seq)
        line = "resave ok=%s refplan=%s preauth=%s insorder=%s charges %d -> %d %s" % (ok, rp, pa, io, n_sent, n_after, err)
        plan_auth = refplans(pid).get(new, (None, None))[1]; line += " plan_preauth=%s" % plan_auth
        if ok and rp == new and plan_auth == auth and n_after == n_sent and "--repoint-only" in sys.argv:
            line += " | repointed, not rebilled again (--repoint-only: the claim queued earlier this run goes out from the visit as it stands now)"
        elif ok and rp == new and plan_auth == auth and n_after == n_sent:
            res = freq1_visit.run(vid, cid, seq); line += " | " + str(res)
        else: line += " | NOT rebilled (resave not as asked)"
        row["visits"][vid] = line; print("  v%s %s" % (vid, line)); time.sleep(0.4)
    after = refplans(pid); row["plans_after"] = after
    changed = {k: (before.get(k), after.get(k)) for k in set(before) | set(after) if before.get(k) != after.get(k)}
    row["plans_changed"] = changed; print("  plans changed:", changed)
    reg.append(row)
json.dump(reg, open("registers/va_stay_auth_%s%s.json" % (S, "" if LIVE else "_dry"), "w"), indent=1)
