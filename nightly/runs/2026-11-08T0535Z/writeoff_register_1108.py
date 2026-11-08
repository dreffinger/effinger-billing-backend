"""Writeoff_register_2026-11-08.xlsx (date, patient, carrier, dos, amount, note) - the ledger counts every write-off pass."""
import openpyxl
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "writeoffs"
ws.append(["date", "patient", "carrier", "dos", "amount", "note"])
note = "WOINS untimely Medigap secondary - Medicare remit 3/10/2024 over 12 months, Humana 277 F0 finalized 0 (Sunday sweep 2026-11-08, William 10/14/2026 rule 9); check ref 277-1108"
for dos, amt, cid, pay in (("12/14/2023", 35.01, "22440103", "10178590"), ("12/14/2023", 15.16, "22440104", "10178591"), ("12/08/2023", 18.07, "22439919", "10178592"), ("12/08/2023", 12.89, "22439920", "10178593")):
    ws.append(["2026-11-08", "MORLAND,BETTINA (pat21021)", "HUM01", dos, amt, note + " charge %s paymentid %s" % (cid, pay)])
wb.save("Writeoff_register_2026-11-08.xlsx"); print("Writeoff_register_2026-11-08.xlsx rows", ws.max_row - 1, "total", round(35.01 + 15.16 + 18.07 + 12.89, 2))
