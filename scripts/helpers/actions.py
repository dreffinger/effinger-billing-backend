#!/usr/bin/env python3
import os
"""Build the 'correct / resubmit / cascade' action list from the non-virtual-card paper EOBs (9/23/2026) - PHI, for William only.
Inputs: fcc_lines_live.json, fb_rows_live.json, champva_claims.json + fb_live.json, correspondence.json, post_register.json.
Outputs: actions.json, /mnt/user-data/outputs/paper_eobs_action_list_<date>.xlsx, action_summary.md"""
import json, os, re, datetime, collections
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
D = os.environ.get("SCANS_DIR", "/home/claude/scans") + ""; OUT = "/mnt/user-data/outputs"; os.makedirs(OUT, exist_ok=True)
STAMP = datetime.date.today().strftime("%Y-%m-%d")
FCC = json.load(open(D + "/fcc_lines_live.json")); FB = json.load(open(D + "/fb_rows_live.json")); CH = json.load(open(D + "/champva_claims.json"))
FBL = json.load(open(D + "/fb_live.json")); REG = json.load(open(D + "/post_register.json")); CORR = json.load(open(D + "/correspondence.json"))
posted = {(r.get("acct"), r.get("cpt")) for r in REG if r.get("status") == "POSTED"}; posted_accts = {r.get("acct") for r in REG if r.get("status") == "POSTED"}
A = []
def add(cat, payer, patient, acct, pid, dos, cpts, billed, live, plans, remark, todo, priority, stake, pages, note=""):
    A.append(dict(category=cat, payer=payer, patient=patient, acct=acct, pid=pid, dos=dos, cpts=cpts, billed=billed, live=live, plans=plans, remark=remark, todo=todo, priority=priority, stake=stake, pages=pages, note=note))
def money(x): return round(float(x or 0), 2)
# ---------------------------------------------------------------- FCC $0 statements
fcc_by_acct = collections.defaultdict(list)
for r in FCC: fcc_by_acct[r["acct"]].append(r)
seen76 = set()
for acct, rs in fcc_by_acct.items():
    r0 = rs[0]; b = r0["bucket"]; lv = [r["live"] for r in rs if r["live"]]
    dos = "%s/%s/20%s" % (r0["dos"][:2], r0["dos"][2:4], r0["dos"][4:]) if r0.get("dos") and len(r0["dos"]) == 6 else r0.get("dos")
    cpts = ",".join(r["cpt"] for r in rs); billed = money(sum(r["billed"] for r in rs)); plans = r0["plans"]; page = r0["page"]; pid = r0["pid"]
    if not lv:
        add("DATA QUALITY", "FCC (FLO99)", r0["patient"], acct, pid, dos, cpts, billed, "visit not on the chart the name points to", plans, "FCC %s" % b,
            "Find the visit: duplicate patient records (several patients have 2-15 charts) - merge charts / locate the charge", "low", 0, page); continue
    openins = money(sum(x["insbal"] for x in lv)); openpat = money(sum(x["patbal"] for x in lv)); fee = money(sum(x["fee"] for x in lv))
    paid_by = sorted(set(p[0] for x in lv for p in x["pays"] if p[1] > 0))
    state = ("OPEN ins $%.2f of $%.2f" % (openins, fee)) if openins else ("PATIENT BAL $%.2f" % openpat if openpat else "SETTLED") + " | paid by %s" % paid_by
    if b == "76":
        if openins:
            add("WRITE-OFF (your OK)", "FCC (FLO99) secondary", r0["patient"], acct, pid, dos, cpts, billed, state, plans, "FCC 76 'provider validation state requirements' on the Medicare crossover (Garcia NF visit)",
                "Medicare paid; the coinsurance ($%.2f) is what FCC refused. FCC's 99309 allowance ($70.62) is below what Medicare paid, so even a validated crossover pays $0-3 -> write off WOCAID2ND (dual, never patient). Credentialing: Garcia's Florida Medicaid/FCC provider validation is the root cause (see ADMIN)." % openins,
                "medium", openins, page)
        else:
            add("INFO (already settled)", "FCC (FLO99) secondary", r0["patient"], acct, pid, dos, cpts, billed, state, plans, "FCC 76 on the Medicare crossover", "Nothing to do - Medicare paid and the coinsurance was already written off", "none", 0, page)
    elif b == "041":
        if openins: add("WRITE-OFF (your OK)", "FCC (FLO99) secondary", r0["patient"], acct, pid, dos, cpts, billed, state, plans, "FCC 041 primary paid >= Medicaid allowed",
                        "Medicare paid more than FCC's allowance; the $%.2f coinsurance is not payable by FCC and cannot go to a dual patient -> WOCAID2ND" % openins, "medium", openins, page)
        else: add("INFO (already settled)", "FCC (FLO99) secondary", r0["patient"], acct, pid, dos, cpts, billed, state, plans, "FCC 041", "Nothing to do", "none", 0, page)
    elif b == "075":
        full = openins > 0 and abs(openins - fee) < 0.02
        if full:
            add("WRITE-OFF (your OK)", "FCC (FLO99) primary", r0["patient"], acct, pid, dos, cpts, billed, state, plans, "FCC 14/075 no allowable amount in the fee schedule (CCM / AWV / ACP)",
                "FCC is this member's medical plan and has no fee for %s -> not payable by Medicaid; write off WONCS (non-covered, primary) - or keep billing only Medicare-covered E/M codes for FCC-primary members" % cpts, "medium", openins, page)
        elif openins:
            add("WRITE-OFF (your OK)", "FCC (FLO99) secondary", r0["patient"], acct, pid, dos, cpts, billed, state, plans, "FCC 14/075 no allowable amount (CCM/AWV/ACP crossover)",
                "Medicare paid; FCC has no fee schedule line for %s so the $%.2f coinsurance will never be paid -> WOCAID2ND (dual)" % (cpts, openins), "medium", openins, page)
        else: add("INFO (already settled)", "FCC (FLO99)", r0["patient"], acct, pid, dos, cpts, billed, state, plans, "FCC 14/075", "Nothing to do", "none", 0, page)
    elif b == "PAID":
        if acct in posted_accts or acct in ("19445157A", "19450698A", "19447341A", "19443546A"): continue   # posted 9/22-23 (re-entered visits included)
        add("POST FROM PAPER", "FCC (FLO99)", r0["patient"], acct, pid, dos, cpts, billed, state, plans, "paid on an FCC statement", "verify posting", "high", money(sum(r["billed"] for r in rs)), page)
