# The Billing Button (set up 2026-10-11, William's order: "package all the billing routines and the nightly cascade in an automatic run, as they are written in GitHub, with a dashboard where I press one button and get reports - no mandatory-approval blocks")

## Since 10/23/2026 the button starts a Claude run

The big trigger on the ehpa Billing Button page ("Run all billing with Claude") no longer dispatches the
GitHub Actions engine. It fires the on-demand Claude scheduled task **trig_01S771Si8VJ8DvcwgHMHGYB5**
("ehpa Billing Button - full billing run (Claude)"; poke-only, no cron; model claude-fable-5-1; the
server gave it permission_mode `auto`), whose prompt is `nightly/button_run_prompt_v1.txt` - the full
2-hourly columns prompt (v12 + v13 insert) reframed for a button press: it works the board, every Claims
Center column, ERA posting, the cascade and the approved packages by the standing prompts, waits for any
approval the environment asks for (William 10/22: manual approvals during the run are fine), and lists
only a command refused outright under "Refused - for William".

* **How it is fired.** The page calls the viewer's Claude Code Remote connector:
  `mcp.callTool('Claude Code Remote','fire_trigger',{trigger_id, text})`, then watches
  `list_triggers` (recurring:false) every 20 s and shows the run bar "Claude is running the billing" with
  an "Open the session" link (`https://claude.ai/code/session_<id without cse_>`). Inside claude.ai no
  token is needed; the page declares `mcp` for `github` (get_file_contents, actions_list,
  actions_run_trigger) and `Claude Code Remote` (fire_trigger, list_triggers).
* **The brief** appended to the prompt on each press:
  `BUTTON PRESS <iso> · mode: live|dry · steps: <steps> · packages: <ids|none> · note: ehpa Billing Button`.
* **The report file.** The run writes `reports/button/<stamp>.json` + `latest.json` (schema
  `button-run/1`, with `"engine":"claude"` and `"trigger":"trig_01S771Si8VJ8DvcwgHMHGYB5"`), commits
  "button run <stamp> (Claude)" and pushes HEAD:main; the page draws it like any engine report.
* **The engine is secondary.** The GitHub `workflow_dispatch` path is still on the page as the small
  "Engine only · GitHub (no Claude)" button (and its schedules are untouched); "Run on this PC" (the
  desktop app) is unchanged.
* **The floating "Run all billing" button** on every billing page (tools/button/fab.py) now reads
  "Claude · columns · ERA · cascade · packages" and says the run may ask for an approval; it still opens
  this page at `#trigger`.
* **Refresh (10/23, William 00:33 ET).** Every page in the set carries a "↻ Refresh" pill at its top-right
  corner (tools/button/refresh_button.py): it calls the page's `window.__ehpaRefresh` hook (the boards
  re-read their store and the Drive inbox and re-render; this page re-reads the task's last run and the
  report; Outstanding Claims re-pulls the snapshot) and shows "refreshed HH:MM"; a page with no loader
  reloads instead. The older reload-only Refresh button (10/22) is replaced by it.

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
| `era` | `era_list.py` before -> `era_post.py --all-unposted` (`--dry`) -> per posted check `era_co45_relink.py <check> --meta` (audit; `--live` where it finds lines) -> `era_fallback_0913b.py --checks --stamp` (`--dry`, then live) -> `era_clear.py` (`--dry`) -> `wo_reversal_post.py` when era_clear wrote reversal rows (`--dry`, then live, then `era_clear.py` again) -> `era_list.py` after; every check still carrying money becomes a waiting line (11/7/2026) |
| `cascade` | `void_rules.py` (`--dry`; skipped without `void_rules.json`); since 11/10/2026 the pre-claim check `precheck.py` is not started here - the nightly insurance cascade routine runs it once a night |
| `sweep` | since 11/10/2026 nothing is started and nothing is bought: the nightly insurance cascade routine asks claim status by need on Sundays (`claim_status_sweep.py --go`, nightly/live/cascade.txt STEP 2); a press that names this step gets one line in the report |
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
| `STEDI_API_KEY` | secret, optional | the Authorization header value Stedi shows. Since 11/10/2026 no engine step starts a Stedi check of its own (the pre-claim check and claim status run in the nightly insurance cascade routine); the deceased-patient guard behind a rebill uses the key when it must ask Medicare. Each Stedi call costs money. |
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
named chart, a hand-post the fallback could not make, a package the register has not marked approved. The Mandatory
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

