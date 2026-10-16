# PLAIN ENGLISH (aging workbook builder, chat 10/15/2026) - turns aging_1015_summary.json + aging_1015_visits.csv into the
#   workbook William reads: Summary, By payer, Payer x action, Visits (chart ids only). Reads only.
import json, csv, re, collections
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
s = json.load(open("aging_1015_summary.json"))
rows = list(csv.DictReader(open("aging_1015_visits.csv")))
for r in rows:
    for k in ("ins_balance", "pr_cost_share", "contractual_on_remit", "writeoffs_posted"): r[k] = float(r[k] or 0)
    for k in ("days_since_sent", "days_since_dos"): r[k] = int(r[k]) if r[k] not in ("", "None") else None
wb = Workbook()
H = Font(bold=True, color="FFFFFF"); HF = PatternFill("solid", fgColor="1F3A5F"); B = Font(bold=True)
def hdr(ws, row, vals):
    for i, v in enumerate(vals, 1):
        c = ws.cell(row=row, column=i, value=v); c.font = H; c.fill = HF; c.alignment = Alignment(wrap_text=True, vertical="top")
def widths(ws, ws_w):
    for i, w in enumerate(ws_w, 1): ws.column_dimensions[get_column_letter(i)].width = w
ws = wb.active; ws.title = "Summary"
ws["A1"] = "Effinger Health PA - open insurance balances by age, payer and action"; ws["A1"].font = Font(bold=True, size=14)
ws["A2"] = "Source: AdvancedMD massrebillsearch (every open insurance balance) + each chart's live transaction history, pulled %s evening ET. Patient balances are not in this list." % s["asof"]
ws["A3"] = "Total: %d visits / %d patients / $%s" % (s["visits"], s["patients"], format(s["total"], ",.2f")); ws["A3"].font = B
r = 5; hdr(ws, r, ["Days since the claim was LAST SENT", "Visits", "$ open", "Standing rule"]); r += 1
rules = {"0-30": "WAIT - inside normal adjudication", "31-60": "WAIT - watch; UNI20/BCBS never auto-rebilled (ERA backlog); pull 277 if silent at 60", "61-90": "CHECK STATUS - no record at the payer -> resend as an ORIGINAL (freq 1)", "91-120": "FIX & RESEND as original after verifying the plan", "over 120": "10/13 rule: must be waiting on an adjudication - otherwise fixed and resent, or written off (primary > 12 months from DOS = WOINS untimely)", "unknown": ""}
for b, v in s["by_bucket_sent"].items():
    if v["n"]: ws.append([b, v["n"], v["amt"], rules[b]]); r += 1
r += 1; hdr(ws, r, ["Days since DATE OF SERVICE", "Visits", "$ open", ""]); r += 1
for b, v in s["by_bucket_dos"].items():
    if v["n"]: ws.append([b, v["n"], v["amt"], "primary claims past 12 months from DOS cannot be resent - write off; secondaries are timely from the primary's remit" if b == "over 120" else ""]); r += 1
r += 1; hdr(ws, r, ["Recommendation", "Visits", "$ open", "What it means"]); r += 1
meaning = {"WAIT": "claim is out and inside its window (or a secondary just sent) - no action", "CORRECT & RESEND": "money that can still be retrieved: bill the secondary on the chart, fix a correctable denial, re-route a wrong-payer denial through the Stedi cascade, resend an original", "WRITE OFF": "nothing left to bill: cost-share with no secondary (WOCLTREQ), unwritten contractual (WOINS), CCM denied on hospice (WONCS), CO-29 (WOLATE), primary > 12 months unpaid (WOINS untimely) - each line still needs your word", "REVIEW": ""}
for b, v in s["by_rec"].items():
    if v["n"]: ws.append([b, v["n"], v["amt"], meaning[b]]); r += 1
