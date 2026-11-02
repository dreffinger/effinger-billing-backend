# PLAIN ENGLISH (Insurance Refresh Board update file for the 11/2/2026 chat run - answers to William's 16 rows)
# Decides: nothing in AMD. Reads registers/board_act_2026-11-02T0855Z.json (what board_act_1102.py did) and writes
#   board_updates_2026-11-02T0855Z.json for the board inbox: one note + status per row, checks[] per section, the facility /
#   name / DOB fields William asked for on the Humana PI197 row. Never a direct board write.
# Usage: python3 board_file_1102.py
import json, datetime, collections
STAMP = "2026-11-02T0855Z"; NOW = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"); WHEN = "11/2"
reg = json.load(open("registers/board_act_%s.json" % STAMP))
by = collections.defaultdict(list)
for s in reg["steps"]: by[s["key"][0]].append(s)
def summ(sec):
    st = by.get(sec, []); ok = [s for s in st if s["ok"]]; bad = [s for s in st if not s["ok"]]
    return ok, bad
def res(sec, ok_text, extra=""):
    ok, bad = summ(sec)
    if not ok and not bad: return "na", "section not run"
    t = ok_text % len(ok) if "%d" in ok_text else ok_text
    if bad: t += " | %d step(s) FAILED: %s" % (len(bad), "; ".join(b["key"] + " - " + b["msg"][:80] for b in bad))
    return ("ok" if not bad else "no"), t + extra
ops = []
def row(rid, sec, ok_text, note, status="done", extra_set=None):
    okv, text = res(sec, ok_text)
    st = status if okv == "ok" else "claude"
    op = {"op": "upsert", "collection": "items", "id": rid, "set": dict({"status": st, "updated": NOW}, **(extra_set or {})),
          "append": {"notes": [{"who": "Claude", "text": note + (" [%s]" % text if okv != "ok" else ""), "at": NOW}],
                     "checks": [{"ok": okv, "result": text, "src": "chat run %s (William's 11/2 board answers)" % STAMP, "when": WHEN}]}}
    ops.append(op)
