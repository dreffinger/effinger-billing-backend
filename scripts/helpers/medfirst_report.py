#!/usr/bin/env python3
# PLAIN ENGLISH (Report for the 9/23 wrong-payer / Medicare-first sweep)
# Decides: Nothing. Joins the sweep results (medfirst_<stamp>.jsonl), the three action registers and the hand-written verification
#          notes into one workbook (PHI - Drive/William only) + a markdown summary, so William sees per visit what was checked,
#          what was proved, what was rebilled where, and what is still his.
# ---
import json, os, collections, datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
SCANS = "/home/claude/scans"; STAMP = "20260923"; OUT = "/mnt/user-data/outputs"
rows = {json.loads(l)["pid"]: json.loads(l) for l in open(os.path.join(SCANS, "medfirst_%s.jsonl" % STAMP))}
regs = []
for f in ("cascade_act_0923_register.json", "medfirst_act_0923_register.json", "medfirst_act2_0923_register.json"):
    p = os.path.join(SCANS, f)
    if os.path.exists(p): regs += [dict(r, src=f.split("_")[0]) for r in json.load(open(p)) if not r.get("dry")]
CAR = json.load(open("/home/claude/unbilled/carriers.json")); CODE2NAME = {v[0]: v[1] for v in CAR.values()}
# --- verification notes (from the Stedi second pass, 9/23) --------------------------------------------------------------------
NOTES = json.load(open(os.path.join(SCANS, "medfirst_notes.json"))) if os.path.exists(os.path.join(SCANS, "medfirst_notes.json")) else {}   # per-chart verification notes (PHI: Drive working copy only)
def visits_of(r): return r.get("visits", [])
# --- per-visit action rows -----------------------------------------------------------------------------------------------------
acts = []
for x in regs:
    w = x["what"]
    if w.startswith("rebill "):
        vid = w.split()[1]; ok = "-> 204" in x["result"]; r = rows.get(x["pid"], {}); v = next((v for v in visits_of(r) if v["vid"] == vid), {})
        seq = w.split("seq ")[1].split()[0] if "seq " in w else ""
        acts.append({"patient": r.get("name", "?"), "chart": x["pid"], "visit": vid, "dos": v.get("dos", ""), "cpts": " ".join(v.get("cpts", [])), "from": v.get("carrier", ""), "to_seq": seq, "amount": v.get("insbal", v.get("patbal", "")), "action": "REBILL (freq 1)", "result": "queued 204" if ok else x["result"][:80], "at": x["at"], "src": x["src"]})
    elif w.startswith(("add plan", "end-date", "chart order", "fix member", "reopen")):
        r = rows.get(x["pid"], {}); acts.append({"patient": r.get("name", "?"), "chart": x["pid"], "visit": "", "dos": "", "cpts": "", "from": "", "to_seq": "", "amount": "", "action": w, "result": x["result"][:80], "at": x["at"], "src": x["src"]})
    elif "to patient" in w or "uninsured" in w:
        r = rows.get(x["pid"], {}); vid = w.split()[-1]; v = next((v for v in visits_of(r) if v["vid"] == vid), {})
        acts.append({"patient": r.get("name", "?"), "chart": x["pid"], "visit": vid, "dos": v.get("dos", ""), "cpts": " ".join(v.get("cpts", [])), "from": v.get("carrier", ""), "to_seq": "patient", "amount": v.get("insbal", ""), "action": "BALANCE TO PATIENT (uninsured / no supplement)", "result": x["result"][:80], "at": x["at"], "src": x["src"]})
    elif w.startswith("repair"):
        r = rows.get(x["pid"], {}); acts.append({"patient": r.get("name", "?"), "chart": x["pid"], "visit": w.split()[-1] if w.split()[-1].isdigit() else "", "dos": "", "cpts": "", "from": "", "to_seq": "", "amount": "", "action": w, "result": x["result"][:80], "at": x["at"], "src": x["src"]})
# --- workbook -------------------------------------------------------------------------------------------------------------------
wb = Workbook(); H = Font(bold=True); FILL = PatternFill("solid", fgColor="DDEBF7")
def sheet(name, headers, data, widths=None):
    ws = wb.create_sheet(name); ws.append(headers)
    for c in ws[1]: c.font = H; c.fill = FILL
    for row in data: ws.append([("" if v is None else v) for v in row])
    for i, w in enumerate(widths or [], 1): ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"; return ws
wb.remove(wb.active)
rebilled = [a for a in acts if a["action"].startswith("REBILL") and a["result"] == "queued 204"]
topat = [a for a in acts if a["action"].startswith("BALANCE")]
by_to = collections.Counter(); amt_to = collections.Counter()
for a in rebilled:
    key = a["src"]; by_to[key] += 1; amt_to[key] += float(a["amount"] or 0)
