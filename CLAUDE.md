# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

The back office of a medical practice (Effinger Health PA, `practices/ehpa/`) run by Claude routines against AdvancedMD (AMD), Stedi, and Neon Postgres. Most code is Python helper scripts that read or write live billing data in AMD. Read `README.md` for the per-folder script tables. Each script opens with a `PLAIN ENGLISH` header that says what it decides, which of William's rules it applies, and what it never touches. The README is generated from those headers, so keep the headers accurate.

## Where the live code is

- **`scripts/helpers/`** (~1,400 flat files) is the mirror of the workspace the routines actually run in, `/home/claude/unbilled`. Every helper was written for that path; `amd.py` keeps its session cache there. The helpers import each other flat, by module name.
- `core/`, `billing/*`, `eligibility/`, `credentialing/`, `claimocity/` and `boards/` are the September reorganized copies the README describes. The same module name can exist in both places. `tools/button/run_all.py` does not import them: its bootstrap step copies every `*.py` from those folders and then from `scripts/helpers` flat into the workspace, so the `scripts/helpers` copy wins on a name clash. Fix a helper in `scripts/helpers/` first.
- `source env.sh` (bash) from the repo root puts only the reorganized folders on PYTHONPATH, not `scripts/helpers` or `tools/`.
- Files named like `act_0510_1006.py`, `inspector_0907.py` or `*_0907.py` are dated one-off passes. Their header records what was decided that night. Treat them as history, not as reusable library code.
- Learn a helper by running it with `--dry` (or `--list`), or by reading its own header. Batched reads across many helper headers have been refused by the auto-mode classifier.

## Running things

- **Billing engine:** `python3 tools/button/run_all.py --mode dry|live --steps all|columns,era,cascade,sweep,packages,cred,money,outstanding,denials,aging` (or `--profile all|columns|cascade|denials|aging`; `--packages <id,...>` limits the approval packages applied). `--mode` defaults to `dry`. `--steps all` leaves out `sweep` and `money` unless they are named. Reports go to `reports/button/<stamp>.json` and `latest.json`. `.github/workflows/billing-button.yml` runs the `columns` profile every two hours (at :17 on odd UTC hours) and the `cascade` profile at 05:35Z. Scheduled runs stay `dry` unless the repo variable `BUTTON_SCHEDULE_MODE=live`.
  - Each run rebuilds the workspace from the repo (default `/home/claude/unbilled`, override with `--ws`). If that path cannot be created it uses `~/ehpa-billing/unbilled` and re-points the path constants in the workspace copy of `amd.py`.
  - It needs `AMD_PSW` or a workspace `.amd_cred.json`. Without `STEDI_API_KEY` the Stedi steps are skipped. A failed AMD login leaves `.amd_login_lock` in the workspace, and every later run stops at bootstrap until a person checks the password and removes the lock. Do not remove it yourself.
  - A helper that fails does not stop the others. Helper output goes to `reports/button/logs_<stamp>/` (git-ignored), never to the console.
- **Self-tests** (offline, with stand-in AMD modules and invented data): `python3 tools/selftest/test_<name>.py`, one file per rule. Each exits 1 on failure. There is no test runner; run the file that covers what you changed. They are written for Linux: on Windows `test_pos_rule.py` fails with a `unicodeescape` SyntaxError because it writes a backslash temp path into generated source. That failure is the test harness, not the rule.
- On Windows use `python` where the commands say `python3`, and Git Bash for `env.sh`.
- **PHI gate:** `python3 tools/mirror/phi_gate.py tree <file-or-dir>` scrubs before commit. `python3 tools/selftest/test_phi_tree.py` tests the gate.
- **Neon app** (`apps/ehpadb`, TypeScript Neon Function, Hono): `npm run build:client`, `npm run typecheck`, `neon dev`, `npm run deploy`. Setup details are in `apps/ehpadb/README.md`. It is served at app.ehpa.dev from Neon Functions, not Vercel.
- **Desktop app** (`desktop/app.py` + `ui.html`): built into a Windows installer by `.github/workflows/desktop-build.yml` on pushes to `desktop/**` or `tools/button/**`.

