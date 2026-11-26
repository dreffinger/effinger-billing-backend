# The triple mirror — GitHub · Postman · Drive

The project's memory lives in three places that are kept identical at the end of **every billing run** (the every-2-hours Claims Center task) and whenever William says "mirror" or "remember". Each copy has a different job:

| Copy | What it holds | Why it exists | PHI? |
|---|---|---|---|
| **GitHub** `dreffinger/effinger-billing-backend` — branch `main` (the record) and `claude/effinger-billing-backend-mirror-w74pqv` (what the Claude project syncs from; pushed identical) | every script with its PLAIN ENGLISH header, `docs/captured_calls.md` (the registry, pseudonymized), `docs/api_vocabulary.json` (the growing vocabulary of every AMD/Stedi call), the generated Postman collection, this runbook, the practice config | the toolkit-of-record; a fresh container restores from it in one clone | **never** — `tools/mirror/phi_gate.py` swaps names for pseudonyms and refuses identifiers |
| **Postman** — collection "Effinger AMD — captured calls" | one runnable request per vocabulary entry, secrets as `{{variables}}` | William can run any call himself if Claude is down | never |
| **Google Drive** → `billing agent project files` (`1-AsLUHMaeqvHq-fqWKUVKKUU4Xkw6XTt`) | `captured_calls.md` with real names, `postman_effinger_amd.json`, `workspace mirror/` (helpers + `pseudonyms.json`), `github mirror/` (bundles when push is blocked), `aa claude folders → chat history` digests | the PHI-OK working copy the chat sessions and the scheduled runs both read first | yes — Drive only |

## The vocabulary is the source

`docs/api_vocabulary.json` is the machine-readable list of every captured call — folder, name, method, URL, headers, body template, the helper that wraps it, the date it was captured, and notes. **Add a call there** (one entry, `id` = `folder/slug`) and `tools/mirror/postman_build.py` regenerates the Postman collection; never hand-edit the collection. `docs/captured_calls.md` stays the narrative registry (dated sections, what was learned, what failed). A call is captured when it is in both.

## Shared registers and the lessons file (10/6/2026)

