# PLAIN ENGLISH (Mark audit row done)
# Decides: Marks a patient done/checked in the audit workbook.
# Rules it uses: Workbook only.
# Never touches: AMD.
# ---
"""Mark a patient DONE/CHECKED in the audit workbook and drop from 'Remaining to check'.
Usage: python3 mark_done.py "<name prefix>" "<status>" "<note>" [green|yellow]"""
import openpyxl, sys
from openpyxl.styles import PatternFill
prefix, status, note = sys.argv[1].upper(), sys.argv[2], sys.argv[3]; color = "E2EFDA" if (len(sys.argv) < 5 or sys.argv[4] == "green") else "FFF2CC"
wb = openpyxl.load_workbook("PR_transfer_audit_2026-09-03.xlsx"); ws = wb["By patient"]; hdr = [c.value for c in ws[1]]
si = hdr.index("Insurance refresh status") + 1; ci = hdr.index("Checked by William") + 1; ni = hdr.index("Notes (PCC / facesheet)") + 1
for r in range(2, ws.max_row + 1):
    if (ws.cell(r, 1).value or "").upper().startswith(prefix):
        ws.cell(r, si).value = status; ws.cell(r, ni).value = note; ws.cell(r, ci).value = ws.cell(r, ci).value or "x  (9/4)"
        for c in ws[r]: c.fill = PatternFill("solid", fgColor=color)
w2 = wb["Remaining to check"]
for r in range(w2.max_row, 1, -1):
    if (w2.cell(r, 1).value or "").upper().startswith(prefix):
        if status.startswith("DONE"): w2.delete_rows(r)
        else:
            w2.cell(r, si).value = status; w2.cell(r, ni).value = note
wb.save("PR_transfer_audit_2026-09-03.xlsx"); print("remaining", w2.max_row - 1)
