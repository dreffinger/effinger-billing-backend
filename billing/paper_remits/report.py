#!/usr/bin/env python3
import os
"""Build the 9/22/2026 paper-remittance deliverables (PHI - for William only):
  paper_remits_posting_workbook_<date>.xlsx  (posted lines, holds, groups, plan holds, virtual cards, physical checks, correspondence, page inventory)
  paper_remits_summary_<date>.md             (numbers + the action list)"""
import json, re, os, datetime, collections
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
D = os.environ.get("SCANS_DIR", "/home/claude/scans") + ""; OUT = os.environ.get("REPORT_OUT", D + "/outputs"); os.makedirs(OUT, exist_ok=True)   # 10/5/2026: output dir from the environment (the 9/22 /mnt path is not on every container)
STAMP = datetime.date.today().strftime("%Y-%m-%d")
P = json.load(open(D + "/plan.json")); REG = json.load(open(D + "/post_register.json")); PAGES = json.load(open(D + "/pages.json"))
R = json.load(open(D + "/remits.json")); STUBS = json.load(open(D + "/vcc_stubs.json")) if os.path.exists(D + "/vcc_stubs.json") else []
REGF = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "practices", "ehpa", "registers", "scan_batches.json"); BATCHES = json.load(open(REGF)) if os.path.exists(REGF) else []
PAYER = {"UA": "United American Insurance Co (Globe Life) - Medigap", "WN": "Washington National / Bankers Life - Medigap", "AET12": "Aetna Senior Supplemental (American Continental) - Medigap",
         "MUT01": "United of Omaha (Mutual of Omaha) - Medigap", "ECHO": "Physicians Life Insurance Co (via ECHO/EPC) - Medigap", "SIM01": "Simply Healthcare LTSS/MMA (Medicaid, via Zelis)",
         "FLO99": "Florida Community Care (Medicaid SMMC) - paper check", "USAA": "USAA Life - Medigap (via Zelis)", "CHAMPVA": "CHAMPVA (EFT - no 835 reaches AMD; posted from the paper EOB)", "BCBS": "Florida Blue (EFT, already electronic)"}
def pg(pages): return ", ".join("%s p%02d" % (b[-6:], p) for b, p in pages)
# latest register row per (family, ref, acct, cpt)
latest = collections.OrderedDict()
for r in REG:
    k = (r.get("family"), r.get("ref"), r.get("acct"), r.get("cpt"))
    if k in latest and latest[k]["status"] == "POSTED" and r["status"] in ("SKIP", "HOLD"): continue   # a later pass re-read an already-posted line
    latest[k] = r
groups_with_posts = {(r.get("family"), r.get("ref")) for r in latest.values() if r["status"] == "POSTED"}
rows = [r for r in latest.values() if not (r.get("acct") == "*" and (r.get("family"), r.get("ref")) in groups_with_posts)]   # group-level errors of an earlier pass that later completed
posted = [r for r in rows if r["status"] == "POSTED"]; other = [r for r in rows if r["status"] not in ("POSTED", "SUPERSEDED")]
claims_by_acct = {c["acct"]: (g, c) for g in P["groups"] for c in g["claims"]}
def patient(acct): return (claims_by_acct.get(acct, (None, {}))[1] or {}).get("patient") or ""

wb = Workbook(); hdr = Font(bold=True, color="FFFFFF"); fill = PatternFill("solid", fgColor="1F4E78")
def sheet(title, header, data, widths=None):
    ws = wb.create_sheet(title) if wb.active.title != "Sheet" else wb.active; ws.title = title
    ws.append(header)
    for c in ws[1]: c.font = hdr; c.fill = fill; c.alignment = Alignment(wrap_text=True, vertical="top")
    for row in data: ws.append([("" if v is None else v) for v in row])
    for i, h in enumerate(header, 1): ws.column_dimensions[get_column_letter(i)].width = (widths or {}).get(h, max(10, min(48, len(h) + 4)))
    ws.freeze_panes = "A2"; return ws