`practices/ehpa/registers/approvals_pending.json` and `practices/ehpa/registers/tf_writeoff_watch.json` are edited by several routines between mirrors: change them only in the `main` checkout right after `git pull --rebase --autostash origin main`, commit each change alone and push at once - never copy a workspace copy over them. `docs/SHARED_LESSONS.md` is append-only and merges with `merge=union` (`.gitattributes`, and apply_bundle.py's UNION list); run `python3 tools/mirror/phi_gate.py docs/SHARED_LESSONS.md docs/SHARED_LESSONS.md` before committing it. Every mirror commit is preceded by `git fetch -q origin main && git rebase --autostash origin/main` as its own command.

## The tree gate (10/6/2026)

Registers, scan summaries and run artifacts copied into `practices/` and `nightly/runs/` used to reach GitHub ungated (`git add -A` after only the registry and helpers were gated): the 9/30 payreason registers carried AMD `LAST,FIRST` names, a 10/3 digest named a patient, 271 reads carried member ids. Now `mirror.py` runs `python3 tools/mirror/phi_gate.py tree .` before `git add -A`: every changed or untracked text file is scrubbed in place (map names -> pseudonyms; any other `LAST,FIRST` value, `LAST,FIRST (pat N)` token or `last-first-<amdid>` slug -> `[name]`; MBI / SSN / ICN / member ids / DOB -> placeholders; code files keep their tokens: a pseudonym that lands in an identifier is written with an underscore, a quoted `'LAST,FIRST'` keeps its quotes and `%%`, a surname that is an ordinary word is never mapped in lowercase except as a whole dict key, and a lowercase surname as a whole word is mapped - the 10/6 afternoon fixes after the history rewrite found three helpers on main that had not compiled since the September gate). The 10/6 history-rewrite hunt added: a real first name beside a pseudonymized surname becomes `LAST,[first]` (JSON name fields, bare `LAST,FIRST`, board slugs `last-[first]-<id>`), `JR`/`SR` suffixes, single-part name fields, member / subscriber / policy ids in any alphanumeric shape (`[member id]`), DOB / DOD in every date shape (`[DOB]`), a 9-10 character MBI fragment (`[MBI]`), a patient's phone (`[phone]`), street addresses (`[address]`), `last_first_yyyymmdd` file names (`[name]_[DOB]`), and ordinary-word surnames as scanned-sheet file names, and a run digest, needs list / needs section or run report is taken back out of the tree (`DRIVE ONLY` in the output) - those are prose about patients and live on Drive only. `phi_gate.py tree <file>` gates a single file before a lone commit; `--all` rescans every file (the one-time scrub). `payreasons.py` and `columns_scan.py` write no patient name at all since 10/6. `rebill_log.jsonl` is copied with overwrite and merges `union`. A stale Drive-overlaid copy of the seven protected helpers (amd, resave, freq1_visit, move_to_ins, ins_update, dx_primary_fix, approval_submit - plus payreasons and columns_scan) never overwrites `scripts/helpers/`: `mirror.py` checks each one's marker before copying. Self-test: `python3 tools/selftest/test_phi_tree.py`.

## Order of operations at the end of a run

```
# 0. the PAT (Gmail thread "github claude token") -> secrets/github_pat.key, chmod 600, never anywhere else
# 1. pull first: download Drive captured_calls.md + captured_calls_additions_*.md into /home/claude/unbilled/
#    and Drive 'workspace mirror'/pseudonyms.json into secrets/  (another session may have added to both)
python3 tools/mirror/mirror.py sync "run <date> <time>: <what changed>"
#    -> merges additions into the workspace registry, PHI-gates it into docs/, refreshes scripts/helpers/,
#       regenerates the Postman collection, commits, pushes main + the synced branch (or writes a bundle)
# 2. Drive: rename old captured_calls.md -> captured_calls_<date>_pre-merge.md, upload the WORKSPACE copy as
#    captured_calls.md; upload docs/postman_effinger_amd.json and trash the previous copy (no duplicates);
#    upload changed helpers + secrets/pseudonyms.json to 'workspace mirror'
# 3. Postman connector: updateCollection with docs/postman_effinger_amd.json (createCollection once)
# 4. chat history: one dated digest
# 5. the ehpa Practice Database (William 11/1/2026): EVERY run (live or dry), ONCE per run - a run that already built in its
#    FEED step (the Button, the 6-hourly columns run) does NOT build again here (its own report is swept in by the next run); a
#    run that builds here does so BEFORE this sync, so the register below is committed with it -
python3 tools/db/practice_db.py build --run <run stamp>     # -> outbox/practice_db/<stamp>/writes_N.json + CALLS.md
#    then ONE ArtifactData call per writes file: action batch, url https://claude.ai/artifact/QrLJpUcpFv3cFRB9xHfLyk,
#    writes = that file's JSON array verbatim (billing_runs/<stamp> from reports/button, era_runs/<stamp>, feed_batches +
#    feed_checks when the run ingested feed files, snapshots/approvals-<stamp> and repo-<stamp>). Every id is new: no if_version.
#    quota_exceeded / invalid_argument -> report verbatim, never retry. The page reads only this database - no GitHub connector.
#    11/6/2026: the build also writes writes_sweep_<day>_N.json (one file set per day) - every engine report (reports/button, the
#    GitHub Actions workflow), ERA register, feed batch and cascade night (practices/ehpa/registers/cascade_runs/, written by
#    tools/db/cascade_record.py) of the last 7 days that main holds and the database does not yet; practices/ehpa/registers/
#    practice_db_written.jsonl (one JSON line per document, merge=union) records every id sent and is committed and pushed by the
#    run RIGHT AFTER its batch calls (CALLS.md prints the command) - never left for this sync's rebase to carry.
#    One batch per writes file, sweep files included; build ONCE per run. An answer naming a document that ALREADY EXISTS:
#    `python3 tools/db/practice_db.py trim --out <dir> --file <writes file> --exists <collection>/<doc_id>`, then send that file again
#    (repeat while another is named). A refused / approval-gated / errored call: `python3 tools/db/practice_db.py unsent --out <dir>
#    --file <writes file>` - its ids leave the register and the next run resends them. Never retry a call as it was.
python3 tools/db/neon_db.py load-writes --out outbox/practice_db/<stamp>     # 11/6/2026: the same documents into the PERMANENT STORE (Neon Postgres, raw.documents)
python3 tools/db/neon_db.py run-log --routine "<routine>" --stamp <stamp> --status ok --headline "<the report's one line>"   # ops.routine_runs
#    neon_db.py reads NEON_DATABASE_URL (an environment credential of the ehpa cloud environment) or, when absent, secrets/
#    neon_database_url written once per container from the Gmail thread 'neon database url' (like the other keys; never Drive,
#    never committed); one line each, never retried. 'no path to the database' = the container's egress policy blocks
#    the Neon hosts (tools/bootstrap/bootstrap_workspace.sh net probes them): report it; the artifact batches above still count.
python3 tools/mirror/mirror.py status      # what would be pushed, is the collection current
```

## The fourth copy: the ehpa Practice Database (11/2/2026)

The page https://claude.ai/artifact/QrLJpUcpFv3cFRB9xHfLyk ("ehpa Practice Database", formerly Claimocity Feed Monitoring) keeps
the artifact's own document database. `tools/db/practice_db.py` turns the PHI-light files on main into documents (collections
`feed_batches`, `feed_checks`, `billing_runs`, `era_runs`, `snapshots`, `practice`), writes them as files and prints the ArtifactData
batch calls; the run makes those calls. Documents are keyed by run stamp so nothing is ever overwritten and no version pinning is
needed. Viewers read the page with no connector or prompt; only the owner and Claude sessions write. The old GitHub-read path is gone.

**Every scheduled run on the page (11/6/2026).** The page's "Nightly insurance cascade" chart reads `cascade_runs` (one document per night: at, date,
checked, changed, dollars, done, note); its "Scheduled billing runs" table reads `billing_runs` + `feed_checks` + `era_runs` + `cascade_runs` by Eastern
day. Two things keep them moving: the nightly cascade's STEP 5b (`nightly/live/cascade.txt`) records its night with `tools/db/cascade_record.py`
(`practices/ehpa/registers/cascade_runs/<stamp>.json`, chart ids and dollars only - it refuses a name), and every `practice_db.py build` SWEEPS main
for the GitHub Actions engine's reports (`reports/button/<stamp>.json` - the engine runs 12 times a day and writes no database document itself),
ERA registers, feed batches and cascade nights of the last 7 days that the database lacks. `practices/ehpa/registers/practice_db_written.jsonl`
(one JSON line per document: collection/doc_id, when, by which run; 45 days kept; `merge=union` so two runs' lines merge) is the never-send-twice
register: a `set` of an id the database already holds fails the whole batch, so nothing another run sent is emitted again (a rebuild of the same
run stamp re-emits that run's own files). Every run commits and pushes the register right after its batch calls - never left uncommitted for a
later rebase to carry, because an unreadable register fails every build closed. When an answer still names a
document that already exists (the register had fallen behind), `practice_db.py trim` drops that entry and the file is sent again; a call refused,
approval-gated or errored is taken back out with `practice_db.py unsent` so the next run resends it. Sweep files are cut per day so a collision
touches one day's file.

The other billing and credentialing pages are copied into the same database by the daily **practice database sync**
(`nightly/practice_db_sync_prompt_v1.txt`, a scheduled task William creates in the UI): `ArtifactData list ... out_dir` saves each
page's collections as files, `Artifact read ... path index.html` saves the page and `tools/db/artifact_embedded.py` pulls the
dataset a report page carries inside its HTML, then `tools/db/artifact_copy.py` packs them into `artifact_copies/<page>-<collection>-<stamp>`
(+ `.p2..` parts over 200 KB), one `artifact_index/<page>-<stamp>` per page that changed and one `sync_runs/<stamp>` per firing.
The register `practices/ehpa/registers/practice_db_copies.json` (ids, counts, sha256 only) is what makes it cheap: a collection whose
content did not change is not copied again, and `--prune-plan 30` (1st of the month) deletes old copies that are no longer the newest
of their collection. The saved out_dir files carry patient names and stay under /home/claude/unbilled - never a commit, never Drive.

`phi_gate.py` exits 2 and the sync stops if an MBI, SSN, ICN, DOB, member number, token or key would leave the workspace. A file whose name carries `.unreadable-` (a deceased cache that could not be read, kept by dg_drive.py) is moved out of the tree before anything else: the line `KEPT OUT OF THE TREE (holds days of death - Drive only): <file> -> <where it lies now>` means upload that file to `workspace mirror` under its own name at once (its folder does not outlive the run) and say the line at the top of the report; `NOT KEPT OUT OF THE TREE: ...` means the gate ended 2 and nothing was committed. A "possible patient name" warning means add the name to `secrets/pseudonyms.json` (then upload that file to `workspace mirror`) and rerun. **New registry entries should not carry patient names at all** — write the AMD chart id (`patNNN`) instead; the gate is the backstop, not the plan.

## When GitHub push is blocked — leave a PACKAGE; the routine applies it (William 9/23/2026)

The session's git proxy only injects credentials for repositories in that session's authorized sources. A push that answers `403 … not in this session's authorized repository set` is policy, not a fault, and it must never mean a lesson stays out of the repo. `mirror.py` (its `bundle()` fallback) writes a **package** to `/home/claude/unbilled/outbox/`:

* `effinger-billing-backend_<date>[_<slug>].bundle` — a THIN bundle (`origin/main..HEAD`; `--all` when origin/main is unknown)
* the same bundle as `.b64` TEXT (Drive text uploads survive; binaries download corrupt through the connector — and a text upload can still flip characters, which is what the sha256 catches)
* `…manifest.json` — sha256, byte count, base/head commits, the commit list, and the exact apply command

The session then (1) `project_write`s the `.b64` as the project doc `mirror/outbox/<stem>.bundle.b64` (with `local_path` — byte-exact, never inline; that copy is for a CHAT session that bootstraps without github.com), (2) uploads to Drive `github mirror` (`1yr8X30h01-tPa0swclvtBFdAisiHzgJ8`) the manifest as `PACKAGE_<stem>.manifest.json`, the `.b64` as PARTS `PACKAGE_<stem>.bundle.b64.partNN` (≤45 KB of text each — `mirror.bundle()` writes them; one connector upload per part, read each back and compare its sha256 from the manifest before moving on), and a loose `PACKAGE_apply_bundle.py` when `tools/mirror/` is not in main yet — **the 2-hourly routine cannot read project docs (9/23 1110Z run: "the .b64 lives only in the Claude project doc, which this routine cannot read: package LEFT"), so Drive must carry the bytes** — and (3) reports "GitHub push blocked — package on Drive (N parts) + project". Nobody waits for William.

**GITHUB INBOX (the 2-hourly routine, at the start of every run, before its own work):** list Drive `github mirror` for `PACKAGE_*.manifest.json` whose sha256 is not in `practices/ehpa/registers/bundles_applied.json`; for each, download its parts `PACKAGE_<stem>.bundle.b64.partNN` (text; the manifest lists them with a sha256 each) — or the single `.b64` for an older package — and `PACKAGE_apply_bundle.py` when `tools/mirror/apply_bundle.py` is not in the clone, and run

```
python3 tools/mirror/apply_bundle.py <part01> <part02> ... --sha256 <manifest sha256>     # concatenates the parts (or takes one .b64), decodes, verifies, pulls main, records it
git push origin main && git push origin HEAD:<synced branch>                     # the routine's session has push rights
python3 tools/mirror/mirror.py sync "apply package <stem>"                       # Postman regenerated, Drive copies, digest
```

then rename the Drive manifest `APPLIED_<stem>.manifest.json` (and the parts / any `.b64` beside it). If `tools/mirror/apply_bundle.py` is not in the clone yet (the first package carries it), do the same by hand: `base64 -d` → `git bundle verify` → `git pull <bundle> main`. A sha256 mismatch or a merge conflict leaves the package where it is and goes in the run digest for William (exit 2 / 3). The register keeps every applied package (sha256, source, HEAD after), so re-listing the folder never re-applies one. William can still push a package himself from his machine (`git pull <bundle> main && git push origin main`) — that is the fallback, not the plan.

The permanent fix is to add the repo to every scheduled task's sources so runs push directly. Reading (clone with `https://x-access-token:<PAT>@github.com/...`) works from every session; **clone `main` explicitly** — the repo's default branch is the synced branch, not `main`.

### When GitHub is blocked for READ too (proven 9/10/2026 nightly)

The Claude project attached to the billing sessions keeps a copy of the latest complete bundle as the doc `mirror/outbox/effinger-billing-backend_<date>.bundle.b64` (plus `mirror/tools/*.py` and `mirror/MIRROR.md`). `project_read` that doc, base64-decode it, then `git clone --branch main <bundle> /home/claude/effinger-billing-backend` — the whole toolkit comes back without touching github.com. Overlay the newer helpers from Drive `workspace mirror` (amd.py with the compat shims, void_rules.json, payments_by_carrier.json, pseudonyms.json → secrets/) and pull the registry + additions from Drive as usual. Every run that ends with a blocked push should refresh that project doc with its new bundle (`project_write` with `local_path`, which never truncates) and keep Drive `github mirror` copies as `.b64` TEXT (binary bundles download corrupt through the Drive connector; small incremental bundles are fine there).

## Restore a fresh container

```
bash scripts/helpers/github_restore.sh          # clones main -> /home/claude/effinger-billing-backend, scrubs the token
cp -n scripts/helpers/* /home/claude/unbilled/  # the working helpers
# then Drive 'workspace mirror' -> secrets/pseudonyms.json, and the registry from Drive
```

## Landing changes without William (11/2/2026)

William 11/2/2026: "make it permanent where I don't have to manually push anything." `mirror.py sync` now lands a run's commit on `main` by itself, in this order: (1) the PAT (`secrets/github_pat.key`, the routines' way) pushes `main` and the synced branch; (2) with no PAT, a Claude Code cloud session that has the repository attached pushes through the **session proxy**, which injects the repository's credential — `mirror.py` fetches `origin/main`, merges it (append-only files by union), pushes `main`, then the synced branch; (3) only when the proxy or GitHub refuses (403 "not in this session's authorized repository set", a protected branch) does it leave HEAD on the session's own branch upstream and write the PACKAGE to `/home/claude/unbilled/outbox/`. That package is a record, not a hand-off: no live routine prompt carries the GITHUB INBOX step any more (the last `practices/ehpa/registers/bundles_applied.json` entry is 10/4/2026; the 10/5–10/12 packages in Drive "github mirror" were never applied), so a package waits for the next session with GitHub access to run `tools/mirror/apply_bundle.py` and then `mirror.py sync`. Drive "github mirror" is the last resort only; GitHub `main` is the one record.

## Prompts by reference (11/2/2026)

On 11/2 the agent's scheduled-tasks tool refused to edit the stored prompt of a routine William had created in the claude.ai UI (`created_via http_api`), and a routine an agent creates cannot carry the repository or the connectors in this organization. So each billing routine's stored prompt is a short pointer (`nightly/live/_stub_<routine>.txt`: fetch `main`, read `nightly/live/<routine>.txt` in full, follow it) and the instructions live in `nightly/live/` — files `mirror.py sync` pushes to `main` by itself. Changing what a routine does = editing its file here + `mirror.py sync`; the next firing fetches `main` and follows the new text. The stored prompt also stops being bound by the 65,536-byte cap (the Billing Button's hit it on 11/2). See `nightly/live/README.md`. 11/7/2026: the Code routines API itself (`RemoteTrigger update` with the routine's full `job_config`, message text swapped, everything else re-sent as stored) does accept the change on those routines - the cascade, columns and feed stubs were pasted that way after it turned out only the Button's had ever been pasted; the README's table says since when. Diff the stored prompt against the live file before pasting: the columns texts had drifted (stored v8 11/5 vs the 11/2 file) and the file was synced first.
