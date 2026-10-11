# Approvals loop (set up 2026-10-01, William's order: "approve the billing to run as continuously as possible without delays")

The scheduled billing runs are auto-mode routines, and the permission classifier refuses
AdvancedMD writes in them (see ROUTINE_PERMISSIONS.md). Every write a run could not make
becomes a *package* that William approves with one tap; the writes themselves run in the
chat session "Nightly insurance cascade" (session_01JYK9QNpG4udFd3o6dqCupt) in ask mode.

## Pieces

| Piece | What it is |
|---|---|
| `practices/ehpa/registers/approvals_pending.json` | The source. Each run appends `items[]` (`id`, `stamp`, `at`, `cmd`, `reason`, `what`, `dollars`, `evidence_file`, `evidence`, `ui`, `status` waiting/done, `answer`). |
| Mandatory Approvals page | Artifact https://claude.ai/artifact/HuYd2bSm2NxkFgYRqra7wR. Database collection `approvals`, one document per package, Approve / Decline buttons. Card anchors: `#<package id>`. |
| Routine "billing approvals sync" (`trig_01Bqg5n4YZZG55SULBq79JKJ`) | Hourly at :15, fires into the cascade session. Copies new waiting packages onto the page, emails William the card links (subject `mandatory approval writes - N new to approve`) plus a push, alerts him when a card is approved, marks cards done when the source says applied. Reads, page database, Gmail and push only. |
| Routine "mandatory approval writes" (`trig_01YUgjTTz71pE9Nh65mMUeGY`) | 8:51 AM / 8:51 PM ET reminder into the same session: what is waiting, what is approved, links to the page. |
| The apply step | William opens the cascade session in ask mode and says `go`. The session reads the page database, applies only the packages marked approved, one package per call, each AMD write arriving as a prompt he answers; then records: source item `done` + `answer`, page card `done`, board inbox file, digest addendum, commit. |

## Rules
- No SSNs, MBIs, member ids or policy numbers on the page, in emails or pushes. Chart ids and dollars are fine.
- Declined cards are left alone; waiting cards are never applied without his word.
- The sync never retries a refused call; it notes it and finishes.
- `.claude/settings.json` allows the sync's tools (git read commands, ArtifactData, Gmail search + send, PushNotification) so the hourly firing never stalls on a prompt in the ask-mode session.


## Any session, immediately (William 10/6/2026: "put this through the approval process ... so as to not slow down the billing" / "save that in a code to automatically do")

A chat session (or a routine) whose AdvancedMD write the classifier refuses no longer waits for the hourly sync. One command,
`scripts/helpers/approval_submit.py`, does the whole submission:

```
cd /home/claude/unbilled && python3 approval_submit.py --stamp <run stamp> --items <items.json> --repo /home/claude/effinger-billing-backend --push-main
```

