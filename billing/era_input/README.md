# billing/era_input — getting remittance scans INTO the pipeline (William, 10/5/2026)

The ScanSnap pushes each stack to Gmail as `Scans` / `Scan` messages from dreffinger@gmail.com to himself, one PDF per message
(`YYYYMMDDHHMMSS.pdf`, 2–80 pages, 150 KB – 21 MB). `billing/paper_remits/` reads them from `SCANS_DIR/raw/`. This module is the part
in front of it: find every batch, get its bytes into the container whatever the size, verify them, register them, and file the originals
in Drive `billing agent project files / eras scanned` (folder `1Fz90JGLa-s_QTw0RSuUdGnvQznxyGEHO`) so the pile is kept once, in one place.

## The size ladder (measured 10/5/2026; every number is a transport limit, not a Gmail one)
| attachment | route | what the session does |
|---|---|---|
| ≤ ~1 MB | Gmail connector `get_message` RAW | result is persisted to a tool-results file → `fetch_scans.py gmail-raw <file>` |
| ≤ 10 MB | Zapier Gmail `Get Attachment by Filename` → hydrate URL → Zapier Drive `Upload File` (folder = eras scanned, `convert=false`, NO `new_name` — Zapier appends `.pdf` again) → Google Drive connector `download_file_content` | persisted → `fetch_scans.py drive <file>` |
| > 10 MB | same upload, then the Zapier code action `google_drive_get_file_byte_range_base64` (`file_id`, `start`, `length` ≤ 4,000,000) once per 4 MB slice | each slice persisted → `fetch_scans.py chunks <files...>` joins them and checks Drive's md5 |
| cut short | `pdf_salvage.py raw/<batch>.pdf` | pulls the JPEG page images straight out of the bytes and OCRs them (pdftoppm renders 0 pages without the trailer) |

Why not simpler: the container proxy answers 403 to `zapier.com` (hydrate URLs) and `drive.google.com`; `www.googleapis.com` is reachable but
needs OAuth the container does not hold; the Gmail connector closes its connection above ~7.5 MB of JSON; the Drive connector refuses files
over 10 MB; Zapier's own code sandbox cannot resolve `zapier.com`, so `upload_urls_to_folder` fails on hydrate URLs — only the native
`Upload File` action hydrates them. Every Zapier call costs one Zapier task: the 10/5 pile (11 batches, 106 MB) used ~45 tasks and the
account hit its monthly limit with ONE 786 KB slice to go (resets 10/30/2026) — the salvage path recovered 76 of that batch's pages.

## Register
`practices/ehpa/registers/scan_batches.json` — one row per Gmail message id: file, size, sent, route, bytes, md5/sha256, pages, verified,
missing ranges. A batch is new when its message id is not there. `python3 fetch_scans.py status` shows raw / OCR state per batch.

## Routine recipe (for the 2-hourly columns run / a chat session)
1. Gmail search `from:dreffinger@gmail.com to:dreffinger@gmail.com subject:(scans OR scan) has:attachment newer_than:2d` → `batches.json` → `fetch_scans.py register`.
2. Per batch by size: the ladder above. Zapier for every batch also files the original in `eras scanned` (do that even when the Gmail RAW route works, so Drive holds the complete pile).
3. `bash billing/paper_remits/ocr.sh` from `SCANS_DIR` (skips batches with `ocr/<batch>/.done`), `pdf_salvage.py` for any batch pdftoppm cannot open.
4. `classify.py → extract.py → assemble.py → plan.py → post_paper.py --dry → post_paper.py → report.py` (billing/paper_remits/README.md).
5. Board rows for correspondence / holds / cards to key; mirror.


## Drive upload folders (11/27/2026) - `scan_intake.py`

William also scans straight into Drive "aa claude folders / scansnap uploads" and its two sub-folders: `scansnap eras and billing scans
files` (route billing) and `scanscnap credentialing files uploads` (route credentialing). The parent folder is route auto. Routes live
in Neon `public.intake_folders` (`scan_intake.py folders`); a new folder is added with `folders-sync` (a name with "credential" =
credentialing, "era"/"billing"/"remit"/"eob" = billing, else auto).

Session steps (chat or routine; Drive connector + Neon):
1. List each intake folder (`search_files`, `parentId = '<folder>'`), save the JSON, `scan_intake.py register <listing.json>`, then
   `scan_intake.py pending`.
2. For each pending file: `download_file_content` (the connector saves the PDF to a local file; its limit is 10 MB - bigger batches
   take the Zapier byte-range route above) → copy it into a new empty directory → `python3 -I scan_intake.py classify --pdf <file>
   --drive-id <id>`. It prints one entry per document found in the scan, with the vault folder and a document id for credentialing ones.
3. Several documents in one scan: `scan_intake.py split <pdf> <dir> --groups <split_groups>` writes one PDF per document.
4. Credentialing document: file it in the vault folder it names - `copy_file` (fileId, parentId = vault_folder_id, a plain title) for
   a whole scan, or `create_file` with the split part - then `credentialing/cred_vault.py add --id <doc_id> --entity <entity>
   --category <vault_category> --title "..." --drive-id <new id> --folder-id <vault_folder_id> [--expires ...] [--restricted]
   --source "scansnap <date>" [--file <part.pdf>]` (`--file` stores a copy in Neon; refused for restricted rows).
5. Remittance: the PDF goes to `SCANS_DIR/raw/drive_<id>.pdf` and the paper-remit pipeline below takes it from there; face sheet:
   the patient's Insurance Refresh Board card; billing letter: a board card.
6. `scan_intake.py mark <drive-id> --status filed|routed|skipped --vault-doc-id ... --routed-to ...`. Anything flagged (unknown,
   whose-document-unclear, a clash between folder and page, a duplicate) is marked `needs_review` and goes to William as one line.
The register, not the folder, says what is done (the connector cannot move or delete a file it did not create). Never commit a scan,
its title or its text: the repository is public.

## 10/6 additions (parse + plan)
- `llm_merge.py`: payer-NAME classifier (`PAYER_RULES`) overrides the agent's family hint; Florida Blue always held; card stubs with claims are remittances; LLM record beats a regex record with the same reference when it has more claims or a different amount; one card-keying row per (card, amount).
- New family **TRI00** (TRICARE East paper checks, car6872) across post_paper / build835 / plan / llm_merge.
- `build835.norm_cas()` maps payer legend codes (FCC "PC 3", Meritain "Co-Ins", PR-45...) to numeric CARCs.
- Square reconciliation of virtual cards: `payments.list` since 9/1 by last4 + amount -> `square_payments_sep.json`; cards not in Square = to key.
