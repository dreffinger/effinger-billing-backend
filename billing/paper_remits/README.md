# billing/paper_remits — paper & virtual-card remittances into the ERA Center (9/22/2026)
Pipeline: `ocr.sh` (pdftoppm 300 dpi gray + tesseract --psm 6) -> `classify.py` (page types: check_front/back, zelis_vcard, ua_eop_cover, ua_eob_detail, wn_remit, aetna_ssi_remit, moo_remit, simply_remit, fcc_remit / fcc_zero_payment, champva_eob, bcbs_remit, medicare_remit, globe_notice, other)
-> `extract.py` (claims per payer family; `fixacct()` repairs the 8-digit+letter AMD claim number) -> `assemble.py` (one record per remittance, links Zelis stubs by payment id / mailing code and physical checks by ICN or amount)
-> `plan.py` (dedupe on (family, acct, paid) across mailings, best reference: physical check > payer check number > EOP cover > Zelis payment id; one 835 per (family, reference); holds $0/COB statements, electronic payers, unreadable accounts, no reference)
-> `build835.py` (005010X221A1; CLP01 = the EOB's Patient Acct # = AMD claim number; ONE CAS segment per reason; claim-level OA-23/253 allocated to lines by allowed) -> `post_paper.py` (upload -> checkdetails -> ERA-linked addpayments under the payer's carrier -> verify -> dismiss -> register) -> `report.py` (workbook + summary, PHI, William only).
Inputs: `SCANS_DIR` (default /home/claude/scans) with raw/<batch>.pdf; Gmail attachments > ~6 MB come through Zapier (docs/input_channels.md).
Lessons (all proven on the live tenant 9/22/2026): see docs/api_vocabulary.json 'Upload an 835' + the RECIPE entry, and practices/ehpa/rules.md.

## 9/23/2026 additions
* `live_pull.py <in.json> <out.json>` — any list of AMD accounts -> live charges/payments/write-offs/plans (name -> chart via the unpaid list, then `lookuppatient` "LAST,FIR%"; handles "LAST,FIRST" and two-word surnames).
* `fb_parse2.py` — Florida Blue paper RA parser v2 (claim numbers Q…/M…/F…, every money column, remark codes, legend).
* `champva_prep.py` — CHAMPVA EOB (EFT, "information only") -> plan groups with per-line amounts read from the chart; `champva_traces.json` (PHI) maps EOB -> EFT trace.
* `actions.py` — the correct / resubmit / cascade / write-off action list joined to the live chart (workbook); `extra_items.json` (PHI) carries the hand-read items.
* `execute_actions.py` — William's word made actions: Medicare-first rebills (frequency 1, move-back, insorder), move-backs for claims already at Medicare, and the $0-statement write-offs (WOCAID2ND / WONCS) with a register.
* `post_paper.py`: `done_acct()` (a claim with no EOB lines counts as posted once any of its AMD lines posted); the re-filed second file carries the group's trn_suffix in its TRN.
Lessons: CHAMPVA never delivers an 835 to the ERA Center — post it from the paper EOB; Florida Blue on a Medicare retiree is secondary (chart order BCBS seq 1 ahead of FLO02 sends the claim to the wrong payer and AMD transfers the $0 denial to the patient); FCC $0 codes 041 / 14-075 / 76 are write-offs or credentialing, not resubmits.
