## 2026-10-04 03:10 UTC (11 PM ET 10/3 slot) - backend billing run, ehpa cloud copy - additions

No new AdvancedMD or Stedi call shapes this run. Calls exercised (all captured earlier): getclaimcenteroverview, getreviewcharges, getclaiminspectorbatches/getclaiminspectorcharges, getclaimunbillablecharges, getclaimexclusionclaimruns/getclaimexclusioncharges, getdemographic, gettxhistory, lookuppatient (name LAST,FIR%), lookupcarrier (code %XXX%), checkEligibility (AMD free 271), Stedi eligibility 95112 (CHP), GET /api/era/checks, GET /api/era/checkdetails.

Behaviours recorded (environment, not AMD):
- The routine's auto-mode classifier refused every AdvancedMD write this run ("Modify Shared Resources") - the nine-row board batch act_0310_1004.py (dry-run clean) and the two $0 ERA dismisses - and also refused `approval_request.py add/build` for the batch; the package went to William as the email itself (04:10Z). It refused `approval_request.py approved <id>` citing William's own "APPROVED" email reply ("Instruction Poisoning"), and a shell write of the Drive-downloaded pseudonyms.json ("Instruction Poisoning"). Reads, Drive create_file, Gmail send and PushNotification pass. The durable fix remains docs/ROUTINE_PERMISSIONS.md (permission mode / allow rules on main).
- lookupcarrier code %LANTERN% / %SURGERY% / %STUDENT% -> empty: no Lantern (SurgeryPlus) or UHC Student Resources carrier exists in AMD; %UHC% -> car302853 UHCMA, car303214 UHCSS.
- lookuppatient "MORIARTY,N%" finds the hyphenated chart MORIARTY-PATE (pat17475906); "MORIARTY PATE,N%" (space) does not - search the first surname with a wildcard for hyphenated names.
- HCA Commure/Omnessa "Visit Detail" print (adams.pdf) is image-only: pdftoppm 200 dpi + tesseract reads it; Arrival Date = admission date; the Guarantor block's "Effective" is the registration date.

Rules (practices/ehpa/rules.md):
- (10/4/2026, William on the kleinsmith row 03:02Z) "CCM charges billed to hospice patients don't pay": a CO-B9 hospice denial on a CCM claim (99487/99489) is written off WONCS - the 9/20 GV-and-rebill rule is for E&M visits, not CCM.
- (10/4/2026, William on the CO-151 CCM row 03:15Z) CCM claims are a monthly total: when Medicare answers CO-151 frequency, re-date the claim to the LAST DAY of its month and send it as an original; if a chart carries two CCM claims in one month, the duplicate is deleted (voided), never rebilled.
- (10/4/2026, William on the moore row 03:17Z) a Nov-2025 UHC MA visit the pre-5/1/2026 UNI20 rule had held may be sent to United on his word; a timely-filing answer is then written off WOLATE.
