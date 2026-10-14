# The Billing Button (set up 2026-10-11, William's order: "package all the billing routines and the nightly cascade in an automatic run, as they are written in GitHub, with a dashboard where I press one button and get reports - no mandatory-approval blocks")

One button runs every billing script this repository carries, in the standing order of the
2-hourly backend billing run and the nightly insurance cascade, on a machine GitHub lends us
(or on William's own PC), with no permission classifier in the path. Pressing the button is the
approval. The result is one report the pages draw.

The plain-words tour of every file is the **App Build** page:
https://claude.ai/artifact/DecNZkNsoQ4V2c1gwLLqiq

## Pieces

| Piece | What it is |
|---|---|
| `tools/button/run_all.py` | The engine. Builds the workspace the helpers expect (`/home/claude/unbilled`), logs in to AdvancedMD once, runs each helper as one plain command in the standing order, parses each helper's own summary line, writes `reports/button/<stamp>.json` + `latest.json` (schema `button-run/1`). `--mode dry` reads and counts; `--mode live` writes by the standing rules. |
| `tools/button/outstanding_claims.py` | Read-only. Every visit with an insurance balance, grouped by age, carrier and month -> `outstanding_claims.json`; the engine copies it to `reports/button/outstanding_latest.json`. |
| `.github/workflows/billing-button.yml` | The cloud runner. `workflow_dispatch` (the button) with inputs mode / steps / packages / note, plus two schedules. Commits the reports back to main. One run at a time (`concurrency: billing-button`). |
| `.github/workflows/desktop-build.yml` | Builds the Windows installer (PyInstaller + Inno Setup) on every push touching `desktop/` or `tools/button/`, and publishes it as a GitHub Release `desktop-v1.0.<run number>`. |
| `desktop/app.py`, `desktop/ui.html`, `desktop/installer.iss`, `desktop/icon.*` | The desktop app: a local web server + an Edge/Chrome app window, Midnight theme. **Manual Bill** runs the engine on the PC; **Run in the cloud** dispatches the workflow. The frozen exe doubles as the Python interpreter for the helpers (`ehpa-billing-button.exe --py <script>`), so nothing else is installed on the PC. |
| `tools/button/billing_button_page.html` + `build_button_page.py` | The "ehpa Billing Button" page (https://claude.ai/artifact/5Eyw5K3ydS13uDHkR8JJyZ): trigger, dry/live, plan, report, history, pages grid, how it works. Rebuild: `python3 tools/button/build_button_page.py reports/button/latest.json out.html --app-build-url https://claude.ai/artifact/DecNZkNsoQ4V2c1gwLLqiq`. |
| `tools/button/build_outstanding_page.py` | The "Outstanding Claims" page (https://claude.ai/artifact/VNssV7RYwYrMrzvNwQtWwQ). `python3 tools/button/build_outstanding_page.py outstanding_claims.json out.html`. |
| `tools/button/fab.py` | Adds the two floating buttons (Run all billing, Open a billing chat) to a saved copy of any billing artifact. Idempotent. `python3 tools/button/fab.py in.html out.html`. |
| `tools/button/app_build_page.html` | The App Build page source. |
| `reports/button/` | The reports. `<stamp>.json` per run, `latest.json`, `outstanding_latest.json`. Counts, dollars, chart / visit / check ids only. |

## Steps and profiles

| Step | What runs (dry form in parentheses) |
|---|---|
| `columns` | `columns_scan.py` before -> `insp_bypass_advisories.py` (plan only) -> `unbilled_repair.py` (no `--live`) -> `payreasons.py --list` (`--unbilled --live` when live) -> `excl_dup_complete.py` / `excl_crossover_complete.py` per claim run that has rows -> `columns_scan.py` after |
| `era` | `era_list.py` before -> `era_post.py --all-unposted` (`--dry`) -> `era_clear.py` (`--dry`) -> `era_list.py` after |
| `cascade` | `void_rules.py` (`--dry`; skipped without `void_rules.json`) -> `precheck.py --days 3 --max 120` (skipped without a Stedi key) |
| `sweep` | `claim_status_sweep.py --min-age N --max 60 --carriers UNI20,BCBS` + `sweep_register.py` (Stedi; only when named) |
| `packages` | every `approved` item in `practices/ehpa/registers/approvals_pending.json` (or `--packages` ids): the package script dry, then live, then `status done` + `answer` in the register |
| `cred` | `cred_check.py` (NPPES, revalidation reminders, LEIE) |
| `money` | `pay_scan.py` when `patient_universe_*.json` exists, then `build_money.py` (only when named) |
| `outstanding` | `outstanding_claims.py --out outstanding_claims.json` |
| `denials` | `denials_refresh.py` (read-only, 10/13/2026): every patient on the unpaid list + every chart already on the Working Denials board is re-read with gettxhistory; every posted $0 line with a CARC is triaged with the board's table; each visit's live status (RESOLVED / WRITTEN-OFF / RESUBMITTED / OPEN) comes from payments, write-offs and the last bill date. Writes `reports/button/working_denials_latest.json` (chart + visit ids, no names, PHI-gated). The board's **Refresh from AMD** button dispatches `steps=denials`, watches the run, then pulls that file and re-renders in place; **Load latest snapshot** pulls it without a run. The columns and cascade profiles run it too, so the board is at most ~2 h stale. |

Profiles: `all` = columns, era, cascade, packages, cred, outstanding, denials. `columns` (the 2-hourly
cadence) = columns, era, packages, outstanding, denials. `cascade` (the nightly slot) = cascade, era,
packages, cred, money, outstanding, denials. `denials` = denials alone (the board's Refresh button).

```
python3 tools/button/run_all.py --mode dry --steps all                      # the default button press
python3 tools/button/run_all.py --mode live --profile columns               # the 2-hourly profile
python3 tools/button/run_all.py --mode live --profile cascade               # the nightly profile
python3 tools/button/run_all.py --mode live --steps packages --packages <id>
```

## One-time setup in GitHub (William)

Settings -> Secrets and variables -> Actions.

| Name | Kind | Value |
|---|---|---|
| `AMD_PSW` | secret, **required** | the POI0712 password. Never typed anywhere else. |
| `STEDI_API_KEY` | secret, optional | the Authorization header value Stedi shows. Without it the Stedi steps (precheck, sweep) are skipped. Each lookup costs money; the pre-check cache is kept between runs. |
| `BUTTON_SCHEDULE_MODE` | variable | `dry` (default when unset) or `live`. Applies to scheduled runs only; the button always sends its own mode. |
| `BUTTON_SCHEDULE_ENABLED` | variable | `false` switches the schedules off; anything else leaves them on. |

The token the pages and the desktop app use: a **fine-grained personal access token** limited
to this repository with **Actions: Read and write** (to start a run and read its status) and
**Contents: Read** (to read `reports/button/*.json` and, for the desktop app, to download the
scripts). It is saved in the page's browser storage or in the app's settings on the PC, never in
the repository.

## Schedules, and the Claude routines

| When (UTC) | Profile | Mode |
|---|---|---|
| :17 on the odd hours (01,03,...,23) | `columns` | `BUTTON_SCHEDULE_MODE` |
| 05:35 | `cascade` | `BUTTON_SCHEDULE_MODE` |

Scheduled runs are **dry until `BUTTON_SCHEDULE_MODE=live`**. Before setting it live, pause the
Claude 2-hourly backend billing routine (and the nightly cascade routine if the cascade profile
goes live) so two engines never write to AdvancedMD in the same hour. The :17 offset keeps the
two from starting at the same minute while both exist. The manual button has no such conflict:
William chooses the moment.

## The desktop app

1. Repository -> Releases -> the newest `desktop-v…` -> download `ehpa-billing-button-setup.exe`, run it. It installs under the user profile (no administrator prompt), puts **ehpa Billing Button** on the desktop and registers the `ehpa-billing://` link so the "Run on this PC" button on the Billing Button page can open it.
2. First open: Settings -> save the GitHub token, the AMD password and (optional) the Stedi key. They live in `%LOCALAPPDATA%\ehpa-billing\settings.json` on that PC only.
3. **Update scripts** downloads main; auto-update does it before every run. **Manual Bill** runs the engine on the PC (dry by default; live asks to confirm). Reports land in `%LOCALAPPDATA%\ehpa-billing\reports`. **Run in the cloud** dispatches the workflow with the saved token.
4. The helpers run from `C:\home\claude\unbilled` when it can be created, else `%USERPROFILE%\ehpa-billing\unbilled` with amd.py's three cache paths re-pointed in the workspace copy.

The first release appears after the desktop-build workflow runs on main (it runs by itself on
the merge, or Actions -> desktop-build -> Run workflow).

## Rules the engine keeps

- **One AdvancedMD login per run.** `.amd_login_lock` in the workspace stops every AMD step; the engine never retries a password (a second failure locks POI0712 and breaks the Claimocity feed).
- **Dry by default.** Live from a page or the app asks for confirmation; live on a schedule needs the variable.
- **No PHI in GitHub.** `tools/mirror/phi_gate.py` reads every report before it is written (counts-only fallback) and scrubs the helper logs before they are kept 14 days as a workflow artifact. Helper output goes to log files, never to the job log.
- **Secrets stay out of the repo.** Password and key come in through the environment; the workflow deletes `.session.json`, `.amd_cred.json` and `secrets/` at the end; the GitHub cache (era_details, registers, precheck cache) never carries them.
- **One run at a time**, a failed helper never stops the others, the helpers run exactly as committed.

## What the engine does not automate

It runs deterministic helpers. Anything that needs a judgement is counted under `waiting` in
the report for a chat session or William: a chart fix after a Stedi answer, a dx cascade on a
named chart, a hand-post, a package the register has not marked approved. The Mandatory
Approvals page still carries those decisions; once a card is approved, the next button press
applies it.

## Where to look when it breaks

| Symptom | Look | Usually |
|---|---|---|
| page says GitHub refused 401/403 | the saved token | expired, or missing Actions read-and-write |
| bootstrap failed `.amd_login_lock exists` / `AMD_PSW is not set` | report errors; the secret | no password or a failed login - do not press again until the password is confirmed |
| step `skipped: helper missing` | the step summary | the script is not on main |
| status `warn` with an error sentence | the step; the run's logs artifact (14 days) | one helper reported a problem; the rest ran |
| nothing happens for minutes, then it starts | Actions: queued | another run was in progress |
| Stedi steps skipped | bootstrap | no `STEDI_API_KEY` |
