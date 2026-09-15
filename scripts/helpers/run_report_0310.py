# PLAIN ENGLISH (run report CSV builder, 11 PM ET 9/14/2026 slot - ehpa cloud run 2026-09-15T0310Z)
# Decides: nothing. Reads this run's column scan (scan_0912/*_after), the board action register, the ERA before/after
# snapshots, the fallback register, and the Availity Florida Blue remit reconciliation/posting registers, and writes
# "_run report 9-15 0310.csv" (per column: cleared / remaining with patient, DOS, carrier, error, action; ERA rows carry
# check id, payer, visit, amount, action; Florida Blue rows carry the Availity trace number as the check).
# Never touches: AMD.
import csv, json, os, re, glob
S = "2026-09-15T0310Z"
rows = []
def add(col, state, patient="", dos="", carrier="", err="", action="", check="", visit="", amt=""):
    rows.append({"column": col, "state": state, "patient": patient, "dos": dos, "carrier": carrier, "error": err,
                 "action": action, "checkid": check, "visit": visit, "amount": amt})
def load(p, default):
    try: return json.load(open(p))
    except Exception: return default
# --- columns
tag = "after" if os.path.exists("scan_0912/summary_after.json") else "before"
ub = open("scan_0912/unbilled_%s.xml" % tag).read() if os.path.exists("scan_0912/unbilled_%s.xml" % tag) else ""
for m in re.finditer(r'<visit ([^>]*)>(.*?)</visit>', ub, re.S):
    a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
    errs = re.findall(r'<error [^>]*name="([^"]*)"', m.group(2)); err = errs[0] if errs else ""
    action = "waiting on William: 2024 manual-post coinsurance line - no captured call edits payment reason codes" if "reason codes" in err.lower() else "held"
    add("Unbilled", "remaining", a.get("patientname", ""), a.get("dateofservice", ""), a.get("carriercode", ""), err, action, visit=a.get("id", ""))
add("Unbilled", "cleared", "WETHERBY,THURLOW", "09/10/2026 + 09/11/2026", "CAP07", "Insurance order is missing on visit", "CAP07 CHP01052326 added seq 1 (William's TMH check), admit 9/10/2026, insorder 1, released - 2 visits $421", visit="19454465, 19454443", amt="421.00")
add("Charge Review", "clear", action="0 batches before and after")
add("Claim Inspector", "clear", action="0 batches before and after")
add("Exclusions", "clear", action="0 open rows before and after; newest claim run still 1700188 (AET12 Standard Professional test undecided)")
# --- board actions
ba = load("registers/board_act_0310_live.json", {})
for k, v in ba.items():
    for line in v:
        add("Board action", "done", k, action=str(line)[:300])
# --- ERA
before = load("era_checks_before_%s.json" % S, []); after = load("era_checks_after_%s.json" % S, [])
aid = {c["id"] for c in after}; bid = {c["id"] for c in before}
for c in before:
    st = "still open" if c["id"] in aid else "cleared"
    add("ERA", st, carrier=c.get("carriercode", ""), check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % c.get("checknumber", ""),
        action=("held - reversal/orphan/already-adjudicated lines, no postable money" if st == "still open" else "cleared this run"))
for c in after:
    if c["id"] not in bid:
        add("ERA", "new (arrived during run)", carrier=c.get("carriercode", ""), check=str(c["id"]), amt=c.get("unpostedamount", ""), err="check %s" % c.get("checknumber", ""))
fb = load("registers/era_fallback_%s_live.json" % S, [])
if isinstance(fb, list):
    for r in fb:
        if r.get("outcome") in ("posted", "residual"):
            add("ERA", "manual-posted", check=str(r.get("checkid", "")), visit=str(r.get("visitid", "")), amt=r.get("pay", r.get("amt", "")), carrier=r.get("carrier", ""), action=r.get("outcome", ""))
# --- Availity Florida Blue remits
cmp = load("registers/availity_vs_amd_%s.json" % S, {"checks": [], "totals": {}})
post = load("registers/availity_post_%s_live.json" % S, {"rows": [], "summary": {}})
t = cmp.get("totals", {}); ps = post.get("summary", {})
add("Florida Blue remits (Availity)", "summary", err="%d checks $%.2f parsed from 266 PDFs" % (t.get("checks", 0), t.get("check_amount", 0)),
    action="already in AMD $%.2f; money not in AMD %d lines $%.2f; posted this run %d payments $%.2f + WOINS $%.2f; residual (charge already $0) $%.2f; statuses %s" % (
        t.get("posted", 0), t.get("missing_lines", 0), t.get("missing", 0), ps.get("posted", 0), ps.get("posted_amount", 0), ps.get("writeoff_amount", 0), ps.get("residual_remit_money", 0), json.dumps(ps.get("status_counts", {}))))
for r in post.get("rows", []):
    add("Florida Blue remits (Availity)", r.get("status", ""), r.get("patient", ""), r.get("dos", ""), r.get("carrier") or "BCBS", "remit paid %.2f cpt %s charge %s" % (r.get("remit_paid", 0), r.get("cpt"), r.get("cid")),
        action=("pay %.2f wo %.2f" % (r.get("pay", 0), r.get("wo", 0)) if r.get("pay") is not None else r.get("msg", "")), check=r.get("trace", ""), visit=r.get("visit", ""), amt=r.get("pay", ""))
for c in cmp.get("checks", []):
    if c.get("in_era_center"):
        add("Florida Blue remits (Availity)", "also in ERA Center", check=c["trace"], amt=c.get("amount", ""), action="check present in GET /api/era/checks - left to the ERA chain")
out = "_run report 9-15 0310.csv"
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["column", "state", "patient", "dos", "carrier", "error", "action", "checkid", "visit", "amount"])
    w.writeheader(); w.writerows(rows)
print("wrote", out, len(rows), "rows")