row("[name]-25558", "A", "%d steps ok", "Your 'restore' is done: the twelve 2025 write-offs (3/3-8/1/2025, $1,919) were voided, the balances put back on insurance and every one of those visits plus the three still-open 9/8-10/25/2025 visits ($771) re-sent to UHC Dual Complete as original claims. They are 13-20 months old, so UHC may answer timely filing - a CO-29 then becomes a WOLATE write-off under the watch.")
row("[name]-17475837", "B", "%d steps ok", "Your 'restore' is done: the seven 2026 WOINS write-offs ($1,986) were voided and the visits re-sent to AARP Medicare Advantage (seq 2) as original claims; all inside 12 months.")
row("[name]-17472519", "C", "%d steps ok", "Florida Blue Medicare Advantage XJPH45025057 (8/1/2024) added as the BCBS1 carrier (the Florida Blue Medicare payer), the dead Humana plan ended 7/31/2024, the 10/27 CCM ($315) re-routed to it as an original claim.")
row("jacobsen-[first]-17477039", "D", "%d steps ok", "Humana Medicare Advantage H73823697 (1/1/2026) added, WellCare ended 12/31/2025, the six July visits ($961) re-sent to Humana as original claims.")
row("[name]-47979", "E", "%d steps ok", "From the HCA facesheet: chart DOB corrected to [DOB], UHC Dual Complete (D-SNP) member [member id] added, the dead UHC MA plan ended 12/31/2025, and the eleven 10/22-10/31 hospital visits ($1,723) re-sent UHC Dual first / FCC second as original claims. UHC's Medicaid line (UHC FL MCD, same id) has no AMD carrier yet - only needed if a cost-share is left after UHC Dual pays.")
row("primrose-cotterell-17478213", "F", "%d steps ok", "The facesheet DOB [DOB] is on the chart now (was 03/07/1958); the eleven Sunshine hospital claims 10/21-10/31 ($1,407) went again as original claims.")
ops.append({"op": "upsert", "collection": "items", "id": "tolliver-[first]-17471204", "set": {"status": "william", "updated": NOW}, "append": {"notes": [{"who": "Claude", "text": "The Aetna plan on the chart already names Rustin as the subscriber (spouse), but his responsible-party record carries no date of birth - that is the likeliest reason Aetna answers 'entity not eligible' on claims it otherwise accepts as active. The backend edit (updaterespparty) is refused with 'Another user has changed this responsible party record' on every echo shape, so this one is yours: Patient > Family / Responsible Party > TOLLIVER,RUSTIN > DOB [DOB], Save. Say 'resend' here afterwards and the four Aetna claims (2/3, 2/4, 3/8, 3/9/2026, $703) go again as originals. No group number is entered (standing rule).", "at": NOW}], "checks": [{"ok": "human", "result": "subscriber DOB edit refused by AMD (record-changed fault x3); claims held until the DOB is on the record", "src": "chat run %s" % STAMP, "when": WHEN}]}})
row("rowantree-rustin-17475392", "H", "%d steps ok", "Stedi's TRICARE East eligibility answers ACTIVE (Plan 315 Prime, retired sponsor family) for the DBN already on the chart, so nothing on the chart was wrong - the seven TRICARE claims (2/2-10/27/2026, $1,429) were re-sent as original claims. If Humana Military returns them again, the return letter's reason is what we need.")
row("[name]-17478229", "I", "%d steps ok", "TRICARE For Life 308568029 added as the Medicare secondary (order Medicare first); the Medicare claims cross over to TFL on their own, nothing re-sent.")
row("[name]-12183299", "J", "%d write-offs posted", "Written off per your 'write-off': the $31.94 coinsurance of 5/8/2026 and the six matching 5/9-5/14 hospital residuals ($14.38 each) still billed to the ended Aetna plan - WOCLTREQ with a dated note, $118.22 in all.")
row("[name]-21593", "K", "%d write-offs posted", "Written off per your 'written off': the eight August-2026 WellCare residuals ($184.33 incl. the 8/11 $31.94) - WOCLTREQ with a dated note (deceased [DOB], no live secondary). The date of death stays yours to mark on the chart.")
row("maplin-kendrew-17469446", "L", "%d visits re-routed", "Per 'Humana Medicaid': every 2025 residual still billed to the dead WellCare plan (18 visits incl. the three you named, $320 in all) was re-routed to the Humana Medicaid plan behind Medicare and sent as an original secondary claim.")
row("osgood-jenna-45011", "M", "%d write-off posted", "Written off per your 'write off': the 1/9/2025 CHP charge $61.34 - WOINS with a dated note (CHP $0 answers, deceased [DOB]). The date of death stays yours to mark on the chart.")
row("thackeray-kendrew-17472874", "N", "%d steps ok", "Per your OK: WellCare ended 12/4/2025 and the two December-2025 visits ($214) re-sent Medicare first, Sunshine second, as original claims. The 15 April-2026 UHC visits UHC finalized as 585 non-covered are handled by today's cleanup pass (written off WONCS - the payer adjudicated them, nothing is pending).")
row("nesbit-edith", "O", "%d steps ok", "Per 'move 10/22 CCM to 10/21': the CCM visit (99487+99489) was re-dated to 10/21/2026 with a full-visit echo (same charge ids) and both it and the 10/22 99309 were re-sent Medicare first as original claims; the CCI hold on the 99309 clears with the re-date.")
ops.append({"op": "upsert", "collection": "items", "id": "nesbit-edith", "set": {"status": "done", "updated": NOW}, "append": {"notes": [{"who": "Claude", "text": "Duplicate placeholder of the NESBIT,EDITH row (same chart 17471793) - closed; the work is recorded on nesbit-edith.", "at": NOW}]}})
ops.append({"op": "upsert", "collection": "items", "id": "[name]-17477533", "set": {"status": "william", "updated": NOW}, "append": {"notes": [{"who": "Claude", "text": "The Capital Square sheet shows the same DOB ([DOB]) and the same MBI ([MBI]) the chart already carries, so the chart is not the problem - Medicare's own record holds a different birth date for this MBI (CMS answers AAA 71 'birth date does not match' on both AMD's and Stedi's eligibility). Needed: the Medicare card itself, or a call to 1-800-MEDICARE / SSA to confirm the DOB on file. The 10/25 CCM ($206) cannot be paid by Medicare until the record matches.", "at": NOW}], "checks": [{"ok": "human", "result": "facesheet DOB and MBI = chart; CMS still AAA 71 - Medicare's record differs; card or 1-800-MEDICARE", "src": "chat run %s" % STAMP, "when": WHEN}]}})
ops.append({"op": "upsert", "collection": "items", "id": "humana-pi197-precert-1031", "set": {"updated": NOW, "patient": "ANSELL,[first] (DOB [DOB], Aspire at Tallahassee) · MORROW,ROWAN (05/13/1980, Brynwood) · [name] (02/14/1968, Brynwood) · DASHWOOD,[first] D (05/16/1978, Brynwood)", "dob": "see patient", "facility": "Aspire at Tallahassee (Ansell) / Brynwood Health and Rehabilitation (Morrow, Ford, Dashwood) - SNF residents", "facnow": {"kind": "SNF", "name": "Aspire at Tallahassee / Brynwood", "dos": "10/23/2026"}},
            "append": {"notes": [{"who": "Claude", "text": "Per your note: names, DOB and facility are on the row now - chart 17469512 ANSELL,[first] 08/21/1967 Aspire (v19459179 10/23); chart 17475713 MORROW,ROWAN 05/13/1980 Brynwood (v19458868 10/19); chart 17471384 [name] 02/14/1968 Brynwood (v19458751 10/05); chart 46048 DASHWOOD,[first] 05/16/1978 Brynwood (v19458752 10/05). The four PI-197 authorization denials ($564) still need the facilities' Humana authorization numbers (or 'write off').", "at": NOW}]}})
out = {"schema": "irb-board-updates/1", "source": "chat run %s (William's 11/2 board answers)" % STAMP, "created": NOW, "ops": ops}
json.dump(out, open("board_updates_%s.json" % STAMP, "w"), indent=1)
print("wrote board_updates_%s.json" % STAMP, len(ops), "ops")