## FAST PATH - what a fresh container actually needs (learned on the 11/5/2026 run; William: "learn from this run and back up steps on the triple mirror to make this process quicker")

The 11/5 full run bootstrapped in 7 minutes and finished the billing work in 20 by skipping what every earlier run had
re-done. The prompt (nightly/live/billing_button.txt) still lists every step; this is the order and the shortcuts that
satisfy it with the fewest tool calls. Everything here is data-safe (no retyped bytes) and leaves the standing rules intact.

1. **Toolkit = the attached clone.** `tools/bootstrap/bootstrap_workspace.sh` and `ws_bundle.py` are on main under
   tools/bootstrap/ - copy them into /home/claude/unbilled/tools/ from the clone; never download them from Drive first.
   `bash tools/bootstrap_workspace.sh net` (AMD_OK / STEDI_CRED_MISSING is the normal answer), then
   `bash tools/bootstrap_workspace.sh layout /home/claude/effinger-billing-backend` restores the 1,300+ helpers, the registers
   (1,773 files from practices/ehpa/registers/), captured_calls.md, the needs list and the laterality log in one command.
2. **Skip the Drive state bundle until a fresh one exists.** The only workspace_state_* set on Drive (2026-09-18_1123UTC, 26 parts)
   is corrupt (part21) and carried registers only - main already has every register. Downloading it cost the 11/3 run an hour.
   Check `title contains 'manifest.json'` in "workspace mirror": a manifest newer than 9/18 = unpack it; none = say
   "state bundle skipped (9/18 set corrupt, registers from main)" and go on. patient_db/ and era_details/ fill from live reads.
3. **Only five Drive files matter at bootstrap**, found by exact title in "workspace mirror" (`title = 'x' or title = 'y'`
   in one search_files call - the folder listing pages 5 at a time and is useless): deceased_cache.json, pseudonyms.json,
   void_rules.json, precheck_cache.json (newest copy), plus any helper .py newer than the last run. Download each with
   download_file_content and decode it with `python3 -I tools/bootstrap/transcript_extract.py drive <fileId>=<path>` -
   the helper reads the connector's answer back out of the session transcript, so nothing is retyped (a result over the
   size cap lands in ~/.claude/projects/<slug>/<session>/tool-results/*.txt and the helper follows that pointer).
4. **Credentials the same way**: AMD password = Gmail thread 1866ce7e2233e4c0, Stedi key = thread 1a083035f566f9fb,
   GCS key = `subject:"claimocity gcs key"` -> `transcript_extract.py gmail-body <threadId>=secrets/gcs_key_mail.txt` then
   `claimocity_gcs.py --install-key`. Pam's facesheet photos: get_message RAW -> `transcript_extract.py raw-attachments
   <messageId>=inbox/pam` (byte-exact JPEGs; apply EXIF rotation and crop/upscale the insurance block before reading it).
5. **Cross-container guard in one search**: `parentId = '<chat history>' and title contains '<today>T0' and title contains 'START'`.
6. **Board in three cheap reads**: items where `updated >` the last run's stamp; items where `status == claude and updated >
   <3 days ago>` (the 11/5 read was 18 rows / 110k tokens - most already settled by the 11/2 runs, so verify LIVE before
   acting: brinson's I10 and brown-lisa's TRI05 were already on the charts); drops where status == new; denials commands
   where status == queued; meta/drive_sync once (its applied map is the only reason to trash inbox files).
7. **Columns**: `columns_scan.py before` is the login; trust its list sections, not the overview (the overview said Unbilled 27,
   the list had 1). Write helpers used this run: `freq1_visit.py reroute <vid> <cid> <order> <seq>` (dry, then live),
   `unbilled_release.py <pid>:<vid> --stamp <stamp> [--live]`, `ins_update.py <pid> <insid> sequence=<order>`.
8. **ERA**: `era_post.py --all-unposted --dry` is the whole list read (0 checks = done; no need to fetch details).
9. **Report + mirror**: a dated report_<mmdd>.py writes the button-run/1 file from outstanding_claims.json /
   working_denials_latest.json; phi_gate both copies; `git rebase --autostash origin/main` then `mirror.py sync`.

Standing lesson behind all of it: never let the model retype a connector payload - decode from the transcript.
