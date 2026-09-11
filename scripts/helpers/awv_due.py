# PLAIN ENGLISH (Annual wellness visit due list)
# Decides: For every active patient, when the next AWV is billable.
# Rules it uses: 11 full months after the last G0438/G0439/G0402.
# Never touches: AMD writes.
# ---
"""AWV due list: for every active patient (visit in last 120 days), last G0438/G0439/G0402 date in AMD, next-eligible
date (1st of the same month next year = 11 full months rule), current facility, primary payer.  Output AWV_due_list.xlsx"""
import txh, resave, amd, json, re, time, datetime, collections, openpyxl
from openpyxl.styles import Font, Alignment
FAC = json.load(open("facilities.json")); CAR = json.load(open("carriers.json"))
pids = json.load(open("audit_pids.json"))
AWV = {"G0439", "G0438", "G0402"}
today = datetime.date.today(); cutoff = today - datetime.timedelta(days=120)
def d(s): return datetime.datetime.strptime(s, "%m/%d/%Y").date()
rows = []; t0 = time.time()
for i, pid in enumerate(pids):
    try: root = txh.fetch(pid)
    except Exception as e: print(pid, "ERR", e, flush=True); time.sleep(5); continue
    charges = [c for c in root.iter("charge") if c.get("void") != "1" and not (c.get("fee") or "").startswith("-") and c.get("dos")]
    if not charges: continue
    last = max(charges, key=lambda c: d(c.get("dos")))
    if d(last.get("dos")) < cutoff: continue
    name = next((p.get("patient") for c in charges for p in c.iter("payment")), "") or ""
    awvs = sorted([c for c in charges if c.get("proccode") in AWV], key=lambda c: d(c.get("dos")))
    last_awv = awvs[-1] if awvs else None
    awv_status = ""
    if last_awv:
        pays = [(p.get("amount"), [r.get("code") for r in p.iter("payreason")]) for p in last_awv.iter("payment") if p.get("void") != "1"]
        paid = any(float(a or 0) != 0 for a, _ in pays)
        awv_status = "paid" if paid else ("denied " + ",".join(sorted({c for _, cs in pays for c in cs})) if pays else "billed, no response")
    try:
        x = resave.detail(last.get("id")); fac = FAC.get(re.search(r'facility="([^"]*)"', re.search(r'<visit [^>]*>', x).group(0)).group(1), "")
        plans = [(m.group(1), m.group(2), m.group(3)) for m in re.finditer(r'<insplan id="ins\d+" carrier="(car\d+)" begindate="[^"]*" enddate="([^"]*)" sequence="(\d+)"', x)]
    except Exception: fac = ""; plans = []
    active = [CAR.get(c, [c])[0] for c, e, s in plans if not e]
    if last_awv:
        la = d(last_awv.get("dos")); nxt = datetime.date(la.year + 1, la.month, 1)
    else: nxt = None
    due = "DUE NOW" if (nxt is None or nxt <= today) else ("due %s" % nxt.strftime("%m/%d/%Y"))
    if nxt and nxt > today and (nxt - today).days <= 60: due = "due soon " + nxt.strftime("%m/%d/%Y")
    rows.append([name, pid, fac, last.get("dos"), ", ".join(active), last_awv.get("dos") if last_awv else "", last_awv.get("proccode") if last_awv else "", awv_status, nxt.strftime("%m/%d/%Y") if nxt else "", due, len(awvs)])
    if i % 50 == 0: print("progress", i, len(rows), "%.0fs" % (time.time() - t0), flush=True)
    time.sleep(0.3)
rows.sort(key=lambda r: (r[2], r[0]))
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "AWV by facility"
ws.append(["Patient", "Patient ID", "Facility (last visit)", "Last visit", "Active plans", "Last AWV DOS", "Code", "Last AWV result", "Next eligible", "Status", "AWVs on file"])
for r in rows: ws.append(r)
ws2 = wb.create_sheet("Read me")
for line in ["AWV due list built %s from AMD transaction history (patients with a visit in the last 120 days)." % today.strftime("%m/%d/%Y"),
             "Next eligible = 1st of the same month one year after the last AWV (Medicare: 11 full months must pass). DUE NOW = no AWV on file in AMD or eligible date passed.",
             "'Last AWV result' denied PR119 = Medicare says another AWV was already paid within 12 months (likely another provider) -> check SPOT eligibility for the last AWV date before rebilling.",
             "No AWV on file in AMD does not prove nobody billed one - SPOT eligibility (First Coast) shows the last AWV date Medicare has. Check doubtful ones before the visit.",
             "MA plans (UHC, Humana, WellCare...) cover the AWV on the same 12-month rule; Medicaid-only patients are excluded from AWV."]:
    ws2.append([line])
for c in ws[1]: c.font = Font(bold=True)
ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = min(44, max(10, max(len(str(c.value or "")) for c in col[:80]) + 2))
ws2.column_dimensions["A"].width = 150
wb.save("AWV_due_list_%s.xlsx" % today.strftime("%Y-%m-%d")); print("DONE", len(rows))