# ---------------------------------------------------------------- Florida Blue RAs
def fb_state(r):
    ch = r.get("charges") or []
    if not ch: return None
    ins = money(sum(c[4] for c in ch)); pat = money(sum(c[5] for c in ch)); fee = money(sum(c[3] for c in ch))
    pays = [(p[0], p[1]) for c in ch for p in c[6] if p[1] > 0]; zero = sorted(set(p[0] for c in ch for p in c[6] if p[1] == 0)); wos = sorted(set(w[0] for c in ch for w in c[7]))
    medicare_paid = any(p[0] == "FLO02" for p in pays); bcbs_paid = any(p[0] == "BCBS" for p in pays)
    return dict(ins=ins, pat=pat, fee=fee, pays=pays, zero=zero, wos=wos, medicare_paid=medicare_paid, bcbs_paid=bcbs_paid, full=(ins > 0 and abs(ins - fee) < 0.02))
_fb = {}
for r in FB:
    if not r["deny"]: continue
    k = r["acct"]
    if k in _fb:
        old = _fb[k]; old["deny"] = sorted(set(old["deny"]) | set(r["deny"])); old["remarks"] = sorted(set(old["remarks"]) | set(r["remarks"])); old["page"] = old["page"] + ", " + r["page"]
        if (r.get("ra_date") or "") > (old.get("ra_date") or ""): old["ra_date"] = r["ra_date"]
        continue
    _fb[k] = dict(r)
