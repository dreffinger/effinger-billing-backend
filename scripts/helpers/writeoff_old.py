# PLAIN ENGLISH (9/4 pre-2025 write-offs)
# Decides: Every pre-2025 audit line, past all timely-filing windows.
# Rules it uses: Your 9/4 approval; carrier = the denying carrier.
# Never touches: 2025+ lines.
# ---
"""William 9/4/2026: write off every pre-2025 audit line (past all timely-filing windows) - WOINS, non-ERA,
carrier = the denying carrier.  Logs to writeoff_old.log; register -> Writeoff_register_2026-09-04.xlsx"""
import json, re, time, resave, manual_post, openpyxl
from openpyxl.styles import Font
hits = json.load(open("audit_pr_transfer.json")); CAR = json.load(open("carriers.json"))
rows = [x for x in hits if x["dos"][-4:] < "2025"]
log = open("writeoff_old.log", "a"); done = {l.split()[1] for l in open("writeoff_old.log") if l.startswith("OK ")}
reg = []; tot = 0.0
for x in sorted(rows, key=lambda x: (x["patient"], x["dos"][-4:], x["dos"])):
    cid = x["chargeid"]
    if cid in done: continue
    d = resave.detail(cid); c = re.search(r'<charge [^>]*>', d).group(0)
    st = dict(re.findall(r'(insbalance|patbalance|void)="([^"]*)"', c))
    bal = float(st.get("insbalance") or 0)
    if st.get("void") == "1" or bal <= 0:
        msg = "SKIP %s %s %s bal %s void %s" % (cid, x["patient"], x["dos"], bal, st.get("void")); print(msg); log.write(msg + "\n"); continue
    car = x["reasons"][0][2]
    if car not in manual_post.CAR: car = "FLO02"
    ok, r = manual_post.post(cid, car, 0.0, bal, "WOINS", "WO-TIMELY", "Past timely filing (%s %s) - William approved write-off 9/4/2026" % (x["reasons"][0][2], x["reasons"][0][0]))
    msg = "%s %s %s %s %s %s $%.2f %s" % ("OK" if ok else "ERR", cid, x["patient"], x["dos"], x["cpt"], x["reasons"][0][0], bal, "" if ok else r[:120])
    print(msg, flush=True); log.write(msg + "\n"); log.flush()
    if ok: reg.append([x["patient"], x["patientid"], x["dos"], x["cpt"], x["reasons"][0][2], x["reasons"][0][0], bal, "WOINS", "past timely filing - approved 9/4/2026"]); tot += bal
    time.sleep(0.6)
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Write-offs 9-4-2026"
ws.append(["Patient", "Patient ID", "DOS", "CPT", "Denying carrier", "Denial code", "Amount", "Code", "Reason"])
for r in reg: ws.append(r)
ws.append(["TOTAL", "", "", "", "", "", round(tot, 2), "", ""])
for c in ws[1]: c.font = Font(bold=True)
for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = min(40, max(10, max(len(str(c.value or "")) for c in col) + 2))
wb.save("Writeoff_register_2026-09-04.xlsx"); print("written off %d lines $%.2f" % (len(reg), tot))
