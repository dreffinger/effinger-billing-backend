# PLAIN ENGLISH (Chat session 10/4/2026 - William on the medicare-co151-ccm-frequency-1003 row: "these are a monthly total charge for CCM -
#   rebill them on the last day of the month; if they are duplicates delete the duplicates")
# Decides, per CCM claim Medicare denied CO-151 / CO-234: (1) is there ANOTHER CCM visit on the chart in the same month? -> the unpaid
#   duplicate is voided (the paid one, or the one with both lines, stays); (2) the surviving denied visit is re-dated to the LAST DAY of its
#   month (visit date + every charge's begin/end date, full-visit echo) and sent to Medicare as an original (frequency 1).
# Never touches: paid charges, other payers' claims, visits outside the ten William named.
# Usage: cd /home/claude/unbilled && python3 chat_1004_ccm_monthend.py [--dry]
import amd, resave, freq1_visit, void_tx, re, sys, json, time, datetime, calendar
import chat_1004_board_act as A
from chat_1004_board_act import L, rec, done, out, chart_rows, live, plans, fmt, full_resave, void_charge, DRY, bypass_advisories
CCM = {"99487", "99489", "99490", "99491", "pcode492676", "pcode492677"}
TARGETS = {"46673": ["19442418"], "17473343": ["19448833", "19452421", "19442414"], "17472553": ["19452441", "19442431"], "21885": ["19442429", "19423619"], "17472517": ["19420933", "19416165"]}
def ym(d): x = datetime.datetime.strptime(d, "%m/%d/%Y").date(); return (x.year, x.month)
def month_end(d): x = datetime.datetime.strptime(d, "%m/%d/%Y").date(); return "%02d/%02d/%d" % (x.month, calendar.monthrange(x.year, x.month)[1], x.year)
def paid(r): return [p for p in r["pays"] if p.get("void") != "1" and float(p.get("amount") or 0) != 0]
amd.login_cached()
for pid, vids in TARGETS.items():
    L("== pat%s" % pid); rows = chart_rows(pid); pa, pl = plans(pid)
    mseq = next((p["sequence"] for p in pl if p.get("carrier") == "car6085" and not p.get("enddate")), None) or next((p["sequence"] for p in pl if p.get("carrier") == "car6085"), None)
    ccm = [r for r in live(rows) if r.get("proccode") in CCM or A.cpt_of(r["id"])[0] in ("99487", "99489")]
    bymonth = {}
    for r in ccm: bymonth.setdefault(ym(r["dos"]), {}).setdefault(r["visit"], []).append(r)
    L("   Medicare seq %s; CCM months: %s" % (mseq, {"%d-%02d" % k: {v: [(x.get("dos"), A.cpt_of(x["id"])[0], x.get("insbal"), x.get("paid")) for x in xs] for v, xs in vv.items()} for k, vv in sorted(bymonth.items())}))
    for vid in vids:
        rs = live(rows, vid=vid)
        if not rs: L("   v%s no live charges (already voided?)" % vid); continue
        k = ym(rs[0]["dos"]); siblings = {v: xs for v, xs in bymonth[k].items() if v != vid}
        # duplicates in the same month: keep a paid sibling, void this one; else keep this one and void unpaid siblings
        if siblings:
            paid_sib = [v for v, xs in siblings.items() if any(paid(x) for x in xs)]
            if paid_sib:
                L("   v%s: a PAID CCM visit %s exists for %d-%02d -> this one is the duplicate -> void" % (vid, paid_sib, k[0], k[1]))
                for x in rs:
                    if paid(x): L("      %s has a payment - left" % x["id"]); continue
                    void_charge("ccm151", pid, x["id"])
                continue
            for v, xs in siblings.items():
                if any(paid(x) for x in xs): continue
                L("   v%s: unpaid duplicate sibling v%s in %d-%02d -> void the sibling" % (vid, v, k[0], k[1]))
                for x in xs: void_charge("ccm151", pid, x["id"])
        if any(paid(x) for x in rs): L("   v%s carries a payment - not re-dated" % vid); continue
        if done("monthend", "%s:%s" % (pid, vid)): L("   v%s already re-dated (register)" % vid); continue
        me = month_end(rs[0]["dos"]); cid = rs[0]["id"]
        if rs[0]["dos"] == me: L("   v%s already dated %s - rebill only" % (vid, me))
        chg_over = {("charge" + x["id"]): {"begindate": me, "enddate": me} for x in rs}
        ok, msg = full_resave(cid, over={"date": me}, chg_over=chg_over, action="updvisitwithcharges"); L("   v%s re-date %s -> %s: %s %s" % (vid, rs[0]["dos"], me, ok, msg[:160]))
        if DRY or not ok or not mseq: continue
        time.sleep(0.6); r1 = freq1_visit.run(vid, cid, int(mseq)); L("      freq1 seq %s -> %s" % (mseq, r1)); rec("monthend", "%s:%s" % (pid, vid), "FAULT" not in str(r1) and "BLOCKED" not in str(r1), msg=str(r1)[:160])
    time.sleep(1.0)
    if not DRY: L("   " + "; ".join(bypass_advisories(vids)))
L("== done")