for r in _fb.values():
    st = fb_state(r); plans = r.get("plans_on_chart") or ""; pid = r.get("pid"); dos = r["lines"][0][0] if r["lines"] else ""; cpts = ",".join(l[1] for l in r["lines"]); page = r["page"]
    payer = "%s (%s)" % ("Florida Blue" if r["plan"] == "Florida Blue" else r["plan"], "BCBS")
    remark = ", ".join(r["deny"]) + " - " + {"MEMNC": "member not covered on this DOS", "OCINF": "other-carrier (Medicare) payment info not received", "OCMSP": "Medicare-secondary: Medicare's adjudication needed (truncated remark; refers to floridablue.com/availity)",
              "EOMB2": "Medicare must process first - send the EOB within 35 days", "EOMB3": "additional information/records requested (35 days)", "DPPPX": "denied - member's plan eligibility", "BSNC": "service not covered under the member's plan",
              "NC275": "advance care planning not a benefit (except hospice)", "MNFNA": "additional info from provider incomplete / not received", "MNFNR": "additional info from provider incomplete / not received", "OCPMM": "other-carrier info requested (35 days)"}.get(r["deny"][0], "")
    wrong_order = bool(re.match(r"BCBS:1.*FLO02", plans))
    has_medicare = "FLO02" in plans
    if st is None:
        add("INSURANCE CASCADE", payer, r["patient"] or "(header on another page)", r["acct"], pid, dos, cpts, r["billed"], "not found on a chart", plans, remark,
            "Locate the patient/visit (name not on this RA page or duplicate chart) and work it like the others in this group", "low", r["billed"], page); continue
    live = ("OPEN ins $%.2f of $%.2f" % (st["ins"], st["fee"])) if st["ins"] else (("PATIENT BAL $%.2f" % st["pat"]) if st["pat"] else "SETTLED") + " | paid %s | $0 posts %s | wo %s" % (st["pays"], st["zero"], st["wos"])
    key = r["deny"][0]
    if st["ins"] == 0 and st["pat"] == 0:
        add("INFO (already settled)", payer, r["patient"], r["acct"], pid, dos, cpts, r["billed"], live, plans, remark, "Resolved after this RA (paid / written off) - nothing to do" + (" - but fix the plan order: Florida Blue is entered ahead of Medicare" if wrong_order else ""), "none", 0, page); continue
    if st["pat"] > 0 and not st["pays"]:   # a $0 denial transferred whole to the patient (a copay left after a real payment is the patient's)
        add("PAYER ORDER FIX + MOVE BACK TO INSURANCE", payer, r["patient"], r["acct"], pid, dos, cpts, r["billed"], live, plans, remark,
            "A $0 wrong-payer denial was transferred to the PATIENT (your 9/3 rule: never). move_to_ins, %sbill Medicare (frequency 1 to FLO02) then Florida Blue as secondary with Medicare's adjudication" % ("put Medicare first (chart shows BCBS seq 1 / FLO02 seq 2), " if wrong_order else ""),
            "high", st["pat"], page); continue
    if key == "MEMNC":
        if st["medicare_paid"]:
            add("INSURANCE CASCADE", payer, r["patient"], r["acct"], pid, dos, cpts, r["billed"], live, plans, remark,
                "Medicare paid; Florida Blue says the member was NOT covered on this DOS -> the FB plan is not the secondary: run eligibility (AMD 271 / Stedi), end-date the FB plan, add the real secondary and rebill it; if none, write off the Medicare contractual (WOINS) and handle the $%.2f coinsurance per policy%s" % (st["ins"] - 0, " (also reorder: BCBS is seq 1 ahead of Medicare)" if wrong_order else ""),
                "high", st["ins"], page)
        else:
            add("INSURANCE CASCADE", payer, r["patient"], r["acct"], pid, dos, cpts, r["billed"], live, plans, remark,
                "Billed to Florida Blue as PRIMARY and denied 'not covered on this DOS' - nothing paid: find the real payer (eligibility 270/271, facesheet, Medicare MBI lookup), replace the plan, rebill%s" % (" (no Medicare plan on the chart)" if not has_medicare else ""),
                "high", st["ins"], page)
    elif key in ("OCINF", "OCMSP", "RVNDR", "RVNDA", "MNFNA", "MNFNR", "OCPMM", "EOMB2", "EOMB3"):
        if st["full"] and not st["medicare_paid"]:
            add("PAYER ORDER FIX (Medicare first)", payer, r["patient"], r["acct"], pid, dos, cpts, r["billed"], live, plans, remark,
                "Full charge still open and Medicare never adjudicated: Florida Blue is a Medicare-secondary plan here - %sbill Medicare first (frequency 1 to FLO02), then the FB secondary carries Medicare's payment" % ("put Medicare first on the chart (BCBS seq 1 / FLO02 seq 2), " if wrong_order else ("add/verify the Medicare plan, " if not has_medicare else "")),
                "high", st["ins"], page)
        elif st["medicare_paid"]:
            add("RESUBMIT SECONDARY WITH MEDICARE EOB", payer, r["patient"], r["acct"], pid, dos, cpts, r["billed"], live, plans, remark,
                "Medicare paid; the FB secondary claim went without Medicare's adjudication -> rebill the secondary (AMD prints the primary payment once posted; or Availity with the Medicare EOB attached)%s; residual open $%.2f" % (" - and put Medicare first on the chart" if wrong_order else "", st["ins"]),
                "medium", st["ins"], page)
        else:
            add("INSURANCE CASCADE", payer, r["patient"], r["acct"], pid, dos, cpts, r["billed"], live, plans, remark,
                "Florida Blue wants another carrier's adjudication and the chart has no Medicare plan: eligibility check -> add the real primary, bill it first", "high", st["ins"], page)
    elif key == "DPPPX":
        add("INSURANCE CASCADE", payer, r["patient"], r["acct"], pid, dos, cpts, r["billed"], live, plans, remark, "Plan-eligibility denial: confirm the real coverage (eligibility) and rebill", "medium", st["ins"] or st["pat"], page)
    elif key == "NC275":
        add("WRITE-OFF (your OK)", payer, r["patient"], r["acct"], pid, dos, cpts, r["billed"], live, plans, remark, "99497 advance care planning is not a benefit under this FEP/FB contract -> WONCS the 99497 line ($%.2f open)" % st["ins"], "low", st["ins"], page)
    elif key == "BSNC":
        add("WRITE-OFF (your OK)", payer, r["patient"], r["acct"], pid, dos, cpts, r["billed"], live, plans, remark, "CCM not covered under the member's plan (Medicare also posted $0): review, then WONCS", "low", st["ins"] or st["pat"], page)
