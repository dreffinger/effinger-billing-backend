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

Registers, scan summaries and run artifacts copied into `practices/` and `nightly/runs/` used to reach GitHub ungated (`git add -A` after only the registry and helpers were gated): the 9/30 payreason registers carried AMD `LAST,FIRST` names, a 10/3 digest named a patient, 271 reads carried member ids. Now `mirror.py` runs `python3 tools/mirror/phi_gate.py tree .` before `git add -A`: every changed or untracked text file is scrubbed in place (map names -> pseudonyms; any other `LAST,FIRST` value, `LAST,FIRST (pat N)` token or `last-first-<amdid>` slug -> `[name]`; MBI / SSN / ICN / member ids / DOB -> placeholders; code files keep their tokens), and a run digest, needs list / needs section or run report is taken back out of the tree (`DRIVE ONLY` in the output) - those are prose about patients and live on Drive only. `phi_gate.py tree <file>` gates a single file before a lone commit; `--all` rescans every file (the one-time scrub). `payreasons.py` and `columns_scan.py` write no patient name at all since 10/6. `rebill_log.jsonl` is copied with overwrite and merges `union`. A stale Drive-overlaid copy of the seven protected helpers (amd, resave, freq1_visit, move_to_ins, ins_update, dx_primary_fix, approval_submit - plus payreasons and columns_scan) never overwrites `scripts/helpers/`: `mirror.py` checks each one's marker before copying. Self-test: `python3 tools/selftest/test_phi_tree.py`.

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
python3 tools/mirror/mirror.py status      # what would be pushed, is the collection current
```

`phi_gate.py` exits 2 and the sync stops if an MBI, SSN, ICN, DOB, member number, token or key would leave the workspace. A "possible patient name" warning means add the name to `secrets/pseudonyms.json` (then upload that file to `workspace mirror`) and rerun. **New registry entries should not carry patient names at all** — write the AMD chart id (`patNNN`) instead; the gate is the backstop, not the plan.

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