# 1 posted
sheet("Posted in AMD", ["Payer family", "Payer", "AMD check # (reference)", "Check/remit date", "Patient", "AMD acct (claim)", "Patient id", "Visit", "Charge id", "CPT", "DOS", "Fee", "EOB paid", "Posted payment", "Write-off", "WO code", "AMD payment id", "Reason codes posted", "Carrier on payment", "Plan on chart", "ERA Center check id", "Verified live", "Notes", "EOB page(s)"],
      [[r["family"], PAYER.get(r["family"]), r["ref"], claims_by_acct.get(r["acct"], ({}, {}))[0].get("date"), patient(r["acct"]), r["acct"], r.get("pid"), r.get("vid"), r.get("cid"), r.get("cpt"), r.get("dos"), r.get("fee"), r.get("eob_paid"), r.get("pay"), r.get("wo"), r.get("wocode"), r.get("paymentid"),
        "; ".join("%s %.2f" % (a, b) for a, b in (r.get("reasons") or [])), r.get("carrier"), r.get("plan"), r.get("checkid"), r.get("verified"), r.get("note"), pg(claims_by_acct.get(r["acct"], ({}, {"pages": []}))[1].get("pages", []))] for r in posted],
      {"Payer": 40, "Patient": 24, "Notes": 70, "Reason codes posted": 30, "Plan on chart": 36, "EOB page(s)": 24})
# 2 holds / errors / skips
sheet("Holds & errors", ["Status", "Payer family", "AMD check # (reference)", "Patient", "AMD acct (claim)", "Patient id", "Visit", "CPT", "EOB paid", "Why / what to decide", "EOB page(s)"],
      [[r["status"], r["family"], r["ref"], patient(r.get("acct") or ""), r.get("acct"), r.get("pid"), r.get("vid"), r.get("cpt"), r.get("eob_paid") or r.get("paid"), r.get("note"), pg(claims_by_acct.get(r.get("acct"), ({}, {"pages": []}))[1].get("pages", []))] for r in other],
      {"Why / what to decide": 90, "Patient": 24})
# 3 groups
def posted_total(g): return round(sum(r.get("pay") or 0 for r in posted if r["family"] == g["family"] and r["ref"] == g["ref"]), 2)
sheet("Checks (groups)", ["Payer family", "Payer", "Reference", "Reference source", "Date", "Claims on EOB", "EOB claims total", "Check / card total", "Complete", "Posted in AMD", "Difference (EOB - posted)", "Note"],
      [[g["family"], PAYER.get(g["family"]), g["ref"], g["ref_source"], g["date"], len(g["claims"]), g["claims_total"], g.get("expected_total"), g.get("complete"), posted_total(g), round(g["claims_total"] - posted_total(g), 2), g.get("note", "")] for g in P["groups"]],
      {"Payer": 40, "Note": 60})
# 4 plan holds
sheet("Not posted (by design)", ["Why", "Payer family", "Patient", "AMD acct", "Paid on statement", "Remit", "EOB page(s)"],
      [[h["why"], h["family"], h.get("patient"), h.get("acct"), h.get("paid"), h.get("remit"), pg(h.get("pages", []))] for h in sorted(P["holds"], key=lambda h: (h["why"], h["family"], str(h.get("acct"))))],
      {"Why": 70, "Patient": 24})
# 5 virtual cards
sheet("Virtual cards to key (Square)", ["Card number (from the stub)", "Last 4", "Valid thru", "CVC (OCR - verify on the stub)", "Zip", "Amount", "Zelis payment id", "Payer family", "Remit", "Claims on the EOB", "Square status", "Batch page", "Mailing code"],
      [[s.get("card"), s.get("last4"), s.get("exp"), s.get("cvc_ocr"), s.get("zip"), s.get("amount"), s.get("payment_id"), s.get("family"), s.get("remit"), s.get("claims"), s.get("square"), "%s p%02d" % (s["batch"][-6:], s["page"]), s.get("mailing")] for s in STUBS],
      {"Card number (from the stub)": 24, "Square status": 44})
# 6 physical checks
pc = [x for x in R if x.get("is_physical_check")]
sheet("Physical checks", ["Payer family", "Payer", "Check number", "Amount", "Date", "ICN printed", "Linked to remit", "Linked by amount to accts", "Page"],
      [[x["family"], x.get("payer"), x.get("check_number"), x.get("amount"), x.get("date"), x.get("icn"), x.get("linked_to"), ", ".join(x.get("linked_by_amount") or []), pg(x["pages"])] for x in pc])