# ---------------------------------------------------------------- CHAMPVA
for c in CH:
    acct = c.get("acct_norm") or c.get("acct"); live = FBL.get(acct) or {}; pid = live.get("pid")
    plans = ",".join("%s:%s" % ({"car6085": "FLO02", "car6447": "CHA03", "car6404": "UNI20", "car6600": "AAR01"}.get(p.get("carrier"), p.get("carrier")), p.get("sequence")) for p in live.get("plans") or [])
    dos = ", ".join(l["dos"] for l in c["lines"]); cpts = ",".join(l["cpt"] for l in c["lines"]); billed = money(sum(l["billed"] for l in c["lines"]))
    if c.get("paid"):
        add("POST FROM PAPER (done 9/23)", "CHAMPVA (CHA03, EFT)", c["patient"], acct, pid, dos, cpts, billed, "CHAMPVA paid $%.2f by EFT (EOB %s) - the payment was not in AMD" % (c["paid"], c["eob_date"]), plans, "info-only EOB, payment by EFT",
            "Posted through the ERA Center from the paper EOB on 9/23 (no CHAMPVA 835 ever reached AMD); Mulvihill's CHA03 plan added; six 2024 patient balances moved back to insurance first", "done", c["paid"], c["page"])
    else:
        codes = c.get("codes", "") + " " + " ".join(l.get("codes", "") for l in c["lines"])
        if "299" in codes:
            add("RESUBMIT / CORRECT", "CHAMPVA (CHA03)", c["patient"], acct, pid, dos, cpts, billed, "open CHA03 coinsurance on the chart", plans, "CHAMPVA 299: billing provider not eligible to receive payment",
                "The 5/2026 hospital-stay claims went out under 'North Florida Senior Care' (payee on the EOB) - CHAMPVA pays Effinger Health PA (the 8/2026 EOBs under William paid). Resubmit under Effinger Health PA NPI 1629515325 with the Medicare EOB attached (paper: CHAMPVA, PO Box 500, Sprague City PA 19475; within 1 year of the 6/3/26 notice)", "medium", money(sum(l["billed"] for l in c["lines"])) * 0.13, c["page"])
        elif "22" in codes:
            add("WRITE-OFF (your OK)", "CHAMPVA (CHA03)", c["patient"], acct, pid, dos, cpts, billed, "settled on the chart (2023 DOS)", plans, "CHAMPVA 22: may be covered by another payer per COB", "2023 dates of service, Medicare paid, CHAMPVA declined COB - already written off (WOINSBANK) - nothing to do", "none", 0, c["page"])
# ---------------------------------------------------------------- other items found in the pile (PHI: extra_items.json beside the scans, one add() per row)
try:
    for it in json.load(open(D + "/extra_items.json")): add(*it)