`items.json` = one entry per chart/decision: `letter`, `command` (the exact refused command, with a `--only <letter>` selector when one
script carries several charts), `reason` (the classifier's words), `what`, `dollars`, `ui`, `evidence` (+ optional `evidence_file`).
The script (1) runs the privacy gate (no SSN / MBI / member / policy ids - exit 2 and nothing written on a hit), (2) appends the
items to BOTH `registers/approvals_pending.json` copies (workspace + repo, idempotent by id), (3) writes the page cards file
`outbox/approval_cards_<stamp>.json` (collection `approvals`, one `set` per card in the page's shape), (4) writes the email
(`outbox/approval_request_<stamp>.md`, subject on line 1: `APPROVAL NEEDED - backend billing run <stamp> (<n> AdvancedMD writes
refused)`) with the card links `https://claude.ai/artifact/HuYd2bSm2NxkFgYRqra7wR#<id>`, the push text (`outbox/approval_push_<stamp>.txt`),
and (5) with `--push-main` commits the register and pushes the branch + a fast-forward of `main`. It then prints the three connector
calls the session makes next: ArtifactData batch (the cards file), Gmail send_message to dreffinger@gmail.com (subject + body files),
PushNotification (the push file). If the session cannot make them, the hourly "billing approvals sync" picks the waiting items up from
`main` within the hour. Approval and the re-attempt work exactly as before: William taps Approve on the card (email replies are no longer read - 10/6/2026 review),
and the next run re-attempts that one command once, citing the id.

Rules for the refused script itself: give every multi-chart action script a `--only <letters>` selector so each card can be approved,
declined and re-attempted on its own; a session script whose comments carry patient names stays OUT of the repo (phi_gate) - it is
uploaded to Drive `workspace mirror` (PHI-OK) and the card's command names that file, as the 9/30 `unbilled_repair.py` card did.

## Permanent in the routines (William 10/6/2026: "make this fix to the routine permanent so it doesn't delay billing - use the programs to send emails to link to approval buttons and push notification with link")

The approval loop now lives in the routine prompts themselves (it had only been in repo docs/inserts; the live 2-hourly routine was still v7):

| Routine | What changed |
|---|---|
| Backend billing run, every 2 hours (`trig_01QRqT8KB4Q1H9EyYRG4NBKX`) - `nightly/columns_task_prompt_ehpa_cloud_v11.txt` | Step **0g MANDATORY APPROVALS**: (1) it is the ONLY routine that applies approved cards (plus William's own "go"), as the LAST step of its run (one classifier refusal taints every later write of a session), at most ONCE per card (a repeat refusal is noted and only William's "go" applies it after that), each card CLAIMED first (note "applying <stamp>" pushed to main), its charts re-read live (already in place -> recorded done, never re-run), its dry run compared with the card; (2) any write refused during the run goes to William that same minute through `approval_submit.py` - HTML email with an *Open Mandatory Approvals* button and one *Review & Approve* button per package (`page#<id>` opens that card's Approve / Decline buttons), a push whose text ends with the link, the page cards, and the register pushed to `main`. Step **0i** LEARN FROM EACH OTHER, step **5(b2)** UNI20/BCBS before 5/1/2026 (the only sender; a 277 claim-status check first, only NOT ON FILE visits are sent), and in STANDING FLAGS the ONE REBILL PER VISIT rule and the TIMELY-FILING WATCH. File: `nightly/columns_task_prompt_ehpa_cloud_v12.txt` (v12 also folds in the v8/v9 rules of 9/21-9/30 that the live routine never received). |
| Nightly insurance cascade (`trig_01XVrVN9dpSdvAbB1ZrsAzFU`) - `nightly/insurance_cascade_prompt_v3.txt` | Submits its own refused writes the same way (run kind "nightly cascade"); never applies approved cards and never sends a UNI20/BCBS pre-5/1 visit (it overlaps the 05:10Z billing run) - it posts answers and writes off timely filing; ONE REBILL rule; LEARN step. The total unpaid audit (`nightly/total_unpaid_audit_prompt_v2.txt`) works the same way. |
| Billing approvals sync, hourly (`trig_01Bqg5n4YZZG55SULBq79JKJ`) - `nightly/approvals_sync_prompt_v3.txt` (v3 = v2 + the EMAIL BUTTON STANDARD below; live on the routine since 10/11/2026 21:23Z) | Every push ends with the link (one package -> its card, several -> the page); the email's links are styled as buttons; "approved" alerts say the next billing run applies them; a card the run could not apply ("refused again") gets one push + email: say go in the cascade session. |
| Mandatory approval writes reminder, 8:51 AM/PM ET (`trig_01YUgjTTz71pE9Nh65mMUeGY`) - `nightly/approvals_reminder_prompt_v3.txt` (v3 = v2 + the EMAIL BUTTON STANDARD below; live on the routine since 10/11/2026 21:28Z) | One alert line (refused again > approved > waiting) ending with its link; on "go" the session CLAIMS each package on main exactly like the billing run (so the two never apply one card twice), re-reads its charts live and skips anything already applied. |

So an approval now costs William one tap: the email or push arrives the minute a write is refused, the link opens the card's Approve button, and the next billing run (at most 2 hours later) applies it after its ERA posting - or the cascade session on "go" if he wants it now (or if the run reports it refused again).

Code made permanent with it (all in `core/` and `scripts/helpers/`, proven offline by `tools/selftest/test_one_rebill_and_approvals.py`): `amd.rebill_charge` one rebill per VISIT + sequence per script run (a repeat answers 204 "SKIPPED", nothing sent; a later run is never blocked; every rebill logged to registers/rebill_log.jsonl), `resave.set_insorder` (visit order, no rebill), `freq1_visit.reroute` (order + ONE freq-1 rebill), `move_to_ins.move(..., rebill=False)`, `ins_update.update` (patient order through an active plan, verified), `approval_submit.py` (HTML buttons + linked push).

## 10/7/2026 - applying in the cascade session (William "Go apply" / "finish all billing tasks now")

- The apply step runs in the session William types in, switched out of auto mode (ask / default): every AdvancedMD write is a permission prompt he answers; the auto-mode classifier refusals of the 0510Z / 0710Z runs do not recur. Do NOT spawn a child session on "Start it" - it blocks on its own AskUserQuestion (a relayed "Start it" is not his go) and was archived.
- Before the first card: `git checkout -B <branch> origin/main` (main was rewritten 10/6), copy main's protected helpers (scripts/helpers/{amd,resave,move_to_ins,freq1_visit,payreasons}.py) over /home/claude/unbilled, stage the card scripts from scripts/helpers/, and rebuild any register the card needs that never reached main (the 0510Z inflated-lines register -> scan_inflated_1007.py).
- Dry-run every card, apply one card at a time in the order the page lists, verify live, then: page card -> done (note = what was written, pinned if_version), practices/ehpa/registers/approvals_pending.json -> done with the answer (the merge script in the chat transcript / approval_submit's register shape), one summary email to William (chart ids and dollars only), lessons -> docs/SHARED_LESSONS.md, helpers + registers -> the repo on the session's branch + PR, digest -> Drive chat history.
- When a card's mechanism cannot run (10/7: processed ERA checks, no remit), a proven alternative that reaches the SAME approved outcome within the card's dollars is applied and the card's note says so; a different outcome needs a new card.

## 10/9/2026 - nine cards applied on "go" after two backend refusals (William approved all nine on the page 19:16Z)

- The 1910Z run's register CLAIM commit and the 2110Z run's first approved write were refused by the auto-mode classifier; the sync alerted (push 20:16Z, Gmail 21:16Z) and William said "go" here at 22:09Z. Everything then ran in this session in ask mode, one package per call: 7 old-claims cards (741 visits, 993 posted actions, $42,835.12, 0 faults, 22:13-23:13Z) + the two Humana ERA cards ($213.64 paid + $106.36 WOINS + $87.20 WOCAID2ND; the dismiss card was a no-op).
- Order of work that is now the recipe: (1) `git worktree add --detach <scratch>/main-wt origin/main`, note "applying <stamp> (go)" on every approved item, commit the register alone, `git push origin HEAD:main`; (2) refresh the seven protected helpers + the card scripts + the facts registers (`practices/ehpa/registers/old_claims_disposition_<stamp>.json`, `era_checks_before_*.json`, `tf_writeoff_watch.json`) from origin/main into /home/claude/unbilled, cache the ERA details the card scripts open (`era_post.details(<checkid>)`), make one XML read so the cached AMD token relogins once; (3) dry-run the smallest package; (4) apply one package per call (over ~100 visits: `run_in_background`), then `old_claims_twocode_fix.py --only <pkg>` (--dry, then --live) whenever the apply log has `SKIP ... already posted` lines; (5) after each package: status done + answer in main's register (own commit, pushed HEAD:main, times from the apply register's `items[].at`), the page document (pinned if_version), the branch register as a union; (6) a final live re-read of every touched visit; (7) lessons, this section, the digest, the registers and the helper on the PR branch, Drive mirror, PR body.
- The 2-hourly run that fires during a go (2310Z) reads the "applying ... (go)" notes and leaves the items alone; the next hourly sync sees done both places and reports no change.
- Verification 23:14-23:29Z: all 741 old-claims visits re-read live (945 touched charges) - patient balance 0 everywhere after 9 plan residuals ($694.55) were moved back from the patient balance; 16 charges ($1,266.39) keep the plan's intentional residual on the insurance balance for the secondary payer. Register: practices/ehpa/registers/old_claims_verify_1009.json.

## 10/11/2026 - one card applied on "go" while it still read waiting; the invisible email buttons

- A-2026-10-11T0110Z-A ($0.00, the 0110Z run's ERA-dismiss of two settled Humana NO-PAY checks, refused by the auto-mode classifier as "Real-World Transactions"): William said "go" here at 03:40Z with that card the only one pending and nothing approved on the page - his word here is the approval. Claimed on main (239413b), helpers refreshed from main, era_new_2026-10-11T0110Z.json + the dry evidence staged, era_details cached through era_post.details after one XML read relogged the 29-hour-old token; dry run (1 + 9 $0 lines recorded, the 4 ERA-posted lines already off the remit, nothing unsettled), then `era_dismiss_settled_1011_0110.py 1053084 1053085 --live`: both dismissed 03:44Z (HTTP 200 issuccess), unposted list = only the held Florida Blue check 1052906. Done on main (1f1cad6), the branch register (union), the workspace copy and the page (answeredBy "William (go in the cascade session)").
- The run's 01:36Z email carried the Open Mandatory Approvals and Review & Approve links, but Gmail strips the `background:` shorthand from inline styles, so the buttons arrived as white text on white. Fix in scripts/helpers/approval_submit.py: `background-color:` (longhand survives). The backend runs send the fixed email once this branch is merged to main; the hourly sync's own emails use background-color from now on.

## EMAIL BUTTON STANDARD (William 10/11/2026: "in the approval requests sent by all billing project tasks and routines ... fix that")

- Every approval-request email - approval_submit.py (backend billing run, nightly cascade, total unpaid audit, chat sessions), the hourly approvals sync's "N new to approve" and "approved, ready to apply" mails, and the twice-daily "mandatory approval writes" reminder - carries one blue "Open Mandatory Approvals" button to the page and one green "Review & Approve" button per package to that card (page#<id>), as inline-styled anchors using the LONGHAND `background-color:` (page #0163aa, card #1b8037; white bold text, padding 12px 20px, border-radius 8px, no underline). Gmail's sanitizer strips the `background:` shorthand, so a shorthand button arrives as white text on white - invisible (the 10/11 01:36Z and 07:57Z mails). A send is checked for `background:` before it goes out.
- The standard lives in scripts/helpers/approval_submit.py (html_email) on main, in nightly/approvals_sync_prompt_v3.txt and nightly/approvals_reminder_prompt_v3.txt (the stored routine prompts, updated on the routines 10/11/2026), and in docs/SHARED_LESSONS.md (2026-10-11T0350Z, 1730Z). A helper fix reaches the 2-hourly run only from main (precondition 0e2 copies scripts/helpers over the workspace).
- 10/11/2026 22:20Z audit of every routine on the account (seven pages of list_triggers): the only senders of approval requests are the approval_submit.py users (2-hourly backend billing run, total unpaid audit, the cascade v3 prompt file) and the two self-sending routine prompts above - all on the standard. `git grep 'background:'` on main finds only approval_submit.py's docstring and the artifact `<style>` of old_claims_review_page.py (a page, not an email). The morning money & posting report, weekly practice metrics, compliance calendar, credentialing inbox watch, Restore check and board-certification check send no approval requests; the 9/6-9/12 routines that predate the loop are disabled. Gap reported to William: the live Nightly insurance cascade routine (`trig_01XVrVN9dpSdvAbB1ZrsAzFU`) still runs the pre-10/6 prompt without the Mandatory Approvals step (its refusals go to its report only), and the live 2-hourly run's prompt text predates v12 (its approval mail comes from approval_submit.py, so its buttons are fixed) - updating either routine needs his word.
- The page's "Mark done" button (shown on an approved card) writes status done with answeredBy "page" and does NOT change the register on main: 10/11/2026 21:29Z William marked A-2026-10-11T0510Z-A and A-2026-10-11T0710Z-A done one minute after the "ready to apply" alert while main's register still listed both waiting and no run had applied them. A sync never changes the register; the mismatch goes to William in the summary.
