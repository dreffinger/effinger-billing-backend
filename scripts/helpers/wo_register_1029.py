# Writes Writeoff_register_<date>.xlsx for tonight's write-off pass (date, patient, carrier, dos, amount, note) so the ledger counts it.
import openpyxl, datetime, json, os
rows = [
 ("2026-10-29", "CARMODY,NORCOTT", "FLO02", "10/25/2025", 206.00, "99487 untimely: primary Medicare claim over 12 months from DOS, never adjudicated (claim carried a typo MBI; chart MBI corrected to the CMS-issued one 10/29/2026) - WOINS, paymentid 10176954, chart 17473431 v19421004 c23326208"),
 ("2026-10-29", "CARMODY,NORCOTT", "FLO02", "10/25/2025", 109.00, "99489 untimely: same visit - WOINS, paymentid 10176955, chart 17473431 v19421004 c23326209"),
]
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "writeoffs"
ws.append(["date", "patient", "carrier", "dos", "amount", "note"])
for r in rows: ws.append(list(r))
fn = "Writeoff_register_20261029.xlsx"; wb.save(fn)
os.makedirs("registers", exist_ok=True)
json.dump([dict(zip(["date", "patient", "carrier", "dos", "amount", "note"], r)) for r in rows], open("registers/writeoff_2026-10-29T0535Z.json", "w"), indent=1)
print(fn, len(rows), "rows", sum(r[4] for r in rows))