except FileNotFoundError: pass
# ---------------------------------------------------------------- what was DONE on 9/23 (William: rebill to Medicare + write off)
try:
    EX = json.load(open(D + "/execute_0923_register.json")); WP = json.load(open(D + "/writeoff_plan.json"))
    rb = {r["key"]: r for r in EX if r["step"] == "rebill" and r["ok"]}; mb = {r["key"]: r for r in EX if r["step"] == "moveback" and r["ok"]}
    wo_done = {r["key"]: r for r in EX if r["step"] == "writeoff" and r["ok"]}
    wo_by_acct = collections.defaultdict(list)
    for w in WP: wo_by_acct[w["acct"]].append(w)
    for a in A:
        if a["acct"] in rb: a["category"] = "DONE 9/23 - REBILLED TO MEDICARE"; a["todo"] = "Done 9/23: balance moved off the patient, visit order Medicare first, frequency-1 claim sent to FLO02 (204). " + a["todo"]
        elif a["acct"] in mb: a["category"] = "DONE 9/23 - MOVED BACK TO INSURANCE (claim already at Medicare)"; a["todo"] = "Done 9/23: patient balance moved back to insurance; the Medicare claim (billed 9/12-9/16) is pending. " + a["todo"]
        elif a["category"] == "WRITE-OFF (your OK)" and a["acct"] in wo_by_acct:
            ws = wo_by_acct[a["acct"]]; posted = [w for w in ws if w["cid"] in wo_done]; held = [w for w in ws if w["code"] == "SKIP"]
            if posted: a["category"] = "DONE 9/23 - WRITTEN OFF"; a["todo"] = "Done 9/23: " + "; ".join("%s %s $%.2f" % (w["cpt"], wo_done[w["cid"]]["code"], wo_done[w["cid"]]["amount"]) for w in posted) + (" | held: " + "; ".join("%s %s (%s)" % (w["cpt"], w["open"], w["why"][:70]) for w in held) if held else "")
            elif held: a["category"] = "WRITE-OFF HELD (review)"; a["todo"] = "Not written off 9/23: " + "; ".join("%s $%.2f - %s" % (w["cpt"], w["open"], w["why"][:90]) for w in held)
        elif a["category"] in ("PAYER ORDER FIX (Medicare first)", "PAYER ORDER FIX + MOVE BACK TO INSURANCE"):
            tg = {t["acct"]: t for t in json.load(open(D + "/fb_rebill_targets.json"))}.get(a["acct"])
            if tg and not tg.get("flo02"): a["category"] = "INSURANCE CASCADE"; a["todo"] = "No Medicare plan on the chart - eligibility first (not rebilled 9/23). " + a["todo"]
            elif tg: a["category"] = "AT MEDICARE ALREADY (billed 9/12-9/16, pending)"; a["todo"] = "Already sent to Medicare by the routine 9/12-9/16 - pending; not re-sent 9/23. " + a["todo"]
except FileNotFoundError: pass
json.dump(A, open(D + "/actions.json", "w"), indent=1)
# ---------------------------------------------------------------- workbook
wb = Workbook(); hdr = Font(bold=True, color="FFFFFF"); fill = PatternFill("solid", fgColor="1F4E78")
def sheet(title, header, data, widths=None):
    ws = wb.create_sheet(title) if wb.active.title != "Sheet" else wb.active; ws.title = title; ws.append(header)
    for c in ws[1]: c.font = hdr; c.fill = fill; c.alignment = Alignment(wrap_text=True, vertical="top")
    for row in data: ws.append([("" if v is None else (", ".join(map(str, v)) if isinstance(v, (list, tuple)) else v)) for v in row])
    for i, h in enumerate(header, 1): ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(h, max(10, min(40, len(h) + 4)))
    ws.freeze_panes = "A2"; return ws