summary = [
 ["Wrong-payer / Medicare-first sweep - 9/23/2026", ""],
 ["Patients checked (AMD 271 on every chart plan + Stedi Medicare MBI lookup on the DOS; discovery / payer eligibility where needed)", len(rows)],
 ["  paper-EOB wrong-insurance group", sum(1 for r in rows.values() if "cascade" in r.get("groups", []))],
 ["  unpaid list, past-year visits at a non-Medicare payer (Tier 1: WellCare, VA, TRICARE, CHP, Humana, Aetna, UHC Dual, Sunshine, Simply, singletons; Tier 2: UHC, Florida Blue, FCC, Medicaid)", sum(1 for r in rows.values() if "unpaid" in r.get("groups", []))],
 ["Visits rebilled to the proven payer (frequency 1, every one queued 204)", len(rebilled)],
 ["  balance re-pointed ($)", round(sum(float(a["amount"] or 0) for a in rebilled), 2)],
 ["Balances moved to the patient (uninsured on the DOS / no supplement left)", len(topat)],
 ["Verdicts", ""],
]
for k, n in collections.Counter(r["verdict"].split(" ")[0] for r in rows.values()).most_common(): summary.append(["  " + k, n])
summary += [["", ""], ["Stedi spend (approx.)", "MBI lookups ~250 + payer eligibility ~20 + discovery 17 x $1.50"], ["CHP", "money lands: 47 CHP payments ($2,315) posted in AMD in September on the 9 CHP charts; ERA 4121958 (9/11) 13 auto-posted + 41 hand-posted by the routine; open CHP = 9/10-9/20 claims in normal lag + seven 2024-Jan 2025 leftovers ($550) past timely filing"]]
sheet("Summary", ["item", "value"], summary, [110, 40])
sheet("Rebilled", ["patient", "chart", "visit", "DOS", "CPTs", "billed to (wrong)", "now billed (plan seq)", "amount", "action", "result", "at (UTC)", "batch"],
      [[a[k] for k in ("patient", "chart", "visit", "dos", "cpts", "from", "to_seq", "amount", "action", "result", "at", "src")] for a in sorted(acts, key=lambda a: (a["chart"], a["visit"]))], [24, 10, 11, 11, 14, 10, 10, 9, 34, 22, 20, 9])
ver = []
for pid, r in sorted(rows.items(), key=lambda kv: -kv[1].get("balance", 0)):
    st, note = NOTES.get(pid, ("", ""))
    c = r.get("cms", {}); a271 = "; ".join("%s %s" % (k, v.get("status")) for k, v in r.get("amd271", {}).items())
    ver.append([r.get("name"), pid, r.get("dob"), round(r.get("balance", 0), 2), ", ".join("%s x%d" % kv for kv in r.get("carriers", {}).items()), r["verdict"], st or ("right payer, claim-content" if r["verdict"].startswith(("MA_SAME", "NO_MEDICARE")) and r["counts"].get("REVIEW", 0) + r["counts"].get("CLAIM_CONTENT", 0) else ""),
                a271, "A %s / B %s" % (c.get("partA") or "-", c.get("partB") or "-"), c.get("death") or "", "; ".join(m["name"][:35] for m in c.get("ma") or []), "; ".join(c.get("partd") or [])[:60], "; ".join(c.get("errors") or [])[:60], note])
sheet("Verification", ["patient", "chart", "DOB", "open $", "unpaid visits by payer", "sweep verdict", "status", "AMD 271 (today)", "CMS Part A / B", "date of death", "Advantage plan (CMS)", "Part D (CMS)", "Stedi errors", "what was decided / why"], ver,
      [24, 10, 11, 9, 22, 22, 16, 30, 22, 11, 30, 26, 22, 110])
will = [[rows[p]["name"], p, round(rows[p].get("balance", 0), 2), NOTES[p][1]] for p in NOTES if NOTES[p][0].startswith(("WILLIAM", "DONE / WILLIAM")) and p in rows]
sheet("Your decisions", ["patient", "chart", "open $", "what and why"], will, [24, 10, 9, 140])
pend = []
for pid, r in rows.items():
    for vid, act in r.get("plan", []):
        if act.startswith(("SECONDARY_PENDING", "CLAIM_CONTENT", "REVIEW", "VA_REVIEW", "BEFORE_DEATH", "AFTER_DEATH")):
            v = next((v for v in visits_of(r) if v["vid"] == vid), {})
            pend.append([r.get("name"), pid, vid, v.get("dos"), " ".join(v.get("cpts", [])), v.get("carrier"), v.get("insbal"), v.get("patbal"), ", ".join(v.get("paid_by") or []), ", ".join((v.get("codes") or [])[:5]), act, NOTES.get(pid, ("", ""))[1][:90]])
sheet("Not changed", ["patient", "chart", "visit", "DOS", "CPTs", "payer", "ins $", "pat $", "paid by", "remit codes", "why not", "note"], sorted(pend, key=lambda x: (x[10], x[0])), [24, 10, 11, 11, 14, 8, 8, 8, 12, 26, 34, 90])
path = os.path.join(OUT, "wrong_payer_sweep_2026-09-23.xlsx"); wb.save(path); print("wrote", path, "rebilled", len(rebilled), "to patient", len(topat), "patients", len(rows))
json.dump({"rebilled": len(rebilled), "amount": round(sum(float(a["amount"] or 0) for a in rebilled), 2), "to_patient": len(topat), "by_batch": dict(by_to), "amt_by_batch": {k: round(v, 2) for k, v in amt_to.items()}}, open(os.path.join(SCANS, "medfirst_report_totals.json"), "w"), indent=1)