## Data and privacy (hard rules)

- **No patient data in this repository.** No names, DOB, MBI, SSN or member ids. Commit chart, visit and charge ids, codes and dollars only. Prose about patients (run digests, needs lists) lives on Google Drive only. `.gitignore` excludes `*.json` / `*.csv` / `*.xlsx` / `*.xml` / `*.log`, `patient_db/` and `secrets/`, with explicit exceptions (`practices/**/*.json`, `reports/button/*.json`, `reports/feed/*.json`, the two `docs/` JSON files, the `apps/ehpadb` package files). Do not force-add ignored data files outside those exceptions.
- Credentials never enter the repo. They live in `secrets/` (git-ignored), the routine environment (`NEON_DATABASE_URL`, `AMD_PSW`, `STEDI_API_KEY`) or `.session.json`.
- Neon Postgres (org `ehpa`, project `ehpa-database`) is the permanent store. `tools/db/neon_db.py` is the only way in; `tools/db/neon_schema.sql` defines the typed `ehpa.*` views.

## Billing rules

`practices/ehpa/rules.md` holds William's standing billing rules: payer order, write-off codes, frequency-1-before-rebill, the timely-filing rules, and the insurance lookup order (patient database → AMD free 271 → Stedi → facesheet → William). Any change that posts, rebills, voids or writes off in AMD must follow it. Practice ids (NPIs, carriers, facilities, Drive and board ids) are in `practices/ehpa/*.json`. A new practice gets its own `practices/<code>/`.

AMD call shapes are recorded in `docs/captured_calls.md` (narrative) and `docs/api_vocabulary.json` (machine-readable). A call that isn't in the registry hasn't been captured: ask, don't guess. `tools/mirror/postman_build.py` generates `docs/postman_effinger_amd.json` from the vocabulary; never hand-edit it. Use one AMD login attempt per run.

## Shared files and git etiquette

- Several scheduled routines commit to `main` concurrently. Before each commit, run `git fetch -q origin main && git rebase --autostash origin/main` as its own command.
- `practices/ehpa/registers/approvals_pending.json` and `tf_writeoff_watch.json`: edit only in the `main` checkout right after pulling, commit each change alone, and push at once. Never copy a workspace copy over them.
- `docs/SHARED_LESSONS.md` is append-only (`merge=union`; format `- <UTC stamp> | <routine> | RULE|FIX|TRAP|WATCH | <one line> | <file>`). Routines read the newer lines at the start of each run. Gate it with `phi_gate.py` before committing. Same union merge for `registers/rebill_log.jsonl` and `practice_db_written.jsonl`.
- `main` is the record. `claude/effinger-billing-backend-mirror-w74pqv` is the branch the Claude project syncs from, pushed identical to `main`. The end-of-run mirror (GitHub · Postman · Drive) is `tools/mirror/mirror.py sync "<message>"`; the full order of operations is in `docs/MIRROR.md`.
- `mirror.py` protects certain helpers (amd, resave, freq1_visit, move_to_ins, ins_update, dx_primary_fix, approval_submit, payreasons, columns_scan, and the feed import helpers) by marker. A stale copy never overwrites `scripts/helpers/`.

## Other docs worth knowing

- `nightly/live/*.txt` are the instructions the scheduled routines actually follow. Each routine's stored prompt is a short pointer (`nightly/live/_stub_<routine>.txt`) that fetches `main` and reads its file there. To change what a routine does, edit its `nightly/live` file and run `mirror.py sync`; nothing is pasted into a routine. `nightly/live/README.md` maps routines to files and trigger ids.
- `nightly/*_prompt_vN.txt` are earlier versioned prompts. They have drifted from the live files, so do not treat them as current. `nightly/runs/<stamp>/` holds each past run's one-off scripts.
- `docs/BILLING_BUTTON.md`, `docs/APPROVALS_LOOP.md`, `docs/ROUTINE_PERMISSIONS.md`: the button engine, the mandatory-approval loop, and what routines may run unattended.