ORDER = ["DONE 9/23 - REBILLED TO MEDICARE", "DONE 9/23 - MOVED BACK TO INSURANCE (claim already at Medicare)", "DONE 9/23 - WRITTEN OFF", "AT MEDICARE ALREADY (billed 9/12-9/16, pending)", "WRITE-OFF HELD (review)", "POST FROM PAPER", "POST FROM PAPER (done 9/23)", "POST FROM PAPER (needs a carrier)", "POST FROM PAPER (payment page missing)", "RECOUPMENT / RESUBMIT", "RESUBMIT / CORRECT", "PAYER ORDER FIX + MOVE BACK TO INSURANCE", "PAYER ORDER FIX (Medicare first)", "RESUBMIT SECONDARY WITH MEDICARE EOB", "INSURANCE CASCADE", "WRITE-OFF (your OK)", "ADMIN / CREDENTIALING", "ADMIN", "DATA QUALITY", "INFO (treasury)", "INFO (facility denials)", "INFO (already settled)"]
A.sort(key=lambda a: (ORDER.index(a["category"]) if a["category"] in ORDER else 99, a["payer"], a["patient"] or "", a["dos"] or ""))
sheet("Action list", ["Category", "Payer", "Patient", "AMD acct(s)", "Patient id", "DOS", "CPT(s)", "Billed", "Live AMD state (9/23)", "Plans on chart (carrier:seq)", "Denial / remark on the paper", "What to do", "Priority", "$ at stake", "EOB page(s)"],
      [[a["category"], a["payer"], a["patient"], a["acct"], a["pid"], a["dos"], a["cpts"], a["billed"], a["live"], a["plans"], a["remark"], a["todo"], a["priority"], a["stake"], a["pages"]] for a in A],
      {"Category": 34, "Payer": 30, "Patient": 26, "AMD acct(s)": 22, "Live AMD state (9/23)": 60, "Plans on chart (carrier:seq)": 34, "Denial / remark on the paper": 60, "What to do": 110, "EOB page(s)": 22})
cnt = collections.OrderedDict()
for a in A: k = a["category"]; cnt.setdefault(k, [0, 0.0]); cnt[k][0] += 1; cnt[k][1] += a["stake"] or 0
sheet("Summary", ["Category", "Items", "$ at stake"], [[k, v[0], round(v[1], 2)] for k, v in cnt.items()], {"Category": 44})
sheet("FCC statements (lines)", ["Bucket", "AMD acct", "Patient", "Provider", "DOS", "CPT", "Billed", "Live: charge id", "Live ins bal", "Live pat bal", "Live payments", "Live write-offs", "Plans on chart", "Page"],
      [[r["bucket"], r["acct"], r["patient"], r["provider"], r["dos"], r["cpt"], r["billed"], (r["live"] or {}).get("cid"), (r["live"] or {}).get("insbal"), (r["live"] or {}).get("patbal"), (r["live"] or {}).get("pays"), (r["live"] or {}).get("wos"), r["plans"], r["page"]] for r in FCC],
      {"Live payments": 50, "Live write-offs": 30, "Plans on chart": 40})
sheet("Florida Blue RAs (claims)", ["RA date", "Plan", "Check/EFT", "Patient", "Member", "AMD acct", "Patient id", "DOS", "CPT(s)", "Billed", "Other carrier paid", "Patient resp", "FB paid", "Remarks", "Denial codes", "Live AMD state", "Plans on chart", "Page"],
      [[r["ra_date"], r["plan"], r["check"], r["patient"], r["member"], r["acct"], r["pid"], r["lines"][0][0] if r["lines"] else "", ",".join(l[1] for l in r["lines"]), r["billed"], r["other_carrier"], r["pt_resp"], r["paid"], r["remarks"], r["deny"], r["live"], r["plans_on_chart"], r["page"]] for r in FB],
      {"Live AMD state": 70, "Plans on chart": 36, "Remarks": 24})
sheet("CHAMPVA EOBs", ["EOB date", "Patient", "AMD acct", "Control #", "Lines (DOS, CPT, billed)", "Allowed", "OHI (Medicare) paid", "CHAMPVA paid", "Codes", "Page"],
      [[c["eob_date"], c["patient"], c.get("acct_norm") or c.get("acct"), c.get("control"), [(l["dos"], l["cpt"], l["billed"]) for l in c["lines"]], c.get("claim_allowed"), c.get("ohi_paid"), c.get("paid"), c.get("codes", "") + " " + " ".join(l.get("codes", "") for l in c["lines"]), c["page"]] for c in CH],
      {"Lines (DOS, CPT, billed)": 50})
sheet("Correspondence & actions", ["Item", "Who / what", "Action", "Pages"], CORR, {"Item": 70, "Who / what": 50, "Action": 80, "Pages": 30})
fn = os.path.join(OUT, "paper_eobs_action_list_%s.xlsx" % STAMP); wb.save(fn); print("wrote", fn)
md = ["# Paper EOBs (non-virtual-card) - correct / resubmit / cascade list %s" % STAMP, "", "| Category | Items | $ at stake |", "|---|---|---|"] + ["| %s | %d | $%.2f |" % (k, v[0], v[1]) for k, v in cnt.items()]
open(D + "/action_summary.md", "w").write("\n".join(md)); print("\n".join(md))