r += 1; hdr(ws, r, ["Reason (recommendation | rule applied)", "Visits", "$ open", ""]); r += 1
for k, v in s["by_rec_reason"].items(): ws.append([k, v["n"], v["amt"]]); r += 1
widths(ws, [62, 9, 14, 110])
for row in ws.iter_rows(min_row=5, max_col=3): row[2].number_format = '#,##0.00'
ws2 = wb.create_sheet("By payer")
hdr(ws2, 1, ["Payer (last billed)", "Visits", "$ open", "0-30 d (n)", "0-30 $", "31-60 (n)", "31-60 $", "61-90 (n)", "61-90 $", "91-120 (n)", "91-120 $", ">120 (n)", ">120 $", "WAIT $", "RESEND $", "WRITE OFF $", "Note"])
notes = {"FLO02": "Florida Medicare. Most of the >120 money is Medicare-PAID coinsurance left under FLO02 with no secondary (WOCLTREQ) or unwritten contractual from the 9/9 postings (WOINS) - see Visits sheet.", "UNI20": "ERA backlog payer - never auto-rebill; 277 / ConnectCenter check first.", "BCBS": "ERA backlog payer - 277 first; 2022-23 Medigap/secondary leftovers are untimely.", "FLO99": "Florida Community Care - all sent in the last 30 days (10/5 dual re-routes); $0 041 answers on coinsurance will become WOCAID2ND.", "MCAD": "Florida Medicaid FFS - CCM lines never pay (write off); E/M lines wait.", "AET12": "Aetna Senior Supplemental (Medigap) - the 50 secondaries re-sent after the CPID fix; wait for the next claim run / remit.", "CAP07": "Capital Health Plan - MA; >120 bucket is wrong-payer / cascade material.", "HUM01": "Humana - check MA vs Medicaid-LTC per chart before any rebill.", "TRI05": "TRICARE For Life (WPS) secondaries - wait; no ERA route yet.", "VACCN": "Optum VA CCN - auth per stay (referral plan)."}
for p, d in s["by_payer"].items():
    bk = d["buckets"]; rc = d["recs"]
    ws2.append([p, d["visits"], d["amt"]] + sum(([bk[x]["n"], bk[x]["amt"]] for x in ("0-30", "31-60", "61-90", "91-120", "over 120")), []) + [rc["WAIT"]["amt"], rc["CORRECT & RESEND"]["amt"], rc["WRITE OFF"]["amt"], notes.get(p, "")])
widths(ws2, [11, 8, 13, 9, 11, 9, 11, 9, 11, 9, 11, 9, 11, 12, 12, 12, 70]); ws2.freeze_panes = "B2"
for row in ws2.iter_rows(min_row=2):
    for c in row[2:16]:
        if isinstance(c.value, (int, float)) and c.column % 2 == 1: c.number_format = '#,##0.00'
ws3 = wb.create_sheet("Payer x action")
hdr(ws3, 1, ["Payer", "Recommendation", "Reason", "Visits", "$ open"])
agg = collections.defaultdict(lambda: [0, 0.0])
for r_ in rows:
    k = (r_["payer_last_billed"], r_["recommendation"], re.sub(r"\$[\d,]+\.\d\d", "$X", re.sub(r"\d+ days", "N days", r_["why"].split(";")[0]))[:110])
    agg[k][0] += 1; agg[k][1] += r_["ins_balance"]
for k, v in sorted(agg.items(), key=lambda kv: (kv[0][0], -kv[1][1])): ws3.append([k[0], k[1], k[2], v[0], round(v[1], 2)])
widths(ws3, [10, 18, 110, 8, 12]); ws3.freeze_panes = "A2"
for row in ws3.iter_rows(min_row=2): row[4].number_format = '#,##0.00'
ws4 = wb.create_sheet("Visits")
cols = ["pid", "visitid", "dos", "cpts", "modifiers", "fee", "ins_balance", "payer_last_billed", "last_sent", "days_since_sent", "bucket_sent", "days_since_dos", "bucket_dos", "primary_paid_by", "primary_paid_on", "live_secondary_on_chart", "pr_cost_share", "contractual_on_remit", "writeoffs_posted", "denial_codes", "last_denial", "deceased_dod", "recommendation", "why"]
names = ["Chart id", "Visit id", "DOS", "CPTs", "Modifiers", "Fee", "Insurance balance", "Payer last billed", "Last sent", "Days since sent", "Sent bucket", "Days since DOS", "DOS bucket", "Primary paid by", "Primary paid on", "Live secondary on chart", "PR cost-share on remit", "Contractual on remit", "Write-offs posted", "Denial CARCs posted", "Last denial", "Date of death (Medicare)", "Recommendation", "Why / rule"]
hdr(ws4, 1, names)
order = {"CORRECT & RESEND": 0, "WRITE OFF": 1, "WAIT": 2, "REVIEW": 3}
for r_ in sorted(rows, key=lambda x: (order.get(x["recommendation"], 9), -x["ins_balance"])): ws4.append([r_[c] for c in cols])
widths(ws4, [10, 10, 11, 14, 8, 8, 11, 9, 11, 7, 9, 7, 9, 10, 11, 12, 9, 9, 9, 10, 11, 11, 17, 90]); ws4.freeze_panes = "C2"; ws4.auto_filter.ref = ws4.dimensions
for row in ws4.iter_rows(min_row=2):
    for i in (5, 6, 16, 17, 18): row[i].number_format = '#,##0.00'
out = "/home/claude/unbilled/AR_aging_by_payer_2026-10-15.xlsx"
wb.save(out); print("saved", out)
