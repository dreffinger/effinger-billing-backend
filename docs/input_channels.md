# Input channels — how paper reaches the ehpa cloud practice (William, 9/22/2026)

The clinician is the end user. Every channel below exists so that the information a practice needs (remittances, facesheets, the daily census) can be dropped into the workflow in whatever way is quickest for the person holding the paper — and so that the same pipeline works for other practices, not only Effinger Health PA.

## 1. ScanSnap → cloud (the scanner is an input device for the practice)
- The ScanSnap machine scans a stack; the **ScanSnap cloud app** pushes each batch to the cloud (Gmail attachment and/or a Drive folder) — no PC, no hand-off.
- Effinger routing today: batches arrive in Gmail as PDF attachments (`msgid__YYYYMMDDHHMMSS.pdf`, 8–70 pages each) and a Drive folder `ScanSnap` (id `1wpksmUG0a8VgPk2q41LNNIfRiwEJAXQh`) is the second landing zone. Watch both; a batch is new when its message id / file id is not in `registers/scan_batches.json`.
- What comes off the scanner (9/22/2026 pile, 13 batches, 502 pages): paper EOBs and EOPs (United American / Globe Life, Washington National–Bankers Life, Aetna Senior Supplemental, United of Omaha, Physicians Life via ECHO, USAA Life, CHAMPVA), Zelis virtual-card payment stubs, physical checks (Florida Community Care, United American, Mutual of Omaha) with their backs, Simply Healthcare LTSS/MMA remits (Zelis mailings), Florida Community Care $0 COB statements, Florida Blue paper RAs (already electronic), Medicare paper RAs, payer correspondence (Optum/WellCare record requests, UHC notices, Cigna/Evernorth recredentialing termination), blank backs.
- Pipeline (`billing/paper_remits/`): `ocr.sh` (pdftoppm 300 dpi + tesseract) → `classify.py` (page types) → `extract.py` (structured claims per payer family) → `assemble.py` (one record per remittance; links stubs and physical checks) → `plan.py` (dedupe across mailings, best payment reference, one 835 per (payer, check)) → `build835.py` → `post_paper.py` (ERA Center import + ERA-linked posting under the payer's carrier).

## 1b. ScanSnap → Drive upload folders, sorted by kind (William, 11/27/2026)
- William scans straight into Drive "aa claude folders / scansnap uploads". Three folders, each a row of Neon `public.intake_folders`:

| folder | route | what goes there |
|---|---|---|
| `scansnap uploads` | auto | anything; the sorter decides |
| `scansnap eras and billing scans files` | billing | EOBs/EOPs/RAs, paper checks, Zelis/ECHO card stubs, face sheets, records requests |
| `scanscnap credentialing files uploads` | credentialing | licenses, DEA, COIs, board/CAQH, Medicaid/Medicare/payer letters, ID cards, collaboration agreements |

- `billing/era_input/scan_intake.py` keeps one register row per Drive file (Neon `public.scan_intake`), reads each scan page by page
  (text layer, else tesseract), splits a scan that holds several documents, and labels each: remittance / face sheet / billing
  letter go to billing (`billing/paper_remits/`, the Insurance Refresh Board); a credentialing document goes to the Credentialing
  Vault folder for its person and category and is indexed with `credentialing/cred_vault.py add`; personal mail is skipped and left
  where it is. The folder is a hint; the page decides, and a clash is flagged. Steps: `billing/era_input/README.md`.
- The Drive connector cannot move or delete a file it did not create, so originals stay in the upload folders; the register is
  what says a file is done.

## 2. Gmail attachments through Zapier (the routine's robust channel)
- The Gmail connector's RAW message read fails above ~6 MB ("session expired"); the scanner's larger batches never come through it.
- Zapier → Gmail (`gmail_get_attachment_by_filename`, params message_id + attachment_filename) returns a hydrate URL that downloads any size with curl. A routine that carries a Zapier connection can therefore fetch every scan batch unattended; the Gmail connector alone cannot.
- Routine recipe: Gmail search `has:attachment filename:pdf newer_than:2d` (ScanSnap subject/sender) → for each attachment not in the batch register: Zapier attachment → download → pipeline above → post → report.

## 3. Facesheets and the daily census
- Today the census comes through the Claimocity app (screens/exports) and PCC facesheets land in Drive (`pcc_facesheets`, id `1hEf4XJ6ppTH_UWva21JPW25g3uebKPAh`).
- Recommendation to explore: scan the facility's printed census list each morning on the ScanSnap and let the same OCR pipeline produce the day's patient list (name, room, payer lines) — one scan instead of app data entry, for any facility that hands the clinician paper. The same drop handles facesheets (insurance cards, ICNs, hospice status) for the insurance cascade.
- Output for the clinician: a census/facesheet board row per patient with what is missing (auth, member id, facesheet) — never a manual re-key.

## 4. Payments that are not checks
- **Zelis / ECHO virtual cards** (MasterCard 5551-50xx…, "Valid Thru mm/yy") are keyed in **Square's Virtual Terminal** by hand. Square's API cannot take a card number (`payments.create` needs a Web Payments SDK token, card-on-file, CASH or EXTERNAL) and recording them as EXTERNAL would misstate collections — so the pipeline produces a keying list (last-4, amount, expiry, payment id, payer) and checks Square's payment history for cards already run. Unrun cards expire and the payer re-issues the same EOB as a paper check → the pipeline dedupes claims across mailings.
- **FCC (Florida Community Care)** pays by paper check; the deposit is the reconciliation (William 9/22/2026).
- Electronic payers (Medicare, Florida Blue, Humana, Centene, CHAMPVA EFT, UHC/Optum Pay) never need this channel: their 835s already feed the ERA Center, and their paper RAs in the pile are held, not posted.

## 5. Where the learned data goes (the triple mirror)
GitHub `main` (code + registers, pseudonymized) · Postman collection (every call, generated from `docs/api_vocabulary.json`) · Drive `billing agent project files` (PHI-OK working copy: the posting workbook, the page inventory, the 835 files) · digest in `chat history`.