# 7 correspondence
CORR = json.load(open(D + "/correspondence.json")) if os.path.exists(D + "/correspondence.json") else []   # the correspondence/action list (PHI) lives beside the scans, not in the repo
sheet("Correspondence & actions", ["Item", "Who / what", "Action", "Pages"], CORR, {"Item": 70, "Who / what": 50, "Action": 80, "Pages": 30})
# 8 page inventory
sheet("Page inventory (%d)" % len(PAGES), ["Batch (Gmail attachment)", "Page", "Type", "Payer", "Amount", "Card / payment id", "First line"],
      [[p["batch"], p["page"], p["type"], p.get("payer", ""), p.get("amount", ""), p.get("card") or p.get("payment_id") or "", p["head"][:100]] for p in PAGES], {"Batch (Gmail attachment)": 34, "First line": 90})
fn = os.path.join(OUT, "paper_remits_posting_workbook_%s.xlsx" % STAMP); wb.save(fn)
# summary
tot_posted = round(sum(r.get("pay") or 0 for r in posted), 2); tot_wo = round(sum(r.get("wo") or 0 for r in posted), 2)
byfam = collections.defaultdict(lambda: [0, 0.0])
for r in posted: byfam[r["family"]][0] += 1; byfam[r["family"]][1] += r.get("pay") or 0
base_groups = [g for g in P["groups"] if not g.get("trn_suffix")]   # re-filed groups repeat claims already counted
plan_total = round(sum(g["claims_total"] for g in base_groups), 2)
holds_c = collections.Counter(h["why"] for h in P["holds"])
md = ["# Paper / virtual-card remittances — posted into AdvancedMD %s" % STAMP, "",
      "**Scanned:** %d ScanSnap batches from Gmail (%s), %d pages OCR'd and categorized (workbook sheet 'Page inventory'); originals filed in Drive 'eras scanned'." % (len(BATCHES) or len({p["batch"] for p in PAGES}), ", ".join(sorted({(b.get("sent") or "")[:10] for b in BATCHES if b.get("sent")})) or STAMP, len(PAGES)), "",
      "**Posting plan:** %d checks/cards, %d claims, $%.2f on the EOBs (sheet 'Checks (groups)'; re-filed groups at the bottom repeat claims whose EOB lines needed AMD's own CPTs)." % (len(base_groups), sum(len(g["claims"]) for g in base_groups), plan_total), "",
      "**Posted in AMD:** %d lines, **$%.2f** payments + $%.2f write-offs (WOMCAD/WOCAID2ND/WOINS), every line through the ERA Center with its reason codes, under the payer's own carrier (sheet 'Posted in AMD')." % (len(posted), tot_posted, tot_wo), ""]
md += ["| Payer | Lines | Posted |", "|---|---|---|"] + ["| %s | %d | $%.2f |" % (PAYER.get(f, f), n, a) for f, (n, a) in sorted(byfam.items(), key=lambda kv: -kv[1][1])]
md += ["", "**Held / to decide:** %d lines (sheet 'Holds & errors'): %s" % (len(other), "; ".join("%s x%d" % (k, v) for k, v in collections.Counter(r["status"] for r in other).items())), ""]
md += ["**Not posted by design (sheet 'Not posted (by design)'):** " + "; ".join("%s: %d" % (k.split(" - ")[0].split(" (")[0], v) for k, v in holds_c.items()), ""]
keyable = [s for s in STUBS if not s.get("warning")]; twins = [s for s in STUBS if s.get("warning")]
md += ["**Virtual cards to key in Square:** %d in the pile, $%.2f (sheet 'Virtual cards to key' carries each card's Square status). %d ($%.2f) are duplicated by a PHYSICAL CHECK of the same amount in the same pile (the payer re-issued the card as a check) — deposit the check, do not key those. That leaves **%d cards, $%.2f to key**." % (len(STUBS), sum(s["amount"] or 0 for s in STUBS), len(twins), sum(s["amount"] or 0 for s in twins), len(keyable), sum(s["amount"] or 0 for s in keyable)), ""]
md += ["**Correspondence needing action** (sheet 'Correspondence & actions'): %d items - " % len(CORR) + "; ".join(str(c[0])[:90] for c in CORR[:12]), ""]
open(os.path.join(OUT, "paper_remits_summary_%s.md" % STAMP), "w").write("\n".join(md))
print("\n".join(md)); print("wrote", fn)
