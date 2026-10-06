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
