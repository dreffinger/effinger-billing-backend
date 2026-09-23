# captured_calls additions — 9/22/2026 chat session (paper & virtual-card remittances → ERA Center)

Merge into `captured_calls.md` (Payments & ERA). Chart ids as patNNN only.

## POST /api/era/upload/835 — proven with synthetic 835s (9/22/2026)
Captured 9/2/2026 from William's UI import (`era_upload.upload`). This session proved what the importer does with files WE build from paper EOBs (`billing/paper_remits/build835.py`):
- multipart field `file`, filename `*.835`, text/plain; response `{"issuccess":true,"filename","filesize","filemd5checksum"}`. The check shows in `GET /api/era/checks` asynchronously — 5 s to ~4.5 min on 9/22; polling every 5 s drew HTTP 500 from `/api/era/checks`, 10 s is fine.
- Dedupe is by file MD5, not TRN: identical bytes are skipped silently; a different file with the same TRN02 creates a NEW check (so a corrected re-upload is possible; the engine dismisses the old one). A CLP03 (charge) of 0 makes the importer drop the whole file silently — a summary-only claim gets CLP03 = paid.
- Matching: CLP01 = the AMD claim number printed on every payer's EOB as "Patient Acct #" (8-digit visit id + sequence letter, e.g. 19442529A) → the visit; each SVC line → the charge by CPT (a claim with no SVC lines still matches the visit and returns chargecount / chargecode / insurancebalance with error "Procedure codes do not match", chargedetailid −1 — a free probe; an EOB CPT that differs from the chart errors the same way → re-file with AMD's own CPT under TRN <ref>L / <ref>N, posted with the clean check number).
- Reasons: ONE reason per CAS segment. `CAS*OA*253*0.93*23*45.44` lost the 23 → "Contains invalid payment reason codes"; `CAS*OA*253*0.93` + `CAS*OA*23*45.44` reads both.
- AMT*B6 is ignored (allowed = charge − adjustments). BPR16 → depositdate; TRN02 → paymentnumber; N1*PR name/REF*2U → `systemcarrier` only when AMD recognizes it, otherwise the visit's billed carrier (MCAD/FLO02/BAN07 seen) — so the posting call sets the carrier explicitly.
- Posting = the ERA-linked addpayments (`payreasons.era_linked_xml`) with `carrierid="car<payer's plan on the chart>"`, `checknumber=<clean check number>`, `paymethod="11"` (CHK) and the reasonlist from checkdetails; then `POST /api/era/checks/dismiss`. Never the Post button on these checks (it would post under the billed carrier).

## Chart writes used (all previously captured shapes)
- `getdemographic` → the payer's plan on the chart; `addinsurance` (no group number) when missing — UNI01 car42005 (United American), BAN07 car41999 (Washington National/Bankers Life), AET12 car42009, MUT01 car42012, PHY10 car302810 (Physicians Life via ECHO), SIM01 car42019, FLO99 car42008, USAA car303211.
- `gettxhistory` before and after every post (live insbalance, payments with reason children, write-offs). NEW: `gettxhistory` with `visitid=<vid>` returns ONE visit's history — page 1 of a long chart misses old visits (`txh.fetch_visit`).
- `void` class=void on a write-off ONLY when its amount equals what the payer then paid (a premature WOINS); `move_to_ins.move(cid)` + `manual_post.post(cid, "FLO02", 0, amt, "WOINS")` re-applied two Medicare contractuals the first version of the engine had voided (pat45520 99308 $49.97, pat17473010 99223 $152.86) — recipe in rules.md.
- Overpayment seen: pat17473010 v19449180 99223 — Simply (7707158635) and Washington National (1942731109) each paid the $31.94 coinsurance; Simply's post kept, WN's voided (`void` class=void payment) and HELD for William.
- Charges voided by the 9/21 re-render and re-entered on NEW visits (pat21489 v19445157 → v19455360; pat23161 v19450698 → v19455341): the FCC payments were filed against the new visits' claim numbers.

## Numbers
13 ScanSnap batches (Gmail attachments; 8 fetched through Zapier `gmail_get_attachment_by_filename` because the Gmail connector's RAW read fails above ~6 MB), 502 pages OCR'd; 40 (payer, check/card) groups, 89 claims $3,289.03 on the EOBs; POSTED 95 lines $3,046.70 + $1,795.97 write-offs (register: Drive `billing agent project files/paper remits 2026-09-22`). Holds by design: ~204 FCC $0 COB statement claims, 190 Florida Blue paper-RA claims (EFT, already electronic), 7 claims with no readable check reference, 2 unreadable account numbers; 1 HOLD (the overpayment above).

## practices/ehpa/rules.md lines (already in the bundle; repeated here for a session that merges by hand)
- (9/22/2026, chat) PAPER / VIRTUAL-CARD REMITS are posted through the ERA Center, never by hand (module billing/paper_remits; docs/input_channels.md).
- (9/22/2026, chat) Never void every write-off on a line to make room for a paper payment; only the premature one. Medigap + Medicaid both paying the same coinsurance = OVERPAYMENT HOLD.
- (9/22/2026, chat) Medicaid-plan paper payments carry their residual write-off in the SAME post (WOCAID2ND / WOMCAD).
- (9/22/2026, chat) Zelis virtual cards are keyed in Square's Virtual Terminal by hand; an unrun card is re-issued as a paper check → dedupe claims across mailings on (payer family, acct, paid).
- (9/22/2026, chat) Simply / USAA / Aetna SSI / United American / MoO / Physicians Life statements arrive on paper only; ScanSnap cloud app → Gmail/Drive is their input channel (Gmail RAW > 6 MB needs Zapier).
